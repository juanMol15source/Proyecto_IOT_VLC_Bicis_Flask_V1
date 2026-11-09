import os

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, render_template

app = Flask(__name__)

PG = dict(
    host=os.getenv("PG_HOST", "postgres"),
    dbname=os.getenv("PG_DB", "valenbisi"),
    user=os.getenv("PG_USER", "valenbisi"),
    password=os.getenv("PG_PASSWORD", "valenbisi_pass"),
)


def consultar(sql):
    """Ejecuta una consulta y devuelve las filas como diccionarios."""
    conn = psycopg2.connect(cursor_factory=psycopg2.extras.RealDictCursor, **PG)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()
    finally:
        conn.close()


# Última medición de cada estación con datos en los últimos 15 minutos.
# Se reutiliza en varias rutas para que todas cuenten las mismas estaciones.
ACTUALES = """
    SELECT DISTINCT ON (estacion_id) estacion_id, bicis_libres, huecos_libres
    FROM mediciones
    WHERE momento > now() - interval '15 minutes'
    ORDER BY estacion_id, momento DESC
"""


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/api/kpis")
def api_kpis():
    r = consultar(f"""
        SELECT COALESCE(SUM(bicis_libres), 0) AS bicis, COUNT(*) AS estaciones
        FROM ({ACTUALES}) u
    """)[0]
    return jsonify({"bicis": int(r["bicis"]), "estaciones": int(r["estaciones"])})


@app.route("/api/top-bicis")
def api_top_bicis():
    filas = consultar(f"""
        SELECT e.nombre AS estacion, u.bicis_libres AS bicis
        FROM estaciones e
        JOIN ({ACTUALES}) u ON u.estacion_id = e.id
        ORDER BY u.bicis_libres DESC
        LIMIT 10
    """)
    return jsonify([{"estacion": f["estacion"], "bicis": int(f["bicis"])} for f in filas])


@app.route("/api/ocupacion")
def api_ocupacion():
    r = consultar(f"""
        SELECT COALESCE(SUM(bicis_libres), 0)  AS bicis,
               COALESCE(SUM(huecos_libres), 0) AS huecos
        FROM ({ACTUALES}) u
    """)[0]
    bicis, huecos = int(r["bicis"]), int(r["huecos"])
    total = bicis + huecos
    return jsonify({
        "bicis": bicis,
        "huecos": huecos,
        "porcentaje": round(100 * bicis / total, 1) if total else 0,
    })


@app.route("/api/evolucion")
def api_evolucion():
    filas = consultar("""
        SELECT tramo, SUM(media) AS bicis
        FROM (
            SELECT date_bin('5 minutes', momento, TIMESTAMPTZ '2000-01-01 00:00:00+00') AS tramo,
                   estacion_id,
                   AVG(bicis_libres) AS media
            FROM mediciones
            WHERE momento > now() - interval '6 hours'
            GROUP BY 1, 2
        ) t
        GROUP BY tramo
        ORDER BY tramo
    """)
    return jsonify([{"hora": f["tramo"].isoformat(), "bicis": float(f["bicis"])} for f in filas])


@app.route("/api/horas")
def api_horas():
    filas = consultar("""
        SELECT EXTRACT(HOUR FROM momento AT TIME ZONE 'Europe/Madrid')::int AS hora,
               ROUND(AVG(bicis_libres), 1) AS media
        FROM mediciones
        WHERE momento > now() - interval '7 days'
        GROUP BY 1
        ORDER BY 1
    """)
    return jsonify([{"hora": f["hora"], "media": float(f["media"])} for f in filas])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
