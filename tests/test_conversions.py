import unittest

from app.conversions import ConversionError, convert_base


class ConversionTests(unittest.TestCase):
    def test_base_conversions(self) -> None:
        cases = (
            ("255", 10, 16, "FF"),
            ("FF", 16, 10, "255"),
            ("1010", 2, 10, "10"),
            ("-10", 10, 2, "-1010"),
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
            ("10", 3, 10),
            ("10", 10, 20),
        )

        for value, from_base, to_base in invalid_cases:
            with self.subTest(value=value):
                with self.assertRaises(ConversionError):
                    convert_base(value, from_base, to_base)


if __name__ == "__main__":
    unittest.main()
