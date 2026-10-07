# Backlog

Objetivos, estado actual, ideas y bugs. Es el documento **volátil** del proyecto: se
actualiza seguido y no pretende ser elegante, sino útil.

---

## Objetivo central

Construir un sistema de gestión integral del comercio de bocaditos, **operado desde
WhatsApp**, con automatización progresiva mediante IA y **ERPNext como fuente de verdad**
para operaciones contables e inventario.

---

## Estado actual

| Componente | Estado |
|---|---|
| Servidor Baileys (dashWhat2) | ✅ recibe mensajes y los reenvía al backend |
| Backend Node.js/Express | ✅ orquestador central, comandos y mensajería |
| ia-service FastAPI | ✅ análisis de conversaciones y pedidos con IA |
| erp-service FastAPI | ✅ capa de integración con ERPNext |
| ERPNext | ✅ en producción, fuente de verdad |
| MongoDB | ✅ persistencia de conversaciones |
| Chatwoot | 🔄 no implementado |
| Efactura (facturación electrónica) | 🔄 no implementado |
| Stack de desarrollo local | ✅ backend + erp_service + ia_service + Mongo |

### Comandos administrativos (completos)

| Comando | Alias | Descripción |
|---|---|---|
| `/agendar` | `/pedido`, `/crear` | Crear un pedido manual |
| `/cobrar` | `/pagado`, `/pagar` | Registrar pago (y factura si no existe) |
| `/hoy` | — | Pedidos pendientes de hoy |
| `/manana` | — | Pedidos pendientes de mañana |
| `/listar` | — | Todos los pedidos pendientes |
| `/hecho` | — | Marcar entregado (genera Delivery Note) |
| `/cancelar` | — | Cancelar un pedido |
| `/reactivar` | — | Reactivar un pedido cancelado |
| `/consultar` | `/informe`, `/reporte`, `/info` | Consultar al agente de IA |

---

## Objetivos y su estado

| # | Objetivo | Estado |
|---|---|---|
| 1 | **Automatización de pedidos** — el cliente pide por WhatsApp, la IA interpreta; el admin puede crear con `/agendar`; se registra como `Sales Order` | ✅ implementado |
| 2 | **Gestión operativa desde WhatsApp** — comandos de pedidos del día, entregas y cancelaciones | ✅ implementado |
| 3 | **Asistente IA por consulta** — el admin pregunta en lenguaje natural | ✅ fase 1 y 4 |
| 4 | **Cobros y pagos** — cobros recibidos, pagos a proveedores, pedidos sin cobrar | 🔄 pendiente |
| 5 | **Control de stock e inventario** — stock por producto, ingresos de compra, alertas | 🔄 pendiente |
| 6 | **Análisis de conversaciones** — historial con un cliente, mensajes sin contestar | 🔄 pendiente |

---

## Agente de IA (`/consultar`) — fases

- ✅ **Fase 1 — Ventas básicas** (2026-05-11): `get_sales_summary`, `get_sales_by_product`,
  `get_pending_orders`.
- ✅ **Fase 4 — Agente autónomo con razonamiento multi-paso** (2026-10-03): bucle ReAct de
  hasta 5 pasos, modelos de razonamiento (`openai/gpt-5` + fallback `claude-sonnet-4.5`),
  contexto temporal de Paraguay, manual de datos de ERPNext, calculadora segura e
  integración con el MCP.
- 🔄 **Fase 2 — Endpoints dedicados de stock y finanzas** (opcional / optimización).
  Hoy muchas de estas consultas ya las resuelve el agente por MCP + ReAct, pero endpoints
  dedicados responderían más rápido:

  | Tool a crear | Endpoint en erp-service | Consulta objetivo |
  |---|---|---|
  | `get_stock_balance` | `GET /api/stock/balance` | "stock de empanadas" |
  | `get_payment_entries` | `GET /api/payments/summary?period=X` | "cobros de esta semana" |
  | `get_pending_payments` | `GET /api/payments/pending` | "pedidos sin cobrar" |
  | `get_supplier_expenses` | `GET /api/expenses/summary?period=X` | "gastos del mes" |

- 🔄 **Fase 3 — Mensajes / MongoDB** (pendiente). Requiere conexión directa de `ia-service`
  a Mongo (sin pasar por el backend): agregar `MONGO_URI` al `.env` de `ia-service`,
  `pymongo` a `requirements.txt` y crear `ia-service/services/mongo_tools.py`.

  | Tool | Parámetros | Consulta objetivo |
  |---|---|---|
  | `get_client_messages` | `client_name, limit=10, only_pending=false` | "últimos mensajes de Juan" |
  | `get_pending_messages` | `limit=20` | "quién está esperando respuesta" |
  | `get_client_summary` | `client_name` | "estado de la conversación con Pedro" |

---

## Ideas

1. Registrar las compras y gastos
2. Pedir ventas en guaraníes por día, semana, mes
3. Pedir ventas por producto por día
4. ~~Separar el directorio de comandos del backend para más claridad (pedidos, compras, etc.)~~ ✅
5. ~~Al crear o editar un pedido, que el sistema avise al cliente que quedó registrado (día/hora, monto, N° de pedido)~~ ✅ *(avisa al admin, no al cliente)*
6. ~~Premium y Eco se pueden pedir por fracción~~ ✅
7. ~~Advertir a la IA al tomar un pedido: delivery por 20 mil ₲ (debe poner 4 unidades de delivery × 5 mil)~~ ✅
8. Subir a Cloudinary las imágenes de los productos y poner los links en `ia-service/detalleProductos.json` para el bot
9. Pedir estado de cuentas del activo corriente (caja, bancos, inventario)
10. El sistema registra las ventas el día que se genera el pedido; se necesita la venta por **día de entrega**
11. Antes de confirmar un pedido, que el asistente revise la conversación cliente↔admin y avise al admin si hay diferencias para que él decida
12. Revisar fecha y hora: parece que toma UTC
13. Alertas proactivas: el agente notifica al admin cuando el stock baja de un umbral
14. Resumen diario automático enviado por WhatsApp al cerrar el día
15. Registro de gastos/egresos por voz o texto libre (ingreso de stock con IA)

## Bugs abiertos

1. La fecha no está bien
2. Al cobrar manda error pero toma el cobro

---

## Pendientes de infraestructura y proceso

- [ ] **Usuario de integración dedicado** en ERPNext, en vez de `Administrator`
      (hoy la integración corre con el usuario más privilegiado del ERP).
- [ ] **Conectar ERPNext en local** (instancia de prueba o ERPNext local) para poder
      testear el mapeo contable antes de producción.
- [ ] **Rotar el token de Chatwoot y la contraseña de MongoDB Atlas** (estuvieron en texto
      plano en el compose; ya se movieron a `.env`, pero conviene rotarlos).
- [ ] **Simulador de mensajería** para probar el flujo de WhatsApp sin correr Baileys.
- [ ] **Mongo en local** contra la base de prueba `test` (hoy se usa un Mongo en contenedor).
- [ ] **Conectar Chatwoot** en local o simularlo.
- [ ] Versionar `docker-compose.yml`, `docker-compose.local.yml`, `dev.sh` y `.env.example`
      en el repo `voraz-control` (hoy existen en disco pero el `.gitignore` los excluye).
- [ ] Resolver la divergencia de `voraz-control` entre local y la VM.
- [ ] Resolver `dashWhat2`: hay **4 archivos modificados solo en la VM**
      (`api/Dockerfile`, `api/main.js`, `api/package.json`, `api/.dockerignore`) que no
      existen en git — hay que revisarlos uno por uno y decidir.
