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

## 2026-10-07 — La VM se sincroniza por pull, con respaldo previo

- **Decisión**: sincronizar la VM con `git pull --ff-only`, respaldando antes lo que no está
  versionado (`docker-compose.yml`, `.env`) y moviendo el compose a un lado durante el pull.
- **Por qué**: el commit entrante agrega un `docker-compose.yml` versionado y el de la VM
  estaba sin versionar: Git se niega a pisar archivos no rastreados. Con el respaldo previo
  se pudo verificar que el resultado era **idéntico** (mismo hash) y que producción no
  cambiaba.
- **Descartado**: forzar el checkout (habría pisado el compose de producción a ciegas).

## 2026-10-07 — Los cambios sueltos de `dashWhat2` van a una rama, no a `main`

- **Decisión**: los 4 archivos modificados a mano en la VM se guardan en la rama
  `respaldo-vm-dashwhat2`, publicada en GitHub. `main` se deja en el refactor que ya estaba
  en `origin` (d39b6bd).
- **Por qué**: son dos trabajos distintos. Lo de la VM son parches para que Baileys conecte
  desde ese servidor; lo de `main` es el refactor posterior del usuario. Meter lo de la VM en
  `main` habría pisado trabajo más nuevo.
- **Descartado**: commitear directo en `main` (perdía el refactor) o dejarlos sin commitear
  (se perdían en el próximo pull).

## 2026-10-07 — NO se rotan el token de Chatwoot ni la contraseña de MongoDB

- **Decisión**: no rotar esas credenciales; se elimina la tarea del backlog.
- **Por qué**: decisión explícita del usuario, que asume el riesgo. Los valores ya no están
  en texto plano en el `docker-compose.yml` (se movieron a `~/voraz/.env`).
- **Descartado**: rotarlas (requiere acceso a los paneles de Chatwoot y MongoDB Atlas).

## 2026-10-08 — Dos usuarios de integración en vez de `Administrator`

- **Decisión**: crear `vorazcde@gmail.com` ("integracion@", rol `Voraz Integracion`, con
  escritura) para `erp-service`, y `xjuanmax@hotmail.com` ("consulta@", rol `Voraz Lectura`,
  solo lectura) para el MCP. Los roles se definieron con `Custom DocPerm` sobre 22 doctypes.
- **Por qué**: `Administrator` es el usuario más privilegiado del ERP — una credencial filtrada
  daba control total (usuarios, configuración, todas las compañías). Con dos usuarios, la
  seguridad no depende solo de la whitelist de herramientas del MCP: **aunque la whitelist
  falle, el ERP rechaza la escritura por permisos**. Defensa en profundidad.
- **Descartado**: usar roles estándar (ninguno da solo-lectura de todo: `Auditor` cubre cuentas
  pero no ventas, y `Stock User` escribe en `Delivery Note`).
- **Nota**: se creó un `Custom DocPerm` por rol y doctype. Hay que recordar que **reemplaza** el
  set estándar — el primer intento rompió los permisos y hubo que revertir borrándolos.

## 2026-10-08 — Validación de teléfono al crear clientes

- **Hallazgo**: `erp-service` crea el `Customer` con `customer_name = <JID>`,
  `customer_type = Individual` y `mobile_no = <parte numérica del JID>`. ERPNext **valida que
  `mobile_no` sea un teléfono real** (`InvalidPhoneNumberError` → 417). Con un JID de prueba no
  numérico, la creación falla.
- **Implicancia**: los JID reales de WhatsApp son numéricos, así que funciona; pero cualquier
  JID no numérico (como los `@lid` de prueba) rompe la creación con un 417 confuso. Vale tenerlo
  presente al diagnosticar.

## 2026-10-08 — Verificación de los 4 flujos críticos

- **Decisión**: probar crear pedido → cobrar → entregar → cancelar contra producción con
  `integracion@`, usando un cliente de prueba y limpiando todo al final.
- **Resultado**: los 4 pasan. Cancelar un pedido **con factura y remito vinculados** da
  `LinkExistsError` (correcto): hay que cancelar los hijos primero (pago → factura → remito →
  pedido), y así funciona.
- **Por qué importa**: confirma que los permisos del rol nuevo alcanzan para toda la operación
  real, que era el riesgo de migrar desde `Administrator`.

## 2026-10-08 — El MCP del agente de WhatsApp, también de solo lectura

- **Hallazgo**: el MCP que levanta `ia-service` para el agente de WhatsApp devolvía **todas** las
  herramientas (`get_tools_schema()` no filtraba nada), incluidas las de escritura, y las corría
  con las credenciales heredadas de `erp-service/.env` (usuario de **escritura**). El LLM del
  agente tenía, por lo tanto, escritura latente sobre el ERP.
- **Decisión**: (a) que el MCP use las credenciales `MCP_ERPNEXT_API_*` (usuario de consulta), y
  (b) filtrar las herramientas a las 5 de lectura, con rechazo también en `call_tool()`.
- **Descartado**: apagar el MCP (`ENABLE_MCP=false`). El agente **sí** lo usa (en los logs hay
  consultas libres reales como *"ventas del mes octubre"*), y las nativas —`get_sales_summary`,
  `get_sales_by_product`, `get_pending_orders`, `calculate`— no cubren consultas arbitrarias.
- **Nota**: Hermes y `ia-service` usan **dos instancias distintas** del mismo
  `erpnext-mcp-server`, en máquinas distintas y para consumidores distintos (Hermes → el
  asistente; `ia-service` → el agente de WhatsApp). No comparten proceso ni credenciales.

## 2026-10-08 — Incidente: los roles nuevos dejaron sin permisos a los demás usuarios

- **Qué pasó**: al crear los roles `Voraz Lectura` / `Voraz Integracion` con `Custom DocPerm`, la
  cuenta de Juanma (`xjuanma.romerox@gmail.com`, Sales Manager y System Manager) perdió el acceso
  a **ventas, inventario y contabilidad**. Solo se notó cuando él lo reportó al entrar al ERP.
- **Causa**: en Frappe, si un DocType tiene **alguna** fila en `tabCustom DocPerm`, esa tabla pasa
  a ser la **única** fuente de permisos de ese DocType y `tabDocPerm` se ignora **para todos los
  roles**. Al escribir solo mis dos roles, quedaron sin permisos los demás. `Administrator` no se
  ve afectado (tiene bypass), por eso las pruebas —que corría como Administrator o como los dos
  usuarios nuevos— no lo detectaron.
- **Por qué se me pasó**: verifiqué la lectura de los usuarios nuevos y la escritura de
  `integracion@`, pero **nunca verifiqué que un usuario estándar siguiera teniendo acceso**. Ese
  es el chequeo que ahora hace `scripts/roles_erpnext.py` en su salida `VPZ_VERIF`.
- **Reparación**: `frappe.permissions.copy_perms(doctype)` por cada uno de los 22 doctypes —
  copia la matriz estándar a la custom (aditivo). Estado verificado después: Juanma recuperó todo,
  `consulta@` sigue solo-lectura, `integracion@` mantiene escritura.
- **Lección**: al personalizar permisos de un DocType hay que dejar la matriz **completa**
  (estándar + propio), que es lo que hace la UI de Frappe. Y al verificar permisos hay que
  incluir **siempre un usuario estándar**, no solo los que se están tocando.



