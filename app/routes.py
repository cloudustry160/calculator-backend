from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from urllib.parse import unquote, urlsplit

from app.calculator import CalculationError, calculate_expression
from app.database import Database


@dataclass
class ApiResponse:
    status: int
    body: dict | None
    headers: dict[str, str] = field(default_factory=dict)


def decimal_to_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def serialize_history_item(record: dict) -> dict:
    return {
        "id": record["id"],
        "expression": record["expression"],
        "result": decimal_to_number(record["result"]),
        "createdAt": record["created_at"],
    }


class ApiRouter:
    def __init__(self, database: Database) -> None:
        self.database = database

    def dispatch(
        self,
        method: str,
        target: str,
        body: dict | None,
    ) -> ApiResponse:
        path = urlsplit(target).path.rstrip("/") or "/"

        if path == "/api/health":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._health()

        if path == "/api/calculations":
            if method != "POST":
                return self._method_not_allowed("POST")
            return self._create_calculation(body)

        if path == "/api/history":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._list_history()

        history_prefix = "/api/history/"
        if path.startswith(history_prefix):
            if method != "DELETE":
                return self._method_not_allowed("DELETE")
            raw_record_id = unquote(path.removeprefix(history_prefix))
            return self._delete_history(raw_record_id)

        return ApiResponse(
            status=404,
            body={"success": False, "message": "接口不存在"},
        )

    def _health(self) -> ApiResponse:
        if not self.database.health_check():
            return ApiResponse(
                status=500,
                body={"success": False, "message": "数据库不可用"},
            )
        return ApiResponse(
            status=200,
            body={"success": True, "status": "ok"},
        )

    def _create_calculation(self, body: dict | None) -> ApiResponse:
        if not isinstance(body, dict) or not isinstance(body.get("expression"), str):
            return ApiResponse(
                status=400,
                body={"success": False, "message": "请求必须包含 expression 字符串"},
            )

        expression = body["expression"].strip()
        try:
            result = calculate_expression(expression)
        except CalculationError as error:
            return ApiResponse(
                status=400,
                body={
                    "success": False,
                    "code": error.code,
                    "message": error.message,
                },
            )

        record = self.database.create_history(expression, result)
        return ApiResponse(
            status=201,
            body={
                "success": True,
                "data": serialize_history_item(record),
            },
        )

    def _list_history(self) -> ApiResponse:
        records = self.database.list_history()
        return ApiResponse(
            status=200,
            body={
                "success": True,
                "data": [serialize_history_item(record) for record in records],
            },
        )

    def _delete_history(self, raw_record_id: str) -> ApiResponse:
        try:
            record_id = int(raw_record_id)
        except ValueError:
            return ApiResponse(
                status=404,
                body={"success": False, "message": "历史记录不存在"},
            )

        if not self.database.delete_history(record_id):
            return ApiResponse(
                status=404,
                body={"success": False, "message": "历史记录不存在"},
            )

        return ApiResponse(status=204, body=None)

    @staticmethod
    def _method_not_allowed(allowed_method: str) -> ApiResponse:
        return ApiResponse(
            status=405,
            body={"success": False, "message": "请求方法不允许"},
            headers={"Allow": allowed_method},
        )
