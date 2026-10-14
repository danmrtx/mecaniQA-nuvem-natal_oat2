# 📡 MecâniQA Tech — Brainstorming de Arquitetura & Observabilidade IoT

> **Projeto:** Plataforma Preditiva e Ingestão de Sensores IoT para Oficinas Mecânicas  
> **Objetivo:** Eliminar a "caixa preta" do cluster, garantir disponibilidade de 99,9% (Contratos Enterprise), autoscaling dinâmico e proteção cibernética contra tráfego massivo de pico.

---

## 1. Contexto do Desafio e Problema de Negócio

As oficinas mecânicas e auto centers parceiros da MecâniQA Tech enviam continuamente milhares de pacotes de telemetria automotiva via sensores IoT (temperatura de bloco do motor, pressão de óleo, rotações por minuto - RPM, anomalias elétricas em alternadores e chicotes, tensão de bateria).

### Dores Enfrentadas:
1. **Cluster "Caixa Preta":** A equipe de Engenharia de Confiabilidade e Operações não possuía visibilidade do estado interno dos serviços, consumo de hardware ou latências.
2. **Picos de Horário Comercial:** Entre 08h e 18h, o volume de leituras sobe vertiginosamente. Sem capacidade de adaptação automática, o sistema sofria degradação de throughput e risco de indisponibilidade geral.
3. **Exigência Contratual Enterprise:** Clientes corporativos firmaram contratos formais de **SLA de 99,9%**. Qualquer queda superior a 43 minutos por mês acarreta multas contratuais pesadas e perda de credibilidade no mercado.
4. **Falta de Segurança no Transporte e Ingestão:** Risco de sensores comprometidos realizarem ataques de negação de serviço (DoS) ou injeção de dados corrompidos.

---

## 2. Brainstorming de Soluções Arquiteturais

Durante as sessões de concepção técnica, foram analisadas três abordagens principais:

```
+-----------------------------------------------------------------------------+
|                            MATRIZ DE DECISÃO ARQUITETURAL                   |
+---------------------+-----------------------+-------------------------------+
| Abordagem           | Prós                  | Contras                       |
+---------------------+-----------------------+-------------------------------+
| 1. Monolito Estático| Baixa complexidade    | Impossível escalar apenas a   |
|    sem métricas     | inicial de código.    | ingestão; "caixa preta"; viola|
|                     |                       | o SLA de 99,9%.               |
+---------------------+-----------------------+-------------------------------+
| 2. Cloud Proprietária| Serviços gerenciados | Custo proibitivo por ingestão |
|    (Datadog/NewRelic)| prontos.             | em volume IoT; vendor lock-in.|
+---------------------+-----------------------+-------------------------------+
| 3. Stack Open-Source| - Padrão da indústria | Requer expertise em manifestos|
|    Cloud-Native     | - Prometheus + Grafana| e tuning de HPA.              |
|    (ESCOLHIDA)      | - HPA no Kubernetes   | (Garante independência e      |
|                     | - Exportador nativo   | controle total de custos).    |
+---------------------+-----------------------+-------------------------------+
```

---

## 3. Arquitetura da Solução Implementada

A arquitetura implantada baseia-se no modelo **Cloud-Native**, desacoplado e resiliente:

```
  [ Sensores IoT Automotivos ]
  (Oficinas Feira, Salvador, etc.)
               │
               │ HTTP POST /api/v1/sensors/telemetry (JSON)
               ▼
  ┌─────────────────────────────────────────────────────────────┐
  │              Kubernetes Ingress & Service (LB)              │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
           ┌─────────────────────┴─────────────────────┐
           ▼                                           ▼
  ┌───────────────────┐                       ┌───────────────────┐
  │  Pod mecaniqa-app │ ◄─────────┐           │  Pod mecaniqa-app │
  │ (FastAPI + Metric)│           │           │ (FastAPI + Metric)│
  └────────┬──────────┘           │           └────────┬──────────┘
           │ /metrics             │                    │ /metrics
           ▼                      │                    ▼
  ┌──────────────────┐            │           ┌──────────────────┐
  │    Prometheus    │            │           │  Metrics Server  │
  │   (Scraper 5s)   │            │           └────────┬─────────┘
  └────────┬─────────┘            │                    │
           │                      │                    │ Pod CPU/RAM
           ▼                      │                    ▼
  ┌──────────────────┐            │           ┌──────────────────┐
  │     Grafana      │            │           │       HPA        │
  │ 4 Dashboards +   │            └───────────┤ (Min: 2, Max: 10)│
  │ 4 Alarmes Ativos │                        └──────────────────┘
  └──────────────────┘
```

### Componentes Principais:
1. **MecâniQA API (Python 3.11 + FastAPI + `prometheus_client`):**
   - Microsserviço de alta performance assíncrona.
   - Instrumentação nativa expondo métricas no endpoint `/metrics`.
   - Processamento resiliente com separação de contadores para sucesso, erros, anomalias elétricas e superaquecimento de motor (> 105°C).
2. **Kubernetes Metrics Server:**
   - Coleta métricas de consumo de CPU e RAM diretamente do cAdvisor no Kubelet de cada nó.
3. **Horizontal Pod Autoscaler (HPA):**
   - Monitora o consumo médio de CPU da aplicação (meta de 50%).
   - Escala dinamicamente de 2 réplicas até o teto de 10 réplicas durante os horários de pico ou testes de estresse.
4. **Prometheus Server (Namespace `monitoring`):**
   - Motor de armazenamento de séries temporais (TSDB).
   - Scrape contínuo a cada 5 segundos dos pods da API.
   - Regras de alerta de infraestrutura e aplicação avaliadas dinamicamente.
5. **Grafana (Namespace `monitoring`):**
   - Camada visual integrada com provisionamento automático de DataSource e Dashboard.
   - Exibição em tempo real dos 4 pilares: CPU, Memória, Erros e Sucessos.
   - 4 Alarmes de monitoramento ativo com disparos e estados auditáveis.

---

## 4. Pilares de Segurança da Informação para IoT

Para garantir que a ingestão em grande escala não seja um vetor de vulnerabilidade:

1. **Princípio do Menor Privilégio (RBAC K8s):**
   - ServiceAccounts e ClusterRoles dedicados exclusivamente com permissões de leitura (`get`, `list`, `watch`) para o Prometheus nos endpoints de métricas.
2. **Isolamento de Namespaces:**
   - A stack de monitoramento opera isolada no namespace `monitoring`, desacoplada do namespace da aplicação `default`.
3. **Higienização e Validação de Carga (Sanitization):**
   - Validação estrita via Pydantic dos dados de telemetria recebidos (`value`, `sensor_type`, `workshop_id`). Leituras inválidas ou valores inconsistentes são rejeitados imediatamente (HTTP 400), prevenindo Buffer Overflows ou memory poisoning.
4. **Proteção contra DoS via Limites de Recursos (cgroups):**
   - Definição mandatória de `resources.limits` e `resources.requests` nos contêineres K8s (CPU: 500m máx, RAM: 256Mi máx). Isso impede que um pod infectado ou sob ataque comprometa o nó hospedeiro.
5. **Contêiner Seguro (Non-Root Execution):**
   - Imagens configuradas para não utilizar o usuário root nos processos do sistema operacional hospedeiro.
