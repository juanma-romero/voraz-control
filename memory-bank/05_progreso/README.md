# Progreso del Proyecto Voraz

> Última actualización: 2026-05-11

---

## Sistema Base 🔄 Incompleto

| Componente | Estado | Notas |
|------------|--------|-------|
| Servidor Baileys (dashWhat2) | ✅ | Recibe mensajes WhatsApp y los reenvía al backend |
| Backend Node.js/Express | ✅ | Orquestador central, gestión de comandos y mensajes |
| ia-service Python/FastAPI | ✅ | Análisis de conversaciones y procesamiento de pedidos con IA |
| erp-service Python/FastAPI | ✅ | Capa de integración con ERPNext |
| ERPNext | ✅ | ERP en producción, fuente de verdad para pedidos e inventario |
| MongoDB | ✅ | Persistencia de conversaciones y estados |
| Efactura | 🔄 | Facturación electrónica SIFEN Paraguay |

---

## Sistema de Comandos Admin ✅ Completo

| Comando | Alias | Estado | Descripción |
|---------|-------|--------|-------------|
| `/agendar` | `/pedido`, `/crear` | ✅ | Crear pedido manual para un cliente |
| `/cobrar` | `/pagado`, `/pagar` | ✅ | Registrar pago (y factura si no existe) de un pedido |
| `/hoy` | — | ✅ | Pedidos pendientes de hoy |
| `/manana` | — | ✅ | Pedidos pendientes de mañana |
| `/listar` | — | ✅ | Todos los pedidos pendientes |
| `/hecho` | — | ✅ | Marcar pedido como entregado (genera Delivery Note) |
| `/cancelar` | — | ✅ | Cancelar un pedido |
| `/reactivar` | — | ✅ | Reactivar un pedido cancelado |

---

## Agente IA (`/consultar`) — Progreso por Fases

### ✅ Fase 1 — Ventas (Completada: 2026-05-11)

**Archivos implementados:**
- `ia-service/routers/agent.py` — Loop de Function Calling con Groq
- `ia-service/services/agent_tools.py` — Dispatcher de tools
- `backend/services/commands/informes/consultar.js` — Comando `/consultar`
- `erp-service/main.py` — Endpoints `/api/sales/summary` y `/api/sales/by-product`

**Tools disponibles:**

| Tool | Consultas de ejemplo |
|------|---------------------|
| `get_sales_summary` | "ventas del mes pasado", "cuánto vendimos esta semana", "ingresos de hoy" |
| `get_sales_by_product` | "productos más vendidos este mes", "qué combo se vendió más" |
| `get_pending_orders` | "pedidos pendientes", "cuántos pedidos hay sin entregar" |

**Modelo:** `llama-3.3-70b-versatile` (Groq plan pago) · Fallback: `gemini-2.5-flash-lite`

---

### 🔄 Fase 2 — Stock y Finanzas (Pendiente)

**Tools a agregar en `ia-service/services/agent_tools.py`:**

| Tool | Endpoint erp-service a crear | Consultas objetivo |
|------|-----------------------------|--------------------|
| `get_stock_balance` | `GET /api/stock/balance` | "stock de empanadas", "qué tengo en inventario" |
| `get_payment_entries` | `GET /api/payments/summary?period=X` | "cobros de esta semana", "cuánto cobré este mes" |
| `get_pending_payments` | `GET /api/payments/pending` | "pedidos sin cobrar", "clientes que deben" |
| `get_supplier_expenses` | `GET /api/expenses/summary?period=X` | "gastos del mes", "pagos a proveedores" |

**Nota técnica:** Los endpoints del erp-service consultarán las APIs de ERPNext:
- Stock: `Bin` doctype (como hace el MCP actual)
- Pagos: `Payment Entry` doctype
- Gastos: `Purchase Invoice` doctype

---

### 🔄 Fase 3 — Mensajes / MongoDB (Pendiente)

**Archivos a crear:**
- `ia-service/services/mongo_tools.py` — Funciones de consulta a MongoDB

**Tools a agregar:**

| Tool | Parámetros | Consultas objetivo |
|------|------------|--------------------|
| `get_client_messages` | `client_name, limit=10, only_pending=false` | "últimos mensajes de Juan", "conversación con María" |
| `get_pending_messages` | `limit=20` | "mensajes sin contestar", "quién está esperando respuesta" |
| `get_client_summary` | `client_name` | "estado de la conversación con Pedro" |

**Requerimientos técnicos:**
- Agregar `MONGO_URI` al `.env` de `ia-service`
- Agregar `pymongo` a `ia-service/requirements.txt`
- La conexión a MongoDB desde `ia-service` será directa (sin pasar por backend)

---

### 🔄 Fase 4 — Multi-tool / Razonamiento cruzado (Pendiente)

Habilitar que el agente combine múltiples tools en un ciclo para responder preguntas compuestas.  
El loop actual procesa una sola `tool_call`. Para Fase 4, el loop en `agent.py` debe iterar hasta que el LLM no pida más tools.

**Ejemplos de consultas objetivo:**
- *"¿Cuánto me debe el cliente que más compró este mes?"* → `get_top_customers` + `get_pending_payments`
- *"¿Qué producto vendí más y cuánto stock me queda?"* → `get_sales_by_product` + `get_stock_balance`

