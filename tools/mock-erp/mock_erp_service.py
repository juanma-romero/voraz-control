#!/usr/bin/env python3
"""
Mock de `erp-service` para desarrollo LOCAL de Voraz.

Reemplaza al microservicio FastAPI real (erp-service/) cuando NO querés conectar
a ERPNext. Implementa la MISMA superficie HTTP que consume el backend, con
estado en memoria (se pierde al reiniciar el contenedor).

Endpoints (idénticos a erp-service/routers/*.py):
  POST /api/customers/sync                 -> {success, customer}
  POST /api/orders                         -> {success, order_name, grand_total, customer}
  POST /api/orders/replace_latest          -> {success, order_name, grand_total, cancelled_order}
  GET  /api/orders/pending[?date=Y-M-D]    -> [ {numero_pedido, contactName, fecha_hora_entrega, productos, monto_total} ]
  POST /api/orders/{id}/deliver            -> {success, message, delivery_note}
  POST /api/orders/{id}/cancel             -> {success, message}   (409 si no se puede)
  POST /api/orders/{id}/pay                -> {success, sales_invoice, payment_entry, order_id}
  POST /api/accounting/expense             -> {success, journal_entry}
  GET  /api/sales/summary?date_from&date_to
  GET  /api/sales/by-product?date_from&date_to
  GET  /health                             -> {status:"ok"}   (extra, para readiness)

Lo que NO hace: no valida contra ERPNext real, no toca contabilidad de verdad,
los precios y numeraciones son ficticios. Es para probar el FLUJO del backend.
"""
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.getenv("PORT", "8001"))
# Latencia artificial (ms): útil para ver estados "cargando" en el simulador.
LATENCY = float(os.getenv("MOCK_ERP_LATENCY_MS", "0")) / 1000.0
TZ = timezone(timedelta(hours=-3))  # Paraguay (UTC-3), igual que el backend

# Catálogo ficticio: item_code -> (nombre, precio unitario en PYG)
CATALOG = {
    "zero": ("Coca Zero 2 lts", 15000), "deli": ("Delivery", 5000),
    "capre": ("Canastita Capresse", 12000), "empaJYQ": ("Empanadita de Jamon y Queso", 8000),
    "empaPollo": ("Empanadita de Pollo", 8000), "milaPollo": ("Milanesa de Pollo", 10000),
    "pizeta": ("Pizeta", 12000), "mini": ("Mini Burger", 12000),
    "empaCarne": ("Empanadita de Carne", 8000), "sandwPollo": ("Sandwich de Mila de Pollo", 12000),
    "milaCarne": ("Milanesita de Carne", 10000), "pre": ("Combo Premium", 25000),
    "sprite": ("Sprite 2lts", 12000), "coca3": ("Coca 3 lts", 20000),
    "clasico": ("Combo Clasico", 15000), "fuga": ("Canastita Fugazeta", 12000),
    "sandJYQ": ("Sandw Jamon y Queso", 10000), "napo": ("Canastita Napolitana", 12000),
    "croq": ("Croquetas", 9000), "guara": ("Fanta Guarana 2lts", 12000),
    "extra": ("Extra", 5000), "naranja": ("Fanta Naranja 2lts", 12000),
    "coca2": ("Coca 2lts", 15000), "mbeju": ("Mbeju", 8000),
    "payagua": ("Payagua", 9000), "soo": ("Chipa So'o", 8000), "mandio": ("Pastel Mandio", 9000),
}

LOCK = threading.Lock()
STATE = {"orders": {}, "counter": 0, "delivery_counter": 0, "pay_counter": 0, "jv_counter": 0}


def today_str(offset_days=0):
    return (datetime.now(TZ) + timedelta(days=offset_days)).strftime("%Y-%m-%d")


def price_of(item_code, cantidad):
    nombre, precio = CATALOG.get(item_code, (item_code, 10000))
    return nombre, precio


def build_order(remote_jid, contact_name, fecha_hora_entrega, productos):
    STATE["counter"] += 1
    name = f"SALES-ORD-MOCK-{STATE['counter']:05d}"
    enriched, total = [], 0
    for p in productos or []:
        code = p.get("item_code", "?")
        cant = float(p.get("cantidad", 1) or 1)
        nombre, precio = price_of(code, cant)
        total += cant * precio
        enriched.append({"item_code": code, "cantidad": cant, "nombre": nombre})
    order = {
        "name": name,
        "customer": remote_jid,
        "contactName": contact_name or "Desconocido",
        "fecha_hora_entrega": fecha_hora_entrega,
        "delivery_date": (fecha_hora_entrega or "")[:10],
        "productos": enriched,
        "grand_total": round(total),
        "status": "active",
    }
    STATE["orders"][name] = order
    return order


def latest_active(customer):
    act = [o for o in STATE["orders"].values()
           if o["customer"] == customer and o["status"] == "active"]
    act.sort(key=lambda o: o["name"])
    return act[-1] if act else None


def seed():
    """Dos pedidos de ejemplo (hoy y mañana) para que /listar, /hoy y /manana
    tengan algo que mostrar desde el arranque."""
    build_order("595981111111@s.whatsapp.net", "Sol",
                f"{today_str()} 17:30:00", [{"item_code": "pre", "cantidad": 2},
                                            {"item_code": "deli", "cantidad": 1}])
    build_order("595982222222@s.whatsapp.net", "Ramiro",
                f"{today_str(1)} 12:00:00", [{"item_code": "empaCarne", "cantidad": 50},
                                             {"item_code": "zero", "cantidad": 3}])


class Handler(BaseHTTPRequestHandler):
    server_version = "MockERPService/1.0"

    # ── helpers ────────────────────────────────────────────────────────────
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _send(self, code, payload):
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
        print(f"[mock-erp] {self.command} {self.path} -> {args[1] if len(args) > 1 else ''}")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    # ── GET ────────────────────────────────────────────────────────────────
    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = u.path
        if LATENCY:
            time.sleep(LATENCY)
        try:
            with LOCK:
                if p == "/health":
                    return self._send(200, {"status": "ok", "orders": len(STATE["orders"])})

                if p == "/api/orders/pending":
                    date = (q.get("date") or [None])[0]
                    pend = [o for o in STATE["orders"].values() if o["status"] == "active"]
                    if date:
                        pend = [o for o in pend if o["delivery_date"] == date]
                    pend.sort(key=lambda o: o["fecha_hora_entrega"] or "")
                    out = [{
                        "numero_pedido": o["name"],
                        "contactName": o["contactName"],
                        "fecha_hora_entrega": o["fecha_hora_entrega"],
                        "productos": [{"cantidad": i["cantidad"], "nombre": i["nombre"]}
                                      for i in o["productos"]],
                        "monto_total": f"$ {o['grand_total']:.0f}",
                    } for o in pend]
                    return self._send(200, out)

                if p == "/api/sales/summary":
                    df = (q.get("date_from") or [""])[0]
                    dt = (q.get("date_to") or [""])[0]
                    done = [o for o in STATE["orders"].values()
                            if o["status"] == "delivered" and df <= o["delivery_date"] <= dt]
                    tot = sum(o["grand_total"] for o in done)
                    return self._send(200, {
                        "periodo": {"desde": df, "hasta": dt},
                        "total_gs": tot, "total_pedidos": len(done),
                        "promedio_por_pedido_gs": round(tot / len(done)) if done else 0,
                    })

                if p == "/api/sales/by-product":
                    df = (q.get("date_from") or [""])[0]
                    dt = (q.get("date_to") or [""])[0]
                    done = [o for o in STATE["orders"].values()
                            if o["status"] == "delivered" and df <= o["delivery_date"] <= dt]
                    agg = {}
                    for o in done:
                        for i in o["productos"]:
                            a = agg.setdefault(i["item_code"], {
                                "item_code": i["item_code"], "item_name": i["nombre"],
                                "cantidad_total": 0, "monto_total_gs": 0})
                            a["cantidad_total"] += i["cantidad"]
                            a["monto_total_gs"] += i["cantidad"] * price_of(i["item_code"], 0)[1]
                    return self._send(200, {
                        "periodo": {"desde": df, "hasta": dt},
                        "total_ordenes_analizadas": len(done),
                        "productos": sorted(agg.values(),
                                            key=lambda x: x["cantidad_total"], reverse=True),
                    })

            return self._send(404, {"detail": "Not Found"})
        except Exception as e:
            return self._send(500, {"detail": f"mock-erp error: {e}"})

    # ── POST ───────────────────────────────────────────────────────────────
    def do_POST(self):
        u = urlparse(self.path)
        p = u.path
        body = self._body()
        if LATENCY:
            time.sleep(LATENCY)
        try:
            with LOCK:
                if p == "/api/customers/sync":
                    jid = body.get("remoteJid")
                    if not jid:
                        return self._send(422, {"detail": "remoteJid requerido"})
                    return self._send(200, {"success": True, "customer": jid})

                if p == "/api/orders":
                    o = build_order(body.get("remoteJid"), body.get("contactName"),
                                    body.get("fecha_hora_entrega"), body.get("productos"))
                    return self._send(200, {"success": True, "order_name": o["name"],
                                            "grand_total": o["grand_total"], "customer": o["customer"]})

                if p == "/api/orders/replace_latest":
                    jid = body.get("remoteJid")
                    old = latest_active(jid)
                    if old:
                        old["status"] = "cancelled"
                    o = build_order(jid, body.get("contactName"),
                                    body.get("fecha_hora_entrega"), body.get("productos"))
                    return self._send(200, {"success": True, "order_name": o["name"],
                                            "grand_total": o["grand_total"],
                                            "cancelled_order": old["name"] if old else None})

                m = re.match(r"^/api/orders/([^/]+)/deliver$", p)
                if m:
                    o = STATE["orders"].get(m.group(1))
                    if not o:
                        return self._send(404, {"detail": f"No existe el pedido {m.group(1)}"})
                    STATE["delivery_counter"] += 1
                    o["status"] = "delivered"
                    dn = f"DELIVERY-NOTE-MOCK-{STATE['delivery_counter']:05d}"
                    return self._send(200, {"success": True,
                                            "message": "Pedido entregado correctamente",
                                            "delivery_note": dn})

                m = re.match(r"^/api/orders/([^/]+)/cancel$", p)
                if m:
                    o = STATE["orders"].get(m.group(1))
                    if not o:
                        return self._send(409, {"detail": f"No se encontró el pedido {m.group(1)}"})
                    if o["status"] == "delivered":
                        # Espeja el LinkExistsError real: no se cancela lo ya entregado
                        return self._send(409, {"detail": "No se puede cancelar: el pedido ya tiene remito vinculado."})
                    o["status"] = "cancelled"
                    return self._send(200, {"success": True, "message": "Pedido cancelado correctamente"})

                m = re.match(r"^/api/orders/([^/]+)/pay$", p)
                if m:
                    oid = m.group(1)
                    if "@" in oid:  # el comando /cobrar puede pasar un JID
                        o = latest_active(oid)
                        if not o:
                            return self._send(400, {"detail": f"El cliente {oid} no tiene pedidos activos."})
                        oid = o["name"]
                    else:
                        o = STATE["orders"].get(oid)
                        if not o:
                            return self._send(400, {"detail": f"No existe el pedido {oid}"})
                    STATE["pay_counter"] += 1
                    return self._send(200, {
                        "success": True,
                        "sales_invoice": f"SINV-MOCK-{STATE['pay_counter']:05d}",
                        "payment_entry": f"PAY-MOCK-{STATE['pay_counter']:05d}",
                        "order_id": oid,
                    })

                if p == "/api/accounting/expense":
                    if not body.get("amount"):
                        return self._send(400, {"detail": "Falta el monto"})
                    STATE["jv_counter"] += 1
                    return self._send(200, {"success": True,
                                            "journal_entry": f"ACC-JV-MOCK-{STATE['jv_counter']:05d}"})

            return self._send(404, {"detail": "Not Found"})
        except Exception as e:
            return self._send(500, {"detail": f"mock-erp error: {e}"})


if __name__ == "__main__":
    seed()
    print(f"[mock-erp] escuchando en 0.0.0.0:{PORT} (latencia {LATENCY*1000:.0f} ms) · "
          f"{len(STATE['orders'])} pedidos de ejemplo", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
