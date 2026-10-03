from decimal import Decimal
import sqlite3
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
            history = reopened_database.list_history()
            records = history["records"]

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["expression"], "1+2")
            self.assertEqual(records[0]["result"], "3")
            self.assertEqual(records[0]["kind"], "calculation")

    def test_initialize_migrates_existing_history_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = f"{temporary_directory}/legacy.db"
            connection = sqlite3.connect(database_path)
            connection.execute(
                """
                CREATE TABLE calculation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expression TEXT NOT NULL,
                    result TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO calculation_history (
                    expression,
                    result,
                    created_at
                )
                VALUES ('1+1', '2', '2026-10-03T00:00:00Z')
                """
            )
            connection.commit()
            connection.close()

            database = Database(database_path)
            database.initialize()
            record = database.list_history()["records"][0]

            self.assertEqual(record["kind"], "calculation")


if __name__ == "__main__":
    unittest.main()
