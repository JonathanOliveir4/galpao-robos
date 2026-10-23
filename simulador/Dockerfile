FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "paho-mqtt>=2.0"
COPY robo.py .
CMD ["python", "-u", "robo.py"]
