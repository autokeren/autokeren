import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class CheckoutHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        
        try:
            data = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        email = data.get("email", "")
        # BUG: email validation is missing or accepts invalid formats
        # We will add the fix here:
        if not email or "@" not in email or "." not in email:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid email address"}).encode("utf-8"))
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "success", "message": "Checkout successful"}).encode("utf-8"))

def run(port: int = 8080) -> None:
    server_address = ("", port)
    httpd = HTTPServer(server_address, CheckoutHandler)
    print(f"Demo server running on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
