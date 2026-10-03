from __future__ import annotations

from dataclasses import dataclass


MAX_INPUT_LENGTH = 80
SUPPORTED_BASES = (2, 8, 10, 16)


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


def _validate_base(base: int) -> None:
    if isinstance(base, bool) or base not in SUPPORTED_BASES:
        raise ConversionError("仅支持 2、8、10 和 16 进制")


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

    digits = "0123456789ABCDEF"
    valid_digits = set(digits[:from_base])
    if any(character not in valid_digits for character in normalized):
        raise ConversionError(f"输入值不是有效的 {from_base} 进制数字")

    number = int(f"{sign}{normalized}", from_base)
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
