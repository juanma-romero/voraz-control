# Servicios del Sistema Voraz

Este documento describe los servicios individuales que componen el sistema Voraz, destacando su función principal, tecnologías clave y responsabilidades a un nivel estratégico.

## 1. Backend (Orquestador y Mensajería)

- **Descripción**: El corazón del sistema, responsable de orquestar las interacciones entre los demás servicios y de gestionar la comunicación con los clientes y administradores.
- **Tecnologías Clave**: Node.js, Express, MongoDB (para persistencia de mensajes), Axios (para comunicación HTTP), Agenda (para tareas programadas).
- **Funciones Principales**:
    - **Recepción y Procesamiento de Mensajes**: Actúa como el punto de entrada para todos los mensajes entrantes (clientes y administradores).
    - **Gestión de Conversaciones**: Almacena el historial de chat y delega el procesamiento a módulos especializados (ej. `Message Processor`).
    - **Orquestación de Servicios**: Invoca al `IA Service`, `erp-service` y `Efactura` según la lógica de negocio.
    - **Manejo de Comandos Administrativos**: Procesa comandos específicos enviados por administradores.
    - **Tareas Programadas (Cron/Jobs)**: Utiliza `Agenda` para disparar acciones periódicas como el resumen de mensajes sin contestar.

## 2. IA Service (Asistente de Inteligencia Artificial)

- **Descripción**: Un servicio dedicado a proporcionar capacidades de IA para entender y responder a las interacciones de los usuarios.
- **Tecnologías Clave**: Python, FastAPI, Proveedores IA: Groq, Google AI Studio.
- **Funciones Principales**:
    - **Análisis de Conversaciones**: Extrae intenciones, entidades y resúmenes de los mensajes de los clientes.
    - **Auditoría de Pedidos**: Valida las notas de los administradores contra el historial del chat para prevenir errores en la carga antes de enviarlos al ERP.
    - **Asistencia Inteligente**: Ayuda a automatizar respuestas y a identificar necesidades específicas del cliente para generar flujos de negocio.
- **Comunicación**: Expone una API REST para ser consumida por el Backend.

## 3. ERPNext (ERP)

- **Descripción**: El sistema de planificación de recursos empresariales que gestiona las operaciones internas del negocio (inventario, ventas, contabilidad, etc.).
- **Tecnologías Clave**: ERPNext.
- **Funciones Principales**:
    - Gestión integral de recursos empresariales.
    - Base de datos centralizada e indiscutible para los pedidos en curso (Sales Orders).
- **Comunicación**: Se interactúa con él delegando toda acción al intermediario `erp-service`.
- **Documentación Detallada**: Los detalles específicos de configuración de ERPNext se encuentran en la documentación base.

## 4. erp-service (Capa de Integración ERPNext)

- **Descripción**: Una capa de abstracción vital que permite al Backend interactuar con la instancia de ERPNext sin chocar contra las estricciones nativas.
- **Tecnologías Clave**: Python, FastAPI.
- **Funciones Principales**:
    - **Gestión Unificada de Clientes (JID-first):** Utiliza el WhatsApp JID como identificador de documento único (`name`) para evitar fusiones erróneas o duplicaciones de clientes en ERPNext. 
    - **Sincronización Automática e Identidad Progresiva:** Soporta la actualización asíncrona de nombres de clientes (PushNames) y creación dinámica sin bloquear flujos críticos.
    - **Resolución de Cobros por JID/Móvil:** Busca y asocia pagos (Payment Entries) de forma infalible resolviendo el JID o número de teléfono del cliente a su último pedido activo.
    - **Centralización de Órdenes (Sales Orders):** Creación y listado de pedidos en ERPNext.
    - **Manejo Contable Avanzado:** Generar `Delivery Notes` para pedidos finalizados, gestionar cancelaciones y revertir estados (`docstatus: 2`) capturando errores específicos.
- **Comunicación**: Expone una API REST (FastAPI) consumida por el Backend (Node.js) de forma síncrona y asíncrona.

## 5. Agente
- **Descripción**: Sistema de agentes de IA basado en *Function Calling* (Groq). Permite al administrador realizar consultas en lenguaje natural desde WhatsApp. El agente interpreta la consulta, selecciona la "tool" adecuada, la ejecuta y formula una respuesta en lenguaje natural formateada para WhatsApp.
- **Comando de activación**: `/consultar [texto libre]` (aliases: `/informe`, `/reporte`, `/info`)
- **Modelo**: `llama-3.3-70b-versatile` (Groq plan pago) · Fallback: `gemini-2.5-flash-lite`
- **Arquitectura**:
    - El Backend detecta el comando y llama a `ia-service POST /agent-query`.
    - El `ia-service` ejecuta el loop de Function Calling: 1ª llamada al LLM (elige tool) → Python ejecuta la función real → 2ª llamada al LLM (formula respuesta).
    - El LLM **nunca ejecuta código ni queries directamente**. Solo elige el nombre de la función y los parámetros dentro de los rangos definidos en `agent_tools.py`.
- **Archivos clave**:
    - `ia-service/routers/agent.py` — Endpoint `/agent-query` y loop de function calling.
    - `ia-service/services/agent_tools.py` — Definición de tools (schema para el LLM) + funciones Python reales.
    - `backend/services/commands/informes/consultar.js` — Comando del agente en el backend.
    - `erp-service/routers/reports.py` — Endpoints `GET /api/sales/summary` y `GET /api/sales/by-product` (usados por las tools del agente).

### Tools implementadas (Fase 1 — ✅ Funcionando)

| Tool | Descripción | Fuente |
|------|-------------|--------|
| `get_sales_summary` | Total de ventas en ₲ y cantidad de pedidos por período | ERPNext vía erp-service |
| `get_sales_by_product` | Ventas desagregadas por producto, ordenadas por cantidad | ERPNext vía erp-service |
| `get_pending_orders` | Lista de pedidos pendientes de entrega | ERPNext vía erp-service |

### Períodos soportados por las tools de ventas
`hoy` · `semana` · `mes` · `mes_pasado` · `anio`

### Fases pendientes del agente

#### Fase 2 — Stock y Finanzas (pendiente)
Nuevas tools a implementar en `agent_tools.py` + endpoints en `erp-service`:
- `get_stock_balance` → `GET /api/stock/balance` en erp-service
- `get_payment_entries` → `GET /api/payments/summary` (cobros recibidos)
- `get_pending_payments` → `GET /api/payments/pending` (cobros pendientes)
- `get_supplier_expenses` → `GET /api/expenses/summary` (pagos a proveedores)

#### Fase 3 — Consultas a MongoDB / Mensajes (pendiente)
Conexión directa de `ia-service` a MongoDB para consultas de conversaciones:
- `get_client_messages(client_name, limit, only_pending?)` — últimos N mensajes de un cliente
- `get_pending_messages(limit)` — mensajes sin contestar
- Requiere agregar `MONGO_URI` al `.env` del `ia-service` y crear `ia-service/services/mongo_tools.py`.

#### Fase 4 — Multi-tool / Razonamiento cruzado (pendiente)
Consultas que requieren combinar varias tools en un solo ciclo de razonamiento.
Ejemplo: *"¿Cuánto me debe el cliente que más compró este mes?"* → `get_top_customers` + `get_pending_payments`.
