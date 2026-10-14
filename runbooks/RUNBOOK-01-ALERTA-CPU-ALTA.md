# 📘 RUNBOOK 01 — Alarme Infra: CPU Alta no Cluster

| Metadado | Detalhe |
|---|---|
| **Nome do Alarme** | `Alarme-Infra-CPU-Alta` / `HighCPUUsageInfra` |
| **UID do Alarme Grafana** | `alert-infra-cpu` |
| **Severidade** | 🔴 CRÍTICA (P1) |
| **Componente Afetado** | Pods `mecaniqa-app` / Kubelet / CPU Node |
| **Impacto no Negócio** | Lentidão na ingestão de telemetria, aumento de latência e violação de SLA (SLO-02). |

---

## 1. Condição de Disparo & Limiar
* **Métrica Avaliada:** `process_cpu_seconds_total` ou `container_cpu_usage_seconds_total`
* **Expressão PromQL:**
  ```promql
  sum(rate(process_cpu_seconds_total{job="mecaniqa-iot-api"}[1m])) * 100 > 75
  ```
* **Duração de Persistência:** Dispara se o valor permanecer $> 75\%$ por mais de 15 segundos.

---

## 2. Diagnóstico Executável Passo a Passo

### Passo 1: Verificar status imediato do HPA no cluster
Abra o terminal e execute:
```powershell
kubectl get hpa mecaniqa-app-hpa
```
* **O que verificar:** Se a coluna `TARGETS` está acima de `50%` e se o número de `REPLICAS` está subindo em direção ao limite de `10`.

### Passo 2: Listar consumo dos pods individuais
```powershell
kubectl top pods -l app=mecaniqa-app
```
* **O que verificar:** Identifique se o alto consumo está distribuído homogeneamente ou concentrado em apenas um pod defeituoso.

### Passo 3: Inspecionar logs dos pods sob carga
```powershell
kubectl logs -l app=mecaniqa-app --tail=100
```
* **O que verificar:** Identificar se há loops infinitos, payloads maliciosos ou processamento anômalo.

---

## 3. Ações de Remediação

### Cenário A: O HPA atingiu o teto máximo (10 pods) e a CPU continua alta
* **Ação Imediata (Mitigação):** Aumente temporariamente o limite máximo de pods para absorver o pico:
  ```powershell
  kubectl patch hpa mecaniqa-app-hpa --patch '{"spec":{"maxReplicas":20}}'
  ```
* **Ação de Escala Manual Emergencial (se o HPA estiver bloqueado):**
  ```powershell
  kubectl scale deployment mecaniqa-app --replicas=12
  ```

### Cenário B: Pod travado consumindo 100% de CPU
* **Ação:** Reinicie o pod problemático para forçar o Kubelet a recriá-lo:
  ```powershell
  kubectl delete pod <NOME_DO_POD>
  ```

---

## 4. Critérios de Normalização & Encerramento
1. A métrica de CPU no Grafana estabiliza abaixo de 50%.
2. O HPA inicia a estabilização e redução gradual de réplicas.
3. Não há requisições sofrendo timeout (`latência P95 < 250ms`).
4. Registrar o incidente no painel de gestão de capacidade.
