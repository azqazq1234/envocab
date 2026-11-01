"""Download a pinned ECDICT snapshot and build a local read-only lookup index."""

import csv
import io
import sqlite3
from urllib.request import urlopen

from app.dictionary import DATA_PATH, SOURCE_REVISION, SOURCE_URL


def main():
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_PATH.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with sqlite3.connect(temporary) as connection:
            connection.execute(
                "CREATE TABLE dictionary (term TEXT PRIMARY KEY COLLATE NOCASE, "
                "phonetic TEXT NOT NULL, translation TEXT NOT NULL)"
            )
            with urlopen(f"{SOURCE_URL}/ecdict.csv", timeout=60) as response:
                reader = csv.DictReader(
                    io.TextIOWrapper(response, encoding="utf-8-sig", newline="")
                )
                connection.executemany(
                    "INSERT OR IGNORE INTO dictionary VALUES (?, ?, ?)",
                    (
                        (row["word"].strip(), row["phonetic"], row["translation"])
                        for row in reader
                        if row["word"].strip() and row["translation"].strip()
                    ),
                )
            connection.execute("CREATE TABLE metadata (revision TEXT NOT NULL)")
            connection.execute("INSERT INTO metadata VALUES (?)", (SOURCE_REVISION,))
            count = connection.execute("SELECT count(*) FROM dictionary").fetchone()[0]
        temporary.replace(DATA_PATH)
        print(f"ECDICT ready: {count:,} entries ({SOURCE_REVISION}).")
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
