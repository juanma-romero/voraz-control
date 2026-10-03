# Asistente de Desarrollo - Proyecto Voraz

*   **Meta Principal:** Administrar el negocio 'Voraz', un comercio de venta de bocaditos (finger-food), mediante un conjunto de aplicaciones y servicios integrados. Este entorno es el ambiente de PRODUCCION del sistema de gestion de la empresa.
*   **Funcionalidades Clave:**
    *   Recepción y procesamiento de pedidos realizados a través de WhatsApp.
    *   Análisis de conversaciones y captura de pedidos mediante un servicio de IA 
    *   Centralización de la comunicación con clientes desde múltiples canales (WhatsApp, Facebook, Instagram) a través de Chatwoot.
    *   Integración con el ERP Erpnext para la gestión empresarial.
*   **Público Objetivo:** Personal administrativo y de gestión de 'Voraz'.

## . Stack Tecnológico (directorios)

*   **dashWhat2:** Libreria Baileys para recibir mensajes de Whatsapp
*   **backend:** Servidor Node.js.  Este servicio actúa como el orquestador principal.
*   **ia-service:** Servidor fastapi para conectar a IA externa.
*   **chat** Chatwoot (todavia no implementado).
*   **erp-service:** Servidor fastapi . Coneccion a ErpNext.
*   **frappe_docker:** sistema de gestion frappe/erpNext, version 16
*   **Base de datos:** Seervicio externo de Mongodb (Atlas) para guardar mensajes de clientes
*   **Infraestructura:** VM de GCP, os y maquina: Ubuntu 24.04 LTS e2-standard-2 (8GB RAM), Docker.
*   **Librerías/Frameworks Clave:** Baileys, Frappe, Node/Express, Fast Api, MongoDB.
---

## Directrices de Contexto Obligatorias (¡Léeme Primero!)

Antes de sugerir cualquier cambio, analizar logs o escribir código, debes seguir estrictamente estos pasos de inicialización de contexto:

1. **Consulta el Memory Bank:** Lee siempre el RESUMEN del archivo README.md en la carpeta `/memory-bank/02-servicios` en la raíz del proyecto.
   - En el directorio `/backend` tienes un backend-README.md con el detalle del servicio backend orquestador que es el mas complejo y mas usado

2. **Entorno Actual:**
    - **Local:** cada servicio se corre por separado (pendiente!: poder correr todos los servicios del mismo modo que en produccion, usando Docker)

---

## 🛠️ Arquitectura del Sistema y Directorios

El sistema está compuesto por microservicios interconectados a través de Docker (archivo docker-compose.yml en la raiz del proyecto):

* 🟢 **Backend Orquestador (Node.js/Express):** Ubicado en `/backend/backend/`. Gestiona la mensajería de WhatsApp mediante Baileys (`dashwhat2`) y procesa comandos dinámicos (`/listar`, `/cobrar`, `/pagar`, etc.).
* 🐍 **Capa de Integración ERP (Python/FastAPI):** Ubicado en `/erp-service/`. Es la API intermediaria que interactúa de manera segura con ERPNext.
* 🤖 **Servicio de IA (Python/FastAPI):** Ubicado en `/ia-service/`. Realiza auditorías de pedidos y análisis de lenguaje natural.

---

## ⚠️ Reglas Críticas e Incompatibilidades Conocidas

### 📊 Mapeo Contable de ERPNext (Local vs Producción)
ERPNext tiene diferencias cruciales en los nombres de las cuentas del catálogo contable entre el entorno local y el de producción. **Siempre** debes respetar estas equivalencias:

| Recurso / Cuenta | Local (Código Legacy) | Producción Real (`vorazadmin.site`) |
| :--- | :--- | :--- |
| **Mode of Payment: Efectivo** | `"Efectivo"` | **`"Cash"`** |
| **Mode of Payment: Transferencia** | `"Transferencia bancaria"` | **`"Wire Transfer"`** |
| **Cuenta: Caja** | `"1110 - Efectivo - Vz"` | **`"Efectivo - Vz"`** |
| **Cuenta: Banco Ueno** | `"1212 - Ueno - Vz"` | **`"1212 - Ueno - Vz"`** |
| **Cuenta: Gastos Varios** | `"5221 - Gastos varios - Vz"` | **`"Gastos varios - Vz"`** |
| **Cuenta: Ajuste Inventario** | `"1414 - Ajuste de inventario - Vz"` | **`"1414 - Ajuste de inventario - Vz"`** |

> [!WARNING]
> Cualquier discrepancia en estos nombres al registrar un `Payment Entry` o un `Journal Entry` provocará un error de validación `417 Client Error: EXPECTATION FAILED` en la API de ERPNext.

---

## Estilo de Trabajo y Comunicación

* **Enfoque Investigativo:** Si el usuario te pide investigar un error o analizar logs en producción, **limítate a diagnosticar e indicar las tareas a realizar localmente**. No toques el código del servidor.
* **Manejo de Respuestas:** Mantén tus respuestas concisas, profesionales y directamente enfocadas en la solución técnica.
* **Propuestas de Código:** Cuando propongas cambios de código, hazlo en formato de diffs claros indicando la ruta exacta del archivo a modificar.
