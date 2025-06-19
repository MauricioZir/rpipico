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
sensor = dht.DHT11(machine.Pin(15))  # Sensor de temperatura y humedad DHT11
led = machine.Pin("LED", machine.Pin.OUT) # LED on board del Raspberry

#Periodo en cuanto publica los datos de humedad y temperatura
periodo = 13


# Manejo de mensajes MQTT para el Switch
async def messages(client):
    async for topic, msg, retained in client.queue:
        try:
            topic = topic.decode()
            msg = msg.decode()
        except Exception as e:
            print(f"Error al decodificar mensaje MQTT: {e}")
            continue

        if topic.endswith("/switch"):
            if msg == "ON":
                led.value(1)
                await client.publish(f"{id_dispositivo}/estado","ON", qos=1)
            elif msg == "OFF":
                led.value(0)
                await client.publish(f"{id_dispositivo}/estado","OFF", qos=1)
            else:
                print(f"Comando desconocido: {msg}")
        else:
            print(f"Tópico no manejado: {topic} -> {msg}")


# Manejo de conexión MQTT
async def up(client):
    while True:
        await client.up.wait()
        client.up.clear()
        try:
            topics = ["switch"]
            for t in topics:
                await client.subscribe(f"{id_dispositivo}/{t}", 1)
            print("Conexión MQTT establecida y suscripciones renovadas")
        except Exception as e:
            print(f"Error al suscribirse a los tópicos: {e}")


# Publicación de datos periódica de temperatura y humedad desde el sensor
async def publicar_datos(client):
    while True:
        try:
            sensor.measure()
            data = {
                "temperatura": sensor.temperature(),
                "humedad": sensor.humidity(),
            }
            await client.publish(f"{id_dispositivo}/mediciones", json.dumps(data), qos=1)
        except Exception as e:
            print(f"Error al publicar datos al broker: {e}")
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

