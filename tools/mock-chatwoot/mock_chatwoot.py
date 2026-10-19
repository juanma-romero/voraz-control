#!/usr/bin/env python3
"""
Mock de Chatwoot para desarrollo LOCAL y testing automatizado en Voraz.

Implementa la superficie exacta que consume el backend (services/chatwoot.service.js):
  - GET  /api/v1/accounts/:acc/inboxes
  - GET  /api/v1/accounts/:acc/contacts/search?q=...
  - POST /api/v1/accounts/:acc/contacts
  - GET  /api/v1/accounts/:acc/contacts/:id/conversations
  - POST /api/v1/accounts/:acc/conversations
  - POST /api/v1/accounts/:acc/conversations/:id/messages

Endpoints especiales de control / testing:
  - GET  /health
  - GET  /_mock/dump                  -> inspeccionar todo el estado en memoria
  - POST /_mock/reset                 -> reiniciar estado
  - POST /_mock/fire-webhook          -> emitir un evento 'message_created' saliente al webhook del backend
"""
import json
import os
import re
import threading
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

PORT = int(os.getenv("PORT", "3000"))
BACKEND_WEBHOOK_URL = os.getenv("BACKEND_WEBHOOK_URL", "http://backend:3000/api/chatwoot/webhook")

LOCK = threading.Lock()

STATE = {
    "contact_counter": 0,
    "conv_counter": 0,
    "message_counter": 0,
    "contacts": {},       # id -> dict
    "conversations": {},  # id -> dict
    "messages": [],       # list of dicts
    "inboxes": [
        {
            "id": 4,
            "name": "WhatsApp Voraz",
            "channel_type": "Channel::Api",
            "inbox_identifier": "local-dev",
        }
    ],
}


def reset_state():
    with LOCK:
        STATE["contact_counter"] = 0
        STATE["conv_counter"] = 0
        STATE["message_counter"] = 0
        STATE["contacts"].clear()
        STATE["conversations"].clear()
        STATE["messages"].clear()


class ChatwootMockHandler(BaseHTTPRequestHandler):
    server_version = "MockChatwoot/1.0"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, api-access-token, api_access_token, X-Forwarded-Proto")
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
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8", "replace"))
        except Exception:
            return {}

    def log_message(self, format, *args):
        print(f"[mock-chatwoot] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        query = parse_qs(u.query)

        if path == "/health":
            with LOCK:
                return self._json(200, {
                    "status": "ok",
                    "contacts": len(STATE["contacts"]),
                    "conversations": len(STATE["conversations"]),
                    "messages": len(STATE["messages"]),
                })

        if path == "/_mock/dump":
            with LOCK:
                return self._json(200, {
                    "contacts": STATE["contacts"],
                    "conversations": STATE["conversations"],
                    "messages": STATE["messages"],
                })

        # GET /api/v1/accounts/:acc/inboxes
        if re.match(r"^/api/v1/accounts/\d+/inboxes/?$", path):
            with LOCK:
                return self._json(200, {"payload": STATE["inboxes"]})

        # GET /api/v1/accounts/:acc/contacts/search?q=...
        if re.match(r"^/api/v1/accounts/\d+/contacts/search/?$", path):
            q = query.get("q", [""])[0].strip().lower()
            results = []
            with LOCK:
                for c in STATE["contacts"].values():
                    name = (c.get("name") or "").lower()
                    ident = (c.get("identifier") or "").lower()
                    phone = (c.get("phone_number") or "").lower()
                    if q and (q in name or q in ident or q in phone):
                        results.append(c)
            return self._json(200, {"payload": results})

        # GET /api/v1/accounts/:acc/contacts/:contact_id/conversations
        m_convs = re.match(r"^/api/v1/accounts/\d+/contacts/(\d+)/conversations/?$", path)
        if m_convs:
            contact_id = int(m_convs.group(1))
            with LOCK:
                convs = [c for c in STATE["conversations"].values() if c.get("contact_id") == contact_id]
            return self._json(200, {"payload": convs})

        self._json(404, {"error": f"Not found: {path}"})

    def do_POST(self):
        u = urlparse(self.path)
        path = u.path
        data = self._body()

        if path == "/_mock/reset":
            reset_state()
            return self._json(200, {"status": "reset_ok"})

        # POST /_mock/fire-webhook (simular mensaje saliente escrito por operador en el panel)
        if path == "/_mock/fire-webhook":
            target_url = data.get("webhook_url") or BACKEND_WEBHOOK_URL
            payload = data.get("payload") or {
                "event": "message_created",
                "id": 99999,
                "content": data.get("content", "Mensaje de prueba desde panel"),
                "message_type": "outgoing",
                "private": False,
                "content_attributes": {},
                "conversation": {
                    "id": data.get("conversation_id", 1),
                    "contact_inbox": {
                        "source_id": data.get("source_id", "595985000000@s.whatsapp.net")
                    }
                },
                "sender": {
                    "name": "Operador Panel",
                    "type": "user"
                }
            }
            try:
                req = urllib.request.Request(
                    target_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resp_data = resp.read().decode("utf-8", "replace")
                    return self._json(200, {"status": "dispatched", "response": resp_data})
            except Exception as e:
                return self._json(500, {"error": str(e)})

        # POST /api/v1/accounts/:acc/conversations/:conv_id/toggle_status
        m_toggle = re.match(r"^/api/v1/accounts/\d+/conversations/(\d+)/toggle_status/?$", path)
        if m_toggle:
            conv_id = int(m_toggle.group(1))
            with LOCK:
                if conv_id not in STATE["conversations"]:
                    return self._json(404, {"error": f"Conversation {conv_id} not found"})
                new_status = data.get("status", "open")
                STATE["conversations"][conv_id]["status"] = new_status
            return self._json(200, {"payload": {"current_status": new_status, "conversation_id": conv_id}})

        # POST /api/v1/accounts/:acc/contacts
        if re.match(r"^/api/v1/accounts/\d+/contacts/?$", path):
            with LOCK:
                STATE["contact_counter"] += 1
                cid = STATE["contact_counter"]
                contact = {
                    "id": cid,
                    "name": data.get("name", f"Contacto {cid}"),
                    "identifier": data.get("identifier"),
                    "phone_number": data.get("phone_number"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                STATE["contacts"][cid] = contact
            return self._json(200, {"payload": {"contact": contact}})

        # POST /api/v1/accounts/:acc/conversations
        if re.match(r"^/api/v1/accounts/\d+/conversations/?$", path):
            with LOCK:
                STATE["conv_counter"] += 1
                cvid = STATE["conv_counter"]
                conv = {
                    "id": cvid,
                    "contact_id": int(data.get("contact_id", 0)),
                    "inbox_id": int(data.get("inbox_id", 4)),
                    "status": data.get("status", "open"),
                    "source_id": data.get("source_id"),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "messages": []
                }
                STATE["conversations"][cvid] = conv
            return self._json(200, conv)

        # POST /api/v1/accounts/:acc/conversations/:conv_id/messages
        m_msg = re.match(r"^/api/v1/accounts/\d+/conversations/(\d+)/messages/?$", path)
        if m_msg:
            conv_id = int(m_msg.group(1))
            with LOCK:
                if conv_id not in STATE["conversations"]:
                    return self._json(404, {"error": f"Conversation {conv_id} not found"})
                STATE["message_counter"] += 1
                mid = STATE["message_counter"]
                msg = {
                    "id": mid,
                    "conversation_id": conv_id,
                    "content": data.get("content"),
                    "message_type": data.get("message_type", "incoming"),
                    "private": bool(data.get("private", False)),
                    "content_attributes": data.get("content_attributes", {}),
                    "created_at": int(datetime.now(timezone.utc).timestamp()),
                }
                STATE["messages"].append(msg)
                STATE["conversations"][conv_id]["messages"].append(msg)
            return self._json(200, msg)

        self._json(404, {"error": f"Not found: {path}"})


def main():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), ChatwootMockHandler)
    print(f"[mock-chatwoot] Iniciando en puerto {PORT}...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
