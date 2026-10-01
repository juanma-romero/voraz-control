# Documentación Técnica del Backend (Orquestador WhatsApp)

## Descripción General

El **backend** es el orquestador central del sistema Voraz. Recibe todos los mensajes entrantes de WhatsApp a través del servidor Baileys (`dashwhat2`), los clasifica según su origen (cliente o administrador), y coordina las acciones correspondientes: análisis de IA, gestión de pedidos en ERPNext, y respuestas automáticas.

---

## Arquitectura del Sistema

### Componentes Principales

#### 1. Servidor Principal (`index.js`)

- **Framework**: Express.js
- **Puerto**: Configurable, por defecto `3000`.
- **Inicialización**: Conecta a MongoDB e inyecta las dependencias (colección y cliente) en los servicios mediante setters (`setCollection`, `setDbClient`). MongoDB actualmente se usa **solo** para el historial de conversaciones (`chatsV2`). Los pedidos viven en ERPNext.

---

#### 2. Rutas (`routes/messages.routes.js`)

Expone el endpoint principal que recibe todos los mensajes de Baileys:

**`POST /api/messages`**

El router distingue dos tipos de origen:

| Origen | Condición | Acción |
|--------|-----------|--------|
| **Admin (chat propio)** | `remoteJid` está en `admin-phones.json` y texto empieza con `/` | Ejecutar comando con `command.handler.js` y devolver `{ reply, targetJid }` a Baileys |
| **Admin (chat de cliente)** | `fromMe: true` y texto empieza con frase clave | Disparar flujo de pedido (crear / modificar) |
| **Cliente** | Cualquier otro `remoteJid` | Guardar en MongoDB y procesar con `message.processor.js` |

> **Importante:** La distinción entre *"chat del admin consigo mismo"* y *"admin hablando dentro de un chat de cliente"* es fundamental. Los comandos `/` solo se procesan en el primer caso. Las frases de agendamiento solo se detectan en el segundo.

---

#### 3. Servicio de MongoDB (`services/mongo.service.js`)

Actualmente usado **exclusivamente para mensajería**. Las funciones de pedidos están marcadas como obsoletas.

**Funciones activas:**
- `saveMessage()` — Guarda mensajes en `chatsV2` por contacto (`remoteJid`).
- `getRecentMessages()` — Obtiene los últimos N mensajes de una conversación.
- `updateChatAnalysis()` — Actualiza el estado semántico de la conversación (ej: `'Pedido Creado'`).
- `getChatByJid()` — Obtiene el nombre de un contacto por su JID.

**Funciones obsoletas (legacy):**
- ~~`saveOrderToDb()`~~ — Los pedidos ahora se crean directo en ERPNext vía `erp-service`.
- ~~`getAllOrders()`~~ — Reemplazado por consultas al `erp-service`.
- ~~`getNextOrderNumber()`~~ — La nomenclatura la genera ERPNext (`SALES-ORD-XXX`).
- ~~`updateOrderStatusByNumber()`~~ — Reemplazado por integraciones nativas con ERPNext.

---

#### 4. Procesador de Mensajes (`services/message.processor.js`)

Coordina el procesamiento de mensajes de clientes. Delega a los manejadores de eventos en orden de prioridad:

1. **`handleOrderTrigger`** — Verifica si el mensaje activa un flujo de pedido. Si lo hace, lo procesa y no continúa.
2. **`handleConversationAnalysis`** — Si no fue un pedido, inicia el temporizador de análisis de IA (60 segundos de "tiempo de calma").

---

#### 5. Manejadores de Eventos (`services/message_events/`)

- **`order.handler.js`**: Detecta frases clave enviadas por el admin dentro de chats de clientes:
  - `"Entonces te agendo:"` → dispara `triggerOrderAnalysis(contactJid, texto, 'create')`
  - `"Modifico tu pedido:"` → dispara `triggerOrderAnalysis(contactJid, texto, 'replace')`
- **`analysis.handler.js`**: Gestiona el temporizador diferido de análisis de conversación. Reinicia el reloj ante cada mensaje nuevo del mismo contacto.

---

#### 6. Servicio de Análisis (`services/analysis.service.js`)

- Obtiene el historial reciente de la conversación para contextualizar a la IA.
- Detecta automáticamente si la conversación requiere actualización de estado o ya derivó en un pedido.

---

#### 7. Servicio de Pedidos (`services/order.service.js`)

Orquesta la creación, modificación y notificación de pedidos.

**Funciones principales:**

- **`triggerOrderAnalysis(jid, texto, action)`** — Construye el prompt con fecha/hora local para la IA y según el `action` invoca `createOrder` o `replaceOrder`.
- **`createOrder(orderData)`** — Envía el pedido al `erp-service` (`POST /api/orders`). Ante éxito, actualiza el estado de la conversación en Mongo y **envía notificación al admin por WhatsApp**.
- **`replaceOrder(orderData)`** — Envía la solicitud de reemplazo al `erp-service` (`POST /api/orders/replace_latest`). Internamente, el microservicio cancela el último pedido activo del cliente y crea el nuevo. También **notifica al admin**.
- **`notifyAdmin(message)`** — Función interna que llama al endpoint `POST /send-message` de Baileys (`dashwhat2`) para enviar un mensaje proactivo al número admin configurado.

**Zona horaria**: Usa `Etc/GMT+3` (UTC-3 fijo) para evitar variaciones estacionales al construir el prompt de fecha/hora.

---

#### 8. Servicio de IA (`services/ia.service.js`)

- Interfaz HTTP para comunicación con el microservicio `ia-service` (FastAPI + Groq/Gemini).
- Configurable mediante `IA_SERVICE_URL`.
- Llama a endpoints específicos como `/analyze-order` o `/analyze-conversation`.

---

#### 9. Servicio ERP (`erp-service`)

Microservicio externo en Python (FastAPI) ubicado en `/erp-service/` en la raíz del proyecto. Ver su propia documentación para detalles internos.

- **Orquestador de Pedidos ERPNext**: Crea `Sales Orders`, genera `Delivery Notes` (para `/hecho`), busca y cancela órdenes activas (para `/cancelado` y `Modifico tu pedido:`).
- Configurable mediante `ERP_SERVICE_URL` (por defecto `http://localhost:8001`).

---

#### 10. Manejador de Comandos (`services/command.handler.js`)

Sistema de **carga dinámica de comandos por directorio**. Al iniciar, recorre `services/commands/` buscando subcarpetas y registra automáticamente cada `.js` como un comando. No requiere edición manual al añadir comandos nuevos.

**Estructura de directorios de comandos:**

```
services/commands/
├── pedidos/          ← Activo
│   ├── listar.js
│   ├── agendar.js
│   ├── hoy.js
│   ├── manana.js
│   ├── hecho.js
│   ├── cancelar.js
├── egresos/          ← Planificado (vacío)
├── informes/         ← Activo
│   ├── consultar.js    
├── ingresos/         ← Activo
│   ├── cobrar.js
└── inventario/       ← Planificado (vacío)
```

**Comandos activos (`pedidos/`):**

| Comando | Descripción |
|---------|-------------|
| `/agendar <número> <detalle>` | Genera un pedido en ERPNext directo desde el chat admin. Formatea automáticamente el número copiado (ej: `+595 971 166266`). Alias: `/pedido`, `/crear`. |
| `/listar` | Lista todos los pedidos activos consultando ERPNext. |
| `/hoy` | Pedidos con entrega para la fecha actual (filtra por `delivery_date` en ERP). |
| `/manana` | Pedidos con entrega para el día siguiente. |
| `/entregado <ID_ERP>` | Marca un pedido como entregado generando un Delivery Note en ERPNext. |
| `/cancelar <ID_ERP>` | Cancela un pedido (`docstatus=2`). Reporta si hay bloqueos contables. |

---

#### 11. Tareas Programadas (`services/agenda.service.js`)

Utiliza la librería **Agenda** (sobre MongoDB) para ejecutar trabajos (`jobs`) tanto diferidos como con horarios fijos (cron).
- **Funciones activas:** 
  - `notificar pendientes`: Se ejecuta periódicamente (ej. 6:00, 8:00, 10:00, etc.) buscando en la DB chats que requieren atención en las últimas 48hs y notifica al admin con un resumen.

---

#### 12. Servicio de Notificaciones (`services/notification.service.js`)

Módulo dedicado para enviar mensajes proactivos desde el sistema hacia los usuarios (principalmente al admin).
- **Funciones principales:**
  - `notifyAdmin(message)`: Llama al endpoint de Baileys para alertar al administrador por WhatsApp (ej. confirmación de pedidos, alerta de mensajes sin responder).

---

## Flujos de Trabajo

### Flujo 1: Mensaje de Cliente

```
Cliente → Baileys → POST /api/messages
  ├── Guardar en MongoDB (chatsV2)
  ├── syncCustomerWithERP() [asíncrono] → erp-service POST /api/customers/sync
  └── processMessage()
        ├── [60s timer] handleConversationAnalysis → ia-service /analyze-conversation
        └── [si admin escribe frase clave] handleOrderTrigger
```

### Flujo 2: Agendamiento de Pedido ("Entonces te agendo:")

```
Admin escribe en chat de cliente → Baileys → POST /api/messages
  └── handleOrderTrigger detecta la frase
  └── triggerOrderAnalysis(jid, texto, 'create')
        └── recupera últimos 15 mensajes del chat para contexto
        └── ia-service /analyze-order → extrae JSON del pedido y audita contra el historial
        └── ¿Existe discrepancia?
              ├── SÍ: Detiene flujo → notifyAdmin() alerta al admin por WhatsApp
              └── NO: createOrder() → erp-service POST /api/orders → ERPNext crea Sales Order
                    └── updateChatAnalysis() → MongoDB actualiza estado conversación
                    └── notifyAdmin() → Baileys POST /send-message → Admin recibe confirmación WA
```

### Flujo 3: Agendamiento Directo de Admin (`/agendar`)

```
Admin escribe `/agendar +595 972 860099 1 combo...` → Baileys → POST /api/messages
  └── handleAdminCommand('agendar')
  └── el comando extrae, limpia el número y forma el JID
  └── triggerOrderAnalysis(jid, texto, 'create')
        └── ia-service /analyze-order → extrae JSON del pedido (manteniendo decimales con punto)
        └── createOrder() → erp-service POST /api/orders → ERPNext crea Sales Order
        └── notifyAdmin() → Admin recibe confirmación WA
```

### Flujo 4: Modificación de Pedido ("Modifico tu pedido:")

```
Admin escribe en chat de cliente → Baileys → POST /api/messages
  └── handleOrderTrigger detecta la frase
  └── triggerOrderAnalysis(jid, texto, 'replace')
        └── ia-service /analyze-order → extrae JSON del nuevo pedido
        └── replaceOrder() → erp-service POST /api/orders/replace_latest
              ├── Cancela último pedido activo del cliente en ERPNext
              └── Crea nuevo Sales Order
        └── updateChatAnalysis() → MongoDB actualiza estado
        └── notifyAdmin() → Admin recibe confirmación con orden vieja y nueva
```

### Flujo 5: Comando de Admin

```
Admin escribe /hoy → Baileys → POST /api/messages
  └── handleAdminCommand('hoy')
  └── commands['hoy'].execute([])
  └── return { reply: "...", targetJid: adminJid }
  └── Baileys recibe reply y llama a sock.sendMessage()
```

---

## Herramientas de Prueba

### Simuladores de Pruebas (Mensajes y Admin)

El proyecto incluye simuladores HTML para probar la lógica (mensajes de clientes y comandos de administrador) sin enviar mensajes reales por WhatsApp.

- **Ubicaciones**: `tests/message_simulator.html` y `tests/admin_simulator.html`
- **Uso Rápido (Recomendado)**:
  1. Desde la carpeta raíz del proyecto (`voraz-main`), ejecutar: `./start_services.sh`
  2. Este script inicia automáticamente la API, la IA, el ERP y el servidor de tests.
  3. Abrir el simulador de mensajes: `http://localhost:5000/message_simulator.html`
  4. Abrir el simulador de administrador: `http://localhost:5000/admin_simulator.html`
  5. Para detener todos los servicios, presionar `Ctrl + C` en esa terminal.

- **Uso Manual (Solo servidor de tests)**:
  1. Dentro de la carpeta `backend`, ejecutar: `npx serve -l 5000 tests`
  2. Abrir las URLs indicadas arriba.

---

## Estructura de Datos

### MongoDB: Colección `chatsV2`

```javascript
{
  _id: ObjectId,
  contactJid: string,           // JID único del contacto (ej: 595981234567@s.whatsapp.net)
  contactName: string,          // Nombre del contacto (si disponible)
  messages: [Message],          // Historial de mensajes
  stateConversation: string,    // Estado semántico (ej: 'Pedido Creado', 'Pedido Modificado')
  contextualSummary: string,    // Resumen generado por la IA
  createdAt: Date,
  updatedAt: Date
}
```

> **Nota**: La colección `pedidos` de MongoDB está en desuso. Los pedidos se gestionan como `Sales Orders` nativos en ERPNext.

---

## Variables de Entorno

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `MONGODB_URI` | Cadena de conexión a MongoDB Atlas | — |
| `PORT` | Puerto del servidor Express | `3000` |
| `IA_SERVICE_URL` | URL del microservicio de IA | `http://localhost:8000` |
| `ERP_SERVICE_URL` | URL del microservicio ERP | `http://localhost:8001` |
| `DASHWHAT_URL` | URL del servidor Baileys (para notificaciones proactivas) | `http://localhost:8880` |
| `ADMIN_NOTIFY_JID` | JID de WhatsApp del admin a notificar tras crear/modificar pedidos | — |

---

## Consideraciones de Escalabilidad

- Los temporizadores de "tiempo de calma" se gestionan en memoria (`Map`). En un entorno con múltiples instancias (Load Balancer), se recomienda migrar a **Redis**.
- Las notificaciones al admin (`notifyAdmin`) fallan silenciosamente para no bloquear el flujo de creación de pedidos.

---

## Posibles Mejoras

1. Implementar autenticación para proteger el endpoint `/api/messages`.
2. Migrar los temporizadores de análisis a Redis para escalabilidad horizontal.
3. Implementar validaciones de esquema con **Joi** o **Zod** para los payloads recibidos de la IA.
4. Eliminar formalmente el comando `/reactivar` y las funciones obsoletas de `mongo.service.js` una vez confirmado que no hay dependencias activas.
5. Poblar las categorías de comandos planificadas: `egresos/`, `informes/`, `ingresos/`, `inventario/`.