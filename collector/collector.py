import requests
import time
import json
import paho.mqtt.client as mqtt

API_URL = "http://api.citybik.es/v2/networks/valenbisi"

MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
MQTT_TOPIC = "valenbisi/stations"

INTERVALO_API = 60   # pedir datos cada 60 s (la API limita las peticiones frecuentes)
ESPERA_ERROR = 60    # si la API falla o limita, esperar 60 s antes de reintentar


def obtener_estaciones():
    """Pide las estaciones a la API. Si falla o hay límite, espera y reintenta."""
    while True:
        try:
            r = requests.get(API_URL, timeout=10, headers={"User-Agent": "valenbisi-iot/1.0"})
            datos = r.json()
            return datos["network"]["stations"][:100]
        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"Error consultando la API: {e}. Espero {ESPERA_ERROR} s", flush=True)
            time.sleep(ESPERA_ERROR)


def main():
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cliente.connect(MQTT_BROKER, MQTT_PORT)
    cliente.loop_start()

    while True:
        estaciones = obtener_estaciones()
        for e in estaciones:
            mensaje = {
                "station": e["name"],
                "free_bikes": e["free_bikes"],
                "empty_slots": e["empty_slots"],
                "latitude": e["latitude"],
                "longitude": e["longitude"]
            }
            cliente.publish(MQTT_TOPIC, json.dumps(mensaje))

        print(f"Enviadas {len(estaciones)} estaciones a MQTT", flush=True)
        time.sleep(INTERVALO_API)


if __name__ == "__main__":
    main()
