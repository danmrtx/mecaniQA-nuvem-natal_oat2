import math
import time
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY
)

app = FastAPI(
    title="MecâniQA IoT Telemetry & Diagnostics API",
    description="Serviço de alta disponibilidade para ingestão e monitoramento de telemetria IoT automotiva.",
    version="1.0.0"
)

# ==========================================
# MÉTRICAS PROMETHEUS (Golden Signals & Custom)
# ==========================================

# 1. Tráfego & HTTP Status (Taxa geral)
HTTP_REQUESTS_TOTAL = Counter(
    "mecaniqa_requests_total",
    "Total de requisições HTTP processadas pela API",
    ["method", "endpoint", "status"]
)

# 2. Latência / Duração
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "mecaniqa_request_duration_seconds",
    "Duração em segundos das requisições HTTP",
    ["endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# 3. Métrica Customizada da Aplicação: Sucesso de Leituras IoT
SENSOR_READINGS_SUCCESS_TOTAL = Counter(
    "mecaniqa_sensor_readings_success_total",
    "Total acumulado de leituras IoT processadas com sucesso pela oficina",
    ["workshop_id", "sensor_type"]
)

# 4. Métrica Customizada da Aplicação: Erros de Processamento / Falhas Críticas
SENSOR_READINGS_ERROR_TOTAL = Counter(
    "mecaniqa_sensor_readings_error_total",
    "Total de leituras de sensores que falharam na validação ou processamento",
    ["workshop_id", "error_type"]
)

# 5. Métrica de Negócio IoT: Alertas de Superaquecimento do Motor
ENGINE_OVERHEAT_ALERTS_TOTAL = Counter(
    "mecaniqa_engine_overheat_alerts_total",
    "Total de ocorrências de superaquecimento de motor detectadas por sensores IoT",
    ["workshop_id"]
)

# 6. Métrica de Negócio IoT: Falhas Elétricas Detectadas
ELECTRICAL_FAULTS_TOTAL = Counter(
    "mecaniqa_electrical_faults_total",
    "Total de anomalias elétricas reportadas pelos sensores IoT em tempo real",
    ["workshop_id"]
)

# 7. Gauge: Temperatura Atual do Motor
ENGINE_TEMPERATURE_GAUGE = Gauge(
    "mecaniqa_engine_temperature_celsius",
    "Última temperatura do motor registrada por veículo",
    ["vehicle_id"]
)

# 8. Gauge: Conexões de Oficinas Ativas
ACTIVE_WORKSHOPS_GAUGE = Gauge(
    "mecaniqa_active_workshops",
    "Número de oficinas conectadas transmitindo telemetria"
)


# ==========================================
# MIDDLEWARE DE LATÊNCIA & MÉTRICAS
# ==========================================
@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    endpoint = request.url.path

    # Evita poluir métricas de negócio com o próprio scraper do prometheus e healthcheck
    if endpoint in ["/metrics", "/health"]:
        return await call_next(request)

    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(endpoint=endpoint).observe(duration)


# ==========================================
# MODELOS DE DADOS
# ==========================================
class SensorTelemetryPayload(BaseModel):
    workshop_id: str = Field(..., example="oficina-feira-01")
    vehicle_id: str = Field(..., example="BR-MEC-408")
    sensor_type: str = Field(..., example="engine_temp", description="engine_temp, electrical_system, oil_pressure, rpm")
    value: float = Field(..., example=95.5)
    is_fault: bool = Field(default=False)
    simulate_error: Optional[bool] = Field(default=False, description="Forçar erro para teste de alarme")
    compute_workload: Optional[int] = Field(default=5000, description="Carga de processamento para teste de estresse")


class StressRequest(BaseModel):
    duration_seconds: float = Field(default=0.5, example=1.0)
    complexity: int = Field(default=150000, example=200000)


# ==========================================
# ROTAS DA APLICAÇÃO
# ==========================================
@app.get("/")
def read_root():
    return {
        "service": "MecâniQA IoT Ingestion Platform",
        "status": "online",
        "sla_target": "99.9%",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "telemetry": "/api/v1/sensors/telemetry",
            "stress": "/api/v1/stress"
        }
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "uptime": "operational",
        "cluster_node": "ready"
    }


@app.get("/metrics")
def get_metrics():
    """Endpoint oficial para coleta do Prometheus."""
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/sensors/telemetry", status_code=status.HTTP_200_OK)
def ingest_telemetry(payload: SensorTelemetryPayload):
    """
    Ingestão de leituras IoT em tempo real.
    Suporta regras de negócio preventivas e simulação controlada de erros.
    """
    # 1. Simulação controlada de falha crítica (para disparar alarmes no Grafana)
    if payload.simulate_error:
        SENSOR_READINGS_ERROR_TOTAL.labels(
            workshop_id=payload.workshop_id,
            error_type="injected_critical_error"
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Falha crítica no processamento da oficina {payload.workshop_id}: Sensor inconsistente"
        )

    # 2. Validação de dados espúrios / ruídos de sensor
    if payload.value < 0 and payload.sensor_type in ["engine_temp", "oil_pressure", "rpm"]:
        SENSOR_READINGS_ERROR_TOTAL.labels(
            workshop_id=payload.workshop_id,
            error_type="invalid_sensor_value"
        ).inc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Valor inválido ({payload.value}) para sensor {payload.sensor_type}"
        )

    # 3. Carga sintética de CPU (simulação de decodificação de telemetria CAN bus / FFT)
    if payload.compute_workload > 0:
        total = 0.0
        limit = min(payload.compute_workload, 200000)
        for i in range(1, limit):
            total += math.sqrt(i) * math.sin(i)

    # 4. Avaliação de Regras de Negócio Mecânica Preditiva
    if payload.sensor_type == "engine_temp":
        ENGINE_TEMPERATURE_GAUGE.labels(vehicle_id=payload.vehicle_id).set(payload.value)
        if payload.value >= 105.0:
            ENGINE_OVERHEAT_ALERTS_TOTAL.labels(workshop_id=payload.workshop_id).inc()

    if payload.sensor_type == "electrical_system" and payload.is_fault:
        ELECTRICAL_FAULTS_TOTAL.labels(workshop_id=payload.workshop_id).inc()

    # 5. Registro de Sucesso
    SENSOR_READINGS_SUCCESS_TOTAL.labels(
        workshop_id=payload.workshop_id,
        sensor_type=payload.sensor_type
    ).inc()

    return {
        "status": "success",
        "workshop_id": payload.workshop_id,
        "vehicle_id": payload.vehicle_id,
        "sensor_type": payload.sensor_type,
        "processed_value": payload.value,
        "timestamp": time.time()
    }


@app.post("/api/v1/stress")
def trigger_cpu_stress(req: StressRequest):
    """
    Endpoint para teste de estresse de CPU para acionar o HPA (Horizontal Pod Autoscaler).
    """
    start = time.time()
    cycles = 0
    while time.time() - start < req.duration_seconds:
        _ = [math.sqrt(x) * math.sin(x) for x in range(1, req.complexity)]
        cycles += 1

    return {
        "status": "stress_complete",
        "duration_seconds": time.time() - start,
        "cycles_executed": cycles
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
