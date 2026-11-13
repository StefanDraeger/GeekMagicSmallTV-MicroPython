# Displaytreiber für den GeekMagic SmallTV

Dieser Ordner enthält `st7789py.py`, den MicroPython-Treiber für den ST7789-Displaycontroller. Die Beispiele dieses Projekts verwenden ihn zur Ansteuerung des 240 × 240 Pixel großen Farbdisplays im GeekMagic SmallTV mit ESP8266.

## Herkunft

Der Treiber wurde aus folgendem Repository übernommen:

- **Repository:** [russhughes/st7789py_mpy](https://github.com/russhughes/st7789py_mpy)
- **Quelldatei:** [lib/st7789py.py](https://github.com/russhughes/st7789py_mpy/blob/master/lib/st7789py.py)
- **Dokumentation:** [ST7789 MicroPython-Treiber](https://russhughes.github.io/st7789py_mpy/)

Das Projekt von Russ Hughes basiert auf dem ursprünglichen Treiber von [devbis](https://github.com/devbis/st7789py_mpy). Der Treiber ist eine eingebundene Fremdbibliothek; die Urheberschaft liegt bei den im Quellcode genannten Autoren.

## Auf dem ESP8266 ablegen

Kopiere `st7789py.py` in das Verzeichnis `/lib` auf dem MicroPython-Dateisystem des SmallTV. Lege den Ordner an, falls er noch nicht vorhanden ist.

| Datei | Ziel auf dem SmallTV |
| --- | --- |
| `st7789py.py` | `/lib/st7789py.py` |

Die README dient nur als Dokumentation und muss nicht auf den Mikrocontroller übertragen werden. Der Ordner `lib` auf deinem Computer oder in diesem GitHub-Repository allein reicht nicht aus: Die Treiberdatei muss auch auf dem Gerät liegen.

## Import prüfen

Führe nach dem Übertragen in der MicroPython-Shell folgenden Test aus:

```python
import st7789py
print("Displaytreiber geladen")
```

Wenn die Meldung erscheint, konnte MicroPython das Modul importieren. Dieser Test initialisiert das Display noch nicht und prüft weder die Pinbelegung noch die Bildausgabe.

Die Displayinitialisierung und die gerätespezifischen Einstellungen übernehmen die jeweiligen Beispielprogramme. Zusätzliche Schrift- oder Bildmodule müssen ebenfalls übertragen werden, sofern ein Beispiel sie importiert.

## Hinweise zur Treiberversion

Verwende die im Projekt mitgelieferte Treiberdatei zusammen mit den dazugehörigen Beispielen. Gleichnamige Dateien aus anderen Forks können eine andere Schnittstelle besitzen.

Bei der hier verlinkten Russ-Hughes-Version erfolgt die Displayinitialisierung bereits im Konstruktor von `ST7789`. Ein zusätzlicher parameterloser Aufruf von `display.init()` passt nicht zu dieser Version, da deren `init()`-Methode eine Befehlsliste erwartet.

## Fehlersuche

- **`ImportError` beim Import:** Prüfe, ob die Datei auf dem Gerät tatsächlich `/lib/st7789py.py` heißt. Kontrolliere auch Groß- und Kleinschreibung sowie versehentliche Endungen wie `.py.txt`.
- **Import funktioniert, Display bleibt dunkel:** Prüfe die Displaykonfiguration und die Ansteuerung der Hintergrundbeleuchtung im Beispielprogramm.
- **Fehlende Methode oder unpassende Argumente:** Prüfe, ob Beispiel und Treiber aus derselben vorgesehenen Version stammen.

## Lizenz und Urheberhinweise

Der eingebundene Treiber steht unter der [MIT-Lizenz des Originalprojekts](https://github.com/russhughes/st7789py_mpy/blob/master/LICENSE). Die Lizenz- und Copyright-Hinweise befinden sich auch am Anfang von `st7789py.py` und müssen bei einer Weitergabe erhalten bleiben.

Eine Lizenz für die eigenen Beispiele dieses Repositorys ersetzt die Lizenz des eingebundenen Treibers nicht.
