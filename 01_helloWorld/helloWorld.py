from machine import Pin, SPI
import framebuf
import st7789py

# Vermutete SmallTV-Belegung:
# SCLK = GPIO14, MOSI = GPIO13
# DC = GPIO0, Reset = GPIO2
# Hintergrundlicht = GPIO5, LOW bedeutet an

backlight = Pin(5, Pin.OUT, value=1)

spi = SPI(
    1,
    baudrate=10000000,
    polarity=1,
    phase=1
)

display = st7789py.ST7789(
    spi,
    240,
    240,
    reset=Pin(2, Pin.OUT),
    dc=Pin(0, Pin.OUT),
    cs=None
)

display.init()
display.fill(st7789py.BLACK)
backlight.value(0)

# Kleiner monochromer Textpuffer statt Vollbildpuffer
text = "Hello World!"
width = len(text) * 8
height = 8
buffer = bytearray(width * height // 8)
text_image = framebuf.FrameBuffer(
    buffer, width, height, framebuf.MONO_HLSB
)
text_image.text(text, 0, 0, 1)

# Schrift doppelt so groß und mittig zeichnen
scale = 2
start_x = (240 - width * scale) // 2
start_y = (240 - height * scale) // 2

for y in range(height):
    for x in range(width):
        if text_image.pixel(x, y):
            display.fill_rect(
                start_x + x * scale,
                start_y + y * scale,
                scale,
                scale,
                st7789py.WHITE
            )

print("Displaytest ausgeführt")