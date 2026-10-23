"""Simulador de robôs: cada robô assina robo/<id>/comando e publica robo/<id>/status.
Para trocar por robôs reais, basta implementar o mesmo contrato MQTT."""
import json
import os
import time

import paho.mqtt.client as mqtt

HOST = os.getenv("MQTT_HOST", "localhost")
PORT = int(os.getenv("MQTT_PORT", "1883"))
TICK = float(os.getenv("TICK", "0.4"))
IDS = os.getenv("ROBO_IDS", "R01,R02,R03").split(",")
BAT_CELULA = 0.5
HEARTBEAT = 5.0


class Robo:
    def __init__(self, rid, x, y):
        self.id, self.x, self.y = rid, x, y
        self.bateria = 100.0
        self.status = "disponivel"
        self.ordem_id = None
        self.rota, self.pickup_idx, self.i, self.coletou = [], 0, 0, False
        self.ultimo_hb = 0.0
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-{rid}")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def iniciar(self):
        self.client.connect_async(HOST, PORT)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        client.subscribe(f"robo/{self.id}/comando", qos=1)
        self.publicar()

    def on_message(self, client, userdata, msg):
        if self.ordem_id is not None:
            return  # ocupado
        cmd = json.loads(msg.payload)
        self.rota = cmd["rota"]
        self.pickup_idx = cmd["pickup_idx"]
        self.i, self.coletou = 0, False
        self.status = "em_transito"
        self.ordem_id = cmd["ordem_id"]
        print(f"[{self.id}] ordem {self.ordem_id}: {len(self.rota)} células", flush=True)
        self.publicar()

    def publicar(self, evento=None, ordem_id=None):
        self.ultimo_hb = time.time()
        self.client.publish(f"robo/{self.id}/status", json.dumps({
            "x": self.x, "y": self.y, "bateria": round(self.bateria, 1),
            "status": self.status,
            "ordem_id": ordem_id if ordem_id is not None else self.ordem_id,
            "evento": evento,
        }), qos=1)

    def tick(self):
        if self.ordem_id is None:
            if self.bateria < 100:
                self.bateria = min(100.0, self.bateria + 0.25)  # recarga simplificada
            if time.time() - self.ultimo_hb >= HEARTBEAT:
                self.publicar()
            return
        if not self.coletou and self.i == self.pickup_idx:
            self.coletou = True
            self.publicar("coleta")
            return
        self.i += 1
        self.x, self.y = self.rota[self.i]
        self.bateria = max(0.0, self.bateria - BAT_CELULA)
        if self.i >= len(self.rota) - 1:
            ordem = self.ordem_id
            self.status = "disponivel"
            self.publicar("entrega_concluida", ordem_id=ordem)
            self.ordem_id = None
            print(f"[{self.id}] ordem {ordem} concluída", flush=True)
            return
        self.publicar()


if __name__ == "__main__":
    robos = [Robo(rid, i, 0) for i, rid in enumerate(IDS)]
    for r in robos:
        r.iniciar()
    while True:
        for r in robos:
            r.tick()
        time.sleep(TICK)
