# 📋 MecâniQA Tech — Governança SRE, Métricas de TI & Continuidade de Negócio

> **Classificação:** Documento Técnico Formal de Gestão de Serviços de TI  
> **Contrato Base:** Clientes Enterprise (99,9% de Disponibilidade)  
> **Metodologias:** Google SRE (Site Reliability Engineering) & ITIL v4 Continuidade de Serviços

---

## 1. Fundamentos de Observabilidade e Métricas de Confiabilidade

Para atender aos rigorosos requisitos de auditoria dos clientes Enterprise, a MecâniQA Tech adota os conceitos fundamentais de Observabilidade moderna:

### Os Três Pilares da Observabilidade:
1. **Métricas (Time-Series):** Indicadores numéricos agregáveis coletados periodicamente via Prometheus (`mecaniqa_requests_total`, `container_cpu_usage_seconds_total`). Essenciais para detecção de tendências, detecção proativa de anomalias e disparo de alarmes.
2. **Logs Estruturados:** Registros de eventos com carimbo temporal (timestamp), identificador de correlação e nível de criticidade emitidos em `stdout` e formatados em JSON pelos pods.
3. **Traces Distribuídos:** Rastreamento do ciclo de vida das requisições através dos múltiplos nós e microsserviços do cluster para diagnóstico de gargalos de rede.

### Metodologias Adotadas:
- **The 4 Golden Signals (Google SRE):**
  * **Latência (Latency):** Tempo de resposta medido em milissegundos para ingestão dos sensores.
  * **Tráfego (Traffic):** Vazão instantânea medida em requisições por segundo (RPS).
  * **Erros (Errors):** Frequência de falhas com códigos HTTP 5xx ou rejeições no processamento.
  * **Saturação (Saturation):** Fração de capacidade máxima consumida (ex: 83% de CPU ou esgotamento de réplicas).
- **Método RED (Request-driven):** Rate (Taxa), Errors (Erros), Duration (Duração).
- **Método USE (Resource-driven):** Utilization (Utilização), Saturation (Saturação), Errors (Erros de hardware).

---

## 2. Acordos de Nível de Serviço (SLA, SLO, SLI)

```
┌────────────────────────────────────────────────────────┐
│                        SLA                             │
│        (Contrato Comercial com o Cliente: 99,9%)       │
│  ┌──────────────────────────────────────────────────┐  │
│  │                     SLO                          │  │
│  │      (Meta Interna de Engenharia: 99,95%)        │  │
│  │  ┌────────────────────────────────────────────┐  │  │
│  │  │                  SLI                       │  │  │
│  │  │     (Métrica Real no Prometheus)           │  │  │
│  │  └────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 2.1. SLA (Service Level Agreement)
* **Definição:** Contrato legal e formal celebrado entre a MecâniQA Tech e os clientes da categoria Enterprise.
* **Compromisso de Disponibilidade:** **99,9% mensal**.
* **Downtime Máximo Permitido:** 
  $$\text{Downtime Máximo} = 30 \times 24 \times 60 \times (1 - 0.999) = 43,8 \text{ minutos por mês}$$
* **Penalidades por Descumprimento:**
  - Disponibilidade < 99,9% e $\ge$ 99,0%: Crédito financeiro de 10% na mensalidade.
  - Disponibilidade < 99,0% e $\ge$ 95,0%: Crédito financeiro de 25% na mensalidade.
  - Disponibilidade < 95,0%: Reembolso integral da mensalidade e cláusula de rescisão unilateral sem multa.

---

### 2.2. SLO (Service Level Objective)
* **Definição:** Metas internas rigorosas estabelecidas pela equipe de Engenharia de Confiabilidade da MecâniQA para assegurar que o SLA externo nunca seja violado.

| Identificador | Objetivo Interno (SLO) | Janela de Medição | Error Budget (Orçamento de Erro) |
|---|---|---|---|
| **SLO-01 (Disponibilidade)** | **$\ge 99,95\%$** das requisições retornam HTTP status < 500 | Móvel de 30 dias | 0,05% (~21,9 minutos de falha tolerada) |
| **SLO-02 (Latência P95)** | **$\le 250\text{ ms}$** para 95% das ingestões de telemetria IoT | Móvel de 7 dias | 5% das requisições podem superar 250ms |
| **SLO-03 (Taxa de Sucesso IoT)** | **$\ge 99,5\%$** de leituras válidas processadas sem corrupção | Diária (24h) | 0,5% de descarte em pacotes anômalos |
| **SLO-04 (Autoscaling Responsiveness)** | HPA escala novos pods em **$\le 60\text{ segundos}$** após saturação de CPU > 50% | Por incidente | Tempo de bootstrapping de pod < 15s |

---

### 2.3. SLI (Service Level Indicator)
* **Definição:** Indicadores técnicos quantitativos calculados diretamente a partir das métricas coletadas pelo Prometheus.

#### SLI 1: Taxa Real de Disponibilidade da API
Fórmula matemática:
$$\text{SLI}_{\text{disponibilidade}} = \frac{\sum \text{Requisições com Status } < 500}{\sum \text{Total de Requisições}} \times 100$$

Expressão PromQL no Prometheus:
```promql
(sum(rate(mecaniqa_requests_total{status!~"5.."}[30d])) / sum(rate(mecaniqa_requests_total[30d]))) * 100
```

#### SLI 2: Latência de Ingestão no Percentil 95 (P95)
Expressão PromQL no Prometheus:
```promql
histogram_quantile(0.95, sum(rate(mecaniqa_request_duration_seconds_bucket[5m])) by (le))
```

#### SLI 3: Taxa de Integridade e Sucesso de Telemetria IoT
Fórmula matemática:
$$\text{SLI}_{\text{sucesso\_iot}} = \frac{\sum \text{Leituras com Sucesso}}{\sum \text{Leituras com Sucesso} + \sum \text{Leituras com Erro}} \times 100$$

Expressão PromQL no Prometheus:
```promql
(sum(rate(mecaniqa_sensor_readings_success_total[30d])) / 
 (sum(rate(mecaniqa_sensor_readings_success_total[30d])) + sum(rate(mecaniqa_sensor_readings_error_total[30d])))) * 100
```

---

## 3. Continuidade de Negócios e Resiliência (RTO & RPO)

Para garantir que desastres de infraestrutura (como falha em instâncias de nós, corrupção de pods ou picos catastróficos) não causem interrupções definitivas, a MecâniQA Tech define os seguintes parâmetros:

```
    Incidente / Falha
         │
         │◄──────── RTO ────────►│
         │ (Tempo de Recuperação)│
─────────┼───────────────────────┼─────────────► Tempo
         │
         ▲
         │◄── RPO ──►│
         (Perda de Dados Tolerada)
```

### 3.1. RTO (Recovery Time Objective)
* **Meta Oficial:** **RTO $\le$ 15 minutos**.
* **Significado:** O tempo máximo decorrido entre a constatação da indisponibilidade do cluster e o restabelecimento completo do serviço de ingestão IoT.
* **Mecanismos de Cumprimento:**
  1. **Deploy Declarativo GitOps / Manifestos K8s:** Todo o cluster, incluindo HPA, Prometheus, Grafana e API, pode ser reconstruído via `kubectl apply` em menos de 2 minutos.
  2. **Horizontal Pod Autoscaler (HPA):** Recuperação autônoma de capacidade sem intervenção humana em menos de 45 segundos.
  3. **Liveness & Readiness Probes:** Reinício automático pelo Kubelet de instâncias de pods que deixarem de responder ao endpoint `/health`.

### 3.2. RPO (Recovery Point Objective)
* **Meta Oficial:** **RPO $\le$ 5 minutos**.
* **Significado:** O volume máximo aceitável de dados de sensores IoT que podem ser perdidos no pior cenário de desastre (ex: queima simultânea de storages).
* **Mecanismos de Cumprimento:**
  1. **Persistência de Séries Temporais no Prometheus TSDB:** Flush periódico de blocos de memória para Persistent Volumes a cada 2 horas com Write-Ahead-Log (WAL) síncrono.
  2. **Buffer Local nos Sensores IoT das Oficinas:** O firmware dos dispositivos IoT das oficinas possui buffer em memória Flash capaz de armazenar até 30 minutos de telemetria offline, reenviando-os automaticamente após o retorno da API da MecâniQA.
  3. **Snapshots de Banco de Dados:** Backup de volumes com periodicidade diária e replicação contínua para storage redundante.
