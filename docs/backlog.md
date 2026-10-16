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
| Stack de desarrollo local | ✅ backend + erp_service (mock) + ia_service + dashwhat_mock + Mongo |

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
16. **Rediseño del modelo de datos de conversaciones en MongoDB (`chatsV3` / `chat_sessions`) para analítica e inteligencia comercial** *(ver especificación detallada al final de este documento)*.
17. **Pregunta abierta después del mensaje automático (recupero de leads fríos).** Hoy el bot responde a *"Hola"* con el link del catálogo (`wa.me/c/...`) y ~180 conversaciones quedan abandonadas ahí, sin que nadie retome. Agregar una segunda línea que invite a responder (ej. *"¿Para cuántas personas estás organizando? Te armo una propuesta en el momento"*) convierte ese envío de link en una conversación de venta y le da al bot una señal concreta para calificar y pedir los datos mínimos (fecha, zona, cantidad, factura). *Medir: tasa de respuesta al mensaje automático antes/después.*
18. **Promocionar la capacidad de producción en el día.** La operación ya puede entregar pedidos hechos en el día (hasta 1–2 h después de recibido), pero hoy no se comunica en ningún canal. Agregar el mensaje *"del día"* al saludo automático, al catálogo y a los copys de Meta/Instagram (ver `marketing/base_comercial_voraz.md`). *Medir: pedidos con lead time < 3 h.*
19. **Combo Cumpleaños completo (bocaditos + torta).** 26 conversaciones pidieron torta dulce; 7 se perdieron enteras por no tenerla y 19 compraron solo salado. Coordinar con Zulma la venta de torta: decidir si se produce en cocina propia o por un aliado/confitería, cargar el ítem en ERPNext con su precio y publicarlo como *"combo cumpleaños completo"* para no seguir resignando esas ventas.
20. **Analizar payload de WhatsApp.** Auditar e inspeccionar en profundidad la estructura completa del payload que entrega Baileys en `messages.upsert` hacia `dashWhat2` y el backend (`messageParser.js`, `parseBaileysMessage`). Mapear y documentar campos de texto, audios, imágenes, ubicaciones, citas/respuestas (`replyTo`), metadatos (`fromMe`, `remoteJid`, timestamps) y casos borde (mensajes de sistema, estados, grupos) para optimizar el procesamiento y evitar pérdida de información en la cadena de mensajes.

## Bugs abiertos

1. La fecha no está bien
2. Al cobrar manda error pero toma el cobro

---

## Pendientes de infraestructura y proceso

- [x] ~~**Usuario de integración dedicado** en ERPNext, en vez de `Administrator`~~
      → creados `integracion@` (escritura) y `consulta@` (solo lectura), con roles propios.
      Los 4 flujos críticos verificados con `integracion@` (2026-10-08). Ver `runbook.md` §7.
- [ ] **Apagar la API key de `Administrator`** (ya no la usa nada; se conserva como rollback
      unos días).
- [x] ~~**MCP de `ia-service`**: hoy hereda las credenciales de `erp-service/.env` (el usuario de
      **escritura**)~~ → resuelto: usa las `MCP_*` (usuario de consulta) y expone al LLM solo las
      5 herramientas de lectura, con rechazo en `call_tool()`. Verificado contra el contenedor
      (2026-10-08). Ver `runbook.md` §7.
- [x] ~~**Simulador de mensajería** para probar el flujo de WhatsApp sin correr Baileys~~ →
      hecho: `backend/backend/tests/chat_simulator.html` + `tools/mock-dashwhat/`
      (loop de entrada **y** salida). Ver `decision-log.md` (2026-10-08).
- [x] ~~**Conectar ERPNext en local** (instancia de prueba o ERPNext local)~~ → por ahora se usa
      un **mock** de `erp-service` (`tools/mock-erp/`), que cubre el flujo sin tocar el ERP.
      Conectar el ERPNext real (instancia local) queda para cuando haga falta testear el mapeo
      contable. Ver `decision-log.md` (2026-10-08).
- [ ] **Mongo en local** contra la base de prueba `test` (hoy se usa un Mongo en contenedor).
- [ ] **Conectar Chatwoot** en local o simularlo.
- [x] ~~Versionar `docker-compose.yml`, `docker-compose.local.yml`, `dev.sh` y `.env.example`~~
      → ya están versionados en `voraz-control` (el `.gitignore` se actualizó).
- [x] ~~Resolver la divergencia de `voraz-control` entre local y la VM~~ → no era divergencia:
      la VM estaba 2 commits atrás. Sincronizada.
- [x] ~~Resolver `dashWhat2`: 4 archivos modificados solo en la VM~~ → se guardaron en su momento
      en `respaldo-vm-dashwhat2`. Tras auditar el diff contra `main`, se verificó que sus cambios
      (parches viejos de Baileys y `testo.txt`) estaban completamente superados por el refactor
      de `main`. La rama fue descartada y eliminada (local y remota). Tarea completada (`t_a926c5b4`).
- [ ] **Puente agente-a-agente local ↔ VM (`hermes peer`)**. Hoy el Hermes local le habla al de
      la VM por SSH (atajo `~/.local/bin/vm-hermes`, skill `voraz-vm-bridge`): funciona, pero
      **solo local → VM** y cae en una **sesión aparte** (no aparece en el bot de Telegram de la
      VM). La vía nativa es `hermes peer`: habilitar `platforms.api_server` en el gateway de la VM
      con un `API_SERVER_KEY` fuerte (hoy no está activo), dejarlo privado con un túnel SSH
      (`ssh -N -L 8377:localhost:8377 voraz`) y registrar el peer desde local
      (`hermes peer add voraz-vm --url http://localhost:8377 --key <KEY>`). Da **Bot Chat canónico**
      en la VM y turnos async (`peer run` / `peer status`). La key es credencial: la maneja el
      usuario. El sentido inverso (VM → local) requiere Tailscale/VPN (la VM no alcanza la PC por
      NAT). Doc: `https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode`
      (*Bot-initiated DMs across machines*).

---

## Propuesta técnica (Idea #16): Rediseño del JSON de mensajes y sesiones en MongoDB para Inteligencia de Gestión

### 1. Problemas detectados en el modelo actual (`dash.chatsV2` en `mongo.service.js`)
Al auditar los 1.011 documentos y 46.836 mensajes de `chatsV2` (2026-10-14), se identificaron 6 limitaciones en `saveMessage()` (`backend/services/mongo.service.js`) que dificultan el análisis directo por agentes y distorsionan las métricas comerciales:
1. **Un documento único infinito por contacto:** Todos los mensajes de la vida del cliente se apilan en un solo array `messages` (hay documentos de hasta 3.781 mensajes y 7+ pedidos de distintos meses mezclados).
2. **Pérdida de campos ricos al guardar en vivo:** Aunque `dashWhat2` extrae `caption`, `mediaUrl`, `quotedMessage` y `location` (`latitude`/`longitude`), el método actual `saveMessage()` de `mongo.service.js` solo guarda `{ id, role, type, content: messageData.textContent || '', timestamp }`, perdiendo en los mensajes nuevos las coordenadas GPS, URLs de comprobantes en Cloudinary y el mensaje citado.
3. **Inyección de ruido de protocolo (~10% de la base):** Se guardan en base de datos eventos de Baileys como `protocolMessage`, `reactionMessage`, `messageContextInfo`, `stickerMessage` y `secretEncryptedMessage` bajo `type: "unsupported"`.
4. **Resolución incompleta de identidad (`@lid` vs teléfono):** El 94,7% de los documentos usa el identificador opaco `@lid` de WhatsApp (`remoteJid`) sin persistir el `remoteJidAlt` / `participantPn` (`5959...@s.whatsapp.net`) cuando Baileys lo informa en el sobre del mensaje.
5. **Mezcla de roles y actores no comerciales:** El teléfono de Voraz también se usa para hablar con **proveedores** (imprenta, carnicería, tapas, avícola), **repartidores de delivery** e **internos**. Como todo mensaje saliente se etiqueta `role: "assistant"`, cuando Voraz le hace un pedido a un proveedor la IA puede confundirlo con una venta.
6. **Falta de vínculo con ERPNext y métricas de tiempos:** No se guarda el `salesOrderId` (`SAL-ORD-...`) cuando el pedido se agenda, ni los hitos horarios (`scheduledFor`, `readyAt`, `dispatchedAt`) para medir demoras reales del delivery.

---

### 2. Arquitectura propuesta: Separar Perfil (`contacts`) de Sesiones (`chat_sessions`)

En lugar de un único documento gigante por número, estructurar la persistencia en dos niveles (o mantener el array corto de ventana activa en el contacto y archivar cada interacción cerrada como un documento en `chat_sessions`):

#### A. Colección `contacts` (1 documento por persona/empresa — CRM ligero)
Guarda la identidad consolidada del contacto y sus datos permanentes para no tener que pedirlos ni extraerlos de nuevo en cada compra:

```json
{
  "_id": "63209067294835@lid",
  "contactJid": "63209067294835@lid",
  "phoneJid": "595981123456@s.whatsapp.net",
  "phone": "+595981123456",
  "contactName": "Brahian Rolón",
  "contactRole": "cliente",
  "erpCustomerName": "Brahian Rolón",
  "billing": {
    "ruc": "5089138-3",
    "legalName": "Brahian Rolón",
    "email": "brahianrolon@gmail.com"
  },
  "savedLocations": [
    {
      "label": "Barrera principal de Itaipú",
      "lat": -25.512209,
      "lng": -54.638012,
      "defaultDeliveryFeeGs": 40000
    }
  ],
  "stats": {
    "totalOrders": 8,
    "totalSpentGs": 2650000,
    "firstContactAt": "2026-02-11T13:18:11Z",
    "lastOrderAt": "2026-10-09T14:51:36Z",
    "avgDaysBetweenOrders": 30
  }
}
```
*Valor de gestión:* Permite detectar automáticamente **clientes frecuentes inactivos** (ej. *"clientes con +3 compras cuyo `lastOrderAt` superó su ciclo habitual de 30 días"*), autocompletar RUC/correo al facturar y cotizar el delivery automáticamente según su ubicación guardada.

---

#### B. Esquema enriquecido de cada mensaje (`messages[]`)
Filtrar en `dashWhat2` / `mongo.service.js` todo `protocolMessage` y `reactionMessage` **antes** de insertar en Mongo, y guardar cada mensaje válido con esta estructura normalizada:

```json
{
  "id": "3EB0A1...",
  "ts": "2026-10-09T14:52:33.000Z",
  "localTimePy": "2026-10-09T11:52:33-03:00",
  "direction": "in",
  "senderType": "contact",
  "isAutoReply": false,
  "type": "text",
  "text": "Para entregar hoy 15:30hs, barrera principal de Itaipu: 50 mini burgers, 30 canastitas...",
  "caption": null,
  "media": {
    "url": "https://res.cloudinary.com/...",
    "mimeType": "image/jpeg",
    "kind": "comprobante_pago"
  },
  "location": {
    "lat": -25.512209,
    "lng": -54.638012,
    "name": "Barrera Itaipú",
    "address": null,
    "mapsUrl": "https://maps.app.goo.gl/..."
  },
  "replyTo": {
    "messageId": "3EA99...",
    "snippet": "Si necesitas factura pásame RUC y nombre"
  }
}
```
*Cambios clave frente al JSON actual:*
- `localTimePy` precalculado en zona `America/Asuncion` (evita errores de UTC vs. hora hablada en el chat).
- `isAutoReply: true` cuando el mensaje es el saludo automático del catálogo o de horario de atención (permite medir el **tiempo real de primera respuesta humana** sin confundirlo con el bot).
- Preservación íntegra de `location`, `media` y `replyTo`.

---

#### C. Colección `chat_sessions` (1 documento por interacción/pedido, cortando tras $\ge 36\text{ h}$ de inactividad)
Cada vez que una conversación se resuelve o pasa 36 horas sin mensajes, se consolida el bloque `analytics` (mediante IA estructurada + vínculos del backend):

```json
{
  "_id": "698c81954a7df570da63ff30_20261009",
  "contactJid": "63209067294835@lid",
  "phone": "+595981123456",
  "contactName": "Brahian Rolón",
  "contactRole": "cliente",
  "startedAt": "2026-10-09T14:51:36Z",
  "endedAt": "2026-10-09T18:38:43Z",
  "initiatedBy": "contact",

  "erpLink": {
    "salesOrderId": "SAL-ORD-2026-00412",
    "salesInvoiceId": "ACC-SINV-2026-00389",
    "paymentEntryId": "ACC-PAY-2026-00401"
  },

  "sla": {
    "firstHumanReplySeconds": 63,
    "leadTimeHours": 3.6,
    "scheduledDeliveryTime": "2026-10-09T15:30:00-03:00",
    "kitchenReadyAt": "2026-10-09T15:05:00-03:00",
    "deliveryDispatchedAt": "2026-10-09T15:21:42-03:00",
    "hadDelayOrComplaint": false,
    "delayReason": null
  },

  "commercial": {
    "intent": "compra_bocaditos",
    "outcome": "venta_cerrada",
    "lostReason": null,
    "eventType": "oficina_empresa",
    "fulfillment": "delivery",
    "deliveryZone": "Barrera principal de Itaipú",
    "items": [
      { "itemCode": "Mini Burger", "qty": 50, "unit": "unidades" },
      { "itemCode": "Canastita", "qty": 30, "unit": "unidades" },
      { "itemCode": "Milanesa Pollo", "qty": 60, "unit": "unidades" },
      { "itemCode": "Gaseosa 2lts", "qty": 1, "unit": "botellas" }
    ],
    "unmetDemand": {
      "askedForCake": false,
      "askedForSweetPastries": false,
      "unavailableProductsRequested": ["sprite 2L", "fanta piña 2L"],
      "customizationsRequested": []
    },
    "financials": {
      "subtotalGs": 333000,
      "deliveryFeeGs": 40000,
      "totalGs": 373000,
      "paymentMethod": "transferencia",
      "invoiced": true
    }
  },

  "cleanTranscript": "[2026-10-09 11:51] CONTACTO: Hola, buenos días..."
}
```

### 3. Nuevos indicadores de gestión que habilita este formato
1. **Auditoría cruzada WhatsApp $\leftrightarrow$ ERPNext (`erpLink`):** Detectar al instante si un pedido confirmado como *"Agendado"* o *"Acreditado"* en WhatsApp se olvidó de cargar o cobrar en ERPNext.
2. **Medición exacta de puntualidad de cocina vs. repartidor (`sla`):** Separar cuándo un atraso fue de cocina (`kitchenReadyAt` tarde) vs. cuándo el pedido estuvo listo a horario pero el repartidor tardó 40 minutos en pasar a buscarlo (`deliveryDispatchedAt - kitchenReadyAt`).
3. **Embudo de ventas perdidas por anticipación (`leadTimeHours`):** Saber cuántos pedidos se pierden por pedir con menos de 2 horas de anticipación o para domingos, para evaluar si conviene tener stock congelado/pre-listo en horas pico.
4. **Radar permanente de nuevos productos (`unmetDemand`):** Contabilizar mes a mes cuánta plata queda sobre la mesa por productos no trabajados (tortas, mesa dulce, bebidas específicas, opciones sin lactosa/vegetales).

