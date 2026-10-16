# Borrador — cambios de arquitectura

> **Estado: BORRADOR DE TRABAJO.** No es el plan definitivo y no describe nada ya implementado.
> Acá se anotan conclusiones, evidencia y decisiones abiertas. Se edita a medida que
> avanzamos. El plan definitivo se escribe **después** de la auditoría de payload de
> WhatsApp (backlog, Idea #20 → marcada P0).
>
> Origen: sesión del 2026-10-16. Cero cambios de código en esta etapa.

---

## 1. Por qué existe este documento

El sistema Voraz es un desarrollo **emergente**: primero ERPNext, después el servidor
Baileys, y recién después se fueron juntando (backend, ia-service, Chatwoot, dashboard).
Eso dejó una topología que funciona pero que **duplica responsabilidades** (dos lugares
donde vive la conversación, cuatro donde vive el catálogo).

La pregunta puesta sobre la mesa: **conviene una reforma de roles antes de que el
sistema siga creciendo**, en particular para habilitar atención omnicanal con agente de IA.

Regla de esta etapa: planificar sin apuro, concluir acá, y recién después ejecutar por
etapas.

---

## 2. Correcciones a afirmaciones de esta sesión (para que no queden erratas en el doc)

| Afirmación inicial | Realidad verificada |
|---|---|
| "los `Customer` basura tipo `@lid` son spam generado por el bot" | **Error mío.** `@lid` es el identificador opaco del nuevo esquema de direcciones de WhatsApp: los mensajes llegan con `@lid` **y** con el JID de teléfono. No es basura. La basura real es **crear un `Customer` en ERPNext por cada mensaje** de quien solo pregunta precio (`syncCustomerWithERP`) — son problemas distintos y la solución es solo la segunda. |
| "`/api/chatwoot/webhook` es código muerto" | **Parcialmente falso.** El webhook **de cuenta** no existe (`webhooks` = 0 filas), pero el inbox de WhatsApp es `Channel::Api` y **sí tiene `webhook_url` cargado**: `http://backend:3000/api/chatwoot/webhook`. Ese camino funcionó 5 veces reales. |
| "responder desde Chatwoot no llega a WhatsApp" | **Falso.** Llega. Ver §4. |
| "el dedupe del eco se hace con `echo_id`" | **No en el webhook.** `echo_id` existe como columna y en el render de la API, pero **NO está en `Message#webhook_data`** → no viaja en el payload del webhook. El mecanismo debe ser `content_attributes` (sí viaja, ver §5). |

Nota de proceso: los 5 puntos de mejora técnica y el alcance omnicanal ya quedaron
anotados en `docs/backlog.md` (commit `b37d12c`, 16:32, otra sesión del proyecto con tu
identidad de git). No se duplican acá.

---

## 3. Evidencia dura recolectada (producción, solo lectura)

Entorno: Chatwoot **4.13.0**, Postgres `pgvector/pgvector:pg16`, imagen `chatwoot/chatwoot:latest`.

| Hallazgo | Cómo se verificó |
|---|---|
| 3 inboxes: `4` = "WhatsApp Voraz" (`Channel::Api`), `6` = "Voraz" (`Channel::FacebookPage`), `7` = "vorazcde" (`Channel::Instagram`) | `GET /api/v1/accounts/1/inboxes` desde el contenedor `voraz_backend` |
| El inbox 4 tiene `webhook_url` apuntando al backend, con `hmac_mandatory = false` | `select id, identifier, webhook_url, hmac_mandatory from channel_api;` sobre `chatwoot_production` |
| **0 webhooks de cuenta** | `select … from webhooks;` → 0 filas |
| **0 agent bots** y 0 agentes listados por API | `GET /agent_bots`, `GET /agents` |
| 23 conversaciones en el inbox 4 (20 mías, 3 sin asignar) | `GET /conversations?inbox_id=4` → `meta.all_count = 23`. Ojo: la respuesta viene envuelta en `{data: {meta, payload}}`, no en `payload` a secas |
| Conversación 410: **9 mensajes, todos `message_type: 0` (entrante)**, incluidos dos que escribió Voraz desde su celular: `"Si, pásame ubicación y te paso el total"` y `"[Reacción: 👍🏻]"` | `GET /conversations/410/messages` |
| 5 salientes panel→WhatsApp, resueltos a JID `@lid` y aceptados por Baileys | `docker logs voraz_backend \| grep -F "[Chatwoot Webhook]"` |
| Un `POST` de mensaje al Chatwoot de un inbox que **no** es `Channel::Api` rechaza `incoming` ("Incoming messages are only allowed in Api inboxes") | `app/builders/messages/message_builder.rb` |
| `content_attributes`, `source_id`, `message_type`, `sender`, `attachments`, `private`, `conversation` **sí** viajan en el payload del webhook; `echo_id` **no** | `app/models/message.rb#webhook_data` (líneas 180-198) |
| El webhook firma con `X-Chatwoot-Signature: sha256=<HMAC(secret, "<ts>.<body>")>` + `X-Chatwoot-Timestamp`; para inboxes API el secreto es `channel.secret` | `lib/webhooks/trigger.rb`, `app/listeners/webhook_listener.rb` (`deliver_api_inbox_webhooks`) |
| Los parámetros que acepta la API al crear un mensaje: `content`, `message_type`, `private`, `content_type`, `content_attributes`, `items`, `in_reply_to`, `echo_id`, `source_id`, `external_created_at`, `sender_type`/`sender_id` (solo `AgentBot`), `attachments`, `template_params`, `campaign_id` | `message_builder.rb#message_params` |
| `Channel::Api` **no tiene servicio de envío propio**: `SendReplyJob` lo mapea a `Messages::SendEmailNotificationService` (notifica por mail, no entrega a WhatsApp) | `app/jobs/send_reply_job.rb` (constante `CHANNEL_SERVICES`) |
| El catálogo está definido en 4 lugares (`CATALOG_NAMES`, `catalog.json`, `detalleProductos.json`, `productosYprecios.json`) | lectura de `backend` e `ia-service` |

---

## 4. Cómo funciona realmente hoy (lo que salió del análisis)

### 4.1 El híbrido ya está ocurriendo, por accidente funcional

Cuando se responde a un cliente **desde el panel de Chatwoot**:

```
Chatwoot (agente escribe) ──webhook inbox──► backend /api/chatwoot/webhook
                                                  └─► dashWhat2 /send-message ──► WhatsApp cliente
```

Y el mensaje que Baileys acaba de salir **vuelve como entrante propio** (`fromMe: true`,
`remoteJid` = cliente — Baileys no filtra `fromMe`, es regla documentada), entonces:

- el backend lo guarda en Mongo con `role: 'assistant'` ✔ correcto,
- lo reenvía a Chatwoot como **`incoming`** ✘ (el bug que originó esta sesión),
- y si el texto era `"Entonces te agendo: …"`, **`order.handler` lo detecta sobre ese eco
  y crea el `Sales Order`** ✔ — así es como el agendamiento desde la PC ya funciona.

**Consecuencia positiva:** no hay que construir el flujo panel→pedido; ya existe, y se
apoya en el eco de Baileys.

**Consecuencia de riesgo (crítica):** cuando el espejo se corrija para publicar los
propios salientes como `outgoing`, Chatwoot va a disparar su webhook por ese mensaje, el
backend lo va a volver a mandar a Baileys, y el ciclo se cierra. En el peor caso eso no
solo duplica el texto al cliente: **puede duplicar el `Sales Order`** (el segundo eco vuelve
a decir `Entonces te agendo:`). Por eso la dedupe no es un detalle de higiene: es
prerrequisito de la corrección de dirección, y hay que probarla antes de activar nada.

### 4.2 Lo que NO conecta a ningún canal con el resto del stack

- IG y FB entran a Chatwoot por webhooks de Meta y **mueren ahí**: no llegan al backend,
  no se guardan en Mongo, no se sincronizan con ERP, no los ve `ia-service`. Por eso no
  existe "un cliente" unificado entre canales.
- La respuesta saliente de IG/FB la da Chatwoot solo (nativo a Meta); no pasa por nada del
  stack propio. Un agente que quiera atender esos canales tiene que vivir del lado de
  Chatwoot, no del backend.
- El inbox de WhatsApp **no puede** responder por sí solo (§3, última fila): la entrega a
  WhatsApp es responsabilidad del backend + dashWhat2, hoy vía webhook de inbox.

---

## 5. Decisión central: el rol de Chatwoot (no el orden de las flechas)

La pregunta "¿`Baileys → Chatwoot → backend`?" trae dos cosas mezcladas: el **orden de
entrada** de WhatsApp y **dónde es la fuente de verdad** de la conversación.

### 5.1 Por qué conviene mantener la entrada de WhatsApp en el backend

`Baileys → backend → Chatwoot` se mantiene, no se invierte:

- Por el mismo número viaja tráfico que **no debe** ser conversación de cliente: comandos
  del admin (`/hoy`, `/cobrar`, `/consultar`), gatillos (`Entonces te agendo:`,
  `Modifico tu pedido:`) y chats con proveedores, carnicería, delivery e internos, que hoy
  filtra `contact_filter.service.js` contra `filtered_contacts` (Mongo). Ninguno de esos
  tres mecanismos existe del lado de Chatwoot.
- Si Chatwoot quedara primero, habría que reconstruir filtros + comandos + gatillos +
  sincronía con ERP adentro de Chatwoot (agent bot / automatizaciones), o meter lógica de
  negocio en `dashWhat2`, que hoy es transporte puro. Es más superficie de riesgo que la
  reforma actual, no menos.
- El backend además es quien resuelve contacto/conversación en Chatwoot (crear el
  `contact` con `identifier = jid`, abrir la conversación, etc.). Ese trabajo no desaparece
  al mover la flecha.

### 5.2 La reforma que sí conviene: Chatwoot pasa de espejo a **bus único de conversación**

Cambio de rol, no de orden:

- **Entrada WhatsApp:** `Baileys → backend → Chatwoot`, pero con **dirección correcta**
  (`incoming` / `outgoing`), `external_created_at` con el timestamp real, y marcador de
  origen en `content_attributes`.
- **Entrada Meta:** ya es Chatwoot. Se agrega un **webhook de CUENTA** (hoy inexistente)
  suscripto a `message_created` + eventos de conversación, apuntando al backend. Ese
  webhook es la única forma de que IG/FB (y TikTok cuando se conecte) entren al resto del
  stack.
- **El agente de IA se escribe UNA sola vez, detrás del bus**, leyendo/escribiendo
  conversaciones de Chatwoot → cubre WhatsApp + IG + FB + TikTok futuro sin tocar Baileys
  por canal. La salida del agente: por API de Chatwoot (IG/FB/TikTok) y por
  Chatwoot→webhook→backend→dashWhat2 (WhatsApp).
- **Regla anti-piso (el humano manda):** antes de responder, el agente chequea si la
  conversación tiene respuesta humana reciente o está asignada a un agente humano. Como el
  humano puede responder desde el panel **o desde el celular**, esa señal hoy es invisible
  (todo llega como `incoming`); con la dirección corregida, la señal existe.

### 5.3 Lo que esto resuelve de raíz (y por qué es "a tiempo")

Si Chatwoot es el bus de conversaciones, **deja de tener sentido construir un mini-CRM en
Mongo**. Chatwoot ya trae, de serie y con UI para Zulma:

| Necesidad | Donde se iba a construir | Donde ya existe |
|---|---|---|
| Ficha del cliente (nombre, teléfono, RUC, e-mail, notas) | colección `contacts` (Idea #16) | `Contact` + `custom_attributes` + `labels` |
| Historial por conversación/sesión | `chat_sessions` (Idea #16) | `Conversation` (+ estado, asignado, equipo) |
| Mensaje enriquecido (media, ubicación, citado, hora local) | `messages[]` (Idea #16) | `Message` + `attachments` + `content_attributes` + `external_created_at` |
| SLA: primer humano que responde, tiempos | `sla` (Idea #16) | métricas de Chatwoot (`first_response`) + timestamps reales |
| Bandeja compartida con traspaso humano | — (hoy resuelto con `agenda` y notificaciones) | inbox / assigns / teams |

**Consecuencia:** la Idea #16 se **reescribe** (pasa de "nuevo esquema en Mongo" a
"Chatwoot como fuente de verdad + Mongo como archivo del payload crudo"), y con eso se
corta la duplicación de transcript que es el mayor deuda del diseño emergente. Esta es la
reforma que conviene hacer ahora, mientras los canales son 3 y los clientes están
ordenados, no cuando la atención automatizada esté encima.

Queda explícitamente abierto qué hace falta conservar del lado Mongo/analítica (por
ejemplo métricas tipo *unmet demand*, lead time < 3 h, cocina vs repartidor) y si se leen
por API de Chatwoot, por su Postgres, o por un índice propio — eso se define en el plan.

### 5.4 Opción C (diferida, pero mencionada con datos): Cloud API oficial de WhatsApp

Sacar `dashWhat2` (Baileys) y conectar el número como canal oficial de WhatsApp en
Chatwoot (`Channel::Whatsapp`).

- **A favor:** desaparece la fragilidad de Baileys (loop de QR al desloguear, error 405 por
  versión de WhatsApp Web, sesión que solo persiste por el volumen), Chatwoot queda
  full-duplex para los 3 canales y la cadena se acorta.
- **En contra hoy:** el número se migra a la plataforma de Meta y eso cambia cómo se usa
  (es el mismo número con el que se habla a proveedores y repartidores desde el celular);
  aparecen costos por conversación y plantillas aprobadas; y la ventana de 24 h pasa a ser
  una restricción real del negocio.
- **Decisión:** no se toca en esta etapa, pero se anota porque **es una opción, no un
  destino inevitable**. Si algún día se toma, el diseño del bus (§5.2) no cambia: lo único
  que se saca es la entrada `Baileys → backend`.

---

## 6. Condición técnica dura para cualquier etapa que escriba mensajes en Chatwoot

**Dedupe por `content_attributes`, no por `echo_id`.**

- Al espejar desde el backend: `content_attributes: { source: 'dashwhat2', wa_message_id:
  <key.id>, by: 'admin'|'bot' }`.
- En el webhook del backend (`message_created`): si el mensaje trae `content_attributes.source`
  → es un eco nuestro → **no** se reenvía a Baileys. Si no lo trae → lo escribió un humano en
  el panel → se entrega.
- Ventanas: `sender_type: 'AgentBot'` + `sender_id` permite distinguir "lo mandó el bot" de
  "lo mandó un humano desde el panel" (Chatwoot lo resuelve en `message_sender`; hay que
  crear el AgentBot para usarlo).
- **Verificación sin tocar producción:** el contrato se prueba contra un **mock de Chatwoot**
  en el stack local, mismo patrón que `tools/mock-erp/` y `tools/mock-dashwhat/`. Hoy el
  override local apunta `CHATWOOT_URL: http://chatwoot:3000` a un DNS inexistente, así que el
  mock además cierra la tarjeta "Conectar Chatwoot en local (o simularlo)".
- La firma entrante se puede validar (`X-Chatwoot-Signature`, HMAC-SHA256 sobre
  `"<ts>.<body>"` con `channel.secret`); el secreto se mueve por archivo a `~/voraz/.env`,
  nunca por el chat.
- `hmac_mandatory = false` en el inbox API: revisar qué se está aflojando antes de
  depender de esto (es verificaciòn de lo que **entra** a Chatwoot, no de lo que sale).

---

## 7. Etapas propuestas (borrador, a confirmar después del P0)

| # | Etapa | Qué entrega | Riesgo |
|---|---|---|---|
| **P0** | **Auditoría del payload de WhatsApp** (backlog #20) | mapa real de `@lid` vs JID de teléfono, dónde viene `participantPn`/`remoteJidAlt`, qué campos se pierden hoy, casos borde | ninguno (lectura) |
| P1 | Espejo direccional + timestamp real + marcador de origen en el espejo, **con dedupe probado** | el panel de Chatwoot deja de mentir; historial de WhatsApp utilizable en la PC | medio: mal dedupe = mensaje duplicado o pedido duplicado. Se valida contra mock |
| P2 | Webhook de cuenta (`message_created` + eventos de conversación) y llegada de IG/FB al backend | el stack por fin ve los canales de Meta | bajo: no toca WhatsApp |
| P3 | Identidad única del cliente entre canales (`@lid` ↔ teléfono ↔ `Customer` de ERP ↔ contacto Chatwoot) | "el que escribió por IG es el que debe un cobro" | medio: merge de contactos |
| P4 | Regla anti-piso (handoff humano/bot) sobre el bus | requisito de que el agente no tape a Zulma | bajo |
| P5 | Agente de atención omnicanal (Idea #21): delivery, saludo/seguimiento, info operativa, detección de pedido completo | atención automática en los 3 canales | alto: habla con clientes reales → se enciende por inbox y con whitelist |
| P6 | Reescribir la Idea #16 sobre el nuevo rol de Mongo (archivo crudo vs transcript) | se elimina la duplicación de historial | medio: migración de datos |
| — | Las 5 mejoras puntuales ya en backlog (no crear `Customer` por mensaje, campos ricos en `saveMessage`, catálogo único, async en `ai_model.py`, higiene de compose) | — | bajo |

Orden no negociable: **P0 antes del plan definitivo**; **P1 no se activa sin la dedupe
probada** (por el riesgo de pedido duplicado); P5 recién con P1–P4 cerrados.

---

## 8. Preguntas abiertas para Juanma

1. **Fuente de verdad del historial:** ¿aceptamos que Chatwoot sea la dueña de la
   conversación y Mongo queda como archivo del payload crudo (o se retira), o querés
   mantener el transcript propio en Mongo?
2. **Número de WhatsApp y Cloud API:** ¿el número actual es el que usás con proveedores y
   repartidores desde el celular? Si sí, ¿la opción C queda descartada o es una
   conversación para más adelante?
3. **Catálogo único:** al unificar en ERPNext, ¿el alto del bot pasa a `Item`/`Item Price`
   sin excepciones, o hay productos que solo existen para el bot?
4. **Quién responde primero por IG/FB:** ¿el agente atiende esos canales desde el minuto uno
   o arrancan espejados "solo para verlos" y el bot entra después por inbox?
5. **Métricas que hoy da Mongo y pasarían a Chatwoot** (unmet demand, lead time, cocina vs
   repartidor): ¿las queremos en el dashboard actual (`dashboard.vorazadmin.site`) leyendo
   Chatwoot, o en un reporte periódico por WhatsApp?

---

## 10. P0 — cómo capturar el payload real (conclusión de la sesión 2026-10-16)

### 10.1 El dump que existía
`dashWhat2/api/main.js` tuvo **`//console.log(message)`** dentro del handler de
`messages.upsert`. Se **borró** (no se comenta ni se descomenta) en el commit `4aed8ea`
(2026-10-14, *"feat: improve message parsing for contacts, reactions, stickers, and
documents"*). Hoy no existe ningún dump del payload: grep de `stringify`/`console.log` del
sobre vacío en el clon local, en el `api/main.js` desplegado de la VM y en `/app/main.js`
del contenedor corriendo. El único `stringify` del repo es `test_parser.js:234`, que es el
cuerpo ya parseado que se postea al backend.

### 10.2 Lo que dice la doc de Baileys (cambia el enfoque del P0)
Fuente: `baileys.wiki` — tipos `WAMessageKey`, `LIDMapping` y la función
`extractAddressingContext`.

- `WAMessageKey` trae, además de `remoteJid`/`participant`: **`remoteJidAlt`**,
  **`participantAlt`**, **`addressingMode`**, `remoteJidUsername`, `participantUsername`,
  `isViewOnce`, `server_id`.
- `extractAddressingContext(stanza) → { addressingMode, recipientAlt, senderAlt }`.
- Existe `isLidUser` / `isHostedLidUser` para clasificar el tipo de `@lid`.

**Consecuencia:** el par `@lid` ↔ teléfono **viaja en el sobre que Baileys entrega**; no es
un dato a inferir ni a pedir por otra vía. El P0 entonces no es "descubrir" el esquema, es
**medir cuántos mensajes reales lo traen y en qué campos**, y documentar qué se descarta.

### 10.3 Sospecha concreta a verificar (por qué el paso 1 va en el backend)
`messageParser.js` retorna `key: message.key` **completo** y `main.js` lo postea tal cual a
`POST /api/messages`. En cambio `saveMessage()` (`services/mongo.service.js`) persiste solo
`{ id, role, type, content, timestamp }`. Si la sospecha es cierta, **el backend ya recibe
`remoteJidAlt` y lo está tirando** — el problema sería de persistencia, no de recepción, y
eso achica muchísimo la Idea #16.

### 10.4 Rutas de captura, por costo/riesgo

| Paso | Dónde | Cómo se despliega | Reversibilidad | Qué alcanza a ver |
|---|---|---|---|---|
| **1 (recomendado)** | `backend` (`routes/messages.routes.js`), log detrás de `LOG_RAW_MESSAGES=true` | `git pull` + `docker compose restart backend` (tiene **bind-mount**, **sin rebuild**) | apagar la flag | el payload **ya parseado** que Baileys manda: qué campos del `key` llegan vivos |
| 2 (si el 1 muestra que el parser rompe el sobre) | `dashWhat2/api/main.js` | **rebuild** del servicio (sin bind-mount) + verificar `df -h /` antes (disco ~85%) | revertir el commit | el sobre **crudo** de `messages.upsert`, antes del parseo |
| 2b (alternativa sin git/rebuild) | parche efímero dentro del contenedor | `docker cp` + `docker restart dashwhat2` | se limpia solo en el próximo recreate | idem 2, pero sin registrar nada en el repo |
| 2c (cero producción) | sesión Baileys con un número de prueba en local | `test_parser.js` / simulación | n/a | payloads reales de un número de prueba; **no** ve la variedad del tráfico de clientes |

**Regla:** el paso 1 se hace primero y solo. No se toca `dashWhat2` ni se reconstruye nada
hasta ver qué dio el log del backend. Nada de esto se ejecuta sin OK explícito de Juanma.

### 10.5 Checklist de casos a capturar (ventana del log)
El P0 se cierra cuando estén vistos en tráfico real, con nombre de campo y presencia/ausencia:

- [ ] mensaje de texto entrante de cliente `@lid` → ¿viene `key.remoteJidAlt` con el teléfono?
- [ ] mensaje de texto entrante de cliente `@s.whatsapp.net` → ¿viene `key.remoteJid` en claro?
- [ ] mensaje propio (`fromMe: true`) en chat de cliente → qué campos hay (`participantPn`, `addressingMode`)
- [ ] **audio** (no se puede transcribir en `dashWhat2`: ver `content: '[Audio]'`) → qué trae `mediaUrl`
- [ ] **imagen** con caption y sin caption (comprobante de pago) → `mediaUrl`, `caption`, `mimetype`
- [ ] **ubicación** estática y en vivo (`locationMessage` vs `liveLocationMessage`)
- [ ] **vCard** de contacto (`contactMessage`, `contactsArrayMessage`)
- [ ] **cita / respuesta** (`quotedMessage` + `contextInfo.stanzaId`) → ¿`replyTo` sobrevive al parseo?
- [ ] **reacción** (`reactionMessage`) → `targetMessageId`
- [ ] envoltorios: `ephemeralMessage`, `viewOnceMessageV2`, `documentWithCaptionMessage`, `editedMessage`
- [ ] ruido a filtrar: `protocolMessage`, `messageContextInfo`, `secretEncryptedMessage`, `@newsletter`, `@broadcast`, `@g.us`, `status@broadcast`
- [ ] `pushName` presente/ausente (de ahí salen los `Customer` tipo `.` en ERPNext)

Salida esperada: tabla `campo → ¿llega al backend? → ¿se guarda en Mongo? → ¿se espeja a Chatwoot?`,
que es la que alimenta el plan definitivo y la reescritura de la Idea #16.

---

## 11. Cómo seguir con este archivo

- Se edita acá, no en el chat: cada conclusión nueva entra como fila/tabla con su evidencia.
- Cuando el P0 esté hecho, este borrador se convierte en `docs/plan-arquitectura.md` (el
  definitivo), con decisiones registradas en `docs/decision-log.md` (fecha · decisión · por
  qué · alternativa descartada) y las etapas llevadas a tarjetas del tablero `voraz`.
- Nada de este archivo autoriza a tocar código todavía.
