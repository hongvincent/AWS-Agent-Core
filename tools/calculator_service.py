"""
Calculator HTTP Service for AgentCore Gateway Testing

This implements the Calculator API defined in calculator_api.yaml
Can be run locally for testing Gateway integration
"""

import json
import logging
from typing import Any, Dict
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CalculatorHandler(BaseHTTPRequestHandler):
    """HTTP request handler for calculator operations"""

    def _send_json_response(self, status_code: int, data: Dict[str, Any]) -> None:
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_error_response(self, status_code: int, error_type: str, message: str) -> None:
        """Send error response"""
        self._send_json_response(status_code, {
            "error": error_type,
            "message": message
        })

    def _parse_request_body(self) -> Dict[str, Any]:
        """Parse JSON request body"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        return json.loads(body.decode())

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Handle POST requests"""
        try:
            path = urlparse(self.path).path

            # Parse request body
            data = self._parse_request_body()
            logger.info(f"Received {path} request: {data}")

            # Validate required parameters
            if 'a' not in data or 'b' not in data:
                self._send_error_response(
                    400,
                    "ValidationError",
                    "Parameters 'a' and 'b' are required"
                )
                return

            # Extract and validate numbers
            try:
                a = float(data['a'])
                b = float(data['b'])
            except (ValueError, TypeError):
                self._send_error_response(
                    400,
                    "ValidationError",
                    "Parameters 'a' and 'b' must be numbers"
                )
                return

            # Route to appropriate operation
            if path == '/v1/add':
                result = self._add(a, b)
            elif path == '/v1/subtract':
                result = self._subtract(a, b)
            elif path == '/v1/multiply':
                result = self._multiply(a, b)
            elif path == '/v1/divide':
                result = self._divide(a, b)
            else:
                self._send_error_response(
                    404,
                    "NotFoundError",
                    f"Endpoint {path} not found"
                )
                return

            if "error" in result:
                self._send_error_response(400, result["error"], result["message"])
            else:
                self._send_json_response(200, result)

        except json.JSONDecodeError:
            self._send_error_response(
                400,
                "ParseError",
                "Invalid JSON in request body"
            )
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            self._send_error_response(
                500,
                "InternalError",
                str(e)
            )

    def _add(self, a: float, b: float) -> Dict[str, Any]:
        """Add two numbers"""
        return {
            "sum": a + b,
            "operation": "addition",
            "inputs": {"a": a, "b": b}
        }

    def _subtract(self, a: float, b: float) -> Dict[str, Any]:
        """Subtract b from a"""
        return {
            "result": a - b,
            "operation": "subtraction",
            "inputs": {"a": a, "b": b}
        }

    def _multiply(self, a: float, b: float) -> Dict[str, Any]:
        """Multiply two numbers"""
        return {
            "product": a * b,
            "operation": "multiplication",
            "inputs": {"a": a, "b": b}
        }

    def _divide(self, a: float, b: float) -> Dict[str, Any]:
        """Divide a by b"""
        if b == 0:
            return {
                "error": "ValidationError",
                "message": "Division by zero is not allowed"
            }

        return {
            "quotient": a / b,
            "operation": "division",
            "inputs": {"a": a, "b": b}
        }

    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.address_string()} - {format % args}")


def run_server(port: int = 8000):
    """Run the calculator HTTP server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, CalculatorHandler)
    logger.info(f"Calculator service running on port {port}")
    logger.info(f"Endpoints:")
    logger.info(f"  POST http://localhost:{port}/v1/add")
    logger.info(f"  POST http://localhost:{port}/v1/subtract")
    logger.info(f"  POST http://localhost:{port}/v1/multiply")
    logger.info(f"  POST http://localhost:{port}/v1/divide")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()
