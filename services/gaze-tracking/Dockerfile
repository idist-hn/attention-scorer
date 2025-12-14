# Gaze Tracking Microservice
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 50055
ENV GRPC_PORT=50055

CMD ["python", "main.py"]

