FROM python:3.12-alpine
WORKDIR /app
# Sin dependencias externas: el mock usa solo la stdlib de Python.
COPY mock_erp_service.py .
EXPOSE 8001
CMD ["python", "-u", "mock_erp_service.py"]
