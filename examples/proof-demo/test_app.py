import unittest
from unittest.mock import MagicMock
from io import BytesIO
import json
from app import CheckoutHandler

class TestCheckoutValidation(unittest.TestCase):
    def test_invalid_email_returns_error(self) -> None:
        handler = MagicMock(spec=CheckoutHandler)
        handler.rfile = BytesIO(b'{"email": "invalid-email"}')
        handler.headers = {"Content-Length": "27"}

        response_body = BytesIO()
        handler.wfile = response_body

        # Mock status response methods
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        # Run POST handler logic
        CheckoutHandler.do_POST(handler)

        handler.send_response.assert_called_with(400)
        res_data = json.loads(response_body.getvalue().decode())
        self.assertIn("error", res_data)

    def test_valid_email_returns_success(self) -> None:
        handler = MagicMock(spec=CheckoutHandler)
        handler.rfile = BytesIO(b'{"email": "ajat@autokeren.com"}')
        handler.headers = {"Content-Length": "31"}

        response_body = BytesIO()
        handler.wfile = response_body

        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        CheckoutHandler.do_POST(handler)

        handler.send_response.assert_called_with(200)
        res_data = json.loads(response_body.getvalue().decode())
        self.assertEqual(res_data["status"], "success")

    def test_real_http_integration(self) -> None:
        import threading
        import urllib.request
        import urllib.error
        from http.server import HTTPServer

        server = HTTPServer(("127.0.0.1", 0), CheckoutHandler)
        port = server.server_address[1]

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            req_data = json.dumps({"email": "valid@domain.com"}).encode("utf-8")
            req = urllib.request.Request(
                f"http://127.0.0.1:{port}",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req) as response:
                self.assertEqual(response.status, 200)
                res_body = json.loads(response.read().decode("utf-8"))
                self.assertEqual(res_body["status"], "success")

            req_data_bad = json.dumps({"email": "invalid"}).encode("utf-8")
            req_bad = urllib.request.Request(
                f"http://127.0.0.1:{port}",
                data=req_data_bad,
                headers={"Content-Type": "application/json"}
            )
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(req_bad)
            self.assertEqual(cm.exception.code, 400)

        finally:
            server.shutdown()
            server.server_close()

if __name__ == "__main__":
    unittest.main()
