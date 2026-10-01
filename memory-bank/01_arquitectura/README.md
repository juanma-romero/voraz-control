# Arquitectura General del Sistema Voraz

Este documento describe la arquitectura de alto nivel del sistema "Voraz", un conjunto de servicios interconectados para la gestión de mensajería, asistencia de IA, operaciones de erpNext y facturación electrónica. El objetivo es proporcionar una visión estratégica de cómo los componentes interactúan para lograr los objetivos del negocio.

## 1. Visión General de la Arquitectura

El sistema Voraz opera como un ecosistema de microservicios, donde cada componente tiene una responsabilidad clara y se comunica con otros servicios a través de interfaces bien definidas, principalmente APIs REST. El `backend` de Node.js actúa como el orquestador central, gestionando el flujo de información y coordinando las interacciones entre los demás servicios.

## 2. Componentes Principales

### 2.1. Backend (Node.js/Express)
- **Función**: Orquestador principal y punto de entrada para la mensajería.
- **Tecnología**: Node.js con Express.
- **Responsabilidades**:
    - Recibir y procesar mensajes de clientes y administradores.
    - Almacenar el historial de conversaciones en MongoDB.
    - Delegar tareas de análisis y procesamiento a otros servicios (ej. IA Service).
    - Manejar comandos administrativos.
    - Servir como puente de comunicación con erpNext y Efactura.

### 2.2. IA Service (Python/FastAPI)
- **Función**: Proporcionar capacidades de inteligencia artificial para el análisis de conversaciones y la asistencia.
- **Tecnología**: Python con FastAPI, utilizando Google Gemini.
- **Responsabilidades**:
    - Analizar el contenido de los mensajes para extraer intenciones, entidades o resúmenes.
    - Asistir en la automatización de respuestas o la identificación de necesidades del cliente.
- **Comunicación**: Se expone como una API REST consumida por el Backend.

### 2.3. ERPNext (ERP)
- **Función**: Sistema de planificación de recursos empresariales (ERP) para la gestión de operaciones comerciales.
- **Tecnología**: Instancia de ERPNext.
- **Responsabilidades**:
    - Gestión de inventario, ventas, clientes, contabilidad, etc.
- **Comunicación**: Se interactúa con él a través del microservicio interno `erp-service`.

### 2.4. erp-service (Microservicio de Integración)
- **Función**: Capa de integración entre el Backend (Node) y la instancia de ERPNext.
- **Tecnología**: Python con FastAPI.
- **Responsabilidades**:
    - Exponer una API REST para que el Backend pueda interactuar con ERPNext de manera controlada y segura.
    - Traducir peticiones y ejecutar lógicas complejas de negocio (ej. creación de Remitos para pedidos listos, o validación de pagos al cancelar órdenes).
- **Comunicación**: Se expone como una API REST consumida por el Backend, puenteando nativamente hacia ERPNext 

La comunicación entre los servicios se realiza principalmente a través de **APIs RESTful**. El `Backend` actúa como el centro de orquestación, invocando a los servicios de IA, `erp-service` y Efactura según sea necesario.

- **Backend <--> IA Service**: Llamadas HTTP/REST para análisis de texto y procesamiento de lenguaje natural.
- **Backend <--> erp-service**: Llamadas HTTP/REST para interactuar con los datos y orquestar flujos de ERPNext.
- **Backend <--> MongoDB**: Conexión directa para persistencia de datos de mensajería.

## 4. Flujo General de Datos (Ejemplo: Mensaje de Cliente)

1. Un cliente envía un mensaje (ej. vía WhatsApp).
2. El `Backend` recibe el mensaje a través de un endpoint, lo guarda en MongoDB y lo pasa al `Message Processor`.
3. El `Message Processor` decide si el mensaje es un comando, un intento de pedido o requiere análisis de conversación.
4. Si requiere análisis, el `Backend` llama al `IA Service` para procesar el mensaje.
5. El `IA Service` devuelve un análisis (ej. intención de compra, resumen).
6. El `Backend` utiliza este análisis para generar una respuesta al cliente, o para iniciar un flujo de negocio (ej. crear un pedido en ERPNext a través de `erp-service`, o generar una factura a través de `Efactura`).

## 5. Infraestructura y Despliegue (Producción)

Si bien el desarrollo general se orquesta en un ambiente local interactivo, el sistema productivo de Voraz está alojado en la nube usando una máquina virtual dedicada en Google Cloud Platform (GCP).

- **Proveedor**: Google Cloud Platform (Compute Engine)
- **Tipo de máquina**: `e2-standard-2`
- **CPU**: 2 vCPUs
- **Memoria RAM**: 8 GB
- **Disco de arranque**: `ubuntu-minimal-2404-noble-amd64`
- **Sistema Operativo**: Ubuntu 24.04.3 LTS (Noble Numbat)

## 6. Estrategia de Documentación por Servicio

Para mantener este memory bank a un nivel estratégico, los detalles técnicos y operativos específicos de cada servicio (ej. el pipeline de SIFEN en Efactura, los modelos de IA, la configuración de erpNext) se documentarán en sus respectivos memory banks o en la sección `02_servicios/` de este memory bank principal, con enlaces cruzados para facilitar la navegación.
