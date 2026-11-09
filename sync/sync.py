"""
Copia los datos de InfluxDB a PostgreSQL. InfluxDB solo se LEE.
"""
import os
import time
from datetime import datetime, timedelta, timezone

import psycopg2
from psycopg2.extras import execute_values
from influxdb_client import InfluxDBClient

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "valenbisi-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "valenbisi")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "valenbisi")

PG = dict(
    host=os.getenv("PG_HOST", "postgres"),
    dbname=os.getenv("PG_DB", "valenbisi"),
    user=os.getenv("PG_USER", "valenbisi"),
    password=os.getenv("PG_PASSWORD", "valenbisi_pass"),
)

INTERVALO = 15   # segundos entre sincronizaciones
SOLAPE = 30      # segundos de solape para no perder datos en el borde


def conectar_postgres():
    while True:
        try:
            return psycopg2.connect(**PG)
        except psycopg2.OperationalError:
            print("Esperando a PostgreSQL...", flush=True)
            time.sleep(3)


def leer_influx(desde):
    flux = f'''
from(bucket: "{INFLUX_BUCKET}")
  |> range(start: {desde.strftime("%Y-%m-%dT%H:%M:%SZ")})
  |> filter(fn: (r) => r._measurement == "mqtt_consumer")
  |> pivot(rowKey: ["_time", "station"], columnKey: ["_field"], valueColumn: "_value")
'''
    filas = []
    with InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG) as client:
        for tabla in client.query_api().query(flux, org=INFLUX_ORG):
            for r in tabla.records:
                v = r.values
                if not v.get("station"):
                    continue
                filas.append((
                    r.get_time(),
                    v.get("station"),
                    v.get("free_bikes"),
                    v.get("empty_slots"),
                    v.get("latitude"),
                    v.get("longitude"),
                ))
    return filas


def guardar(conn, filas):
    with conn.cursor() as cur:
        # Una sola fila por nombre de estación (si se repite, gana el último valor)
        estaciones = {}
        for f in filas:
            estaciones[f[1]] = (f[1], f[4], f[5])

        execute_values(cur, """
            INSERT INTO estaciones (nombre, latitud, longitud) VALUES %s
            ON CONFLICT (nombre) DO UPDATE
              SET latitud = EXCLUDED.latitud, longitud = EXCLUDED.longitud
        """, list(estaciones.values()))

        cur.execute("SELECT nombre, id FROM estaciones")
        ids = dict(cur.fetchall())

        datos = [(ids[f[1]], f[0], f[2], f[3]) for f in filas]
        execute_values(cur, """
            INSERT INTO mediciones (estacion_id, momento, bicis_libres, huecos_libres)
            VALUES %s ON CONFLICT (estacion_id, momento) DO NOTHING
        """, datos)
        insertadas = cur.rowcount

        cur.execute(
            "INSERT INTO sincronizaciones (filas_leidas, filas_insertadas) VALUES (%s, %s)",
            (len(filas), insertadas),
        )
    conn.commit()
    return insertadas

def main():
    conn = conectar_postgres()
    print("Conectado a PostgreSQL", flush=True)

    # Primera pasada: TODO el histórico que haya en InfluxDB
    desde = datetime(1970, 1, 1, tzinfo=timezone.utc)

    while True:
        try:
            filas = leer_influx(desde)
            if filas:
                insertadas = guardar(conn, filas)
                ultimo = max(f[0] for f in filas)
                desde = ultimo - timedelta(seconds=SOLAPE)
                print(f"Leídas {len(filas)} | insertadas {insertadas} | hasta {ultimo}", flush=True)
            else:
                print("Sin datos nuevos en InfluxDB", flush=True)
        except psycopg2.Error as e:
            print(f"Error PostgreSQL: {e}", flush=True)
            conn.rollback()
            conn = conectar_postgres()
        except Exception as e:
            print(f"Error sincronizando: {e}", flush=True)

        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
