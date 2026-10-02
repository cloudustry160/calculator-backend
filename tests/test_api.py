from __future__ import annotations

import json
import tempfile
import threading
import unittest
from urllib.parse import quote
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.database import Database
from app.server import create_server


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.database = Database(
            f"{cls.temporary_directory.name}/calculator-test.db"
        )
        cls.database.initialize()
        cls.server = create_server(
            ("127.0.0.1", 0),
            cls.database,
            ("http://127.0.0.1:5500",),
        )
        cls.server_thread = threading.Thread(
            target=cls.server.serve_forever,
            daemon=True,
        )
        cls.server_thread.start()
        host, port = cls.server.server_address
        cls.base_url = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=5)
        cls.temporary_directory.cleanup()

    def setUp(self) -> None:
        self.database.clear_history()

    def request(
        self,
        method: str,
        path: str,
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict | None, dict]:
        body = None
        request_headers = dict(headers or {})

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"

        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=5) as response:
                response_body = response.read()
                parsed_body = json.loads(response_body) if response_body else None
                return response.status, parsed_body, dict(response.headers)
        except HTTPError as error:
            response_body = error.read()
            parsed_body = json.loads(response_body) if response_body else None
            return error.code, parsed_body, dict(error.headers)

    def test_health(self) -> None:
        status, body, _headers = self.request("GET", "/api/health")

        self.assertEqual(status, 200)
        self.assertEqual(body, {"success": True, "status": "ok"})

    def test_create_calculation_and_list_history(self) -> None:
        status, body, _headers = self.request(
            "POST",
            "/api/calculations",
            {"expression": "(1+2)*3"},
        )

        self.assertEqual(status, 201)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["expression"], "(1+2)*3")
        self.assertEqual(body["data"]["result"], 9)
        self.assertTrue(body["data"]["createdAt"])

        history_status, history_body, _headers = self.request(
            "GET",
            "/api/history",
        )
        self.assertEqual(history_status, 200)
        self.assertEqual(len(history_body["data"]), 1)
        self.assertEqual(history_body["data"][0]["id"], body["data"]["id"])

    def test_failed_calculation_is_not_stored(self) -> None:
        status, body, _headers = self.request(
            "POST",
            "/api/calculations",
            {"expression": "2/0"},
        )

        self.assertEqual(status, 400)
        self.assertEqual(body["code"], "DIVISION_BY_ZERO")
        self.assertEqual(self.database.list_history()["records"], [])

    def test_delete_specific_history(self) -> None:
        _status, first, _headers = self.request(
            "POST",
            "/api/calculations",
            {"expression": "1+1"},
        )
        _status, second, _headers = self.request(
            "POST",
            "/api/calculations",
            {"expression": "2+2"},
        )

        delete_status, delete_body, _headers = self.request(
            "DELETE",
            f"/api/history/{first['data']['id']}",
        )
        self.assertEqual(delete_status, 204)
        self.assertIsNone(delete_body)

        _status, history, _headers = self.request("GET", "/api/history")
        self.assertEqual(
            [item["id"] for item in history["data"]],
            [second["data"]["id"]],
        )

        missing_status, _body, _headers = self.request(
            "DELETE",
            f"/api/history/{first['data']['id']}",
        )
        self.assertEqual(missing_status, 404)

    def test_history_is_returned_newest_first(self) -> None:
        _status, first, _headers = self.request(
            "POST",
            "/api/calculations",
            {"expression": "1+1"},
        )
        _status, second, _headers = self.request(
            "POST",
            "/api/calculations",
            {"expression": "2+2"},
        )

        _status, history, _headers = self.request("GET", "/api/history")

        self.assertEqual(
            [item["id"] for item in history["data"]],
            [second["data"]["id"], first["data"]["id"]],
        )

    def test_history_search_and_pagination(self) -> None:
        for index in range(12):
            self.request(
                "POST",
                "/api/calculations",
                {"expression": f"{index}+1"},
            )

        status, body, _headers = self.request(
            "GET",
            "/api/history?page=2&pageSize=5",
        )

        self.assertEqual(status, 200)
        self.assertEqual(len(body["data"]), 5)
        self.assertEqual(
            body["pagination"],
            {
                "page": 2,
                "pageSize": 5,
                "total": 12,
                "totalPages": 3,
            },
        )

        search_status, search_body, _headers = self.request(
            "GET",
            f"/api/history?q={quote('3+1')}",
        )
        self.assertEqual(search_status, 200)
        self.assertEqual(search_body["data"][0]["expression"], "3+1")

    def test_base_conversion_is_stored(self) -> None:
        status, body, _headers = self.request(
            "POST",
            "/api/conversions/base",
            {"value": "FF", "fromBase": 16, "toBase": 10},
        )

        self.assertEqual(status, 201)
        self.assertEqual(body["data"]["result"], "255")
        self.assertEqual(body["data"]["kind"], "base")

        _status, history, _headers = self.request("GET", "/api/history")
        self.assertEqual(history["data"][0]["expression"], "FF base 16 -> base 10")

    def test_unit_conversion_is_stored(self) -> None:
        status, body, _headers = self.request(
            "POST",
            "/api/conversions/units",
            {
                "value": "100",
                "category": "length",
                "fromUnit": "cm",
                "toUnit": "m",
            },
        )

        self.assertEqual(status, 201)
        self.assertEqual(body["data"]["result"], "1")
        self.assertEqual(body["data"]["kind"], "unit")

    def test_favorite_can_be_toggled_and_filtered(self) -> None:
        _status, calculation, _headers = self.request(
            "POST",
            "/api/calculations",
            {"expression": "7+8"},
        )

        favorite_status, favorite_body, _headers = self.request(
            "PATCH",
            f"/api/history/{calculation['data']['id']}/favorite",
            {"favorite": True},
        )
        self.assertEqual(favorite_status, 200)
        self.assertTrue(favorite_body["data"]["isFavorite"])

        _status, favorite_history, _headers = self.request(
            "GET",
            "/api/history?favorite=true",
        )
        self.assertEqual(len(favorite_history["data"]), 1)
        self.assertEqual(favorite_history["data"][0]["id"], calculation["data"]["id"])

        removed_status, removed_body, _headers = self.request(
            "PATCH",
            f"/api/history/{calculation['data']['id']}/favorite",
            {"favorite": False},
        )
        self.assertEqual(removed_status, 200)
        self.assertFalse(removed_body["data"]["isFavorite"])

    def test_cors_allows_local_frontend(self) -> None:
        request = Request(
            f"{self.base_url}/api/calculations",
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
            method="OPTIONS",
        )

        with urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(
                response.headers["Access-Control-Allow-Origin"],
                "http://127.0.0.1:5500",
            )


if __name__ == "__main__":
    unittest.main()
