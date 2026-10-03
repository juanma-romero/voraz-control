# Objetivos del Proyecto Voraz

## Objetivo Central
Construir un sistema de gestión integral de un comercio de bocaditos y empanadas, operado principalmente desde WhatsApp, con automatización progresiva mediante IA y ERPNext como fuente de verdad para operaciones contables e inventario.

---

## Objetivos Estratégicos

### 1. Automatización de Pedidos ✅ Implementado
- Los clientes pueden pedir por WhatsApp y el sistema interpreta sus mensajes con IA.
- Los administradores pueden crear pedidos manualmente con `/agendar`.
- Los pedidos se registran automáticamente como Sales Orders en ERPNext.

### 2. Gestión Operativa desde WhatsApp ✅ Implementado
- Comandos para ver pedidos del día (`/hoy`, `/manana`, `/listado`).
- Comandos para marcar pedidos como entregados (`/hecho`) o cancelados (`/cancelado`).
- Reactivación de pedidos cancelados (`/reactivar`).

### 3. Asistente IA por Consulta (Agente) ✅ Fase 1 Implementada
- Administrador puede consultar datos del negocio en lenguaje natural desde WhatsApp.
- El agente interpreta la consulta, busca los datos y formula una respuesta clara.
- Ver sección de progreso para detalle de fases.

### 4. Gestión de Cobros y Pagos 🔄 Pendiente (Fase 2 del Agente)
- Consultar cobros recibidos de clientes por período.
- Consultar pagos realizados a proveedores.
- Ver pedidos con pagos pendientes.

### 5. Control de Stock e Inventario 🔄 Pendiente (Fase 2 del Agente)
- Consultar stock actual por producto desde WhatsApp.
- Registrar ingresos de stock (compras a proveedores).
- Alertas de stock bajo.

### 6. Análisis de Conversaciones con Clientes 🔄 Pendiente (Fase 3 del Agente)
- Consultar historial de mensajes con clientes específicos.
- Ver mensajes pendientes de contestar.
- Resumen del estado de una conversación.

