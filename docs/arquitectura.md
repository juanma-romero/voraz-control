# Arquitectura del sistema Voraz

Visión de alto nivel: cómo está armado el sistema, cómo se conectan los componentes y
dónde corre cada cosa. El detalle de cada servicio está en `servicios.md`.

---

## 1. Visión general

Voraz opera como un ecosistema de **microservicios**, cada uno con una responsabilidad
clara, comunicados principalmente por **APIs REST**. El `backend` (Node.js) es el
**orquestador central**: recibe la mensajería, mantiene el estado de las conversaciones y
coordina a los demás servicios.

La regla de oro del diseño: **ERPNext es la fuente de verdad** para pedidos, clientes,
stock y contabilidad. Ningún servicio escribe en el ERP salvo a través de `erp-service`,
que concentra esa responsabilidad.

---

## 2. Componentes principales

### 2.1. backend (Node.js / Express)
- **Función**: orquestador principal y punto de entrada de la mensajería.
- **Responsabilidades**:
  - Recibir y procesar mensajes de clientes y administradores.
  - Persistir el historial de conversaciones en MongoDB.
  - Delegar análisis y procesamiento a los otros servicios.
  - Ejecutar los comandos administrativos (`/agendar`, `/cobrar`, `/hoy`, …).
  - Servir de puente hacia ERPNext (vía `erp-service`) y hacia WhatsApp (vía `dashWhat2`).

### 2.2. ia-service (Python / FastAPI)
- **Función**: capacidades de IA — análisis de conversaciones y agente consultable.
- **Responsabilidades**:
  - Extraer intenciones, entidades y resúmenes de los mensajes.
  - Auditar pedidos contra el historial del chat para detectar inconsistencias.
  - Ejecutar el **agente** (`/consultar`) con bucle ReAct y tools (nativas + MCP).

### 2.3. erp-service (Python / FastAPI)
- **Función**: capa de integración entre el backend y ERPNext.
- **Responsabilidades**:
  - Exponer una API REST controlada hacia ERPNext.
  - Traducir peticiones y ejecutar lógica de negocio (crear Sales Orders, generar
    Delivery Notes, validar y registrar cobros, resolver cancelaciones).
  - Aislar al resto del sistema de las restricciones nativas de ERPNext.

### 2.4. dashWhat2 (Node / Baileys)
- **Función**: recepción y envío de mensajes de WhatsApp.
- Reenvía los mensajes entrantes al backend y mantiene la sesión vinculada de WhatsApp.

### 2.5. ERPNext
- **Función**: ERP — gestión integral (inventario, ventas, clientes, contabilidad).
- Se interactúa con él **únicamente** a través de `erp-service` (o por consulta de lectura
  vía el MCP).

### 2.6. Chatwoot (integración futura)
- Centralización de la atención al cliente en múltiples canales (WhatsApp, Facebook,
  Instagram). El backend ya tiene el cableado; la implementación está pendiente.

---

## 3. Comunicación entre servicios

Todo por HTTP/REST, dentro de la red Docker compartida:

| Origen → Destino | Para qué |
|---|---|
| Backend → ia-service | Análisis de texto y consultas del agente |
| Backend → erp-service | Operar sobre ERPNext |
| Backend → MongoDB | Persistencia de mensajería (conexión directa) |
| Backend → dashWhat2 | Enviar mensajes de WhatsApp |
| ia-service → erpnext-mcp-server | Consultas libres al ERP (stdio, MCP) |
| ia-service → erp-service | Tools nativas de ventas |

---

## 4. Flujo de datos (ejemplo: mensaje de un cliente)

1. El cliente escribe por WhatsApp.
2. `dashWhat2` recibe el mensaje y lo reenvía al `backend`.
3. El backend lo guarda en MongoDB y lo pasa al procesador de mensajes.
4. El procesador decide: ¿es un comando, un pedido, o requiere análisis?
5. Si requiere análisis, el backend llama a `ia-service`.
6. Con el análisis, el backend o bien responde al cliente, o bien inicia un flujo de
   negocio (crear el pedido en ERPNext a través de `erp-service`).

---

## 5. Entornos

### Local (PC de desarrollo)
- Ruta: `/home/juanma/Documentos/voraz/` — **espeja la estructura de la VM**.
- Se levanta un **slice** del stack con Docker: `./dev.sh` (backend, erp_service,
  ia_service y un Mongo local). Ver `runbook.md`.
- **No se corre `dashwhat2` en local**: una segunda sesión de WhatsApp puede invalidar la
  de producción.

### Producción (GCP)
- VM `instance-voraz-main`, zona `us-central1-f`, IP `34.44.100.213`.
- `e2-standard-2`: 2 vCPU, 8 GB RAM, disco de arranque 29 GB (uso ~85%).
- Ubuntu 24.04 LTS, todo en Docker.
- Acceso: `ssh voraz` (usuario `xjuanma_romerox`).
- Servicios: los cuatro propios + ERPNext (frappe_docker) + Chatwoot.

---

## 6. Estrategia de documentación

Este documento se mantiene a nivel **estratégico y estable**. El detalle técnico y
operativo vive donde corresponde:

- **Por servicio** → el `README.md` dentro del repo de cada servicio.
- **Operación** → `runbook.md`.
- **Decisiones y su porqué** → `decision-log.md`.
- **Qué falta / qué sigue** → `backlog.md`.
