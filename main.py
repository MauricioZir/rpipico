# Germán Andrés Xander 2024

from machine import Pin
import time

print("\nesperando pulsador")

sw = Pin(28, Pin.IN, Pin.PULL_DOWN)
led_board = Pin("LED", Pin.OUT)
contador = 0
bandera = True

while True:
    try:
        if sw.value() and bandera:
            bandera = False
            led_board.toggle()
            # led_board.value(not led_board.value())
            contador += 1
            print(contador)
        elif not sw.value():
            bandera = True
        time.sleep_ms(5)
    except KeyboardInterrupt:
        print('Keyboard interrupt at loop level.')
        break
