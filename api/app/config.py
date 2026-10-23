import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./galpao.db")
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

LARGURA = 20
ALTURA = 20
BATERIA_POR_CELULA = 0.5   # % gasto por célula percorrida
MARGEM_BATERIA = 15        # % mínima que deve sobrar ao fim da tarefa
