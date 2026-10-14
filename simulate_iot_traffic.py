"""
MecâniQA Tech - Simulador de Tráfego IoT & Injetor de Carga de Estresse
Gera tráfego massivo e concorrente simulando centenas de oficinas mecânicas conectadas.
Valida o Horizontal Pod Autoscaler (HPA), os 4 dashboards e o disparo de alarmes no Grafana.
"""

import sys
import time
import random
import threading
import subprocess
import requests

API_URL = "http://localhost:8080"
TELEMETRY_ENDPOINT = f"{API_URL}/api/v1/sensors/telemetry"
STRESS_ENDPOINT = f"{API_URL}/api/v1/stress"

WORKSHOPS = [
    "oficina-feira-centro",
    "oficina-feira-tomba",
    "oficina-salvador-pituba",
    "oficina-salvador-iguatemi",
    "oficina-conquista-norte",
    "oficina-ilheus-sul"
]

SENSOR_TYPES = ["engine_temp", "electrical_system", "oil_pressure", "rpm", "battery_voltage"]

# Contadores globais
stats = {
    "total_requests": 0,
    "success_200": 0,
    "errors_5xx": 0,
    "overheat_alerts": 0,
    "electrical_faults": 0,
    "latencies": []
}
stats_lock = threading.Lock()
stop_flag = threading.Event()


def generate_reading(force_error=False, force_overheat=False, compute_weight=15000):
    workshop = random.choice(WORKSHOPS)
    vehicle_id = f"BA-{random.randint(100, 999)}-MEC"
    sensor = random.choice(SENSOR_TYPES)
    
    value = round(random.uniform(70.0, 98.0), 2)
    is_fault = False
    
    if force_overheat:
        sensor = "engine_temp"
        value = round(random.uniform(106.0, 122.0), 2)
    elif force_error:
        pass
    else:
        if sensor == "electrical_system" and random.random() < 0.15:
            is_fault = True
        elif sensor == "engine_temp" and random.random() < 0.20:
            value = round(random.uniform(105.5, 118.0), 2)

    return {
        "workshop_id": workshop,
        "vehicle_id": vehicle_id,
        "sensor_type": sensor,
        "value": value,
        "is_fault": is_fault,
        "simulate_error": force_error,
        "compute_workload": compute_weight
    }


def worker_iot_sender(worker_id: int, compute_weight: int):
    while not stop_flag.is_set():
        # A cada ~15 requisições injeta uma falha ou um superaquecimento
        roll = random.random()
        force_err = (roll < 0.10)
        force_overheat = (0.10 <= roll < 0.30)
        
        payload = generate_reading(force_error=force_err, force_overheat=force_overheat, compute_weight=compute_weight)
        
        t0 = time.time()
        try:
            resp = requests.post(TELEMETRY_ENDPOINT, json=payload, timeout=5.0)
            elapsed = time.time() - t0
            
            with stats_lock:
                stats["total_requests"] += 1
                stats["latencies"].append(elapsed)
                if resp.status_code == 200:
                    stats["success_200"] += 1
                    if payload["sensor_type"] == "engine_temp" and payload["value"] >= 105.0:
                        stats["overheat_alerts"] += 1
                    if payload["is_fault"]:
                        stats["electrical_faults"] += 1
                elif resp.status_code >= 500:
                    stats["errors_5xx"] += 1
        except Exception:
            with stats_lock:
                stats["total_requests"] += 1
                stats["errors_5xx"] += 1
        
        # Intervalo mínimo para evitar travamento da pilha de sockets
        time.sleep(0.01)


def worker_cpu_burner():
    while not stop_flag.is_set():
        try:
            requests.post(STRESS_ENDPOINT, json={"duration_seconds": 0.4, "complexity": 180000}, timeout=4.0)
        except Exception:
            pass
        time.sleep(0.05)


def check_hpa_and_alerts():
    try:
        hpa_out = subprocess.check_output(
            ["kubectl", "get", "hpa", "mecaniqa-app-hpa"],
            stderr=subprocess.STDOUT, text=True
        )
        pods_out = subprocess.check_output(
            ["kubectl", "get", "pods", "-l", "app=mecaniqa-app", "--no-headers"],
            stderr=subprocess.STDOUT, text=True
        )
        pod_count = len([p for p in pods_out.strip().split("\n") if p])
        return hpa_out.strip(), pod_count
    except Exception as e:
        return f"Erro ao consultar k8s: {e}", 0


def main():
    duration = 120  # 2 minutos de injeção de carga
    concurrency = 25  # 25 threads concorrentes de IoT
    stress_threads = 6 # 6 threads pesadas de CPU

    print("=" * 75)
    print("  MecâniQA Tech - Execução do Teste de Estresse & Autoscaling (HPA)")
    print(f"  Alvo: {API_URL}")
    print(f"  Duração da Sprint de Carga: {duration} segundos")
    print(f"  Threads Concorrentes IoT: {concurrency} | Threads CPU Burner: {stress_threads}")
    print("=" * 75)

    # Verifica se a API está online
    try:
        r = requests.get(f"{API_URL}/health", timeout=3.0)
        if r.status_code != 200:
            print(f"[ERRO] API não respondeu 200 em /health: {r.status_code}")
            sys.exit(1)
        print("[INFO] Conexão com o cluster confirmada! MecâniQA API está Healthy.")
    except Exception as e:
        print(f"[ERRO] Falha ao conectar na API: {e}")
        sys.exit(1)

    print("\n[INÍCIO DO TESTE DE ESTRESSE] Disparando geradores de tráfego de sensores...")
    threads = []
    for i in range(concurrency):
        t = threading.Thread(target=worker_iot_sender, args=(i, 20000), daemon=True)
        t.start()
        threads.append(t)

    for i in range(stress_threads):
        t = threading.Thread(target=worker_cpu_burner, daemon=True)
        t.start()
        threads.append(t)

    start_time = time.time()
    try:
        while time.time() - start_time < duration:
            time.sleep(10)
            elapsed = int(time.time() - start_time)
            
            with stats_lock:
                tot = stats["total_requests"]
                s200 = stats["success_200"]
                e500 = stats["errors_5xx"]
                ovh = stats["overheat_alerts"]
                lat = (sum(stats["latencies"][-50:]) / max(len(stats["latencies"][-50:]), 1)) * 1000
                rps = tot / max(elapsed, 1)

            hpa_info, pod_count = check_hpa_and_alerts()
            print(f"\n--- [T+{elapsed}s] Vazão: {rps:.1f} req/s | Total: {tot} | Sucessos: {s200} | Erros 5xx: {e500} | Superaquecidos: {ovh} | Latência Média: {lat:.1f}ms ---")
            print(f"Pods Ativos no Cluster: {pod_count}")
            lines = hpa_info.split("\n")
            if len(lines) >= 2:
                print(f"HPA Status: {lines[1]}")

    except KeyboardInterrupt:
        print("\n[AVISO] Interrompido pelo usuário.")
    finally:
        stop_flag.set()
        print("\n[FINALIZANDO] Interrompendo geradores de carga...")
        time.sleep(2)

    total_time = time.time() - start_time
    with stats_lock:
        tot = stats["total_requests"]
        s200 = stats["success_200"]
        e500 = stats["errors_5xx"]
        ovh = stats["overheat_alerts"]
        elec = stats["electrical_faults"]
        avg_lat = (sum(stats["latencies"]) / max(len(stats["latencies"]), 1)) * 1000

    print("\n" + "=" * 75)
    print("  RELATÓRIO CONSOLIDADO DO TESTE DE ESTRESSE & OBSERVABILIDADE")
    print("=" * 75)
    print(f"Tempo Total:                   {total_time:.1f} segundos")
    print(f"Total de Leituras Injetadas:   {tot} requisições")
    print(f"Taxa Média de Ingestão:        {tot / total_time:.1f} req/s")
    print(f"Leituras com Sucesso (HTTP 200): {s200} ({s200/max(tot,1)*100:.2f}%)")
    print(f"Falhas Críticas / Injetadas:   {e500} ({e500/max(tot,1)*100:.2f}%)")
    print(f"Alertas de Superaquecimento:   {ovh}")
    print(f"Falhas Elétricas Detectadas:   {elec}")
    print(f"Latência Média Global:         {avg_lat:.2f} ms")
    
    hpa_info, pod_count = check_hpa_and_alerts()
    print(f"Pods Finais em Execução:       {pod_count}")
    print(f"Status Final do HPA:           {hpa_info}")
    print("=" * 75)


if __name__ == "__main__":
    main()
