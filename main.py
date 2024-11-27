# Germán Andrés Xander 2024

from machine import Pin
import time

print("\nesperando pulsador")

sw = Pin(28, Pin.IN, Pin.PULL_DOWN)
led = Pin("LED", Pin.OUT)
contador=0
bandera=True

while True:
    try:
        if sw.value() and bandera:
            bandera=False
            led.toggle()
            # led.value(not led.value())
            contador += 1
            print(contador)
        elif not sw.value():
            bandera=True
        time.sleep_ms(5)
    except KeyboardInterrupt:
        break
