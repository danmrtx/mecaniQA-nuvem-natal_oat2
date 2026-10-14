# 📘 RUNBOOK 03 — Alarme Customizado: Alta Taxa de Erros na Aplicação

| Metadado | Detalhe |
|---|---|
| **Nome do Alarme** | `Alarme-App-Taxa-Erros` / `HighApplicationErrorRate` |
| **UID do Alarme Grafana** | `alert-app-erros` |
| **Severidade** | 🔴 CRÍTICA (P1) |
| **Componente Afetado** | Rota `/api/v1/sensors/telemetry` / Endpoint Ingestão |
| **Impacto no Negócio** | Perda de leituras dos veículos nas oficinas parceiras e consumo acelerado do Error Budget do SLA de 99,9%. |

---

## 1. Condição de Disparo & Limiar
* **Métrica Avaliada:** `mecaniqa_sensor_readings_error_total` e `mecaniqa_requests_total{status=~"5.."}`
* **Expressão PromQL:**
  ```promql
  sum(rate(mecaniqa_sensor_readings_error_total[1m])) > 1 or (sum(rate(mecaniqa_requests_total{status=~"5.."}[1m])) / sum(rate(mecaniqa_requests_total[1m]))) * 100 > 5
  ```
* **Duração de Persistência:** Dispara se a taxa de erros superar `1 erro/s` ou taxa de falhas HTTP $> 5\%$ por mais de 10 segundos.

---

## 2. Diagnóstico Executável Passo a Passo

### Passo 1: Filtrar mensagens de erro nos logs da API
Execute no terminal:
```powershell
kubectl logs -l app=mecaniqa-app --tail=200 | Select-String -Pattern "500|ERROR|Exception|Falha"
```
* **O que verificar:** Identifique se os erros são decorrentes de exceções não tratadas, problemas de parse JSON ou falha de comunicação com dependências.

### Passo 2: Analisar qual oficina (`workshop_id`) está originando as falhas
Consulte o Prometheus via PromQL:
```powershell
curl.exe -s "http://localhost:9090/api/v1/query?query=sum%20by%20(workshop_id)%20(rate(mecaniqa_sensor_readings_error_total[5m]))"
```
* **O que verificar:** Descobrir se é um problema sistêmico geral ou se uma oficina específica está enviando leituras corrompidas.

### Passo 3: Testar a rota de saúde `/health`
```powershell
curl.exe -i http://localhost:8080/health
```

---

## 3. Ações de Remediação

### Cenário A: Falha pontual em uma oficina com firmware corrompido
* **Ação:** Isolar a oficina problemática via filtro de validação na API ou acionar a equipe de campo para atualização do dispositivo IoT da oficina.

### Cenário B: Instabilidade sistêmica após deploy recente
* **Ação Imediata (Rollback):** Reverter para a versão anterior estável:
  ```powershell
  kubectl rollout undo deployment mecaniqa-app
  ```
* **Verificação do Rollback:**
  ```powershell
  kubectl rollout status deployment mecaniqa-app
  ```

---

## 4. Critérios de Normalização & Encerramento
1. A taxa de requisições HTTP 5xx cai para menos de 0,1%.
2. A métrica `mecaniqa_sensor_readings_success_total` retoma o padrão normal.
3. Alarme transiciona de `firing` para `inactive` no Grafana.
4. O cálculo do Error Budget mensal é auditado.
