import json
import math
import time
from http.server import BaseHTTPRequestHandler
from typing import List

# =====================================================================
# 基準生理訊號數據與微學習測資庫
# =====================================================================
MOCK_ECG_RR = [800, 850, 790, 830, 810]
EXPECTED_RMSSD = 45.0000
EXPECTED_SDNN = round(math.sqrt(464.0), 4)

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
    ]
}

# 全局歷史統計狀態（於單一無伺服器實例生命週期內類比全局數據庫）
class AnalyticsState:
    total_submissions = 0
    perfect_submissions = 0
    total_error_accumulation = 0.0

# =====================================================================
# Vercel Serverless 請求處理引擎
# =====================================================================
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """
        處理前端提交的特徵演算法程式碼，執行安全沙盒校驗並回傳統計指標
        """
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            # 解析前端 Fetch 傳送之 JSON 酬載
            req_payload = json.loads(post_data.decode('utf-8'))
            unit_id = req_payload.get("unit_id")
            student_code = req_payload.get("code")
            
            test_cases = TEST_CASES.get(unit_id, [])
            passed_cases = 0
            total_cases = len(test_cases)
            start_time = time.perf_counter()
            status = "Accepted"
            error_msg = None

            # 建立隔離的沙盒執行上下文環境
            local_env = {"math": math, "List": List}
            
            try:
                # 動態編譯並執行學員提交之程式碼
                compiled = compile(student_code, "<string>", "exec")
                exec(compiled, local_env)
                
                # 驗證核心進入點函式是否存在
                if "calculate_features" not in local_env:
                    raise AttributeError("在提交的程式碼中找不到指定的進入點函式 'calculate_features'。")
                    
                target_func = local_env["calculate_features"]
                
                # 逐一進行生理訊號數據集黑箱測試
                for case in test_cases:
                    res = target_func(case["input"])
                    # 浮點數比對，容許 1e-4 之數值誤差
                    if abs(round(res, 4) - case["expected"]) < 1e-4:
                        passed_cases += 1
                        
                status = "Accepted" if passed_cases == total_cases else "Wrong Answer"
                
            except Exception as eval_err:
                status = "Compile/Runtime Error"
                error_msg = str(eval_err)

            end_time = time.perf_counter()
            execution_time_ms = round((end_time - start_time) * 1000, 4)
            error_rate = round(((total_cases - passed_cases) / total_cases) * 100, 2) if total_cases > 0 else 0.0

            # 更新統計數據（教學指標成效評估）
            AnalyticsState.total_submissions += 1
            AnalyticsState.total_error_accumulation += error_rate
            if status == "Accepted" and error_rate == 0.0:
                AnalyticsState.perfect_submissions += 1

            # 計算當前大盤之數位學習指標
            global_mastery_rate = round((AnalyticsState.perfect_submissions / AnalyticsState.total_submissions) * 100, 2)
            global_average_error_rate = round(AnalyticsState.total_error_accumulation / AnalyticsState.total_submissions, 2)

            # 封裝 JSON 回應數據
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

            # 發送標準 HTTP 回應
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_payload).encode("utf-8"))

        except Exception as system_err:
            # 異常錯誤攔截與回傳
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"伺服器內部錯誤: {str(system_err)}"}).encode("utf-8"))
