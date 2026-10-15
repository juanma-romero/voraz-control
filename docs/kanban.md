# Kanban — Voraz

Tablero de tareas **accionables** y su estado. Complementa a `backlog.md`, que es el documento de visión, ideas y estado del sistema: el backlog dice *qué queremos*; este tablero dice *en qué anda cada cosa*.

> ⚙️ Generado automáticamente por `scripts/kanban-md.py` desde el board Kanban de Hermes (`voraz`) — **no editar a mano**.
> Última generación: 2026-10-15 09:35 (hora de Paraguay) · 20 tarjetas abiertas.

## Resumen

| Estado | Tarjetas |
|---|---:|
| 🔧 En curso | 0 |
| 👀 En revisión | 0 |
| 🚧 Bloqueado | 1 |
| ⏰ Agendado | 0 |
| 📋 Listo para hacer | 11 |
| 📋 Por hacer (esperando dependencias) | 0 |
| 💡 Sin definir (ideas) | 8 |
| ✅ Hecho | 0 |
| **Total abiertas** | **20** |

## Tablero

### 🚧 Bloqueado (1)

| ID | P | Tarea | Dueño | Creada |
|---|---:|---|---|---|
| `t_29430e78` | 20 | Apagar la API key de Administrator en ERPNext | — | 2026-10-15 |

### 📋 Listo para hacer (11)

| ID | P | Tarea | Dueño | Creada |
|---|---:|---|---|---|
| `t_eff7c05f` | 10 | Fase 2 — Endpoints dedicados de stock y finanzas | — | 2026-10-15 |
| `t_8cc7506e` | 10 | Fase 3 — Tools de mensajes / MongoDB en `ia-service` | — | 2026-10-15 |
| `t_c9febeb6` | 15 | Objetivo 4 — Cobros y pagos | — | 2026-10-15 |
| `t_e6a144e3` | 15 | Objetivo 5 — Control de stock e inventario | — | 2026-10-15 |
| `t_b8d99aea` | 15 | Objetivo 6 — Análisis de conversaciones | — | 2026-10-15 |
| `t_6d393fe7` | 20 | Mongo en local contra la base de prueba `test` | — | 2026-10-15 |
| `t_564c5804` | 20 | Conectar Chatwoot en local (o simularlo) | — | 2026-10-15 |
| `t_59e26649` | 20 | Puente agente-a-agente: `hermes peer` local ↔ VM | — | 2026-10-15 |
| `t_a926c5b4` | 20 | Decidir destino de la rama `respaldo-vm-dashwhat2` | — | 2026-10-15 |
| `t_d454fd51` | 30 | Bug: la fecha y la hora no son las correctas | — | 2026-10-15 |
| `t_6e49ae3b` | 30 | Bug: al cobrar manda error pero toma el cobro | — | 2026-10-15 |

### 💡 Sin definir (ideas) (8)

| ID | P | Tarea | Dueño | Creada |
|---|---:|---|---|---|
| `t_514867ba` | 5 | Idea #8 — Imágenes de productos a Cloudinary | — | 2026-10-15 |
| `t_407d3d52` | 5 | Idea #11 — Validación IA antes de confirmar un pedido | — | 2026-10-15 |
| `t_79b2e011` | 5 | Idea #13 — Alertas proactivas de stock bajo | — | 2026-10-15 |
| `t_ac79d309` | 5 | Idea #14 — Resumen diario automático por WhatsApp | — | 2026-10-15 |
| `t_6fcd49e2` | 5 | Idea #1+#15 — Registro de compras y gastos (incl. por voz/texto libre) | — | 2026-10-15 |
| `t_1fe471b5` | 5 | Idea #16 — Rediseño del modelo de datos de conversaciones en Mongo | — | 2026-10-15 |
| `t_61aa6242` | 5 | Idea #9 — Estado de cuentas del activo corriente | — | 2026-10-15 |
| `t_48614549` | 5 | Idea #10 — Ventas por día de entrega | — | 2026-10-15 |

## Detalle de las tarjetas abiertas

### 🚧 Bloqueado

<details><summary><code>t_29430e78</code> — Apagar la API key de Administrator en ERPNext</summary>

Ya no la usa nada; se conservó como rollback unos días (backlog.md → Pendientes de
infraestructura; runbook.md §7).

Requiere tus clics/credenciales en ERPNext (System Manager).

Criterio de hecho: key de `Administrator` revocada y los 4 flujos críticos
verificados funcionando con `integracion@` (escritura) y `consulta@` (lectura).

</details>

### 📋 Listo para hacer

<details><summary><code>t_eff7c05f</code> — Fase 2 — Endpoints dedicados de stock y finanzas</summary>

Opcional / optimización (backlog.md → Agente de IA, fases).

Hoy muchas de estas consultas ya las resuelve el agente por MCP + ReAct, pero
endpoints dedicados responderían más rápido.

| Tool a crear | Endpoint en erp-service | Consulta objetivo |
|---|---|---|
| `get_stock_balance` | `GET /api/stock/balance` | "stock de empanadas" |
| `get_payment_entries` | `GET /api/payments/summary?period=X` | "cobros de esta semana" |
| `get_pending_payments` | `GET /api/payments/pending` | "pedidos sin cobrar" |
| `get_supplier_expenses` | `GET /api/expenses/summary?period=X` | "gastos del mes" |

</details>

<details><summary><code>t_8cc7506e</code> — Fase 3 — Tools de mensajes / MongoDB en `ia-service`</summary>

Pendiente (backlog.md → Agente de IA, fases).

Requiere conexión directa de `ia-service` a Mongo (sin pasar por el backend):
agregar `MONGO_URI` al `.env` de `ia-service`, `pymongo` a `requirements.txt` y
crear `ia-service/services/mongo_tools.py`.

| Tool | Parámetros | Consulta objetivo |
|---|---|---|
| `get_client_messages` | `client_name, limit=10, only_pending=false` | "últimos mensajes de Juan" |
| `get_pending_messages` | `limit=20` | "quién está esperando respuesta" |
| `get_client_summary` | `client_name` | "estado de la conversación con Pedro" |

</details>

<details><summary><code>t_c9febeb6</code> — Objetivo 4 — Cobros y pagos</summary>

Estado 🔄 pendiente (backlog.md → Objetivos).

Alcance: cobros recibidos, pagos a proveedores y pedidos sin cobrar.

Se apoya en la idea #15 (registro de gastos/egresos) y en el bug de `/cobrar`.

</details>

<details><summary><code>t_e6a144e3</code> — Objetivo 5 — Control de stock e inventario</summary>

Estado 🔄 pendiente (backlog.md → Objetivos).

Alcance: stock por producto, ingresos de compra y alertas de stock bajo.

Relacionado: `get_stock_balance` (Fase 2) y las alertas proactivas (idea #13).

</details>

<details><summary><code>t_b8d99aea</code> — Objetivo 6 — Análisis de conversaciones</summary>

Estado 🔄 pendiente (backlog.md → Objetivos).

Alcance: historial de conversación con un cliente y mensajes sin contestar.

Depende de la Fase 3 (conexión directa de `ia-service` a Mongo) y mejora mucho con
el rediseño del modelo de datos (idea #16).

</details>

<details><summary><code>t_6d393fe7</code> — Mongo en local contra la base de prueba `test`</summary>

Hoy el stack local usa un Mongo en contenedor (backlog.md → Pendientes de
infraestructura).

Objetivo: poder correr el flujo completo en local contra una base de prueba
descartable, sin tocar la base del entorno de producción.

</details>

<details><summary><code>t_564c5804</code> — Conectar Chatwoot en local (o simularlo)</summary>

Chatwoot figura como 🔄 no implementado en el estado actual (backlog.md).

Falta decidir si se conecta el Chatwoot real (el self-hosted de la VM) al entorno
local o si se arma un mock, igual que se hizo con `erp-service` y `dashWhat2`.

</details>

<details><summary><code>t_59e26649</code> — Puente agente-a-agente: `hermes peer` local ↔ VM</summary>

Hoy el Hermes local le habla al de la VM por SSH (atajo `~/.local/bin/vm-hermes`,
skill `voraz-vm-bridge`): funciona, pero **solo local → VM** y cae en una **sesión
aparte** (no aparece en el bot de Telegram de la VM).

La vía nativa es `hermes peer`:
1. Habilitar `platforms.api_server` en el gateway de la VM con un `API_SERVER_KEY` fuerte.
2. Dejarlo privado con un túnel SSH: `ssh -N -L 8377:localhost:8377 voraz`.
3. Registrar el peer desde local: `hermes peer add voraz-vm --url http://localhost:8377 --key <KEY>`.

Da **Bot Chat canónico** en la VM y turnos async (`peer run` / `peer status`).

La key es credencial: la manejás vos.
El sentido inverso (VM → local) requiere Tailscale/VPN (la VM no alcanza la PC por NAT).

Doc: https://hermes-agent.nousresearch.com/docs/user-guide/bot-mode
(*Bot-initiated DMs across machines*).

</details>

<details><summary><code>t_a926c5b4</code> — Decidir destino de la rama `respaldo-vm-dashwhat2`</summary>

Los 4 archivos que vivían solo en la VM quedaron guardados en la rama
`respaldo-vm-dashwhat2` (publicada en GitHub) y la VM se sincronizó en `main`.

La rama tiene los parches de conexión de Baileys (`Platform.MACOS`, browser
simulado) y un extractor de texto para mensajes de botones/listas.

Pendiente: decidir si se rescata algo de ahí (y se integra a `main`) o se descarta
y se borra la rama.

</details>

<details><summary><code>t_d454fd51</code> — Bug: la fecha y la hora no son las correctas</summary>

El sistema parece registrar en UTC en vez de la hora de Paraguay (`America/Asuncion`).

Detectado en el backlog: bug #1 y "Idea #12 — Revisar fecha y hora: parece que toma UTC".

Impacto: pedidos, entregas y cobros quedan con fecha/hora corrida, lo que rompe
`/hoy`, `/manana` y cualquier métrica por día de entrega.

Criterio de hecho: el mismo pedido creado a las 20:00 hora PY queda fechado
2026-xx-xxT20:00-03:00 (no +1 día), verificado en ERPNext y en MongoDB.

</details>

<details><summary><code>t_6e49ae3b</code> — Bug: al cobrar manda error pero toma el cobro</summary>

Al ejecutar `/cobrar`, el flujo devuelve error al admin aunque el pago **sí** queda
registrado (backlog.md → Bugs #2).

Impacto: el admin no sabe si el cobro entró, así que puede cobrar o facturar dos veces.

Criterio de hecho: `/cobrar` responde OK y el pago queda en ERPNext; si falla algo
posterior (factura, notificación), el pago no se duplica y el error se reporta claro.

</details>

### 💡 Sin definir (ideas)

<details><summary><code>t_514867ba</code> — Idea #8 — Imágenes de productos a Cloudinary</summary>

Subir a Cloudinary las imágenes de los productos y poner los links en
`ia-service/detalleProductos.json` para el bot.

</details>

<details><summary><code>t_407d3d52</code> — Idea #11 — Validación IA antes de confirmar un pedido</summary>

Antes de confirmar un pedido, que el asistente revise la conversación
cliente↔admin y avise al admin si hay diferencias para que él decida.

</details>

<details><summary><code>t_79b2e011</code> — Idea #13 — Alertas proactivas de stock bajo</summary>

El agente notifica al admin cuando el stock baja de un umbral.

</details>

<details><summary><code>t_ac79d309</code> — Idea #14 — Resumen diario automático por WhatsApp</summary>

Resumen diario automático enviado por WhatsApp al cerrar el día.

</details>

<details><summary><code>t_6fcd49e2</code> — Idea #1+#15 — Registro de compras y gastos (incl. por voz/texto libre)</summary>

Consolida la idea #1 (registrar las compras y gastos) y la #15 (registro de
gastos/egresos por voz o texto libre → ingreso de stock con IA).

</details>

<details><summary><code>t_1fe471b5</code> — Idea #16 — Rediseño del modelo de datos de conversaciones en Mongo</summary>

Rediseño de `chatsV3` / `chat_sessions` para analítica e inteligencia comercial.
La especificación detallada (problemas del modelo actual, colecciones `contacts` y
`chat_sessions`, mensajes enriquecidos, e indicadores nuevos) está al final de
`docs/backlog.md`.

Es la base que habilita: auditoría cruzada WhatsApp↔ERPNext, puntualidad de cocina
vs. repartidor, embudo de ventas perdidas y radar de productos no trabajados.

</details>

<details><summary><code>t_61aa6242</code> — Idea #9 — Estado de cuentas del activo corriente</summary>

Pedir estado de cuentas del activo corriente (caja, bancos, inventario).

</details>

<details><summary><code>t_48614549</code> — Idea #10 — Ventas por día de entrega</summary>

Hoy el sistema registra las ventas el día que se genera el pedido; se necesita poder pedir la venta por **día de entrega**.

</details>

## Cómo se usa

El board vive en Hermes (`~/.hermes/kanban/boards/voraz/kanban.db`):

```bash
hermes kanban --board voraz ls              # ver el tablero en terminal
hermes kanban --board voraz watch           # stream en vivo de eventos
hermes kanban --board voraz show <id>       # detalle de una tarjeta
hermes kanban --board voraz assign <id> default   # darle dueño (la ejecuta el dispatcher)
hermes kanban --board voraz complete <id> <id>    # cerrar tarjetas
hermes dashboard                            # panel web con el tablero
python3 scripts/kanban-md.py                # regenerar este archivo
```

Una tarjeta **sin dueño** queda visible pero quieta: el dispatcher la ignora (`Skipped (unassigned)`). Al asignarle un perfil, el dispatcher la toma y la ejecuta en un workspace aislado, y pasa a *En curso*.

> ⚠️ **La columna «Sin definir (ideas)» es la columna `triage` de Hermes.** Por eso `kanban.auto_decompose` debe quedar en **`false`**: con ese ajuste activo, el dispatcher levanta solo las tarjetas de `triage` y las parte en subtareas asignadas que **empieza a ejecutar sin preguntar**. Para descomponer una idea a mano y a propósito: `hermes kanban --board voraz decompose <id>`.
