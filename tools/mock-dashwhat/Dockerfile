FROM python:3.12-alpine
WORKDIR /app
# Sin dependencias externas: el mock usa solo la stdlib de Python.
COPY mock_dashwhat.py .
# El HTML del simulador se monta como volumen (ver docker-compose.local.yml),
# no se copia acá: así editarlo no requiere reconstruir la imagen.
EXPOSE 8880
CMD ["python", "-u", "mock_dashwhat.py"]
