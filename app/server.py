from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
import sys
from typing import Any

from app.config import settings
from app.database import Database
from app.routes import ApiResponse, ApiRouter


MAX_REQUEST_BODY = 64 * 1024
logger = logging.getLogger("calculator_server")


class CalculatorHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        router: ApiRouter,
        allowed_origins: tuple[str, ...],
    ) -> None:
        self.router = router
        self.allowed_origins = allowed_origins
        super().__init__(server_address, CalculatorRequestHandler)

    def is_origin_allowed(self, origin: str | None) -> bool:
        if origin is None:
            return False
        return "*" in self.allowed_origins or origin in self.allowed_origins

    def handle_error(
        self,
        request: object,
        client_address: tuple[str, int],
    ) -> None:
        error = sys.exc_info()[1]
        if isinstance(error, (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


class CalculatorRequestHandler(BaseHTTPRequestHandler):
    server: CalculatorHTTPServer
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        self._handle_request("GET")

    def do_POST(self) -> None:
        self._handle_request("POST")

    def do_DELETE(self) -> None:
        self._handle_request("DELETE")

    def do_OPTIONS(self) -> None:
        origin = self.headers.get("Origin")
        if not self.server.is_origin_allowed(origin):
            self._send_response(
                ApiResponse(
                    status=403,
                    body={"success": False, "message": "Origin is not allowed"},
                )
            )
            return

        self._send_response(
            ApiResponse(
                status=204,
                body=None,
                headers={
                    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Max-Age": "86400",
                },
            ),
            origin=origin,
        )

    def _handle_request(self, method: str) -> None:
        content_length = self.headers.get("Content-Length")
        body: dict | None = None

        if content_length:
            try:
                body_length = int(content_length)
            except ValueError:
                self._send_response(self._bad_request("Invalid Content-Length"))
                return

            if body_length > MAX_REQUEST_BODY:
                self._send_response(
                    ApiResponse(
                        status=413,
                        body={"success": False, "message": "Request body is too large"},
                    )
                )
                return

            raw_body = self.rfile.read(body_length)
            if raw_body:
                try:
                    parsed_body: Any = json.loads(raw_body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self._send_response(
                        self._bad_request("Request body must be valid JSON")
                    )
                    return

                if not isinstance(parsed_body, dict):
                    self._send_response(
                        self._bad_request(
                            "Request body must be a JSON object"
                        )
                    )
                    return
                body = parsed_body

        response = self.server.router.dispatch(method, self.path, body)
        self._send_response(response, origin=self.headers.get("Origin"))

    @staticmethod
    def _bad_request(message: str) -> ApiResponse:
        return ApiResponse(
            status=400,
            body={"success": False, "message": message},
        )

    def _send_response(
        self,
        response: ApiResponse,
        origin: str | None = None,
    ) -> None:
        encoded_body = None
        if response.body is not None:
            encoded_body = json.dumps(
                response.body,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")

        self.send_response(response.status)
        if encoded_body is not None:
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded_body or b"")))

        for name, value in response.headers.items():
            self.send_header(name, value)

        if self.server.is_origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin or "*")
            self.send_header("Vary", "Origin")

        self.end_headers()
        if encoded_body is not None:
            self.wfile.write(encoded_body)

    def log_message(self, format_string: str, *arguments: object) -> None:
        logger.info(
            "%s - %s",
            self.address_string(),
            format_string % arguments,
        )


def create_server(
    address: tuple[str, int],
    database: Database,
    allowed_origins: tuple[str, ...],
) -> CalculatorHTTPServer:
    return CalculatorHTTPServer(
        address,
        ApiRouter(database),
        allowed_origins,
    )


def main() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    database = Database(settings.database_path)
    database.initialize()

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    server = create_server((host, port), database, settings.allowed_origins)

    logger.info("Calculator API listening on http://%s:%s", host, port)
    logger.info("SQLite database: %s", settings.database_path)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping calculator API")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
