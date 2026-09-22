from __future__ import annotations

from dataclasses import dataclass
from decimal import (
    Decimal,
    DecimalException,
    InvalidOperation,
    localcontext,
)


MAX_EXPRESSION_LENGTH = 200
MAX_NUMBER_DIGITS = 30
MAX_ABSOLUTE_RESULT = Decimal("1e50")


class CalculationError(Exception):
    def __init__(self, message: str, code: str = "INVALID_EXPRESSION") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class Token:
    kind: str
    value: str


def _tokenize(expression: str) -> list[Token]:
    tokens: list[Token] = []
    index = 0

    while index < len(expression):
        character = expression[index]

        if character.isspace():
            index += 1
            continue

        if character in "+-*/()":
            tokens.append(Token(character, character))
            index += 1
            continue

        if character.isdigit() or character == ".":
            start = index
            digit_count = 0
            has_decimal_point = False

            while index < len(expression):
                current = expression[index]

                if current.isdigit():
                    digit_count += 1
                    index += 1
                    continue

                if current == "." and not has_decimal_point:
                    has_decimal_point = True
                    index += 1
                    continue

                break

            if digit_count == 0:
                raise CalculationError("小数格式不正确")
            if digit_count > MAX_NUMBER_DIGITS:
                raise CalculationError("单个数字不能超过 30 位")

            tokens.append(Token("number", expression[start:index]))
            continue

        raise CalculationError(f"不支持的字符：{character}")

    if not tokens:
        raise CalculationError("表达式不能为空")

    return tokens


class ExpressionParser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.position = 0

    def parse(self) -> Decimal:
        value = self._parse_expression()

        if self._current() is not None:
            token = self._current()
            raise CalculationError(f"存在多余内容：{token.value}")

        return value

    def _current(self) -> Token | None:
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position]

    def _advance(self) -> Token:
        token = self._current()
        if token is None:
            raise CalculationError("表达式不完整")
        self.position += 1
        return token

    def _match(self, kind: str) -> bool:
        token = self._current()
        if token is not None and token.kind == kind:
            self.position += 1
            return True
        return False

    def _parse_expression(self) -> Decimal:
        value = self._parse_term()

        while True:
            if self._match("+"):
                value += self._parse_term()
            elif self._match("-"):
                value -= self._parse_term()
            else:
                return value

    def _parse_term(self) -> Decimal:
        value = self._parse_unary()

        while True:
            if self._match("*"):
                value *= self._parse_unary()
            elif self._match("/"):
                divisor = self._parse_unary()
                if divisor == 0:
                    raise CalculationError("不能除以零", "DIVISION_BY_ZERO")
                value /= divisor
            else:
                return value

    def _parse_unary(self) -> Decimal:
        if self._match("+"):
            return self._parse_primary()
        if self._match("-"):
            return -self._parse_primary()
        return self._parse_primary()

    def _parse_primary(self) -> Decimal:
        token = self._current()

        if token is None:
            raise CalculationError("表达式不完整")

        if token.kind == "number":
            self._advance()
            try:
                return Decimal(token.value)
            except InvalidOperation as error:
                raise CalculationError("数字格式不正确") from error

        if self._match("("):
            value = self._parse_expression()
            if not self._match(")"):
                raise CalculationError("括号不匹配")
            return value

        if token.kind == ")":
            raise CalculationError("括号位置不正确")

        raise CalculationError(f"操作符位置不正确：{token.value}")


def calculate_expression(expression: str) -> Decimal:
    normalized_expression = expression.strip()

    if len(normalized_expression) > MAX_EXPRESSION_LENGTH:
        raise CalculationError("表达式不能超过 200 个字符", "EXPRESSION_TOO_LONG")
    if not normalized_expression:
        raise CalculationError("表达式不能为空")

    compact_expression = "".join(normalized_expression.split())
    if "++" in compact_expression or "--" in compact_expression:
        raise CalculationError("不支持连续的正负号")

    tokens = _tokenize(normalized_expression)

    try:
        with localcontext() as context:
            context.prec = 50
            result = ExpressionParser(tokens).parse()

            if not result.is_finite():
                raise CalculationError("计算结果不是有效数字")
            if abs(result) > MAX_ABSOLUTE_RESULT:
                raise CalculationError("计算结果超出支持范围")
    except CalculationError:
        raise
    except (DecimalException, OverflowError) as error:
        raise CalculationError("无法计算该表达式") from error

    if result == 0:
        return Decimal("0")
    return result.normalize()
