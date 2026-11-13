# Bilder im RGB565-Format anzeigen

Dieses Beispiel zeigt ein Bild auf dem 240 × 240 Pixel großen Farbdisplay des GeekMagic SmallTV mit ESP8266 und MicroPython. Das Bild wird vorher am Computer in eine RGB565-Rohdatei umgewandelt und anschließend zusammen mit dem Beispielprogramm auf den SmallTV übertragen.

Die Vorbereitung am Computer erspart dem ESP8266 die Dekodierung von PNG- oder JPEG-Dateien. Das Beispiel liest die fertigen Pixeldaten zeilenweise ein, statt das gesamte Bild im Arbeitsspeicher abzulegen.

## Voraussetzungen

- GeekMagic SmallTV mit ESP8266 und ST7789-Display, passend zur Hardwarekonfiguration des Beispiels.
- Installierte MicroPython-Firmware.
- Verbindung zum Gerät, beispielsweise über Thonny.
- Displaytreiber `st7789py.py` im Verzeichnis `/lib` auf dem Gerät.
- Ein vorbereitetes Bild im nachfolgend beschriebenen RGB565-Format.

Hinweise zum Displaytreiber findest du in der [README des Ordners lib](../lib/README.md). Verwende die zum Beispiel passende Treiberversion; gleichnamige Dateien aus verschiedenen Forks sind nicht automatisch austauschbar.

## Bildformat

Das Programm erwartet rohe Pixeldaten mit folgenden Eigenschaften:

| Eigenschaft | Vorgabe |
| --- | --- |
| Auflösung | Genau 240 × 240 Pixel |
| Farbformat | RGB565: 5 Bit Rot, 6 Bit Grün, 5 Bit Blau |
| Speicherbedarf | 2 Byte pro Pixel |
| Byte-Reihenfolge | Big Endian: höherwertiges Byte zuerst |
| Pixelreihenfolge | Zeilenweise von links nach rechts, oben nach unten |
| Dateikopf, Palette, Kompression | Keine |
| Dateigröße | Genau 115.200 Byte |

Eine PNG- oder JPG-Datei lediglich umzubenennen genügt nicht. Die Bilddaten müssen tatsächlich konvertiert werden. Transparente Bereiche werden vor der Konvertierung auf einen schwarzen Hintergrund verrechnet.

## PNG oder JPG vorbereiten

Bringe dein Ausgangsbild zunächst auf 240 × 240 Pixel. Wähle den Ausschnitt so, dass das Motiv auf dem kleinen Display gut erkennbar bleibt. Große Formen, klare Konturen und deutliche Kontraste eignen sich besser als kleine Schrift oder sehr feine Details.

Die Umrechnung eines RGB-Pixels mit Kanalwerten von 0 bis 255 erfolgt so:

```python
wert = ((rot >> 3) << 11) | ((gruen >> 2) << 5) | (blau >> 3)
```

Gespeichert werden zuerst `(wert >> 8) & 0xFF` und danach `wert & 0xFF`.

### Bild mit KI-Unterstützung konvertieren

Wenn deine KI-Umgebung Dateien mit Python verarbeiten kann, kannst du folgenden Prompt zusammen mit deinem Bild verwenden:

> Konvertiere das angehängte Bild mit genau 240 × 240 Pixeln mit Python in eine RGB565-Rohdatei. Erzeuge das Motiv nicht neu und ändere die Auflösung nicht. Verwende 5 Bit Rot, 6 Bit Grün und 5 Bit Blau. Speichere pro Pixel zwei Byte, höherwertiges Byte zuerst (Big Endian). Schreibe die Pixel zeilenweise von links nach rechts und von oben nach unten. Verwende keinen Dateikopf, keine Palette und keine Kompression. Verrechne transparente Bereiche auf Schwarz. Nenne die Datei bild.rgb565, prüfe die Dateigröße von genau 115.200 Byte und stelle die konvertierte Datei zum Download bereit.

Die KI unterstützt dabei die Dateikonvertierung. Die eigentliche Umrechnung muss durch ausgeführten Code erfolgen; eine Beschreibung oder ein neu generiertes Bild ersetzt die Rohdatei nicht.

## Dateien auf den SmallTV übertragen

1. Kopiere den Displaytreiber nach `/lib/st7789py.py`, falls er noch nicht auf dem Gerät liegt.
2. Übertrage das Python-Beispiel aus diesem Verzeichnis auf den SmallTV.
3. Kopiere die RGB565-Datei auf das Gerät. Der im Beispielprogramm eingestellte Bildpfad muss genau zu ihrem Speicherort und Dateinamen passen.
4. Starte das Beispielprogramm über Thonny.

Die Bilddatei muss auf dem MicroPython-Dateisystem liegen. Eine Datei, die nur auf dem Computer vorhanden ist, kann das Programm auf dem ESP8266 nicht öffnen.

Für einen automatischen Start nach dem Einschalten muss das Beispiel als `/main.py` vorliegen oder aus einer vorhandenen `main.py` aufgerufen werden. Sichere eine bereits vorhandene `main.py`, bevor du sie ersetzt.

## So funktioniert die Ausgabe

Eine Bildzeile umfasst 240 Pixel und damit 480 Byte. Das Beispiel liest jeweils eine Zeile aus der Datei und überträgt sie an die entsprechende Position des Displays. Für die Bilddaten wird dadurch nur ein kleiner Zeilenpuffer benötigt. Ein vollständiger Bildpuffer würde allein 115.200 Byte beanspruchen, zusätzlich zum Speicherbedarf von MicroPython und Programm.

Nach erfolgreichem Laden zeigt das Display das Bild über die gesamte Fläche. Für ein anderes Motiv genügt es, eine passende RGB565-Datei zu übertragen und bei Bedarf den Bildpfad anzupassen.

## Fehlersuche

| Problem | Prüfen |
| --- | --- |
| Bilddatei nicht gefunden | Liegt sie auf dem Gerät? Stimmen Pfad, Name und Groß-/Kleinschreibung? |
| Falsche Dateigröße | Die unkomprimierte Datei muss bei 240 × 240 Pixeln genau 115.200 Byte groß sein. |
| Verfälschte Farben | Byte-Reihenfolge der Datei und RGB-/BGR-Einstellung des Treibers prüfen. |
| Verschobenes oder gedrehtes Bild | Auflösung, Rotation und Display-Offsets im Beispiel prüfen. |
| Display bleibt dunkel | Displayinitialisierung, Pinbelegung und Hintergrundbeleuchtung prüfen. |
| Fehler bei `display.init()` | Treiberversion prüfen: Die Russ-Hughes-Version initialisiert bereits im Konstruktor und erwartet bei `init()` eine Befehlsliste. |

## Weiterführende Links

- [Projektübersicht auf GitHub](https://github.com/StefanDraeger/GeekMagicSmallTV-MicroPython)
- [Original-Repository des Displaytreibers](https://github.com/russhughes/st7789py_mpy)
- [Blog: GeekMagic SmallTV mit MicroPython umprogrammieren](https://draeger-it.blog/geekmagic-smalltv-micropython/)
