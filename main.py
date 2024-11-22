from machine import Pin
from time import sleep

pin = Pin("LED", Pin.OUT)

print("LED esta destellando...")
while True:
    try:
        pin.toggle()
        sleep(.5) # sleep 1sec
    except KeyboardInterrupt:
        break
pin.off()
print("Listo")
