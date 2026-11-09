# Valenbisi IoT: bicis en tiempo real

Proyecto de la práctica de Implantación de Aplicaciones Web. Recoge el estado de las estaciones de Valenbisi, lo guarda en InfluxDB, lo copia a PostgreSQL y lo muestra en una web Flask y en Grafana.

## Flujo de datos

```
collector → Mosquitto (MQTT) → Telegraf → InfluxDB
                                              ↓
                                    sync (copia cada 15 s)
                                              ↓
                                          PostgreSQL → pgAdmin
                                           ↓          ↓
                                        Flask      Grafana
```

## Requisitos

- Docker y Docker Compose.
- Git (solo si quieres clonar el repositorio).

## Puesta en marcha

1. Sitúate en la carpeta del proyecto.

2. Da permisos a la carpeta de Grafana (solo la primera vez):

   ```bash
   sudo chown -R 472:472 ./grafana
   ```

3. Arranca todos los servicios:

   ```bash
   docker compose up -d --build
   ```

4. Comprueba que todos están en marcha:

   ```bash
   docker compose ps -a
   ```

   Todos deben aparecer como `Up`.

Espera unos minutos: el colector necesita tiempo para llenar InfluxDB y `sync` para copiarlo a PostgreSQL.

## Accesos

| Servicio | Dirección | Usuario | Contraseña |
|---|---|---|---|
| Flask (web con gráficas) | http://localhost:5000 | – | – |
| Grafana | http://localhost:3000 | `admin` | `admin` (te pedirá cambiarla) |
| pgAdmin | http://localhost:5050 | `admin@valenbisi.org` | `admin12345` |
| PostgreSQL (dentro de pgAdmin) | servidor "Valenbisi Postgres" | `valenbisi` | `valenbisi_pass` |
| InfluxDB | http://localhost:8086 | `admin` | `admin12345` |

En pgAdmin, el servidor ya viene configurado. Solo te pedirá la contraseña de PostgreSQL.

## Qué muestra cada cosa

- **Flask**: dos cifras (bicicletas libres y estaciones activas) y cuatro gráficas: top 10 de estaciones, ocupación de la red, evolución en las últimas 6 horas y media por hora del día.
- **Grafana**: un gráfico de barras con el top 10 de estaciones.
- **pgAdmin**: permite consultar las tablas `estaciones`, `mediciones` y `sincronizaciones`.

## Comandos útiles

Ver si el colector envía datos:

```bash
docker compose logs collector --tail 10
```

Ver si `sync` copia datos a PostgreSQL:

```bash
docker compose logs sync --tail 10
```

Contar las mediciones guardadas:

```bash
docker compose exec postgres psql -U valenbisi -d valenbisi -c "SELECT COUNT(*) FROM mediciones;"
```

Parar todo:

```bash
docker compose down
```

## Problemas frecuentes

**"The container name ... is already in use"**
Hay un contenedor antiguo con el mismo nombre. Bórralo y vuelve a arrancar:

```bash
docker rm -f valenbisi-influxdb
docker compose up -d
```

**Grafana no arranca y aparece "permission denied"**
Ejecuta `sudo chown -R 472:472 ./grafana` y vuelve a arrancar con `docker compose up -d grafana`.

**La web aparece sin datos**
Espera unos minutos y comprueba los logs de `collector` y `sync`. Si `collector` muestra "Error consultando la API", es el límite de peticiones de la API de citybik.es: el colector espera y reintenta solo.

**Hay menos de 100 estaciones**
Las consultas solo cuentan las estaciones con datos en los últimos 15 minutos. Si el colector lleva poco tiempo en marcha, puede haber menos.

## Estructura

```
├── docker-compose.yml   Definición de todos los servicios
├── collector/           Pide datos a la API de Valenbisi y los envía por MQTT
├── telegraf/            Lleva los datos de MQTT a InfluxDB
├── mosquitto/           Broker MQTT
├── influxdb/            Datos de InfluxDB (no se sube a GitHub)
├── sync/                Copia los datos de InfluxDB a PostgreSQL
├── postgres/            Creación de tablas de PostgreSQL
├── web/                 Aplicación Flask y su plantilla HTML
├── grafana/             Configuración y dashboards de Grafana
└── pgadmin/             Configuración del servidor de pgAdmin
```

## Autor

Juan Andrés Molina Ascanio
