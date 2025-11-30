import psycopg2
import os
import pytest


def test_postgres_connection():
    """Test that PostgreSQL connection can be established."""
    with psycopg2.connect(
        host="localhost",
        port=5432,
        user=os.getenv("POSTGRES_USER", "vra"),
        password=os.getenv("POSTGRES_PASSWORD"),
        database="vra"
    ) as conn:
        assert conn.closed == 0  # Connection is open
    assert conn.closed == 1  # Connection is closed