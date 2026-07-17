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

if __name__ == "__main__":
    unittest.main()
