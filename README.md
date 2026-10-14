# 🚗 MecâniQA Tech — Observabilidade, Autoscaling & Continuidade de Negócio

> **Solução de Alta Disponibilidade para Ingestão e Diagnóstico Preventivo de Sensores IoT em Oficinas Mecânicas**  
> **Contrato Enterprise:** Garantia de 99,9% de Disponibilidade com Autoscaling (HPA) e Observabilidade Completa.

---

## 👥 Integrantes da Equipe

- **André Valter Menezes Leite**
- **Daniel Queiroga Santana Martins**
- **Gabriel de Souza Nascimento**
- **João Roberto Santos Cardoso**
- **Pedro Henrique Freitas Couto**
- **Victor Tadeu Augusto**

---

## 📌 Contexto do Produto & Desafio

A **MecâniQA Tech** é uma empresa de tecnologia aplicada para oficinas mecânicas e auto centers (em Feira de Santana, Salvador e região). O sistema recebe milhares de leituras simultâneas de sensores IoT automotivos (temperatura de bloco do motor, pressão de óleo, falhas elétricas, RPM e telemetria de bateria) em horários de pico comercial.

Anteriormente, o cluster operava como uma **"caixa preta"**, sem visibilidade da saúde das aplicações. Com a entrada de clientes corporativos exigindo contratos com **SLA de 99,9% de disponibilidade**, este projeto eliminou a caixa preta, implementou observabilidade de ponta a ponta, configurou autoscaling dinâmico e estabeleceu governança formal de SRE e Continuidade de Negócios.

---

## 🏛️ Arquitetura da Solução

```
  [ Sensores IoT das Oficinas ]
      (Feira, Salvador, etc.)
                 │
                 ▼ (HTTP POST /api/v1/sensors/telemetry)
  ┌────────────────────────────────────────────────────────┐
  │              Kubernetes Service (LoadBalancer)         │
  └──────────────────────────┬─────────────────────────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   [ mecaniqa-app Pod 1 ]           [ mecaniqa-app Pod N ]
   (Python + Prometheus)            (Auto-escalado até 10)
            │                                 │
            ├───────────────┬─────────────────┘
            ▼ /metrics      ▼
     ┌──────────────┐ ┌──────────────┐
     │  Prometheus  │ │Metrics-Server│
     └──────┬───────┘ └──────┬───────┘
            │                │
            ▼                ▼
     ┌──────────────┐ ┌──────────────┐
     │   Grafana    │ │     HPA      │
     │ 4 Dashboards │ │ (Min:2 Max:10│
     │  4 Alarmes   │ └──────────────┘
     └──────────────┘
```

---

## 🚀 Requisitos Técnicos Entregues

### 1. Projeto de Métricas (Aplicação Python Instrumentada)
- Microsserviço Python em `app-python/` utilizando FastAPI e a biblioteca oficial `prometheus_client`.
- Métricas expostas no endpoint `/metrics`:
  * `mecaniqa_requests_total`: Contagem total de tráfego e status HTTP (200, 4xx, 5xx).
  * `mecaniqa_request_duration_seconds`: Histograma de latência por endpoint.
  * `mecaniqa_sensor_readings_success_total`: **Métrica customizada** de sucesso por oficina e sensor.
  * `mecaniqa_sensor_readings_error_total`: **Métrica customizada** de falhas e leituras corrompidas.
  * `mecaniqa_engine_overheat_alerts_total`: Alertas de motores com temperatura crítica ($\ge 105^\circ\text{C}$).
  * `mecaniqa_electrical_faults_total`: Anomalias em chicotes e alternadores.
  * `mecaniqa_engine_temperature_celsius`: Gauge de temperatura por veículo.

### 2. Stack de Monitoração no Cluster Kubernetes
- **Prometheus** (Namespace `monitoring`):
  * Scrape automático a cada 5 segundos dos pods da API.
  * Regras de alerta ativas para infraestrutura e regras de negócio IoT.
- **Grafana** (Namespace `monitoring`):
  * Data Source Prometheus pré-provisionado como padrão (`uid: Prometheus`).
  * **Exatamente 4 Dashboards/Painéis Visuais** provisionados automaticamente:
    1. **Monitoramento de CPU (Infraestrutura)**
    2. **Monitoramento de Memória (Infraestrutura)**
    3. **Erro na Aplicação (Métrica Customizada IoT)**
    4. **Sucesso na Aplicação (Métrica Customizada IoT)**
  * **Exatamente 4 Alarmes Ativos e Monitorados**:
    1. `Alarme-Infra-CPU-Alta` (Infra: CPU $> 75\%$)
    2. `Alarme-Infra-Memoria-Alta` (Infra: Memória $> 150\text{ MB}$)
    3. `Alarme-App-Taxa-Erros` (App Customizada: Erros $> 1\text{ erro/s}$ ou falha $> 5\%$)
    4. `Alarme-App-Superaquecimento-Motores` (App Customizada: Taxa de superaquecimento $> 0,05\text{ alertas/s}$)

### 3. Horizontal Pod Autoscaler (HPA)
- Manifesto em `k8s/hpa.yaml` configurado para o Deployment `mecaniqa-app`.
- **Mínimo:** 2 pods | **Máximo:** 10 pods.
- **Métricas Alvo:** CPU média em 50% e Memória média em 75%.
- Comportamento de escala imediato (`scaleUp: 0s stabilization`) para absorver rajadas de telemetria.

### 4. Teste de Estresse & Validação Prática
- Script executável em `simulate_iot_traffic.py` injetando tráfego simultâneo de sensores IoT.
- **Resultado Comprovado:** Escalonamento automático de **2 réplicas para 10 réplicas**, com disparo em tempo real dos alarmes no Grafana e Prometheus.
- Relatório com logs consolidados disponível em [`docs/EVIDENCIAS_TESTE_ESTRESSE.md`](docs/EVIDENCIAS_TESTE_ESTRESSE.md).

### 5. Governança SRE & Continuidade de Negócios
- Documentação técnica definindo formalmente **SLA (99,9%)**, **SLO**, **SLI**, **RTO ($\le 15$ min)** e **RPO ($\le 5$ min)** em [`docs/SRE_SLA_SLO_CONTINUIDADE_NEGOCIO.md`](docs/SRE_SLA_SLO_CONTINUIDADE_NEGOCIO.md).
- Estudo arquitetural e segurança cibernética em [`docs/ARQUITETURA_E_BRAINSTORMING_IOT.md`](docs/ARQUITETURA_E_BRAINSTORMING_IOT.md).

### 6. Runbooks Operacionais Estruturados (Troubleshooting Executável)
Cada alarme possui um manual detalhado passo a passo de como diagnosticar, mitigar e resolver incidentes:
1. [`runbooks/RUNBOOK-01-ALERTA-CPU-ALTA.md`](runbooks/RUNBOOK-01-ALERTA-CPU-ALTA.md)
2. [`runbooks/RUNBOOK-02-ALERTA-MEMORIA-ALTA.md`](runbooks/RUNBOOK-02-ALERTA-MEMORIA-ALTA.md)
3. [`runbooks/RUNBOOK-03-ALERTA-ERROS-APLICACAO.md`](runbooks/RUNBOOK-03-ALERTA-ERROS-APLICACAO.md)
4. [`runbooks/RUNBOOK-04-ALERTA-FALHAS-IOT-SUPERAQUECIMENTO.md`](runbooks/RUNBOOK-04-ALERTA-FALHAS-IOT-SUPERAQUECIMENTO.md)

---

## 🛠️ Como Executar o Projeto

### Pré-requisitos
- Docker Desktop com Kubernetes habilitado (ou Minikube / K3s)
- `kubectl` configurado
- Python 3.10+

---

### Opção 1: Deploy Completo no Kubernetes (Cluster Oficial)

1. **Construir a imagem da aplicação Python IoT:**
   ```powershell
   docker build -t mecaniqa-python:v1 ./app-python
   ```

2. **Implantar o namespace de monitoramento, Prometheus e Grafana:**
   ```powershell
   kubectl apply -f k8s/monitoring-namespace.yaml
   kubectl apply -f k8s/prometheus.yaml
   kubectl apply -f k8s/grafana.yaml
   ```

3. **Implantar a API MecâniQA e o HPA:**
   ```powershell
   kubectl apply -f k8s/api.yaml
   kubectl apply -f k8s/hpa.yaml
   ```

4. **Verificar os pods em execução:**
   ```powershell
   kubectl get pods -A
   kubectl get hpa mecaniqa-app-hpa
   ```

5. **Acessar as interfaces no navegador:**
   - **Grafana:** [http://localhost:3000](http://localhost:3000) (Login: `admin` / Senha: `admin` — painel disponível em *MecâniQA Observability*)
   - **Prometheus:** [http://localhost:9090](http://localhost:9090)
   - **MecâniQA API (Health):** [http://localhost:8080/health](http://localhost:8080/health)
   - **Métricas Prometheus:** [http://localhost:8080/metrics](http://localhost:8080/metrics)

---

### Opção 2: Executar o Teste de Estresse & Assistir o Autoscaling

Com o cluster rodando, execute o simulador em um terminal:
```powershell
python simulate_iot_traffic.py
```
Acompanhe em tempo real:
- O tráfego subindo de 0 para mais de 10 req/s.
- O consumo de CPU ultrapassando 50%.
- O HPA multiplicando os pods de **2 para 4, 8 e 10 réplicas**.
- Os alarmes disparando no Grafana (`http://localhost:3000/alerting/list`).

---

### Opção 3: Executar via Docker Compose (Ambiente Local Simplificado)

Se preferir rodar toda a stack via Docker Compose:
```powershell
docker compose up -d --build
```
Para finalizar:
```powershell
docker compose down -v
```

---

## 📁 Estrutura de Diretórios do Repositório

```text
mecaniqa-lab/
├── app-python/                     # Aplicação IoT instrumentada
│   ├── Dockerfile                  # Imagem container Python 3.11
│   ├── main.py                     # API FastAPI + Métricas Prometheus
│   └── requirements.txt            # Dependências
├── k8s/                            # Manifestos Kubernetes
│   ├── api.yaml                    # Deployment & Service da API MecâniQA
│   ├── hpa.yaml                    # Horizontal Pod Autoscaler (Min: 2, Max: 10)
│   ├── monitoring-namespace.yaml   # Namespace 'monitoring'
│   ├── prometheus.yaml             # Prometheus, RBAC, ConfigMap e Alertas
│   ├── grafana.yaml                # Grafana, Datasource, 4 Painéis e 4 Alarmes
│   ├── mysql.yaml                  # Manifesto K8s MySQL
│   └── redis.yaml                  # Manifesto K8s Redis
├── runbooks/                       # Manuais de Troubleshooting Executáveis
│   ├── RUNBOOK-01-ALERTA-CPU-ALTA.md
│   ├── RUNBOOK-02-ALERTA-MEMORIA-ALTA.md
│   ├── RUNBOOK-03-ALERTA-ERROS-APLICACAO.md
│   └── RUNBOOK-04-ALERTA-FALHAS-IOT-SUPERAQUECIMENTO.md
├── docs/                           # Documentação Técnica e SRE
│   ├── ARQUITETURA_E_BRAINSTORMING_IOT.md
│   ├── SRE_SLA_SLO_CONTINUIDADE_NEGOCIO.md
│   └── EVIDENCIAS_TESTE_ESTRESSE.md
├── simulate_iot_traffic.py         # Script de injeção de carga e estresse
├── docker-compose.yml              # Orquestração local completa
├── README.md                       # Documentação principal consolidada
└── .gitignore
```
