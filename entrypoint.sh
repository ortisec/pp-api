#!/bin/sh
set -e

echo "Esperando a la base de datos..."
python - <<'PY'
import os
import sys
import time

import psycopg

url = os.environ.get("DATABASE_URL", "")
# psycopg no acepta el prefijo +psycopg como scheme de conexion directa
dsn = url.replace("postgresql+psycopg://", "postgresql://")

last = None
for attempt in range(1, 31):
    try:
        with psycopg.connect(dsn, connect_timeout=3):
            print("Base de datos disponible.")
            sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        last = exc
        print(f"Intento {attempt}/30: {exc}")
        time.sleep(2)
print(f"No se pudo conectar a la base de datos: {last}")
sys.exit(1)
PY

echo "Aplicando migraciones..."
alembic upgrade head

echo "Iniciando API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
