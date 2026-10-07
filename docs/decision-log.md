# Registro de decisiones

**Formato append-only**: las entradas no se reescriben ni se borran; si una decisión se
revierte, se agrega una entrada nueva que la reemplaza y se referencia la anterior.

Cada entrada: **fecha · decisión · por qué · alternativa descartada**.

---

## 2026-10-07 — Hermes corre en local, no en la VM

- **Decisión**: el agente Hermes vive en la PC de desarrollo. Accede a la VM por SSH para
  diagnosticar, y los cambios viajan por Git.
- **Por qué**: la VM tiene 2 vCPU, 8 GB RAM (4 GB disponibles) y el disco al 85%, con 19
  contenedores de producción. Un contenedor de Hermes pide 2–4 GB de RAM y trae Chromium:
  competiría con el ERP. Además, un agente *dentro* de producción contradice la propia
  regla de "no tocar producción".
- **Descartado**: (a) Hermes en un contenedor en la VM — riesgo de desestabilizar el ERP y
  de llenar el disco; (b) backend de terminal remoto por SSH desde Hermes local — cada
  escritura del agente caería directo en producción.

## 2026-10-07 — MCP por API REST, no una app Frappe

- **Decisión**: la conexión de Hermes a ERPNext usa el MCP server que habla la **API REST**
  (`erpnext-mcp-server`, TypeScript), en lugar de instalar una app Frappe dentro del ERP.
- **Por qué**: ERPNext corre en **Docker** (`frappe_docker`), así que instalar una app
  implica reconstruir imágenes — con el disco al 85% eso es riesgoso y toca producción. La
  vía REST logra lo mismo sin modificar el ERP.
- **Descartado**: app nativa Frappe (mejores permisos por rol y audit log) — queda como
  alternativa futura si se necesita escritura con permisos finos.

## 2026-10-07 — El MCP arranca en solo lectura

- **Decisión**: exponer a la IA únicamente `get_doctypes`, `get_doctype_fields`,
  `get_documents`, `get_document` y `run_report`.
- **Por qué**: reducir superficie de riesgo. Las herramientas de escritura existen en el
  server pero quedan fuera de la whitelist hasta que se habiliten explícitamente.
- **Descartado**: exponer todo el catálogo del server.

## 2026-10-07 — Se rota la API key de ERPNext y se sacan los secretos del compose

- **Decisión**: rotar la API key/secret de ERPNext (estaba filtrada) y mover los secretos
  que estaban en texto plano en `docker-compose.yml` a `~/voraz/.env`.
- **Por qué**: la credencial se expuso en salidas de diagnóstico, y la integración corría
  con el usuario **Administrator** (el más privilegiado del ERP). Los valores salidos del
  compose fueron `MONGODB_URI`, `CHATWOOT_API_TOKEN` y `CHATWOOT_INBOX_IDENTIFIER`;
  verificados byte a byte (hash) después del cambio.
- **Descartado**: dejar el compose con valores inline y rotar después.

## 2026-10-07 — Al rotar credenciales de Frappe NO usar el ORM

- **Decisión**: las credenciales se escriben con `frappe.db.set_value` + 
  `set_encrypted_password`, y se verifican con `curl` antes de tocar los consumidores.
- **Por qué**: `generate_keys()` devuelve el secreto nuevo pero **el ORM no persiste los
  campos `read_only`**. El resultado fue un 401 para todas las credenciales y la integración
  caída. Usar `bench console` (IPython) además rompe al pegar bloques multilínea.
- **Descartado**: `generate_keys()` vía `bench console`.
- **Procedimiento completo**: `runbook.md` §6.

## 2026-10-07 — Se eliminan los usuarios `juanma` y `demian` de la VM

- **Decisión**: borrar esos dos usuarios con shell.
- **Por qué**: `juanma` era un duplicado del acceso del propio usuario, creado por un
  asistente anterior (tenía su clave local y aterrizaba en un home vacío en vez de
  `~/voraz`); `demian` era el usuario de su PC anterior. Ambos tenían `sudo` sin contraseña.
  Nada los referenciaba. Se conservó únicamente `ubuntu` (estándar de la imagen GCP, sin
  claves).
- **Descartado**: dejarlos "por si acaso".

## 2026-10-07 — La estructura local espeja la de la VM

- **Decisión**: `Documentos/voraz/` es el working copy del repo `voraz-control` (como
  `~/voraz/` en la VM) y `backend` se anida como `backend/backend`.
- **Por qué**: así el compose de producción y el override local usan **rutas idénticas** —
  cero divergencia y el compose puede versionarse. Se aceptó la fealdad del doble nivel a
  cambio de no tocar producción para arreglarlo.
- **Descartado**: mantener layouts distintos y un compose local aparte (dos fuentes de
  verdad).

## 2026-10-07 — La documentación se organiza por durabilidad, no por tema

- **Decisión**: reemplazar `memory-bank/` (secciones 01–06) y `SKILL.md` por `docs/` con
  `arquitectura.md`, `servicios.md`, `runbook.md`, `decision-log.md` y `backlog.md`, más
  `AGENTS.md` como puerta de entrada.
- **Por qué**: los documentos "de estado" hay que reescribirlos enteros para que sigan
  valiendo, y por eso se pudren (había una sección vacía desde 2025 y el índice apuntaba a
  una carpeta inexistente). Un registro append-only (`decision-log`) y un backlog no
  envejecen. Se elimina además la colisión de nombre `SKILL.md`, que confunde con las
  skills reales de Hermes.
- **Descartado**: seguir con el memory bank y "acordarse de actualizarlo".

## 2026-10-07 — Los Dockerfile se versionan

- **Decisión**: quitar `Dockerfile` de los `.gitignore` de `backend`, `erp-service` e
  `ia-service` y commitearlos.
- **Por qué**: estaban **solo en la VM**. Si se perdía la VM, se perdía la forma de
  construir los servicios.
- **Descartado**: dejarlos como archivos locales de cada servidor.

## 2026-10-07 — El MCP de `ia-service` es opcional

- **Decisión**: gatear el arranque del MCP con la variable `ENABLE_MCP` (por defecto
  encendido, apagado en local).
- **Por qué**: en local el MCP necesita el `build/` del server y un ERP real que no existen.
  Con el valor por defecto, producción no cambia de comportamiento.
- **Descartado**: desactivar el MCP solo en local con un parche aparte (divergiría el código).
