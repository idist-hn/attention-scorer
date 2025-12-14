# Attention Scorer Microservice
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 50057
ENV GRPC_PORT=50057

CMD ["python", "main.py"]

