from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from urllib.parse import parse_qs, unquote, urlsplit

from app.calculator import CalculationError, calculate_expression
from app.conversions import ConversionError, convert_base, convert_unit
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
    result: int | float | str = record["result"]
    if record["kind"] == "calculation":
        try:
            result = decimal_to_number(Decimal(record["result"]))
        except Exception:
            result = record["result"]

    return {
        "id": record["id"],
        "expression": record["expression"],
        "result": result,
        "kind": record["kind"],
        "isFavorite": record["is_favorite"],
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
        parsed_target = urlsplit(target)
        path = parsed_target.path.rstrip("/") or "/"

        if path == "/api/health":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._health()

        if path == "/api/calculations":
            if method != "POST":
                return self._method_not_allowed("POST")
            return self._create_calculation(body)

        if path == "/api/conversions/base":
            if method != "POST":
                return self._method_not_allowed("POST")
            return self._create_base_conversion(body)

        if path == "/api/conversions/units":
            if method != "POST":
                return self._method_not_allowed("POST")
            return self._create_unit_conversion(body)

        if path == "/api/history":
            if method != "GET":
                return self._method_not_allowed("GET")
            return self._list_history(parsed_target.query)

        history_prefix = "/api/history/"
        if path.startswith(history_prefix):
            relative_path = unquote(path.removeprefix(history_prefix))

            if relative_path.endswith("/favorite"):
                if method != "PATCH":
                    return self._method_not_allowed("PATCH")
                raw_record_id = relative_path.removesuffix("/favorite")
                return self._update_favorite(raw_record_id, body)

            if method != "DELETE":
                return self._method_not_allowed("DELETE")
            return self._delete_history(relative_path)

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

    def _create_base_conversion(self, body: dict | None) -> ApiResponse:
        if not isinstance(body, dict):
            return self._bad_request("请求体必须是 JSON 对象")

        value = body.get("value")
        from_base = body.get("fromBase")
        to_base = body.get("toBase")
        if not isinstance(value, str):
            return self._bad_request("请求必须包含 value 字符串")
        if isinstance(from_base, bool) or not isinstance(from_base, int):
            return self._bad_request("fromBase 必须是整数")
        if isinstance(to_base, bool) or not isinstance(to_base, int):
            return self._bad_request("toBase 必须是整数")

        try:
            conversion = convert_base(value, from_base, to_base)
        except ConversionError as error:
            return self._conversion_error(error)

        record = self.database.create_history(
            conversion.expression,
            conversion.result,
            kind="base",
        )
        return self._created(record)

    def _create_unit_conversion(self, body: dict | None) -> ApiResponse:
        if not isinstance(body, dict):
            return self._bad_request("请求体必须是 JSON 对象")

        value = body.get("value")
        category = body.get("category")
        from_unit = body.get("fromUnit")
        to_unit = body.get("toUnit")
        if not isinstance(value, str):
            return self._bad_request("请求必须包含 value 字符串")
        if not isinstance(category, str):
            return self._bad_request("请求必须包含 category 字符串")
        if not isinstance(from_unit, str):
            return self._bad_request("请求必须包含 fromUnit 字符串")
        if not isinstance(to_unit, str):
            return self._bad_request("请求必须包含 toUnit 字符串")

        try:
            conversion = convert_unit(
                value,
                category,
                from_unit,
                to_unit,
            )
        except ConversionError as error:
            return self._conversion_error(error)

        record = self.database.create_history(
            conversion.expression,
            conversion.result,
            kind="unit",
        )
        return self._created(record)

    def _list_history(self, query_string: str) -> ApiResponse:
        query_parameters = parse_qs(query_string)
        page = self._parse_positive_int(query_parameters, "page", default=1)
        page_size = self._parse_positive_int(
            query_parameters,
            "pageSize",
            default=10,
        )
        if page is None or page_size is None:
            return self._bad_request("page 和 pageSize 必须是正整数")

        history = self.database.list_history(
            page=page,
            page_size=min(page_size, 50),
            query=query_parameters.get("q", [""])[0],
            favorite_only=query_parameters.get("favorite", ["false"])[0]
            == "true",
        )
        return ApiResponse(
            status=200,
            body={
                "success": True,
                "data": [
                    serialize_history_item(record)
                    for record in history["records"]
                ],
                "pagination": {
                    "page": history["page"],
                    "pageSize": history["page_size"],
                    "total": history["total"],
                    "totalPages": history["total_pages"],
                },
            },
        )

    def _update_favorite(
        self,
        raw_record_id: str,
        body: dict | None,
    ) -> ApiResponse:
        record_id = self._parse_record_id(raw_record_id)
        if record_id is None:
            return self._not_found()
        if not isinstance(body, dict) or not isinstance(
            body.get("favorite"),
            bool,
        ):
            return self._bad_request("favorite 必须是布尔值")

        record = self.database.set_favorite(record_id, body["favorite"])
        if record is None:
            return self._not_found()

        return ApiResponse(
            status=200,
            body={
                "success": True,
                "data": serialize_history_item(record),
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
    def _parse_record_id(raw_record_id: str) -> int | None:
        try:
            return int(raw_record_id)
        except ValueError:
            return None

    @staticmethod
    def _parse_positive_int(
        query_parameters: dict[str, list[str]],
        key: str,
        default: int,
    ) -> int | None:
        raw_value = query_parameters.get(key, [str(default)])[0]
        try:
            value = int(raw_value)
        except ValueError:
            return None
        return value if value > 0 else None

    @staticmethod
    def _created(record: dict) -> ApiResponse:
        return ApiResponse(
            status=201,
            body={
                "success": True,
                "data": serialize_history_item(record),
            },
        )

    @staticmethod
    def _bad_request(message: str) -> ApiResponse:
        return ApiResponse(
            status=400,
            body={"success": False, "message": message},
        )

    @staticmethod
    def _conversion_error(error: ConversionError) -> ApiResponse:
        return ApiResponse(
            status=400,
            body={
                "success": False,
                "code": error.code,
                "message": error.message,
            },
        )

    @staticmethod
    def _not_found() -> ApiResponse:
        return ApiResponse(
            status=404,
            body={"success": False, "message": "历史记录不存在"},
        )

    @staticmethod
    def _method_not_allowed(allowed_method: str) -> ApiResponse:
        return ApiResponse(
            status=405,
            body={"success": False, "message": "请求方法不允许"},
            headers={"Allow": allowed_method},
        )
