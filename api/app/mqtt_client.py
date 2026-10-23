import json
import logging

import paho.mqtt.client as mqtt

from .config import MQTT_HOST, MQTT_PORT

log = logging.getLogger("mqtt")


class Bus:
    """Tópicos: robo/<id>/comando (backend -> robô) e robo/<id>/status (robô -> backend)."""

    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="backend-galpao")
        self.handler = None
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        log.info("MQTT conectado (%s)", reason_code)
        client.subscribe("robo/+/status", qos=1)

    def _on_message(self, client, userdata, msg):
        try:
            robo_id = msg.topic.split("/")[1]
            data = json.loads(msg.payload)
            if self.handler:
                self.handler(robo_id, data)
        except Exception:
            log.exception("erro ao processar mensagem MQTT")

    def start(self, handler):
        self.handler = handler
        self.client.connect_async(MQTT_HOST, MQTT_PORT)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish_comando(self, robo_id: str, payload: dict):
        self.client.publish(f"robo/{robo_id}/comando", json.dumps(payload), qos=1)


bus = Bus()
