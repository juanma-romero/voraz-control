FROM python:3.12-alpine
WORKDIR /app
# Sin dependencias externas: el mock usa solo la stdlib de Python.
COPY mock_chatwoot.py .
EXPOSE 3000
CMD ["python", "-u", "mock_chatwoot.py"]
