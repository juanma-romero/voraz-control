# Servicios del sistema Voraz

Qué hace cada servicio, sus tecnologías y responsabilidades. La vista de conjunto está en
`arquitectura.md`; el detalle de código, en el README de cada repo.

---

## 1. backend — orquestador y mensajería

- **Repo**: `backend` · **Ruta local**: `backend/backend` · **Puerto**: 3000
- **Tecnologías**: Node.js, Express, MongoDB, Axios, Agenda (tareas programadas).
- **Funciones**:
  - Punto de entrada de todos los mensajes (clientes y administradores).
  - Guarda el historial de conversaciones y delega el procesamiento.
  - Orquesta a `ia-service` y `erp-service`.
  - Ejecuta los comandos administrativos.
  - Envía al cliente las confirmaciones con `🤖`: N° de orden, entrega, detalle de
    productos, delivery en ₲ y total.
  - Jobs periódicos con Agenda (ej. resumen de mensajes sin contestar).
- **Base de datos**: `NODE_ENV=local` → base **`test`**; producción → base **`dash`**
  (definido en `db.js`).

## 2. ia-service — asistente de IA

- **Repo**: `ia-service` · **Ruta local**: `ia-service` · **Puerto**: 8000
- **Tecnologías**: Python, FastAPI. Proveedores: Groq (principal) y Google AI Studio
  (fallback).
- **Funciones**:
  - Análisis de conversaciones: intenciones, entidades, resúmenes.
  - Auditoría de pedidos contra el historial del chat (alerta al admin si detecta
    inconsistencias; no bloquea la operación).
  - **Agente** consultable desde WhatsApp (ver sección 5).
- **MCP opcional**: al arrancar levanta el servidor MCP de ERPNext (Node, por stdio). Se
  puede desactivar con `ENABLE_MCP=false` — se usa en local, donde no hay ERP conectado.

## 3. ERPNext

- **Ubicación**: `https://vorazadmin.site` · Docker `frappe/erpnext:v16.12.0`
- **Función**: ERP y **fuente de verdad** para pedidos, clientes, stock y contabilidad.
- **Acceso**: siempre a través de `erp-service`; para consultas de lectura existe además el
  MCP `voraz_erpnext` (solo lectura).
- **Nombres contables**: ver la tabla en `AGENTS.md` — usar exactamente esos valores.

## 4. erp-service — capa de integración con ERPNext

- **Repo**: `erp-service` · **Ruta local**: `erp-service` · **Puerto**: 8001
- **Tecnologías**: Python, FastAPI.
- **Funciones**:
  - **Gestión unificada de clientes (JID-first)**: usa el JID de WhatsApp como
    identificador único (`name`) del `Customer`, para evitar fusiones o duplicados.
  - **Identidad progresiva**: actualiza nombres de clientes de forma asíncrona sin
    bloquear los flujos críticos.
  - **Resolución de cobros por JID/móvil**: asocia `Payment Entry` al último pedido
    activo del cliente.
  - **Órdenes centralizadas**: creación y listado de `Sales Order`, devolviendo
    `order_name` y `grand_total` para confirmar al cliente.
  - **Manejo contable**: `Delivery Notes` para pedidos entregados, cancelaciones y
    reversiones (`docstatus: 2`).

## 5. Agente de IA (`/consultar`)

Sistema de agente autónomo basado en *function calling* y razonamiento iterativo (ReAct).
Permite al administrador consultar cualquier aspecto del negocio en lenguaje natural
desde WhatsApp.

- **Comando**: `/consultar [texto]` (aliases: `/informe`, `/reporte`, `/info`)
- **Modelo principal**: `openai/gpt-5` (vía OpenRouter) · **fallback**:
  `anthropic/claude-sonnet-4.5`
- **Arquitectura**:
  - El backend detecta el comando y llama a `ia-service POST /agent-query`.
  - **Contexto temporal dinámico**: fecha, día y hora de Paraguay (UTC-3), inyectados.
  - **Manual de datos ERPNext** en el prompt: `Sales Order` (incluido el campo
    personalizado `custom_dia_y_hora_entrega`), `Sales Invoice`, `Customer`, `Item`,
    `Bin` (stock) y `Payment Entry` (cobros).
  - **Bucle ReAct**: hasta 5 iteraciones de pedir tool → ejecutar → observar, hasta
    consolidar la respuesta.
- **Archivos clave**:
  - `ia-service/routers/agent.py` — endpoint `/agent-query`, bucle ReAct, prompt.
  - `ia-service/services/agent_tools.py` — dispatcher de tools nativas.
  - `ia-service/services/mcp_client.py` — cliente del `erpnext-mcp-server`.
  - `backend/services/commands/informes/consultar.js` — comando en el backend.
  - `erp-service/routers/reports.py` — `GET /api/sales/summary`, `GET /api/sales/by-product`.

### Tools del agente

| Tool | Tipo | Para qué |
|---|---|---|
| `get_sales_summary` | Nativa | Total de ventas en ₲ y cantidad de pedidos por período |
| `get_sales_by_product` | Nativa | Ventas por producto, ordenadas por cantidad |
| `get_pending_orders` | Nativa | Pedidos pendientes de entrega |
| `calculate` | Nativa | Calculadora aritmética exacta (AST seguro de Python) |
| `get_documents` | MCP | Búsqueda y filtrado libre de documentos en ERPNext |
| `get_document` | MCP | Detalle completo de un documento por ID |
| `get_doctype_fields` | MCP | Introspección de campos de cualquier DocType |

**Períodos soportados** por las tools de ventas: `hoy` · `semana` · `mes` · `mes_pasado` · `anio`

## 6. dashWhat2 — puente de WhatsApp

- **Repo**: `dashWhat2` · **Ruta local**: `dashWhat2` (código en `api/`) · **Puerto**: 8880
- **Tecnología**: Node.js + Baileys.
- Mantiene la **sesión vinculada** de WhatsApp y reenvía los mensajes al backend.
- ⚠️ **No correrlo en local**: una segunda sesión del mismo número puede invalidar la de
  producción.

## 7. Chatwoot

- Servicio aparte (`~/chats` en la VM; Postgres + Redis, dominio `chat.vorazadmin.site`,
  detrás del `nginx-proxy` con TLS).
- Canales: **WhatsApp** (inbox `Channel::Api`, el único que usa el flujo del stack) y
  **Facebook** (inbox `Channel::FacebookPage`, conectado 2026-10-08). Instagram: pendiente.
