# Claude-Tokenmonitor auf dem GeekMagic SmallTV (ESP8266, 240x240).
import gc
import time

import network
import ujson
import usocket
from machine import SPI, Pin

try:
    import ustruct as struct
except ImportError:
    import struct

import config
import st7789py as st

W = 240
H = 240
M = 16  # Rand

BLACK = st.BLACK
WHITE = st.WHITE
TURQUOISE = st.color565(0x46, 0xDC, 0xFF)  # Highlight
GRAY_DARK = st.color565(0x33, 0x33, 0x33)  # Funktionsgrau, nur Flaechen
GRAY_MID = st.color565(0x66, 0x66, 0x66)
SIG_GREEN = st.color565(0x00, 0xAA, 0x00)  # Signalfarben (dunkle Variante)
SIG_ORANGE = st.color565(0xFF, 0xB9, 0x00)
SIG_RED = st.color565(0xFF, 0x28, 0x50)

# ---------------------------------------------------------------- Display

backlight = Pin(5, Pin.OUT, value=1)
spi = SPI(1, baudrate=getattr(config, "SPI_BAUD", 10000000), polarity=1, phase=1)
tft = st.ST7789(spi, W, H, reset=Pin(2, Pin.OUT), dc=Pin(0, Pin.OUT), cs=None)
tft.init()
tft.fill(BLACK)


def _lut():
    """256 Eintraege x 4 Pixel RGB565: 2-Bit-Deckkraft weiss auf schwarz."""
    shades = []
    for a in range(4):
        v = a * 255 // 3
        c = st.color565(v, v, v)
        shades.append(bytes((c >> 8, c & 0xFF)))
    out = bytearray(2048)
    i = 0
    for b in range(256):
        for shift in (6, 4, 2, 0):
            s = shades[(b >> shift) & 3]
            out[i] = s[0]
            out[i + 1] = s[1]
            i += 2
    return memoryview(out)


LUT = _lut()

# Nicht jede MicroPython-Variante kann in memoryviews per Slice schreiben.
try:
    memoryview(bytearray(2))[0:2] = b"ok"
    SLICE_ASSIGN = True
except Exception:
    SLICE_ASSIGN = False


def _row(data, w):
    """Eine Bitmapzeile (2 Bit/Pixel) in RGB565 umsetzen."""
    if not SLICE_ASSIGN:
        return b"".join([bytes(LUT[b * 8:b * 8 + 8]) for b in data])[:w * 2]
    row = bytearray(len(data) * 8)
    mrow = memoryview(row)
    j = 0
    for b in data:
        mrow[j:j + 8] = LUT[b * 8:b * 8 + 8]
        j += 8
    return mrow[:w * 2]


class Font:
    """Vorgerenderte Sen-Schrift aus assets/*.fnt (siehe tools/make_assets.py)."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            head = f.read(4)
            self.h = head[2]
            n = head[3]
            idx = f.read(7 * n)
        self.base = 4 + 7 * n
        self.glyphs = {}
        for i in range(n):
            code, w, off = struct.unpack(">HBI", idx[7 * i:7 * i + 7])
            self.glyphs[chr(code)] = (w, off)

    def width(self, s):
        g = self.glyphs
        return sum(g[c][0] for c in s if c in g)

    def draw(self, s, x, y):
        h = self.h
        with open(self.path, "rb") as f:
            for c in s:
                if c not in self.glyphs:
                    continue
                w, off = self.glyphs[c]
                rb = (w + 3) // 4
                if x + w > W:
                    break
                f.seek(self.base + off)
                data = f.read(rb * h)
                for r in range(h):
                    tft.blit_buffer(_row(data[r * rb:(r + 1) * rb], w), x, y + r, w, 1)
                x += w
        gc.collect()
        return x


BIG = Font("assets/big.fnt")
VAL = Font("assets/val.fnt")
LBL = Font("assets/lbl.fnt")


def put(font, s, x, y, align="l", clear=0):
    """Text zeichnen; align l/r/c bezogen auf x. clear = zu loeschende Breite."""
    w = font.width(s)
    if align == "r":
        x -= w
    elif align == "c":
        x -= w // 2
    if clear:
        cx = x if align == "l" else (x + w - clear if align == "r" else x + (w - clear) // 2)
        cx = max(0, cx)
        tft.fill_rect(cx, y, min(clear, W - cx), font.h, BLACK)
    font.draw(s, x, y)


def logo(x, y):
    with open("assets/logo.bin", "rb") as f:
        w, h = struct.unpack(">HH", f.read(4))
        row = bytearray(w * 2)
        for r in range(h):
            f.readinto(row)
            tft.blit_buffer(row, x, y + r, w, 1)
    return w, h


def fmt(n):
    """1234 -> 1,2K; 12345678 -> 12,3M (deutsches Komma)."""
    for div, unit in ((1000000000, "Mrd"), (1000000, "M"), (1000, "K")):
        if n >= div:
            v = n / div
            s = ("%.1f" % v) if v < 100 else ("%d" % v)
            return s.replace(".", ",") + unit
    return str(n)


# ---------------------------------------------------------------- Netzwerk

wlan = network.WLAN(network.STA_IF)


def wifi():
    if wlan.isconnected():
        return True
    wlan.active(True)
    wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
    for _ in range(40):
        if wlan.isconnected():
            return True
        time.sleep_ms(250)
    return False


def fetch():
    addr = usocket.getaddrinfo(config.BRIDGE_HOST, config.BRIDGE_PORT)[0][-1]
    s = usocket.socket()
    s.settimeout(8)
    try:
        s.connect(addr)
        req = "GET /usage HTTP/1.0\r\nHost: %s\r\n\r\n" % config.BRIDGE_HOST
        s.send(req.encode())
        data = b""
        while True:
            chunk = s.recv(512)
            if not chunk:
                break
            data += chunk
    finally:
        s.close()
    sep = data.find(b"\r\n\r\n")
    status_line = data[:data.find(b"\r\n")]
    if sep < 0 or b" 200 " not in status_line:
        raise OSError("HTTP " + status_line[:40].decode())
    return ujson.loads(data[sep + 4:].decode())


# ---------------------------------------------------------------- Layout
#   16..40   Claude-Logo links, Uhrzeit rechts, Statusquadrat
#   56..70   "Claude Tokens heute"
#   76..118  Tokens heute (Sen Bold)
#  126..130  Fortschritt zum Tagesziel
#  146..179  Woche | Monat | API-Wert
#  192..216  letzte 7 Tage (heute in Tuerkis)
#  222..236  Wochentage

COLS = (M, M + 72, M + 144)
BAR_TOP, BAR_H, BAR_W, BAR_GAP = 192, 24, 22, 9

last = {}


def changed(key, value):
    if last.get(key) == value:
        return False
    last[key] = value
    return True


def splash(msg=""):
    tft.fill(BLACK)
    backlight.value(0)  # LOW = an
    lw, lh = 120, 24
    logo((W - lw) // 2, 92)
    put(LBL, "Code usage monitor", W // 2, 126, "c")
    if msg:
        put(LBL, msg, W // 2, 200, "c", clear=W)


def frame():
    tft.fill(BLACK)
    logo(M, 16)
    put(LBL, "Claude Tokens heute", M, 56)
    labels = ("Woche", "Monat", "API-Wert")
    for x, text in zip(COLS, labels):
        put(LBL, text, x, 146)
    last.clear()


def status(ok):
    if changed("ok", ok):
        tft.fill_rect(W - M - 6, 21, 6, 6, SIG_GREEN if ok else SIG_RED)


def draw(d):
    if changed("t", d["t"]):
        put(VAL, d["t"], W - M - 12, 18, "r", clear=60)

    big = fmt(d["today"])
    if changed("big", big):
        tft.fill_rect(M, 76, W - 2 * M, BIG.h, BLACK)
        put(BIG, big, M, 76)

    goal = getattr(config, "DAILY_GOAL", 0)
    if goal and changed("bar", d["today"]):
        frac = min(d["today"] / goal, 1.0)
        col = TURQUOISE if frac < 0.7 else (SIG_ORANGE if frac < 1.0 else SIG_RED)
        full = W - 2 * M
        fill = int(full * frac)
        tft.fill_rect(M, 126, full, 4, GRAY_DARK)
        if fill:
            tft.fill_rect(M, 126, fill, 4, col)

    values = (fmt(d["week"]), fmt(d["month"]), ("%.2f $" % d["usd"]).replace(".", ","))
    for i, v in enumerate(values):
        if changed("v%d" % i, v):
            put(VAL, v, COLS[i], 163, clear=68)

    days = d["days"]
    if changed("days", tuple(days)):
        peak = max(max(days), 1)
        tft.fill_rect(0, BAR_TOP, W, BAR_H, BLACK)
        tft.fill_rect(0, 222, W, LBL.h, BLACK)
        labels = d.get("dl", "")
        for i, v in enumerate(days[:7]):
            x = M + i * (BAR_W + BAR_GAP)
            h = max(v * BAR_H // peak, 1 if v else 0)
            if h:
                today = i == 6
                tft.fill_rect(x, BAR_TOP + BAR_H - h, BAR_W, h, TURQUOISE if today else GRAY_MID)
            if i < len(labels):
                put(LBL, labels[i], x + BAR_W // 2, 222, "c")


# ---------------------------------------------------------------- Hauptschleife

def main():
    splash("WLAN ...")
    first = True
    while True:
        try:
            if not wifi():
                raise OSError("kein WLAN")
            d = fetch()
            if first:
                frame()
                first = False
            draw(d)
            status(True)
        except Exception as e:  # weiterlaufen, beim naechsten Mal neu versuchen
            print("Fehler:", e)
            if first:
                splash(str(e)[:32])
            else:
                status(False)
        gc.collect()
        time.sleep(config.POLL_SECONDS)


main()
