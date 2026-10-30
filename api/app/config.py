import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://galpao:galpao@localhost:3307/galpao?charset=utf8mb4",
)
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

LARGURA = 20
ALTURA = 20
BATERIA_POR_CELULA = 0.5
MARGEM_BATERIA = 15
