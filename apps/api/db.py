from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2.extensions import connection

from apps.api.config import settings


@contextmanager
def get_conn() -> Iterator[connection]:
    conn = psycopg2.connect(settings.database_url)
    try:
        yield conn
    finally:
        conn.close()
