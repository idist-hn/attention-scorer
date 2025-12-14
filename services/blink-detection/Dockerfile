# Blink Detection Microservice
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 50056
ENV GRPC_PORT=50056

CMD ["python", "main.py"]

