# Runbook — operar el sistema Voraz

Todo lo operativo: dónde está cada cosa, cómo se despliega, cómo se diagnostica y cómo se
rotan credenciales. Se actualiza cuando cambia un procedimiento.

---

## 1. Entornos y accesos

| Entorno | Dónde | Cómo se accede |
|---|---|---|
| **Local** (desarrollo) | `/home/juanma/Documentos/voraz/` | esta PC, Docker |
| **Producción** | VM GCP `instance-voraz-main` | `ssh voraz` (usuario `xjuanma_romerox`) |
| **ERPNext** | `https://vorazadmin.site` | API REST / MCP `voraz_erpnext` |
| **Repos** | `github.com/juanma-romero/*` | git |

El alias `ssh voraz` usa la clave dedicada `~/.ssh/voraz_ed25519`. **No ejecutar
`gcloud compute config-ssh`**: reinyecta claves que expiran al mes y rompe el acceso.

---

## 2. Desarrollo local

Se levanta un **slice** del stack (no todo): `backend`, `erp_service`, `ia_service` y un
Mongo local.

```bash
cd /home/juanma/Documentos/voraz
./dev.sh              # levanta el slice
./dev.sh ps           # estado
./dev.sh logs -f backend
./dev.sh build backend
./dev.sh down         # apaga (los datos de Mongo quedan en el volumen)
```

- Puerto del backend en local: **3100** (el 3000 está ocupado en esta PC). ia-service
  **8100**, erp_service **8101**.
- Los contenedores llevan sufijo `_local` (`voraz_backend_local`, …): es imposible
  confundirlos con los de producción.
- **No se levanta `dashwhat2`** (riesgo de invalidar la sesión de WhatsApp de producción).
- **Chatwoot no corre en local**: las rutas que lo usan fallan con error de DNS.
- **ERPNext no está conectado en local** (pendiente): `erp_service` arranca pero las
  llamadas al ERP fallan.
- El MCP de ERPNext se apaga con `ENABLE_MCP=false` en `ia-service`.

### Estructura de archivos del stack

```
docker-compose.yml         base, = producción (fuente de verdad)
docker-compose.local.yml   override solo-dev
dev.sh                     atajo: siempre usa los dos -f + --env-file .env.local
.env.example               nombres de variables (versionado)
.env.local                 valores de desarrollo (NO versionado)
```

⚠️ Nunca invocar `docker-compose.yml` solo: esa es la configuración de producción.

---

## 3. Despliegue

Flujo: **se edita en local → commit → push → la VM hace pull + rebuild**.

```bash
# 1) LOCAL
cd /home/juanma/Documentos/voraz/<repo>
git add -A && git commit -m "..." && git push

# 2) VM: traer el cambio
ssh voraz 'cd ~/voraz/<ruta> && git pull --ff-only'

# 3) VM: reconstruir SOLO ese servicio
ssh voraz 'cd ~/voraz && docker compose up -d --build <servicio>'

# 4) Verificar
ssh voraz 'cd ~/voraz && docker compose ps'
ssh voraz 'docker logs --tail 30 <contenedor>'
```

| Servicio | Ruta local | Ruta en la VM | Servicio compose | Contenedor |
|---|---|---|---|---|
| backend | `backend/backend` | `~/voraz/backend/backend` | `backend` | `voraz_backend` |
| erp-service | `erp-service` | `~/voraz/erp-service` | `erp_service` | `erp_service_fastapi` |
| ia-service | `ia-service` | `~/voraz/ia-service` | `ia_service` | `ia_service_fastapi` |
| dashWhat2 | `dashWhat2` | `~/voraz/dashWhat2` | `dashwhat2` | `dashwhat2` |

**Antes de desplegar**, verificar que la VM no tenga cambios sin commitear
(`git -C ~/voraz/<ruta> status --porcelain`): un `git pull` puede fallar o pisar trabajo.

**Revertir**: `git checkout <commit-bueno>` en la VM → `docker compose up -d --build <servicio>`
→ volver a `main` cuando se arregle.

---

## 4. Diagnóstico (solo lectura)

```bash
ssh voraz 'cd ~/voraz && docker compose ps --format "{{.Service}}: {{.Status}}"'
ssh voraz 'docker ps --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"'
ssh voraz 'docker logs --tail 50 <contenedor>'
ssh voraz 'cd ~/voraz && git -C <ruta> log --oneline -3 && git -C <ruta> status --porcelain'
ssh voraz 'df -h / | tail -1; free -h | head -2'
```

Chequeos funcionales:

```bash
ssh voraz 'curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/docs'   # erp_service
ssh voraz 'curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/docs'   # ia_service
ssh voraz 'curl -s http://localhost:8001/api/orders/pending | head -c 200'        # dato real del ERP
```

---

## 5. Credenciales

**Ningún secreto en el código, en `docker-compose.yml` ni en el chat.**

| Archivo | Contiene |
|---|---|
| `~/voraz/.env` (raíz del compose) | `MONGODB_URI`, `CHATWOOT_API_TOKEN`, `CHATWOOT_INBOX_IDENTIFIER`, `CLOUDINARY_*` |
| `~/voraz/erp-service/.env` | `ERPNEXT_URL`, `ERPNEXT_API_KEY`, `ERPNEXT_API_SECRET` |
| `~/voraz/ia-service/.env` | Claves de modelos (Google, Groq, OpenRouter) |
| `~/chats/.env` | Chatwoot |

El `docker-compose.yml` los referencia como `${VAR}`. Los `.env` no se versionan.

**Desde Hermes**, el MCP `voraz_erpnext` usa las credenciales de ERPNext guardadas en
`~/.hermes/.env` de esta PC; las inyecta el lanzador `~/Documentos/voraz/bin/mcp-erpnext.sh`.

### Cambiar un `.env`
Requiere **recrear** el contenedor, no reiniciarlo:
```bash
ssh voraz 'cd ~/voraz && docker compose up -d --force-recreate <servicio>'
```
(`config.py` usa `load_dotenv()`, que no sobrescribe variables ya inyectadas al crear el
contenedor.)

---

## 6. Rotar la API key de ERPNext

⚠️ **Pitfall que tumbó la integración una vez**: `frappe.core.doctype.user.user.generate_keys()`
**devuelve** el secreto nuevo, pero **el ORM de Frappe no persiste los campos `read_only`**
(y `api_key`/`api_secret` lo son). Resultado: la API queda en **401 para todos**, incluida
la credencial vieja que se intenta restaurar.

**Método que sí funciona** (verificado en Frappe/ERPNext v16): escribir por primitivas
canónicas, **no** por el ORM.

1. Ejecutar python directo en el contenedor. **No usar `bench console`**: IPython corta los
   bloques multilínea pegados por heredoc y contamina stdout.
   ```bash
   ssh voraz 'docker exec frappe-backend-1 bash -lc "mkdir -p /home/frappe/frappe-bench/sites/vorazadmin.site/logs"'
   scp script.py voraz:/tmp/script.py
   ssh voraz 'docker cp /tmp/script.py frappe-backend-1:/tmp/script.py'
   ssh voraz 'docker exec -u root frappe-backend-1 chmod 644 /tmp/script.py'  # docker cp deja el archivo root-owned
   ssh voraz 'docker exec frappe-backend-1 bash -lc "cd /home/frappe/frappe-bench/sites && ../env/bin/python /tmp/script.py"'
   ```
   El `cd sites` y el `mkdir logs` son obligatorios: `frappe.init` falla sin ellos.

2. El script:
   ```python
   import frappe
   frappe.init(site="vorazadmin.site"); frappe.connect(); frappe.set_user("Administrator")
   from frappe.utils.password import set_encrypted_password
   frappe.db.set_value("User", "Administrator", "api_key", NUEVA_KEY, update_modified=False)
   set_encrypted_password("User", "Administrator", NUEVO_SECRET, "api_secret")
   frappe.db.commit()
   ```
   `api_secret` es fieldtype **Password**: vive encriptado en la tabla `__Auth`, no en
   `tabUser`. Se lee con `get_decrypted_password`.

3. **Verificar con `curl` antes de tocar los consumidores**, y hacer rollback con el mismo
   método si falla. Nunca rotar sin tener las credenciales anteriores a mano.

4. Actualizar `erp-service/.env` + `docker compose up -d --force-recreate erp_service`, y
   las de Hermes en `~/.hermes/.env` (trasladarlas por archivo, nunca por stdout; borrar
   los temporales con `shred`).

> Solo el usuario **Administrator** tiene API key: la integración corre con el usuario más
> privilegiado del ERP. Evaluar un usuario de integración dedicado (ver `backlog.md`).

---

## 7. Usuarios de integración en ERPNext

La integración **no usa `Administrator`**. Hay dos usuarios dedicados con permisos propios:

| Usuario | Rol | Para qué | Credencial |
|---|---|---|---|
| `vorazcde@gmail.com` ("integracion@") | `Voraz Integracion` | **Escritura**: lo usa `erp-service` | `ERPNEXT_API_KEY` / `ERPNEXT_API_SECRET` en `erp-service/.env` |
| `xjuanmax@hotmail.com` ("consulta@") | `Voraz Lectura` | **Solo lectura**: lo usa el MCP | `MCP_ERPNEXT_API_KEY` / `MCP_ERPNEXT_API_SECRET` en `erp-service/.env`, y en `~/.hermes/.env` |

Los roles se crearon con `Custom DocPerm` sobre 22 doctypes (ventas, inventario y contabilidad).

> ⚠️⚠️ **PITFALL CRÍTICO — `Custom DocPerm` PISA los permisos estándar de ese doctype.**
> Si un DocType tiene **alguna** fila en `tabCustom DocPerm`, Frappe usa esa tabla como **única**
> fuente de permisos para ese DocType e **ignora por completo** `tabDocPerm` — para **todos** los
> roles, no solo para el nuevo. Ver `frappe/permissions.py`:
> ```python
> doctypes_with_custom_perms = get_doctypes_with_custom_docperms()
> for p in perms:
>     if p.parent not in doctypes_with_custom_perms:   # la estándar solo
>         custom_perms.append(p)                       # cuenta si NO hay custom
> ```
> **Consecuencia real (pasó el 2026-10-08):** crear los dos roles sin copiar la matriz estándar
> dejó a **todos los demás usuarios sin acceso** a los 22 doctypes. Juanma (Sales Manager, System
> Manager) no podía entrar a ventas. `Administrator` no se ve afectado porque tiene bypass, así
> que el error es **invisible** desde esa cuenta.
>
> **Regla:** al personalizar permisos de un DocType hay que dejar la matriz **completa** (lo
> estándar **más** lo propio). Es lo mismo que hace la UI de Frappe al «personalizar» permisos.
> Usar `scripts/roles_erpnext.py`, que copia la estándar antes de agregar los roles.
>
> **Cómo repararlo** si ya pasó: `frappe.permissions.copy_perms(doctype)` copia la matriz estándar
> a la custom (es **aditivo**, no borra). O `frappe.permissions.reset_perms(doctype)`, que borra
> los `Custom DocPerm` del doctype y devuelve el control a la tabla estándar (pero entonces los
> roles propios pierden el acceso).

> ⚠️ **Pitfall**: el ORM de Frappe **no persiste** cambios en la tabla `Has Role` (igual que con
> `api_key`): hay que escribir en la DB directamente.

### El MCP del agente de WhatsApp es de solo lectura

`ia-service` levanta su **propia** instancia del MCP (no la de Hermes) para que el agente de
WhatsApp haga consultas libres al ERP. Está limitada a lectura en **tres capas**:

1. `get_tools_schema()` expone al LLM solo 5 herramientas (`get_doctypes`, `get_doctype_fields`,
   `get_documents`, `get_document`, `run_report`).
2. `call_tool()` rechaza cualquier otra, aunque el LLM la pida.
3. El MCP usa las credenciales `MCP_ERPNEXT_API_*` (usuario de consulta), así que el ERP también
   las rechazaría.

Verificado el 2026-10-08 contra el contenedor: el LLM recibe 5 herramientas, las 4 de escritura
probadas son rechazadas, y una de lectura devuelve datos reales.


### Agregar un permiso nuevo
**Usar `scripts/roles_erpnext.py`** (idempotente): define los roles y los doctypes arriba, y
agregar el nombre del doctype a la lista `DOCTYPES`. El script copia la matriz estándar y después
los roles propios, así que no hay riesgo de dejar sin permisos a los demás usuarios.

```bash
# respaldo de la tabla antes de tocarla (siempre)
docker exec frappe-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python -c "
import json,frappe; frappe.init(site=\"vorazadmin.site\"); frappe.connect()
json.dump(frappe.db.sql(\"select * from \\`tabCustom DocPerm\\`\", as_dict=True), open(\"/tmp/bk.json\",\"w\"), default=str)"'
docker cp frappe-backend-1:/tmp/bk.json ./

# ejecutar
docker cp scripts/roles_erpnext.py frappe-backend-1:/tmp/
docker exec -u root frappe-backend-1 chmod 644 /tmp/roles_erpnext.py
docker exec frappe-backend-1 bash -lc 'cd /home/frappe/frappe-bench/sites && ../env/bin/python /tmp/roles_erpnext.py'
```

La salida `VPZ_VERIF` confirma, por doctype, que `integracion@` lee y escribe, que `consulta@`
solo lee, y que un **usuario estándar** sigue leyendo (esto último es el chequeo que faltaba
hacer antes y por eso el problema pasó desapercibido).

### Verificado en producción
Los 4 flujos críticos pasan con `integracion@`: **crear pedido, cobrar, entregar y cancelar**
(probado el 2026-10-08). `consulta@` lee los 22 doctypes y **no puede escribir** (403).

## 8. Disco y backups

- El disco de la VM está **al ~85%** (≈4 GB libres de 29 GB). Antes de builds grandes
  (`docker compose build`), chequear `df -h /`. Si falta espacio:
  `docker image prune -f` (solo imágenes huérfanas; no toca volúmenes).
- **No correr `docker compose down`** en la raíz: baja los cuatro servicios de golpe.
- ERPNext (frappe_docker) es el mayor consumidor de disco: las imágenes base son grandes.

---

## 9. Páginas legales de Chatwoot

Meta exige tres URLs para publicar una app (**Go live**) y para App Review. Las servimos como
estáticos desde el propio Chatwoot, en `chat.vorazadmin.site`:

| Página | URL |
|---|---|
| Política de privacidad | `https://chat.vorazadmin.site/legal/privacidad.html` |
| Términos de servicio | `https://chat.vorazadmin.site/legal/terminos.html` |
| Eliminación de datos | `https://chat.vorazadmin.site/legal/eliminacion-de-datos.html` |

**Cómo están publicadas.** Los archivos viven en la VM en `~/chats/legal/` y se montan dentro
del contenedor en `/app/public/legal` (Chatwoot sirve `/app/public` como estáticos de Rails).
El montaje está declarado en `~/chats/docker-compose.yaml`, en el ancla `base`:

```yaml
    volumes:
      - storage_data:/app/storage
      - ./legal:/app/public/legal:ro
```

**Editar una página** (efecto inmediato, sin reinicio):

```bash
ssh voraz 'docker cp ~/chats/legal/. chats-rails-1:/app/public/legal/'
curl -s -o /dev/null -w "%{http_code}\n" https://chat.vorazadmin.site/legal/privacidad.html
```

⚠️ **Pitfall**: el montaje del compose **solo se aplica al recrear** el contenedor. Si se copian
los archivos con `docker cp` y un recreate posterior ocurre **sin** el volumen en el compose, los
archivos desaparecen y las tres URLs pasan a **404** — con la app ya publicada, eso puede hacer
que Meta la observe o la rechace. Antes de cualquier recreate de Chatwoot, confirmar que el
volumen sigue en el compose (`docker compose config | grep legal`).

**Contenido**: el contacto publicado es `xjuanma.romerox@gmail.com` y el WhatsApp
**0983 422 117**. Falta razón social/RUC si se quiere formalizar la página.

---

## 10. Canales de Meta (Facebook e Instagram) en Chatwoot

Dos apps de Meta, una por canal:

| App de Meta | IDs | Canal |
|---|---|---|
| **wootOct26** | App ID `1073626225286220` | Facebook — página *Voraz* (`108460077968811`) |
| **testearFoto** | App ID `2010013926374688` · Instagram app ID `1676307624126614` | Instagram — @vorazcde (`17841446280417992`) |

**Dónde viven las credenciales**: en el **super_admin de Chatwoot**
(`/super_admin/app_config?config=facebook` y `?config=instagram`), o sea en la tabla
`installation_configs`. Hay además `FB_*` en `~/chats/.env`, pero **el valor de la base de datos
gana sobre la variable de entorno** — el `.env` puede quedar con las claves vacías sin afectar
nada.

**Endpoints de webhook** (los que se configuran en Meta):

| Canal | Callback URL | Verify token en Chatwoot |
|---|---|---|
| Facebook | `https://chat.vorazadmin.site/bot` | `FB_VERIFY_TOKEN` |
| Instagram | `https://chat.vorazadmin.site/webhooks/instagram` | `INSTAGRAM_VERIFY_TOKEN` |

**Verificar sin tocar el panel** (el token de app es `{app-id}|{app-secret}`):

```bash
# desde la VM, con las credenciales en un archivo
curl -s --get "https://graph.facebook.com/v23.0/2010013926374688/subscriptions" \
  --data-urlencode "access_token=<APP_ID>|<APP_SECRET>"
```

El procedimiento completo, los pasos en el panel de Meta y los **pitfalls** (app borrada,
etiqueta `ACCOUNT_UPDATE` retirada, dónde va la redirect URI, dónde va el token de verificación,
modo Live) están en la skill **`chatwoot-meta-channels`**.
