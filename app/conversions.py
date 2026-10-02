from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, DecimalException, InvalidOperation, localcontext


MAX_INPUT_LENGTH = 80
MAX_ABSOLUTE_RESULT = Decimal("1e50")
MIN_BASE = 2
MAX_BASE = 36


class ConversionError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "INVALID_CONVERSION",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class ConversionResult:
    expression: str
    result: str


LINEAR_UNITS: dict[str, dict[str, Decimal]] = {
    "length": {
        "mm": Decimal("0.001"),
        "cm": Decimal("0.01"),
        "m": Decimal("1"),
        "km": Decimal("1000"),
        "in": Decimal("0.0254"),
        "ft": Decimal("0.3048"),
        "yd": Decimal("0.9144"),
        "mi": Decimal("1609.344"),
    },
    "mass": {
        "mg": Decimal("0.000001"),
        "g": Decimal("0.001"),
        "kg": Decimal("1"),
        "t": Decimal("1000"),
        "oz": Decimal("0.028349523125"),
        "lb": Decimal("0.45359237"),
    },
    "time": {
        "ms": Decimal("0.001"),
        "s": Decimal("1"),
        "min": Decimal("60"),
        "h": Decimal("3600"),
        "day": Decimal("86400"),
    },
}

TEMPERATURE_UNITS = {"c", "f", "k"}


def _normalize_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"

    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _parse_decimal(value: str) -> Decimal:
    normalized = value.strip()
    if not normalized:
        raise ConversionError("请输入要转换的数值")
    if len(normalized) > MAX_INPUT_LENGTH:
        raise ConversionError("输入数值过长")

    try:
        number = Decimal(normalized)
    except InvalidOperation as error:
        raise ConversionError("数值格式不正确") from error

    if not number.is_finite():
        raise ConversionError("数值必须是有限数字")
    if abs(number) > MAX_ABSOLUTE_RESULT:
        raise ConversionError("数值超出支持范围")
    return number


def _validate_base(base: int) -> None:
    if isinstance(base, bool) or not MIN_BASE <= base <= MAX_BASE:
        raise ConversionError(f"进制必须在 {MIN_BASE} 到 {MAX_BASE} 之间")


def convert_base(value: str, from_base: int, to_base: int) -> ConversionResult:
    _validate_base(from_base)
    _validate_base(to_base)

    normalized = value.strip().upper()
    if not normalized:
        raise ConversionError("请输入要转换的数值")
    if len(normalized) > MAX_INPUT_LENGTH:
        raise ConversionError("输入数值过长")

    sign = ""
    if normalized[0] in "+-":
        sign = normalized[0]
        normalized = normalized[1:]

    if not normalized:
        raise ConversionError("数值格式不正确")

    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    valid_digits = set(digits[:from_base])
    if any(character not in valid_digits for character in normalized):
        raise ConversionError(f"输入值不是有效的 {from_base} 进制数字")

    number = int(f"{sign}{normalized}", from_base)
    if abs(number) > int(MAX_ABSOLUTE_RESULT):
        raise ConversionError("数值超出支持范围")

    if number == 0:
        converted = "0"
    else:
        negative = number < 0
        remaining = abs(number)
        output: list[str] = []

        while remaining:
            remaining, digit = divmod(remaining, to_base)
            output.append(digits[digit])

        converted = "".join(reversed(output))
        if negative:
            converted = f"-{converted}"

    expression = f"{sign}{normalized} base {from_base} -> base {to_base}"
    return ConversionResult(expression=expression, result=converted)


def _temperature_to_celsius(value: Decimal, unit: str) -> Decimal:
    if unit == "c":
        return value
    if unit == "f":
        return (value - Decimal("32")) * Decimal("5") / Decimal("9")
    if unit == "k":
        return value - Decimal("273.15")
    raise ConversionError("不支持的温度单位")


def _celsius_to_temperature(value: Decimal, unit: str) -> Decimal:
    if unit == "c":
        return value
    if unit == "f":
        return value * Decimal("9") / Decimal("5") + Decimal("32")
    if unit == "k":
        return value + Decimal("273.15")
    raise ConversionError("不支持的温度单位")


def convert_unit(
    value: str,
    category: str,
    from_unit: str,
    to_unit: str,
) -> ConversionResult:
    number = _parse_decimal(value)
    normalized_category = category.strip().lower()
    normalized_from = from_unit.strip().lower()
    normalized_to = to_unit.strip().lower()

    if normalized_category == "temperature":
        if normalized_from not in TEMPERATURE_UNITS:
            raise ConversionError("不支持的源温度单位")
        if normalized_to not in TEMPERATURE_UNITS:
            raise ConversionError("不支持的目标温度单位")

        with localcontext() as context:
            context.prec = 50
            celsius = _temperature_to_celsius(number, normalized_from)
            result = _celsius_to_temperature(celsius, normalized_to)
    else:
        units = LINEAR_UNITS.get(normalized_category)
        if units is None:
            raise ConversionError("不支持的单位分类")
        if normalized_from not in units:
            raise ConversionError("不支持的源单位")
        if normalized_to not in units:
            raise ConversionError("不支持的目标单位")

        with localcontext() as context:
            context.prec = 50
            result = number * units[normalized_from] / units[normalized_to]

    if not result.is_finite():
        raise ConversionError("转换结果不是有效数字")
    if abs(result) > MAX_ABSOLUTE_RESULT:
        raise ConversionError("转换结果超出支持范围")

    try:
        formatted_result = _normalize_decimal(result)
    except DecimalException as error:
        raise ConversionError("无法完成单位换算") from error

    expression = f"{value.strip()} {normalized_from} -> {normalized_to}"
    return ConversionResult(expression=expression, result=formatted_result)
