#!/usr/bin/env python3
"""
Mock de `dashWhat2` para desarrollo LOCAL — cierra el loop de SALIDA.

`dashWhat2` real es Baileys (WhatsApp). Acá NO hay WhatsApp: este servicio hace
dos cosas, en un solo contenedor:

  1. Sirve el simulador de chat (`chat_simulator.html`) como página.
  2. Escucha `POST /send-message` — el endpoint que el backend usa para mandarle
     mensajes al cliente o al admin (`services/notification.service.js`) — y los
     guarda. El simulador los lee por `GET /outbox` y los muestra en el chat.

Así el ciclo queda completo en local:
  cliente/admin -> backend (/api/messages) -> ... -> backend -> /send-message -> acá

Variables:
  PORT              puerto de escucha (default 8880, igual que dashWhat2)
  STATIC_DIR        carpeta con el HTML a servir (default /static)
  OUTBOX_MAX        máximo de mensajes guardados en memoria (default 500)
"""
import json
import os
import posixpath
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

PORT = int(os.getenv("PORT", "8880"))
STATIC_DIR = os.getenv("STATIC_DIR", "/static")
OUTBOX_MAX = int(os.getenv("OUTBOX_MAX", "500"))
INDEX = "chat_simulator.html"

LOCK = threading.Lock()
OUTBOX = []          # [{seq, jid, message, ts}]
SEQ = {"n": 0}


class Handler(BaseHTTPRequestHandler):
    server_version = "MockDashWhat/1.0"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8", "replace"))
        except Exception:
            return {}

    def log_message(self, format, *args):
        print(f"[mock-dashwhat] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    # ── GET: estáticos + outbox ────────────────────────────────────────────
    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        if p == "/health":
            with LOCK:
                return self._json(200, {"status": "ok", "outbox": len(OUTBOX)})
        if p == "/outbox":
            since = 0
            q = u.query
            if "since=" in q:
                try:
                    since = int(q.split("since=")[1].split("&")[0])
                except ValueError:
                    since = 0
            with LOCK:
                msgs = [m for m in OUTBOX if m["seq"] > since]
            return self._json(200, {"messages": msgs})
        # estáticos
        return self._static(p)

    def _static(self, path):
        rel = unquote(path.lstrip("/")) or INDEX
        # evitar path traversal
        rel = posixpath.normpath(rel)
        if rel.startswith("..") or rel.startswith("/"):
            return self._json(403, {"detail": "forbidden"})
        full = os.path.join(STATIC_DIR, rel)
        if not os.path.isfile(full):
            return self._json(404, {"detail": f"no existe {rel}"})
        ctype = "text/html; charset=utf-8" if full.endswith(".html") else "application/octet-stream"
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ── POST /send-message ─────────────────────────────────────────────────
    def do_POST(self):
        p = urlparse(self.path).path
        if p != "/send-message":
            return self._json(404, {"detail": "Not Found"})
        data = self._body()
        jid, message = data.get("jid"), data.get("message")
        if not jid or not message:
            return self._json(400, {"error": "Faltan parámetros: jid y message son requeridos"})
        with LOCK:
            SEQ["n"] += 1
            OUTBOX.append({
                "seq": SEQ["n"], "jid": jid, "message": message,
                "ts": datetime.now(timezone.utc).isoformat(),
            })
            if len(OUTBOX) > OUTBOX_MAX:
                del OUTBOX[: len(OUTBOX) - OUTBOX_MAX]
        print(f"[mock-dashwhat] saliente a {jid}: {str(message)[:60]}…", flush=True)
        # misma respuesta que dashWhat2 real (main.js)
        return self._json(200, {"success": True, "message": "Mensaje enviado exitosamente"})

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()


if __name__ == "__main__":
    print(f"[mock-dashwhat] escuchando en 0.0.0.0:{PORT} · estáticos: {STATIC_DIR}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
