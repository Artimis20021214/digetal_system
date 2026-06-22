import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# 記憶體內留言資料庫 (Prototype 模擬用)
# 注意：Vercel Serverless 環境為無狀態，休眠重啟後留言將重置
COMMENTS_DB = {
    "1": [
        {"timestamp": "2026-06-22 10:00:00", "user": "系統導師", "content": "歡迎在此提出 RMSSD 實作的相關問題。"}
    ],
    "2": [
        {"timestamp": "2026-06-22 10:00:00", "user": "系統導師", "content": "SDNN 的分母定義與傳統標準差不同，請留意。"}
    ],
    "3": [
        {"timestamp": "2026-06-22 10:00:00", "user": "系統導師", "content": "若 pNN50 計算出現型別錯誤，請檢查百分比轉換邏輯。"}
    ]
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """處理取得特定單元留言的請求"""
        parsed_path = urlparse(self.path)
        query = parse_qs(parsed_path.query)
        unit_id = query.get('unit_id', [''])[0]
        
        comments = COMMENTS_DB.get(unit_id, [])
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(comments).encode("utf-8"))

    def do_POST(self):
        """處理發布新留言的請求"""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
            unit_id = payload.get("unit_id")
            content = payload.get("content")
            
            if unit_id in COMMENTS_DB and content:
                new_comment = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "user": "匿名學習者",
                    "content": content
                }
                COMMENTS_DB[unit_id].append(new_comment)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "comment": new_comment}).encode("utf-8"))
            else:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "無效的單元ID或內容為空"}).encode("utf-8"))
                
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
