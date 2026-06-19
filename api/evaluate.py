import json
import math
import time
from http.server import BaseHTTPRequestHandler
from typing import List

# =====================================================================
# 基準生理訊號數據與微學習測資庫 (新增單元三測資)
# =====================================================================
MOCK_ECG_RR = [800, 850, 790, 830, 810]
EXPECTED_RMSSD = 45.0000
EXPECTED_SDNN = round(math.sqrt(464.0), 4)

# 單元三 (pNN50) 數學推論計算:
# 相鄰 RR 間期差值絕對值為: [|850-800|, |790-850|, |830-790|, |810-830|] = [50, 60, 40, 20]
# 其中嚴格大於 50 毫秒的差值有: 60 (共 1 個)
# 總差值數量為 4 個
# 預期百分比結果: (1 / 4) * 100 = 25.0%
EXPECTED_PNN50 = 25.0000

TEST_CASES = {
    "1": [
        {"input": MOCK_ECG_RR, "expected": EXPECTED_RMSSD}, 
        {"input": [1000, 1000, 1000], "expected": 0.0}, 
        {"input": [], "expected": 0.0}
    ],
    "2": [
        {"input": MOCK_ECG_RR, "expected": EXPECTED_SDNN}, 
        {"input": [900, 900], "expected": 0.0}, 
        {"input": [], "expected": 0.0}
    ],
    "3": [
        {"input": MOCK_ECG_RR, "expected": EXPECTED_PNN50},
        {"input": [900, 920, 910], "expected": 0.0}, # 差值均未超過50ms
        {"input": [], "expected": 0.0}
    ]
}

class AnalyticsState:
    total_submissions = 0
    perfect_submissions = 0
    total_error_accumulation = 0.0

# =====================================================================
# Vercel Serverless 請求處理引擎
# =====================================================================
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            req_payload = json.loads(post_data.decode('utf-8'))
            unit_id = req_payload.get("unit_id")
            student_code = req_payload.get("code")
            
            test_cases = TEST_CASES.get(unit_id, [])
            passed_cases = 0
            total_cases = len(test_cases)
            start_time = time.perf_counter()
            status = "Accepted"
            error_msg = None

            local_env = {"math": math, "List": List}
            
            try:
                compiled = compile(student_code, "<string>", "exec")
                exec(compiled, local_env)
                
                if "calculate_features" not in local_env:
                    raise AttributeError("在提交的程式碼中找不到指定的進入點函式 'calculate_features'。")
                    
                target_func = local_env["calculate_features"]
                
                for case in test_cases:
                    res = target_func(case["input"])
                    if abs(round(res, 4) - case["expected"]) < 1e-4:
                        passed_cases += 1
                        
                status = "Accepted" if passed_cases == total_cases else "Wrong Answer"
                
            except Exception as eval_err:
                status = "Compile/Runtime Error"
                error_msg = str(eval_err)

            end_time = time.perf_counter()
            execution_time_ms = round((end_time - start_time) * 1000, 4)
            error_rate = round(((total_cases - passed_cases) / total_cases) * 100, 2) if total_cases > 0 else 0.0

            AnalyticsState.total_submissions += 1
            AnalyticsState.total_error_accumulation += error_rate
            if status == "Accepted" and error_rate == 0.0:
                AnalyticsState.perfect_submissions += 1

            global_mastery_rate = round((AnalyticsState.perfect_submissions / AnalyticsState.total_submissions) * 100, 2)
            global_average_error_rate = round(AnalyticsState.total_error_accumulation / AnalyticsState.total_submissions, 2)

            response_payload = {
                "status": status,
                "error_message": error_msg,
                "execution_time_ms": execution_time_ms,
                "passed_cases": passed_cases,
                "total_cases": total_cases,
                "error_rate": error_rate,
                "global_mastery_rate": global_mastery_rate,
                "global_average_error_rate": global_average_error_rate
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload).encode("utf-8"))

        except Exception as system_err:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"伺服器內部錯誤: {str(system_err)}"}).encode("utf-8"))
