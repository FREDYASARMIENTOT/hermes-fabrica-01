#!/bin/bash
set -e

echo "[hermes-fabrica-01] Starting deployment..."

cd /home/site/wwwroot

echo "[hermes-fabrica-01] Installing dependencies..."
pip install -r requirements.txt -q

echo "[hermes-fabrica-01] Creating data directory..."
mkdir -p data

echo "[hermes-fabrica-01] Initializing database schema..."
python -c "
import sqlite3, os
db_path = os.path.join('data', 'proyecto.db')
schema_path = os.path.join('tools', 'Templates', 'database', 'schema.sql')
if os.path.exists(schema_path):
    conn = sqlite3.connect(db_path)
    with open(schema_path) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print('Database schema initialized')
elif not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE IF NOT EXISTS Proyecto (Id INTEGER PRIMARY KEY AUTOINCREMENT, Nombre TEXT, Descripcion TEXT, Version TEXT, CorrelationId TEXT, Estado TEXT, Repositorio TEXT, Branch TEXT, CommitHash TEXT, UrlPublica TEXT, EstadoAzure TEXT, EstadoGitHub TEXT, EstadoCI TEXT, TiempoBuild REAL, TiempoDeploy REAL, TiempoSmokeTest REAL, FechaCreacion TEXT, FechaActualizacion TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS Timeline (Id INTEGER PRIMARY KEY AUTOINCREMENT, CorrelationId TEXT, Evento TEXT, Estado TEXT, Fecha TEXT, Detalle TEXT, Duracion REAL)')
    conn.execute('CREATE TABLE IF NOT EXISTS SmokeTestResults (Id INTEGER PRIMARY KEY AUTOINCREMENT, CorrelationId TEXT, Endpoint TEXT, HTTPCode INTEGER, Estado TEXT, TiempoRespuesta REAL, Fecha TEXT, Detalle TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS BitacoraEventos (Id INTEGER PRIMARY KEY AUTOINCREMENT, CorrelationId TEXT, Fecha TEXT, Hora TEXT, Usuario TEXT, Paso TEXT, Estado TEXT, Duracion REAL, Mensaje TEXT, Resultado TEXT)')
    conn.commit()
    conn.close()
    print('Database schema initialized (inline)')
"

echo "[hermes-fabrica-01] Starting application..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}

