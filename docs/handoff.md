# Handoff — estado del trabajo al 2026-10-18

Resumen de la sesión del 16/10 al 18/10 (auditoría del payload de WhatsApp + análisis de
arquitectura). El detalle con evidencia está en `docs/borrador-cambios-arquitectura.md`.

## Qué se desplegó y está vivo

| Cosa | Estado |
|---|---|
| Visor de payload crudo de Baileys (`dashwhat2`, `[RAW-PAYLOAD]`) | **ENCENDIDO** en producción |
| Visor de payload parseado (`voraz_backend`, `[AUDIT-PAYLOAD]`) | **ENCENDIDO** en producción |
| `dashWhat2` `551f4cc` | desplegado (rebuild; la sesión de WhatsApp sobrevivió, sin QR) |
| `backend` `68b7a61` | desplegado |
| `voraz-control` (borrador + backlog) | `112488b` |

Apagado de los visores: `LOG_RAW_PAYLOADS=false` / `LOG_RAW_MESSAGES=false` en el bloque
`environment` del compose + deploy, o revirtiendo el default en el código.

## Regla operativa (medida el 19/10, no ignorar)

**Responder desde el panel de Chatwoot NO ejecuta los gatillos.** Solo manda texto al cliente
(`chatwoot.routes.js` → `sendClientMessage`). El gatillo de pedido
(`order.handler.js:16`: `isFromMe && textContent.startsWith('Entonces te agendo:')`) vive en
el camino de los mensajes que entran por Baileys.

- Para **agendar/modificar un pedido o usar un comando**, escribirlo **desde el WhatsApp de
  la línea** en el chat del cliente. Desde el panel *parece* que se agendó y no pasa nada.
- En el panel, los mensajes que Voraz mandó **por WhatsApp** se ven como si los hubiera
  escrito el cliente (`message_type=0`). Solo lo escrito **dentro del panel** figura como
  saliente. No confiar en la columna de quién habló hasta que se corrija el §5-§6.

## Lecturas rápidas

```bash
ssh voraz 'docker logs dashwhat2 2>&1 | grep -F "[RAW-PAYLOAD]" | tail -20'
ssh voraz 'docker logs voraz_backend 2>&1 | grep -F "[AUDIT-PAYLOAD]" | tail -20'
```

**Ojo:** recrear un contenedor **borra su `docker logs`**. Para una auditoría en vivo, no
recrear los servicios hasta terminar la captura.

## Conclusiones cerradas (no reabrir)

1. **La identidad `@lid` ↔ teléfono llega hasta el backend.** Baileys entrega siempre
   `key.remoteJidAlt` + `addressingMode: "lid"` (25/25 medidos) y el backend lo recibe
   (17/17). Se pierde **al persistir**: `saveMessage()` guarda solo
   `{id, role, type, content, timestamp}`. **No hace falta tocar `dashwhat2` para esto.**
2. **No se pierde ningún mensaje de cliente.** Los que no llegan al backend son estados
   (`status@broadcast`) y mensajes propios, ignorados a propósito.
3. **El flujo híbrido ya se usa**: respuestas desde el panel de Chatwoot y pedidos agendados
   con `"Entonces te agendo: …"` escrito desde el panel (se detecta por el eco de Baileys).
4. **Respuesta desde WhatsApp se ve en Chatwoot, pero como `message_type=0`** (como si la
   hubiera escrito el cliente). Es el defecto de dirección a corregir.

## Correcciones de código ya hechas en `dashWhat2` (deployadas)

`app.listen`/`setInterval` fuera de `connectToWhatsApp` (EADDRINUSE + intervals acumulados),
`shouldIgnoreMessage(msg, phonesToFilter)` (faltaba el 2º argumento), `SELF_URL` en vez de
`localhost:8880`, `fetchLatestWaWebVersion` con fallback (ya no muere sin reconectar),
`statusCode` en el log de conexión, `messages.update` registrado, y `npm ci` en el Dockerfile
(antes `npm install` con dependencias en `"*"` bajaba una rc nueva de Baileys en cada build).

## Pendientes, con el detalle en el borrador

1. **Chatwoot fragmenta conversaciones** (§12.1): 424 conversaciones para 106 contactos.
   Causa parcial confirmada: el código saltea las conversaciones `resolved`
   (`chatwoot.service.js:161`) y las conversaciones se resuelven a mano al cerrar cada
   pedido. Falta instrumentar `getInboxId()` y el `301` hacia HTTPS.
2. **Adjuntos del panel nunca llegan a WhatsApp** (§12.4): el handler exige `content` no
   vacío y envía solo texto. Un PDF adjunto se descarta en silencio.
3. **PDF entrante llega sin archivo**: solo el nombre (`[Documento: x.pdf]`), sin
   `mediaUrl` — a diferencia de imagen y audio.
4. **Espejo direccional + marca de origen** (§6): publicar `outgoing` los mensajes propios,
   con dedupe por `content_attributes` (no `echo_id`: no viaja en el payload del webhook).
   **Sin la dedupe probada, el eco puede duplicar el `Sales Order`.**
5. **Tarjeta `t_564c5804` ("Conectar Chatwoot en local o simularlo", tablero `voraz`)**:
   recomendación escrita como comentario — mock en `tools/mock-chatwoot/` que imite las
   rarezas reales, no el Chatwoot real en local (ensuciaría la bandeja de producción).
6. **Pruebas a repetir con el visor encendido**: reenviar un PDF y responder **con texto**
   desde el panel (ida y vuelta completo: panel → Baileys → eco `fromMe` → espejo).
7. **Videos**: `videoMessage` entra al log crudo pero el parser no lo maneja. **Audio**: se
   sube a Cloudinary pero no se transcribe (`content: '[Audio]'`), así que el agente no lo ve.
8. **Higiene de docs**: el disco de la VM está al 50% (29 G libres de 58 G), no al 85% que
   dicen `runbook.md` y `AGENTS.md`.

## Preguntas abiertas para decidir (borrador §8)

1. ¿Chatwoot como dueña de la conversación y Mongo como archivo crudo (o se retira)?
2. ¿El número actual se puede migrar a Cloud API oficial (opción C) o queda descartado?
3. ¿El catálogo se unifica en ERPNext sin excepciones?
4. ¿El agente atiende IG/FB desde el principio o primero espejados "solo para verlos"?
5. Las métricas que hoy da Mongo (unmet demand, lead time, cocina vs repartidor): ¿al
   dashboard actual leyendo Chatwoot, o reporte periódico por WhatsApp?
