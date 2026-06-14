# Imagen del backend. Con nzpy (Python puro) NO se necesita Java ni driver ODBC.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# APP_ROLE decide qué arranca este contenedor: "api" (default) o "collector".
ENV APP_ROLE=api
EXPOSE 8000

CMD ["sh", "-c", "if [ \"$APP_ROLE\" = collector ]; then python -m collector; else uvicorn main:app --host 0.0.0.0 --port 8000; fi"]
