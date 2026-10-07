# Voraz — espacio de trabajo

Contexto permanente del proyecto **Voraz**: comercio de **bocaditos / finger food**
para eventos, reuniones y fiestas. Elaboración propia y venta por pedido.

Este archivo se carga automáticamente en cada conversación que corre dentro de
`/home/juanma/Documentos/voraz`, y es la **puerta de entrada**: acá están el mapa,
las reglas duras y el índice de todo lo demás. El detalle vive en `docs/`.

---

## Índice de documentación

| Documento | Qué contiene |
|---|---|
| `docs/arquitectura.md` | Cómo está armado el sistema y cómo se conectan los servicios |
| `docs/servicios.md` | Qué hace cada servicio en detalle (backend, ia, erp, dashWhat2, ERPNext) |
| `docs/runbook.md` | Cómo se opera: desplegar, desarrollo local, diagnóstico, rotar credenciales |
| `docs/decision-log.md` | **Por qué** se decidió cada cosa (registro append-only) |
| `docs/backlog.md` | Objetivos, progreso por fases, ideas y bugs abiertos |

Skills de Hermes relacionadas: `voraz-erpnext` (consultar el ERP), `voraz-deploy` (desplegar).

---

## Mapa del entorno

**Local (esta PC):** `/home/juanma/Documentos/voraz/` — espeja la estructura de la VM.
Acá se edita y se prueba. Cada servicio es su propio repo git (`juanma-romero/*`).

**Producción:** VM de GCP `instance-voraz-main` (zona `us-central1-f`), acceso `ssh voraz`
(alias configurado; clave dedicada `~/.ssh/voraz_ed25519`).

```
Documentos/voraz/            ~/voraz/ (en la VM)
├── AGENTS.md
├── docs/
├── backend/backend/         repo backend   · Node/Express · puerto 3000
├── erp-service/             repo erp-service · FastAPI · puerto 8001
├── ia-service/              repo ia-service  · FastAPI · puerto 8000
├── dashWhat2/               repo dashWhat2   · Baileys   · puerto 8880
├── docker-compose.yml       stack (base = producción)
├── docker-compose.local.yml override de desarrollo
└── dev.sh                   atajo del stack local
```

**ERPNext** — `https://vorazadmin.site` (Docker `frappe/erpnext:v16.12.0`). Es la fuente
de verdad para pedidos, clientes, stock y contabilidad. Se consulta por API REST; desde
Hermes hay un MCP de **solo lectura** (`voraz_erpnext`).

**El usuario correcto en la VM es `xjuanma_romerox`** (uid 1001, dueño de `~/voraz`).
Deben existir solo dos usuarios con shell: ese y `ubuntu` (estándar de la imagen GCP, sin
claves autorizadas). **Si aparece cualquier otro usuario con shell, es un error: avisá al
usuario antes de usarlo y no le generes ni copies claves.**

---

## Reglas duras

### Producción
- **Nunca modificar código directamente en la VM.** Es producción: se diseña y se prueba
  en local, y se despliega por Git (`docs/runbook.md`).
- Cuando el usuario pida "revisar un error en producción": **solo diagnosticar y proponer
  diffs**. Se permite usar `curl` y comandos de lectura (`docker logs`, `git log`).
- **El disco de la VM está al ~85%** (≈4 GB libres de 29 GB). Antes de cualquier operación
  que genere imágenes o archivos grandes (rebuilds, builds), chequear `df -h /` y avisar.
- No correr `docker compose down` en la raíz de la VM: baja los cuatro servicios de golpe.

### Credenciales
- **Ningún secreto va en el código, en `docker-compose.yml` ni en el chat.** Viven en
  archivos `.env` (detalle y ubicaciones en `docs/runbook.md`).
- Las credenciales de producción **nunca** se reusan en local: fue exactamente el origen
  del incidente de la API key filtrada.
- Nunca repetir el valor de un secreto en una respuesta, aunque aparezca en una salida de
  herramienta.

### Estilo de trabajo
- Responder en **español**, conciso y directo, enfocado en la solución técnica.
- Al proponer cambios de código: **diff** con la ruta exacta del archivo.
- Preferir **consultar datos reales** (ERP vía MCP, `docker logs`, API) antes que suponer
  estructuras o nombres.

### Nombres contables de ERPNext (verificados contra producción)
Usar exactamente estos valores: el nombre equivocado en un `Payment Entry` o `Journal Entry`
rompe la operación.

| Recurso | Valor en producción |
|---|---|
| Modo de pago — efectivo | `Cash` |
| Modo de pago — transferencia | `Wire Transfer` |
| Cuenta caja | `Efectivo - Vz` |
| Cuenta banco Ueno | `1212 - Ueno - Vz` |
| Cuenta gastos varios | `Gastos varios - Vz` |
| Cuenta ajuste de inventario | `1414 - Ajuste de inventario - Vz` |

Moneda de la Company: **PYG (guaraníes)**, montos enteros sin decimales.

> Nota: en el ERP hay muchos `Customer` basura generados por el bot de WhatsApp
> (ej. `30807917879527@lid`, o `.`). Excluirlos al armar reportes.

---

## Cómo mantener este espacio

- **Una sola fuente de verdad por dato.** El README técnico de cada servicio vive **en su
  repo**; `docs/` es la vista de conjunto y enlaza, no copia.
- **Lo que se decide, se registra** en `docs/decision-log.md` (fecha · decisión · por qué ·
  alternativa descartada). Es append-only: no se reescribe, se agrega.
- **Lo que cambia seguido va a `docs/backlog.md`**, no a un documento "de estado" que haya
  que reescribir entero para que siga valiendo.
