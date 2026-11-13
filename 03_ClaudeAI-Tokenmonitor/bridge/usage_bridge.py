"""Claude-Code-Tokenverbrauch fuer das GeekMagic SmallTV bereitstellen.

Liest die lokalen Claude-Code-Transkripte (~/.claude/projects/**/*.jsonl),
summiert den Tokenverbrauch und liefert eine kleine JSON-Antwort per HTTP,
die das SmallTV im WLAN abholt.

Start:
    python usage_bridge.py              # HTTP-Server auf Port 8765
    python usage_bridge.py --once       # einmal ausgeben und beenden
    python usage_bridge.py --port 9000 --bind 0.0.0.0

Nur Standardbibliothek, Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import threading
import time
import functools
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Preise in USD pro 1 Mio. Tokens: (input, output, cache_read).
# Nur eine Schaetzung zu API-Listenpreisen; bei einer Enterprise-Lizenz
# zahlt ihr pro Sitz, nicht pro Token. Laengster passender Praefix gewinnt.
PRICES = {
    "claude-fable-5-2": (8.00, 40.00, 0.20),
    "claude-mythos-5-2": (8.00, 40.00, 0.20),
    "claude-fable-5": (10.00, 50.00, 1.00),
    "claude-mythos-5": (10.00, 50.00, 1.00),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-opus-5": (5.00, 25.00, 0.50),
    "claude-opus-4": (5.00, 25.00, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00, 0.10),
    "claude-sonnet-5": (2.00, 10.00, 0.20),
    "claude-sonnet-4": (3.00, 15.00, 0.30),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "claude-haiku-4": (1.00, 5.00, 0.10),
}
CACHE_WRITE_5M = 1.25  # Faktor auf den Input-Preis
CACHE_WRITE_1H = 2.0

print = functools.partial(print, flush=True)  # sofort ins Log schreiben

WEEKDAYS = "MDMDFSS"  # Mo..So


def projects_dir() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    root = Path(base) if base else Path.home() / ".claude"
    return root / "projects"


def price_for(model: str):
    best = None
    for prefix, price in PRICES.items():
        if model.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, price)
    return best[1] if best else None


class UsageStore:
    """Liest JSONL-Dateien inkrementell und haelt eine Nachricht pro ID."""

    def __init__(self, root: Path):
        self.root = root
        self.offsets: dict[Path, int] = {}
        # (message.id, requestId) -> (lokales Datum, model, in, out, cache_read, cw5m, cw1h)
        self.entries: dict[tuple, tuple] = {}
        self.lock = threading.Lock()

    def refresh(self) -> None:
        with self.lock:
            if not self.root.is_dir():
                return
            for path in self.root.rglob("*.jsonl"):
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                start = self.offsets.get(path, 0)
                if size < start:  # Datei wurde gekuerzt/ersetzt
                    start = 0
                if size == start:
                    continue
                self.offsets[path] = self._read_from(path, start)

    def _read_from(self, path: Path, start: int) -> int:
        with open(path, "rb") as fh:
            fh.seek(start)
            data = fh.read()
        end = data.rfind(b"\n")
        if end < 0:  # noch keine vollstaendige Zeile
            return start
        for raw in data[: end + 1].splitlines():
            self._ingest(raw)
        return start + end + 1

    def _ingest(self, raw: bytes) -> None:
        if b'"usage"' not in raw:
            return
        try:
            rec = json.loads(raw)
        except ValueError:
            return
        msg = rec.get("message")
        if not isinstance(msg, dict):
            return
        usage = msg.get("usage")
        model = msg.get("model") or ""
        ts = rec.get("timestamp")
        if not isinstance(usage, dict) or not ts or model.startswith("<"):
            return
        try:
            day = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().date()
        except ValueError:
            return
        cache = usage.get("cache_creation") or {}
        cw_total = usage.get("cache_creation_input_tokens") or 0
        cw1h = cache.get("ephemeral_1h_input_tokens") or 0
        cw5m = cache.get("ephemeral_5m_input_tokens")
        if cw5m is None:
            cw5m = max(cw_total - cw1h, 0)
        key = (msg.get("id") or id(rec), rec.get("requestId"))
        # Gestreamte Antworten stehen mehrfach im Log; der letzte Eintrag gewinnt.
        self.entries[key] = (
            day,
            model,
            usage.get("input_tokens") or 0,
            usage.get("output_tokens") or 0,
            usage.get("cache_read_input_tokens") or 0,
            cw5m,
            cw1h,
        )

    def summary(self) -> dict:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        per_day = {d: 0 for d in days}

        t_in = t_out = t_cr = t_cw = 0
        week = month = 0
        usd = 0.0
        unpriced = set()

        with self.lock:
            for day, model, i, o, cr, cw5m, cw1h in self.entries.values():
                total = i + o + cr + cw5m + cw1h
                if day in per_day:
                    per_day[day] += total
                if day >= month_start:
                    month += total
                if day >= week_start:
                    week += total
                if day != today:
                    continue
                t_in += i
                t_out += o
                t_cr += cr
                t_cw += cw5m + cw1h
                price = price_for(model)
                if price is None:
                    unpriced.add(model)
                    continue
                p_in, p_out, p_cr = price
                usd += (
                    i * p_in
                    + o * p_out
                    + cr * p_cr
                    + cw5m * p_in * CACHE_WRITE_5M
                    + cw1h * p_in * CACHE_WRITE_1H
                ) / 1_000_000

        return {
            "t": datetime.now().strftime("%H:%M"),
            "today": t_in + t_out + t_cr + t_cw,
            "in": t_in,
            "out": t_out,
            "cr": t_cr,
            "cw": t_cw,
            "week": week,
            "month": month,
            "usd": round(usd, 2),
            "days": [per_day[d] for d in days],
            "dl": "".join(WEEKDAYS[d.weekday()] for d in days),
            "unpriced": sorted(unpriced),
        }


class Handler(BaseHTTPRequestHandler):
    store: UsageStore
    min_interval = 10.0
    _last_refresh = 0.0

    def do_GET(self):  # noqa: N802
        if self.path.split("?")[0] not in ("/", "/usage"):
            self.send_error(404)
            return
        now = time.monotonic()
        if now - Handler._last_refresh >= self.min_interval:
            self.store.refresh()
            Handler._last_refresh = now
        body = json.dumps(self.store.summary(), separators=(",", ":")).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        print("%s %s" % (self.address_string(), fmt % args))


def local_ips() -> list[str]:
    """IPv4-Adressen dieses Rechners (ohne Loopback/Link-local)."""
    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
    except OSError:
        return []
    ips = {info[4][0] for info in infos}
    return sorted(ip for ip in ips if not ip.startswith(("127.", "169.254.")))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bind", default="0.0.0.0", help="Adresse (Standard: alle)")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--once", action="store_true", help="einmal ausgeben und beenden")
    args = ap.parse_args()

    store = UsageStore(projects_dir())
    t0 = time.monotonic()
    store.refresh()
    print(
        "%d Antworten aus %d Dateien in %.1fs gelesen (%s)"
        % (len(store.entries), len(store.offsets), time.monotonic() - t0, store.root)
    )
    if args.once:
        print(json.dumps(store.summary(), indent=2))
        return

    Handler.store = store
    Handler._last_refresh = time.monotonic()
    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    if args.bind in ("0.0.0.0", ""):
        hosts = ["localhost"] + local_ips()
    else:
        hosts = [args.bind]
    print("Bridge laeuft. Erreichbar unter:")
    for host in hosts:
        print("  http://%s:%d/usage" % (host, args.port))
    print("Fuer config.py BRIDGE_HOST die IP aus dem WLAN des SmallTV nehmen.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
