import re
import sqlite3
from datetime import date

import pytest
from werkzeug.security import check_password_hash

from database.db import get_db, init_db, seed_db

CATEGORIES = {
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other",
}


def _count(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_tables_and_columns_exist(db):
    users = {r["name"]: r for r in db.execute("PRAGMA table_info(users)")}
    expenses = {r["name"]: r for r in db.execute("PRAGMA table_info(expenses)")}

    assert set(users) == {"id", "name", "email", "password_hash", "created_at"}
    assert set(expenses) == {
        "id", "user_id", "amount", "category", "date",
        "description", "created_at",
    }
    for col in ("name", "email", "password_hash"):
        assert users[col]["notnull"] == 1
    for col in ("user_id", "amount", "category", "date"):
        assert expenses[col]["notnull"] == 1
    assert expenses["description"]["notnull"] == 0


def test_get_db_settings(db):
    assert db.row_factory is sqlite3.Row
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_init_db_is_idempotent(db):
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("A", "a@example.com", "x"),
    )
    db.commit()
    init_db()
    init_db()
    assert _count(db, "users") == 1


def test_seed_inserts_demo_data(db):
    seed_db()
    assert _count(db, "users") == 1
    assert _count(db, "expenses") == 8


def test_seed_is_idempotent(db):
    seed_db()
    seed_db()
    assert _count(db, "users") == 1
    assert _count(db, "expenses") == 8


def test_seed_covers_all_categories(db):
    seed_db()
    rows = db.execute("SELECT DISTINCT category FROM expenses").fetchall()
    assert {r["category"] for r in rows} == CATEGORIES


def test_seed_dates_in_current_month(db):
    seed_db()
    today = date.today()
    prefix = f"{today.year:04d}-{today.month:02d}-"
    for row in db.execute("SELECT date FROM expenses"):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date"])
        assert row["date"].startswith(prefix)


def test_seed_password_is_hashed(db):
    seed_db()
    row = db.execute(
        "SELECT password_hash FROM users WHERE email = ?",
        ("demo@spendly.com",),
    ).fetchone()
    assert row["password_hash"] != "demo123"
    assert check_password_hash(row["password_hash"], "demo123")


def test_duplicate_email_rejected(db):
    sql = "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)"
    db.execute(sql, ("A", "dup@example.com", "x"))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(sql, ("B", "dup@example.com", "y"))


def test_expense_with_unknown_user_rejected(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date)"
            " VALUES (?, ?, ?, ?)",
            (999, 10.0, "Food", "2026-01-01"),
        )


def test_null_amount_rejected(db):
    db.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("A", "a@example.com", "x"),
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date)"
            " VALUES (?, ?, ?, ?)",
            (1, None, "Food", "2026-01-01"),
        )
