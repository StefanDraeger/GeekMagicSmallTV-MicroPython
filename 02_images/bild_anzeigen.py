from machine import Pin, SPI
import os
import st7789py

WIDTH = 240
HEIGHT = 240
IMAGE_PATH = "/landschaft.rgb565"

# Das Bild liegt als RGB565 vor: zuerst das hoeherwertige Byte.
expected_size = WIDTH * HEIGHT * 2
if os.stat(IMAGE_PATH)[6] != expected_size:
    raise ValueError("Bilddatei muss genau 115200 Byte gross sein")

# Getestete CryptoTracker-Pinbelegung, Hintergrundlicht invertiert.
backlight = Pin(5, Pin.OUT, value=1)
spi = SPI(1, baudrate=10000000, polarity=1, phase=1)
display = st7789py.ST7789(
    spi, WIDTH, HEIGHT,
    reset=Pin(2, Pin.OUT),
    dc=Pin(0, Pin.OUT),
    cs=None
)
display.init()

# Nur eine Zeile mit 480 Byte im RAM halten.
row = bytearray(WIDTH * 2)
with open(IMAGE_PATH, "rb") as image:
    for y in range(HEIGHT):
        if image.readinto(row) != len(row):
            raise ValueError("Bilddatei ist unvollstaendig")
        display.blit_buffer(row, 0, y, WIDTH, 1)

backlight.value(0)
print("Landschaft angezeigt: 240 x 240 Pixel")
