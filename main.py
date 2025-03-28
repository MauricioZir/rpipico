import machine
import uasyncio as asyncio
import dht
import json
from mqtt_as import MQTTClient
from mqtt_local import config
import network
import time
from settings import SSID, password

# Obtener un ID único basado en la dirección MAC del Raspberry Pi Pico W
id_dispositivo = "".join("{:02X}".format(b) for b in machine.unique_id())
print(id_dispositivo)

# Definición de pines
sensor = dht.DHT22(machine.Pin(15))  # Sensor de temperatura y humedad DHT22
rele = machine.Pin(2, machine.Pin.OUT)  # Relé para controlar calefacción
led = machine.Pin(25, machine.Pin.OUT)  # LED indicador en la placa




async def wifi_han(state):
    print('WiFi está', 'conectado' if state else 'desconectado')
    await asyncio.sleep(1)






# Función para leer los parámetros desde config.json
def leer_parametros():
    """Lee los parámetros desde un archivo JSON."""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"setpoint": 25, "periodo": 10, "modo": "auto", "rele": 0}

# Cargar valores almacenados
config_data = leer_parametros()
setpoint = config_data["setpoint"]
periodo = config_data["periodo"]
modo = config_data["modo"]
rele_estado = config_data["rele"]

# Función para guardar parámetros en config.json
def guardar_parametros():
    """Guarda los parámetros en un archivo JSON."""
    with open("config.json", "w") as f:
        json.dump({"setpoint": setpoint, "periodo": periodo, "modo": modo, "rele": rele_estado}, f)

async def manejar_mensajes(topic, msg):
    """Maneja los mensajes recibidos por MQTT y actualiza los parámetros."""
    global setpoint, periodo, modo, rele_estado
    topic = topic.decode()
    msg = msg.decode()
    
    print("HOLAAAAAAAAAAAAAAAAAA")

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

    await client.connect()
    
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

        print(data)

        await client.publish(id_dispositivo, json.dumps(data), qos=1)
        await asyncio.sleep(periodo)

async def conexion_exitosa(client):
    """Se ejecuta cuando se establece la conexión MQTT."""
    await client.subscribe(f"{id_dispositivo}/setpoint", 1)
    await client.subscribe(f"{id_dispositivo}/periodo", 1)
    await client.subscribe(f"{id_dispositivo}/modo", 1)
    await client.subscribe(f"{id_dispositivo}/rele", 1)
    await client.subscribe(f"{id_dispositivo}/destello", 1)
    print("Conexión MQTT exitosa")
    
 


# Configuración de MQTT
config['subs_cb'] = manejar_mensajes
config['server'] = config['server']
config['connect_coro'] = conexion_exitosa
config['wifi_coro'] = wifi_han
config['ssl'] = True

# Configuración y ejecución del cliente MQTT
MQTTClient.DEBUG = True
client = MQTTClient(config)

try:
    asyncio.run(publicar_datos(client))
finally:
    client.close()
    asyncio.new_event_loop()











