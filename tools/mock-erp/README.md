# mock-erp — `erp-service` simulado para desarrollo local

Reemplaza al microservicio `erp-service` real cuando **no querés conectar a
ERPNext** (en local no hay ERP). Implementa la misma superficie HTTP que consume
el backend, con estado en memoria.

## Por qué

En local, `erp-service` real arranca pero todas sus llamadas a ERPNext fallan
(`ERPNEXT_URL` vacío y sin API key), así que los comandos de pedidos
(`/listar`, `/hoy`, `/hecho`, `/cobrar`, …) devuelven error. Este mock los hace
funcionar y permite probar el flujo del backend de punta a punta sin tocar ERP.

## Cómo se activa

Ya está enganchado en `docker-compose.local.yml`, que **pisa el servicio
`erp_service`** de la config base para correr este mock. Se levanta con el stack
local normal:

```bash
cd /home/juanma/Documentos/voraz
./dev.sh                 # levanta backend + erp_service(mock) + ia_service + mongo
./dev.sh logs -f erp_service
```

El backend y `ia-service` siguen apuntando a `http://erp_service:8001`: el mock
ocupa el mismo nombre de servicio y puerto, así que no hay que cambiar URLs.

Para volver al `erp-service` real, quitá el override de `erp_service` en
`docker-compose.local.yml` (dejá solo `container_name` + `ports`).

## Endpoints

Idénticos a `erp-service/routers/*.py`:

| Método | Ruta | Devuelve |
|---|---|---|
| POST | `/api/customers/sync` | `{success, customer}` |
| POST | `/api/orders` | `{success, order_name, grand_total, customer}` |
| POST | `/api/orders/replace_latest` | `{success, order_name, grand_total, cancelled_order}` |
| GET | `/api/orders/pending[?date=Y-M-D]` | lista de pedidos activos |
| POST | `/api/orders/{id}/deliver` | `{success, message, delivery_note}` |
| POST | `/api/orders/{id}/cancel` | `{success, message}` (409 si ya se entregó) |
| POST | `/api/orders/{id}/pay` | `{success, sales_invoice, payment_entry, order_id}` |
| POST | `/api/accounting/expense` | `{success, journal_entry}` |
| GET | `/api/sales/summary` | totales de ventas |
| GET | `/api/sales/by-product` | ventas por producto |
| GET | `/health` | `{status:"ok"}` (extra) |

## Qué NO hace

- No valida contra ERPNext real ni toca contabilidad de verdad.
- Precios y numeraciones son **ficticios** (`CATALOG` y `SALES-ORD-MOCK-*`).
- Estado **en memoria**: se pierde al reiniciar el contenedor (al arrancar siembra
  2 pedidos de ejemplo, uno para hoy y uno para mañana).

## Variables

| Var | Default | Para qué |
|---|---|---|
| `PORT` | `8001` | puerto de escucha |
| `MOCK_ERP_LATENCY_MS` | `0` | latencia artificial, para ver estados de carga |
