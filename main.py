import machine
import uasyncio as asyncio
import dht
from mqtt_as import MQTTClient
from mqtt_local import config
import ujson as json

# Obtener un ID único basado en la dirección MAC del Raspberry Pi Pico 2W
id_dispositivo = "".join("{:02X}".format(b) for b in machine.unique_id())
print(id_dispositivo)

# Definición de pines
sensor = dht.DHT11(machine.Pin(15))  # Sensor de temperatura y humedad DHT22
rele = machine.Pin(2, machine.Pin.OUT)  # Relé para controlar calefacción
led = machine.Pin("LED", machine.Pin.OUT) # LED on board del Raspberry

# Diccionario para almacenar el estado
estado = {
    "setpoint": 20,
    "periodo": 10,
    "modo": "auto",
    "rele": 0
}

# Leer configuración desde archivo JSON
def leer_parametros():
    try:
        with open("config.json", "r") as f:
            estado.update(json.load(f))  # Actualiza el diccionario con los valores leídos
    except (OSError, ValueError):
        pass  # Si falla, mantiene los valores por defecto

# Guardar configuración en archivo JSON
def guardar_parametros():
    try:
        with open("config.json", "w") as f:
            json.dump(estado, f)
        print("Parámetros guardados.")
    except Exception as e:
        print(f"Error al guardar parámetros: {e}")

# Cargar valores almacenados
leer_parametros()

# Parpadeo del LED
async def destellar_led():
    try:
        for _ in range(5):
            led.on()
            await asyncio.sleep(0.5)
            led.off()
            await asyncio.sleep(0.5)
    except Exception as e:
        print(f"Error al destellar LED: {e}")

# Control del relé
async def actualizar_rele():
    try:
        await asyncio.sleep(0)  # Cede control antes de cualquier operación
        if estado["modo"] == "auto":
            rele.value(0 if sensor.temperature() > estado["setpoint"] else 1)
            estado["rele"] = rele.value()
        else:
            rele.value(estado["rele"])
    except Exception as e:
        print(f"Error en actualizar el relé: {e}")

# Manejo de mensajes MQTT
async def messages(client):
    async for topic, msg, retained in client.queue:
        try:
            topic = topic.decode()
            msg = msg.decode()
        except Exception as e:
            print(f"Error al decodificar mensaje MQTT: {e}")
            continue  # Ignorar este mensaje y seguir con el siguiente

        if topic.endswith("/setpoint"):
            estado["setpoint"] = int(msg)
        elif topic.endswith("/periodo"):
            estado["periodo"] = int(msg)
        elif topic.endswith("/modo"):
            estado["modo"] = msg
        elif topic.endswith("/rele"):
            estado["rele"] = 1 if estado["rele"] == 0 else 0
        elif topic.endswith("/destello") and msg == "destello":
            asyncio.create_task(destellar_led())
        else:
            print(f"Mensaje en tópico desconocido: {topic} -> {msg}")
            continue  # No hacer nada si es un tópico desconocido
        guardar_parametros()
        await actualizar_rele()

# Manejo de conexión MQTT
async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        try:
            topics = ["setpoint", "periodo", "modo", "rele", "destello"]
            for t in topics:
                await client.subscribe(f"{id_dispositivo}/{t}", 1)
            print("Conexión MQTT establecida y suscripciones renovadas")
        except Exception as e:
            print(f"Error al suscribirse a los tópicos: {e}")

# Publicación de datos periódica
async def publicar_datos(client):
    while True:
        try:
            sensor.measure()
            await actualizar_rele()
            data = {
                "temperatura": sensor.temperature(),
                "humedad": sensor.humidity(),
                "setpoint": estado["setpoint"],
                "periodo": estado["periodo"],
                "modo": estado["modo"]
            }
            print(data)
            await client.publish(id_dispositivo, json.dumps(data), qos=1)
        except Exception as e:
            print(f"Error al publicar datos al broker: {e}")
        await asyncio.sleep(estado["periodo"])

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
