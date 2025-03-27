import machine
import uasyncio as asyncio
import btree
import dht
from mqtt_as import MQTTClient
from mqtt_local import config
import json

# Obtener un ID único basado en la dirección MAC del Raspberry Pi Pico W
id_dispositivo = ""
for b in machine.unique_id():
    id_dispositivo += "{:02X}".format(b)

# Definición de pines
sensor = dht.DHT22(machine.Pin(15))  # Sensor de temperatura y humedad DHT22
rele = machine.Pin(2, machine.Pin.OUT)  # Relé para controlar calefacción
led = machine.Pin(25, machine.Pin.OUT)  # LED indicador en la placa

# Abrir o crear base de datos para almacenamiento no volátil
try:
    f = open("config.db", "r+b")
except OSError:
    f = open("config.db", "w+b")
db = btree.open(f)

# Cargar valores almacenados o establecer valores predeterminados
setpoint = int(db.get(b"setpoint", b"25"))
periodo = int(db.get(b"periodo", b"10"))
modo = db.get(b"modo", b"auto").decode()
rele_estado = int(db.get(b"rele", b"0"))

def guardar_parametros():
    """Guarda los parámetros en memoria no volátil."""
    db[b"setpoint"] = str(setpoint).encode()
    db[b"periodo"] = str(periodo).encode()
    db[b"modo"] = modo.encode()
    db[b"rele"] = str(rele_estado).encode()
    db.flush()

async def manejar_mensajes(topic, msg, retained):
    """Maneja los mensajes recibidos por MQTT y actualiza los parámetros."""
    global setpoint, periodo, modo, rele_estado
    topic = topic.decode()
    msg = msg.decode()
    
    if topic.endswith("/setpoint"):
        setpoint = int(msg)
    elif topic.endswith("/periodo"):
        periodo = int(msg)
    elif topic.endswith("/modo"):
        modo = msg
    elif topic.endswith("/rele"):
        rele_estado = int(msg)
    elif topic.endswith("/destello"):
        for _ in range(5):
            led.on()
            await asyncio.sleep(0.5)
            led.off()
            await asyncio.sleep(0.5)
    
    guardar_parametros()
    actualizar_rele()

def actualizar_rele():
    """Controla el estado del relé según el modo de operación."""
    if modo == "auto":
        sensor.measure()
        temperatura = sensor.temperature()
        rele.value(temperatura > setpoint)
    else:
        rele.value(rele_estado)

async def publicar_datos(client):
    """Publica periódicamente los datos del sensor en MQTT."""
    while True:
        sensor.measure()
        data = {
            "temperatura": sensor.temperature(),
            "humedad": sensor.humidity(),
            "setpoint": setpoint,
            "periodo": periodo,
            "modo": modo
        }
        await client.publish(id_dispositivo, json.dumps(data), qos=1)
        await asyncio.sleep(periodo)

async def conexion_exitosa(client):
    """Se ejecuta cuando se establece la conexión MQTT."""
    await client.subscribe(f"{id_dispositivo}/setpoint", 1)
    await client.subscribe(f"{id_dispositivo}/periodo", 1)
    await client.subscribe(f"{id_dispositivo}/modo", 1)
    await client.subscribe(f"{id_dispositivo}/rele", 1)
    await client.subscribe(f"{id_dispositivo}/destello", 1)

# Configuración de MQTT
config['subs_cb'] = manejar_mensajes
config['server'] = config['server']
config['connect_coro'] = conexion_exitosa
config['ssl'] = True

# Configuración y ejecución del cliente MQTT
MQTTClient.DEBUG = True
client = MQTTClient(config)

try:
    asyncio.run(publicar_datos(client))
finally:
    client.close()
    asyncio.new_event_loop()