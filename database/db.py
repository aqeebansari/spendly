import calendar
import os
import sqlite3
from contextlib import closing
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "expense_tracker.db",
)


def get_db():
    """Return a SQLite connection with Row access and FK enforcement on."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables if they do not exist. Safe to call repeatedly."""
    with closing(get_db()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """
        )


def seed_db():
    """Insert a demo user and sample expenses (amounts in INR) once."""
    with closing(get_db()) as conn, conn:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cursor.lastrowid

        # Fixed days spread across the current month; clamped to the month
        # length so short months (e.g. February) still produce valid dates.
        today = date.today()
        last_day = calendar.monthrange(today.year, today.month)[1]

        def month_date(day):
            return date(today.year, today.month, min(day, last_day)).isoformat()

        expenses = [
            (user_id, 450.00, "Food", month_date(2), "Groceries"),
            (user_id, 220.50, "Food", month_date(9), "Lunch"),
            (user_id, 180.00, "Transport", month_date(5), "Metro and auto"),
            (user_id, 1250.00, "Bills", month_date(7), "Electricity bill"),
            (user_id, 600.00, "Health", month_date(12), "Pharmacy"),
            (user_id, 499.00, "Entertainment", month_date(16), "Movie and snacks"),
            (user_id, 1899.00, "Shopping", month_date(21), "T-shirt"),
            (user_id, 300.00, "Other", month_date(26), "Miscellaneous"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            expenses,
        )
