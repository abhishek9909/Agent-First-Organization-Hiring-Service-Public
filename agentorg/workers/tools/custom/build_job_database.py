import sqlite3
import argparse
from pathlib import Path
import os


def build_database(folder_path):
    db_path = Path(folder_path) / "show"
    if os.path.exists(db_path):
        os.remove(db_path)

    # Creating the database with a .sqlite extension
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create tables based on the provided schema
    cursor.execute('''
        CREATE TABLE applications (
            id VARCHAR(40) PRIMARY KEY,
            job_id VARCHAR(40),
            user_name VARCHAR(40),
            linkedin_url VARCHAR(100),
        )
    ''')

    # Commit changes and close the connection
    conn.commit()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder_path", required=True, type=str, help="location to save the documents")
    args = parser.parse_args()

    if not os.path.exists(args.folder_path):
        os.makedirs(args.folder_path)

    build_database(args.folder_path)