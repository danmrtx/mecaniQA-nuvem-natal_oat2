# 📘 RUNBOOK 02 — Alarme Infra: Memória RAM Alta no Cluster

| Metadado | Detalhe |
|---|---|
| **Nome do Alarme** | `Alarme-Infra-Memoria-Alta` / `HighMemoryUsageInfra` |
| **UID do Alarme Grafana** | `alert-infra-mem` |
| **Severidade** | 🟡 ALERTA (P2) |
| **Componente Afetado** | Pods `mecaniqa-app` / Memória RAM do Host / cgroups |
| **Impacto no Negócio** | Risco iminente de terminação de pods por `OOMKilled` (Exit Code 137), perda de conexões e instabilidade. |

---

## 1. Condição de Disparo & Limiar
* **Métrica Avaliada:** `process_resident_memory_bytes` ou `container_memory_working_set_bytes`
* **Expressão PromQL:**
  ```promql
  sum(process_resident_memory_bytes{job="mecaniqa-iot-api"}) / (1024 * 1024) > 150
  ```
* **Duração de Persistência:** Dispara se o consumo total ultrapassar `150 MB` por mais de 15 segundos.

---

## 2. Diagnóstico Executável Passo a Passo

### Passo 1: Listar pods com maior uso de memória RAM
Execute no terminal:
```powershell
kubectl top pods -l app=mecaniqa-app --sort-by=memory
```
* **O que verificar:** Se há pods individuais consumindo próximo a `256Mi` (que é o limite estrito definido em `k8s/api.yaml`).

### Passo 2: Verificar se algum pod foi finalizado por OOMKilled
Execute:
```powershell
kubectl get pods -l app=mecaniqa-app -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}{end}'
```
* **O que verificar:** Se aparecer `OOMKilled`, o contêiner estourou o limite de memória do cgroup.

### Passo 3: Inspecionar eventos de desalocação e nós
```powershell
kubectl get events --field-selector reason=Killing
```

---

## 3. Ações de Remediação

### Cenário A: Memory Leak na aplicação Python
* **Ação Imediata (Mitigação):** Efetuar um rollout restart seguro (rolling update com zero downtime):
  ```powershell
  kubectl rollout restart deployment mecaniqa-app
  ```
* **Ação Preventiva/Aumento de Limites:** Se o volume legítimo de dados IoT cresceu:
  Edite `k8s/api.yaml` e aumente `resources.limits.memory` para `512Mi`:
  ```powershell
  kubectl set resources deployment mecaniqa-app --limits=memory=512Mi --requests=memory=128Mi
  ```

---

## 4. Critérios de Normalização & Encerramento
1. Consumo de memória nos pods reduzido para a faixa saudável (< 100MB).
2. Quantidade de reinícios dos contêineres (`RESTARTS`) estabilizada em zero.
3. Alarme transiciona de `firing` para `inactive` no Grafana.
