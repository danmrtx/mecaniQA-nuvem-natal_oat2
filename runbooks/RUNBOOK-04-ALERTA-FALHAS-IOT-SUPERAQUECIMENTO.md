# 📘 RUNBOOK 04 — Alarme Customizado IoT: Superaquecimento de Motores & Falhas Críticas

| Metadado | Detalhe |
|---|---|
| **Nome do Alarme** | `Alarme-App-Superaquecimento-Motores` / `IoTOverheatAnomalySpike` |
| **UID do Alarme Grafana** | `alert-app-superaquecimento` |
| **Severidade** | 🔴 CRÍTICA DE NEGÓCIO (P1) |
| **Componente Afetado** | Sensores IoT Automotivos / Mecânica Preditiva |
| **Impacto no Negócio** | Risco de fundição de motores de clientes, quebras catastróficas em trânsito e falha no valor preditivo do software MecâniQA. |

---

## 1. Condição de Disparo & Limiar
* **Métrica Avaliada:** `mecaniqa_engine_overheat_alerts_total`
* **Expressão PromQL:**
  ```promql
  sum(rate(mecaniqa_engine_overheat_alerts_total[1m])) > 0.05
  ```
* **Duração de Persistência:** Dispara se a taxa de eventos com temperatura do motor $\ge 105^\circ\text{C}$ superar `0,05 alertas/s` por mais de 10 segundos.

---

## 2. Diagnóstico Executável Passo a Passo

### Passo 1: Identificar quais veículos e oficinas estão gerando os alertas
Consulte as séries temporais ativas no Prometheus:
```powershell
curl.exe -s "http://localhost:9090/api/v1/query?query=topk(5,%20mecaniqa_engine_temperature_celsius)"
```
* **O que verificar:** Quais placas de veículos (`vehicle_id`) estão apresentando picos perigosos de temperatura.

### Passo 2: Verificar ocorrência simultânea de falhas elétricas
```powershell
curl.exe -s "http://localhost:9090/api/v1/query?query=sum(rate(mecaniqa_electrical_faults_total[5m]))"
```
* **O que verificar:** Se o superaquecimento está associado a panes na ventoinha / chicote elétrico do radiador.

### Passo 3: Inspecionar o painel do Grafana
* Acesse `http://localhost:3000/d/mecaniqa-core-dashboard`
* Observe o painel **3. Erro na Aplicação (Métrica Customizada IoT)** e o status da regra de alerta na aba **Alerting**.

---

## 3. Ações de Remediação & Fluxo Operacional

### Ação 1: Notificação Preditiva Imediata para as Oficinas
* Disparar broadcast de alerta pelo sistema MecâniQA para as bancadas mecânicas das oficinas correspondentes:
  * Solicitar parada imediata de testes de dinamômetro e desligamento dos motores indicados.
  * Iniciar teste de vazamento de líquido de arrefecimento e pressurização do radiador.

### Ação 2: Validação de Ruído / Calibração de Sensores
* Se múltiplos veículos apresentarem exatamente a mesma temperatura anômala no mesmo segundo:
  * Verificar se houve oscilação eletromagnética ou problema de terra no barramento CAN da oficina.
  * Solicitar calibração dos módulos de leitura OBD-II/IoT da MecâniQA.

---

## 4. Critérios de Normalização & Encerramento
1. A temperatura dos motores monitorados retorna para a faixa de operação segura ($< 95^\circ\text{C}$).
2. A taxa da métrica `mecaniqa_engine_overheat_alerts_total` retorna a zero.
3. O status do alarme no Grafana transiciona de `Firing` para `Normal/Inactive`.
4. Os relatórios de manutenção preventiva dos veículos são atualizados no histórico.
