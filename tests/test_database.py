from decimal import Decimal
import tempfile
import unittest

from app.database import Database


class DatabaseTests(unittest.TestCase):
    def test_history_survives_new_database_instance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = f"{temporary_directory}/history.db"

            first_database = Database(database_path)
            first_database.initialize()
            first_database.create_history("1+2", Decimal("3"))

            reopened_database = Database(database_path)
            reopened_database.initialize()
            records = reopened_database.list_history()

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["expression"], "1+2")
            self.assertEqual(records[0]["result"], Decimal("3"))


if __name__ == "__main__":
    unittest.main()
