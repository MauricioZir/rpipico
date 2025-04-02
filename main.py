import machine
import uasyncio as asyncio
import dht
from mqtt_as import MQTTClient
from mqtt_local import config
import ujson as json

# Obtener un ID único basado en la dirección MAC del Raspberry Pi Pico W
id_dispositivo = "".join("{:02X}".format(b) for b in machine.unique_id())
print(id_dispositivo)

# Definición de pines
sensor = dht.DHT11(machine.Pin(15))  # Sensor de temperatura y humedad DHT22
rele = machine.Pin(2, machine.Pin.OUT)  # Relé para controlar calefacción
led = machine.Pin("LED", machine.Pin.OUT) # LED on board del Raspberry

# Leer configuración desde archivo JSON
def leer_parametros():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"setpoint": 20, "periodo": 10, "modo": "auto", "rele": 0}

# Guardar configuración en archivo JSON
def guardar_parametros():
    try:
        json_data = {"setpoint": setpoint, "periodo": periodo, "modo": modo, "rele": rele_estado}
        with open("config.json", "w") as f:
            json.dump(json_data, f)
        print("Parámetros guardados.")
    except Exception as e:
        print(f"Error al guardar parámetros: {e}")

# Cargar valores almacenados
config_data = leer_parametros()
setpoint = config_data["setpoint"]
periodo = config_data["periodo"]
modo = config_data["modo"]
rele_estado = config_data["rele"]

# Parpadeo del LED
async def destellar_led():
    for _ in range(5):
        led.on()
        await asyncio.sleep(0.5)
        led.off()
        await asyncio.sleep(0.5)

# Control del relé
''' Si se accede por cambiar de modo se vuelve a medir para actualizar el relé,
    si se accede por publicar datos al broker no hace falta medir de vuelta.'''
async def actualizar_rele(medir=True):
    global setpoint, modo, rele_estado
    try:
        if modo == "auto":
            if medir:
                await asyncio.sleep(0)  # Cede control antes de medir
                sensor.measure()
            rele.value(0 if sensor.temperature() > setpoint else 1)
        else:
            rele.value(rele_estado)
    except Exception as e:
        print(f"Error en actualizar el relé: {e}")


# Manejo de mensajes MQTT
''' Se ejecuta cada vez que hay un mensaje en la cola.'''
async def messages(client):
    async for topic, msg, retained in client.queue:
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
            rele_estado = 1 if rele_estado == 0 else 0
        elif topic.endswith("/destello") and msg == "destello":
            asyncio.create_task(destellar_led())
        guardar_parametros()
        asyncio.create_task(actualizar_rele(True))


# Manejo de conexión MQTT
''' Se ejecuta la primera vez cuando la conexión MQTT está lista, 
    luego solo se vuelve a ejecutar si hay una reconexión.'''
async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        topics = ["setpoint", "periodo", "modo", "rele", "destello"]
        for t in topics:
            await client.subscribe(f"{id_dispositivo}/{t}", 1)
        print("Conexión MQTT establecida y suscripciones renovadas")


# Publicación de datos periódica
''' Se ejecuta siempre a cada período.'''
async def publicar_datos(client):
    while True:
        try:
            sensor.measure()
            asyncio.create_task(actualizar_rele(False))
            data = {
                "temperatura": sensor.temperature(),
                "humedad": sensor.humidity(),
                "setpoint": setpoint,
                "periodo": periodo,
                "modo": modo
            }
            print(data)
            await client.publish(id_dispositivo, json.dumps(data), qos=1)
        except Exception as e:
            print(f"Error en publicar_datos: {e}")
        await asyncio.sleep(periodo)


# Función principal
async def main(client):
    await client.connect()
    for coroutine in (up, messages, publicar_datos):
        asyncio.create_task(coroutine(client))
    while True:
        await asyncio.sleep(10)


# Configuración de MQTT
config["queue_len"] = 1
MQTTClient.DEBUG = True
client = MQTTClient(config)

try:
    asyncio.run(main(client))
finally:
    client.close()
