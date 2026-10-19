# Mock de Chatwoot (tools/mock-chatwoot/)

Mock liviano en Python (stdlib pura) que emula la API de Chatwoot para desarrollo local y tests.

## Por qué un mock y no Chatwoot real en local
1. Chatwoot real es un stack pesado de 4 contenedores (Rails, Sidekiq, Postgres con pgvector, Redis).
2. Las pruebas locales contra una instancia compartida ensuciarían la bandeja de atención de clientes reales en producción.
3. Permite verificar de forma determinista:
   - Agrupación de conversaciones (10 mensajes del mismo contacto -> 1 sola conversación abierta, no 10).
   - Publicación correcta de mensajes salientes (admin) vs entrantes (cliente).
   - Prevención de loops de eco mediante `content_attributes.source = 'dashwhat2'`.

## Endpoints expuestos
- Estándar Chatwoot v1: `/api/v1/accounts/:id/...` (`inboxes`, `contacts`, `conversations`, `messages`).
- `GET  /health`: estado básico.
- `GET  /_mock/dump`: volcado de contactos, conversaciones y mensajes en memoria.
- `POST /_mock/reset`: limpiar estado.
- `POST /_mock/fire-webhook`: simula el disparo de un webhook de Chatwoot al backend (ej. operador respondiendo en el panel).
