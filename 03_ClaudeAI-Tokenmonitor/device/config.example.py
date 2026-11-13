# Kopieren nach config.py und anpassen. config.py nicht einchecken.

WIFI_SSID = "MeinWLAN"
WIFI_PASSWORD = "geheim"

# IP-Adresse des Rechners, auf dem usage_bridge.py laeuft
BRIDGE_HOST = "192.168.178.20"
BRIDGE_PORT = 8765

# Abfrageintervall in Sekunden
POLL_SECONDS = 60

# Tagesziel fuer den Fortschrittsbalken (Tokens inkl. Cache)
DAILY_GOAL = 20000000

# SPI-Takt; 10 MHz ist getestet, 40 MHz zeichnet schneller
SPI_BAUD = 10000000
