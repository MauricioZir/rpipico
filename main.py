from machine import Pin
from time import sleep

led_board = Pin("LED", Pin.OUT)
sleep(1)    #le damos tiempo a vREPL
print("\nLED esta destellando...")
while True:
    try:
        led_board.toggle()
        # led_board.value(not led_board.value())
        sleep(.5) # sleep 1sec
    except KeyboardInterrupt:
        break
led_board.off()
print("Listo")
