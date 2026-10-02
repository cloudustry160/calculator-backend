from decimal import Decimal
import unittest

from app.conversions import (
    ConversionError,
    convert_base,
    convert_unit,
)


class ConversionTests(unittest.TestCase):
    def test_base_conversions(self) -> None:
        cases = (
            ("255", 10, 16, "FF"),
            ("FF", 16, 10, "255"),
            ("1010", 2, 10, "10"),
            ("-10", 10, 2, "-1010"),
            ("Z", 36, 10, "35"),
        )

        for value, from_base, to_base, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    convert_base(value, from_base, to_base).result,
                    expected,
                )

    def test_invalid_base_conversions(self) -> None:
        invalid_cases = (
            ("2", 2, 10),
            ("G", 16, 10),
            ("", 10, 2),
            ("10", 1, 10),
            ("10", 10, 37),
        )

        for value, from_base, to_base in invalid_cases:
            with self.subTest(value=value):
                with self.assertRaises(ConversionError):
                    convert_base(value, from_base, to_base)

    def test_linear_unit_conversions(self) -> None:
        cases = (
            ("100", "length", "cm", "m", Decimal("1")),
            ("1", "length", "km", "m", Decimal("1000")),
            ("1", "mass", "kg", "lb", Decimal("2.204622621848775807229")),
            ("2", "time", "h", "min", Decimal("120")),
        )

        for value, category, from_unit, to_unit, expected in cases:
            with self.subTest(category=category, from_unit=from_unit):
                result = Decimal(
                    convert_unit(
                        value,
                        category,
                        from_unit,
                        to_unit,
                    ).result
                )
                self.assertEqual(
                    result.quantize(Decimal("0.000000000001")),
                    expected.quantize(Decimal("0.000000000001")),
                )

    def test_temperature_conversions(self) -> None:
        self.assertEqual(
            convert_unit("0", "temperature", "c", "f").result,
            "32",
        )
        self.assertEqual(
            convert_unit("32", "temperature", "f", "c").result,
            "0",
        )
        self.assertEqual(
            convert_unit("0", "temperature", "c", "k").result,
            "273.15",
        )

    def test_invalid_unit_conversions(self) -> None:
        with self.assertRaises(ConversionError):
            convert_unit("1", "length", "kg", "m")
        with self.assertRaises(ConversionError):
            convert_unit("abc", "length", "m", "cm")
        with self.assertRaises(ConversionError):
            convert_unit("1", "unknown", "m", "cm")


if __name__ == "__main__":
    unittest.main()
