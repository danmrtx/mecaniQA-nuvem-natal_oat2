"""
Gerador contínuo de tráfego de fundo para manter os gráficos do Grafana
ativos e com dados em tempo real enquanto o usuário tira as capturas de tela.
"""
import time
import random
import requests

API_URL = "http://localhost:8080/api/v1/sensors/telemetry"
WORKSHOPS = ["oficina-feira-centro", "oficina-salvador-pituba", "oficina-conquista-norte"]
SENSORS = ["engine_temp", "electrical_system", "oil_pressure", "rpm"]

print("[INFO] Gerador de tráfego contínuo iniciado.")
while True:
    try:
        workshop = random.choice(WORKSHOPS)
        sensor = random.choice(SENSORS)
        roll = random.random()
        force_err = (roll < 0.08)
        is_overheat = (0.08 <= roll < 0.25)
        
        val = round(random.uniform(75.0, 95.0), 2)
        if is_overheat:
            sensor = "engine_temp"
            val = round(random.uniform(106.0, 115.0), 2)
            
        payload = {
            "workshop_id": workshop,
            "vehicle_id": f"BA-{random.randint(100, 999)}-MEC",
            "sensor_type": sensor,
            "value": val,
            "is_fault": (sensor == "electrical_system" and random.random() < 0.15),
            "simulate_error": force_err,
            "compute_workload": 8000
        }
        
        requests.post(API_URL, json=payload, timeout=3.0)
    except Exception:
        pass
    
    time.sleep(0.3)
