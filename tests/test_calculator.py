from decimal import Decimal
import unittest

from app.calculator import CalculationError, calculate_expression


class CalculatorTests(unittest.TestCase):
    def test_valid_expressions(self) -> None:
        cases = {
            "1+2*3": Decimal("7"),
            "(1+2)*3": Decimal("9"),
            "10 / 2 + 7": Decimal("12"),
            "8-3*2": Decimal("2"),
            "-5+8": Decimal("3"),
            "3*-2": Decimal("-6"),
            "0.1+0.2": Decimal("0.3"),
            ".5*2": Decimal("1"),
            "2*(3+4)-5/2": Decimal("11.5"),
        }

        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(calculate_expression(expression), expected)

    def test_invalid_expressions(self) -> None:
        invalid_expressions = (
            "",
            "   ",
            "1+",
            "1++2",
            "(1+2",
            "1+2)",
            "()",
            "1..2",
            "sqrt(4)",
            "eval('1+1')",
            "2^3",
        )

        for expression in invalid_expressions:
            with self.subTest(expression=expression):
                with self.assertRaises(CalculationError):
                    calculate_expression(expression)

    def test_division_by_zero(self) -> None:
        with self.assertRaises(CalculationError) as context:
            calculate_expression("10/0")

        self.assertEqual(context.exception.code, "DIVISION_BY_ZERO")

    def test_expression_length_limit(self) -> None:
        with self.assertRaises(CalculationError) as context:
            calculate_expression("1" * 201)

        self.assertEqual(context.exception.code, "EXPRESSION_TOO_LONG")


if __name__ == "__main__":
    unittest.main()
