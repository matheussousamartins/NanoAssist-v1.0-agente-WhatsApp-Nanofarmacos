# NanoAssist - Documento Operacional Atualizado

## 1) Visao Geral

NanoAssist e um agente de atendimento WhatsApp da Nanofarmacos.
A solucao recebe mensagens pelo webhook, processa o estado da conversa via LangGraph e responde no canal do CRM.

Stack atual:
- Python 3.13 (local) / alvo 3.11
- FastAPI
- LangGraph
- SQLite (checkpointer)
- httpx

## 2) Arquitetura Implementada (estado real)

Entrada:
- Cliente WhatsApp
- CRM -> `POST /webhook`

Orquestracao:
- `main.py` chama `graph.ainvoke(...)`
- roteamento por estado em `agent/graph.py`

Nos ativos:
- `menu`
- `flow1_buscar`
- `flow1_confirmar`
- `flow1_pagamento`
- `flow1_comprovante`
- `flow1_finalizar`
- `flow2_coletar`
- `flow2_validar`
- `ai_fallback`

Persistencia:
- checkpointer em `persistence/store.py`
- fallback para `InMemorySaver` quando necessario

Integracoes:
- CRM/WhatsApp: Dix como padrao
- Compatibilidade legada: MediPharma
- ReceitaFace: busca de receita (token ou sessao temporaria)
- Gateway de pagamento: estrutura pronta com mock em dev

## 3) Status de Implementacao

- Fase 1 (Core): concluida
- Fase 2 (Testes): concluida (`34 passed`)
- Fase 3 (Integracao real e deploy): em andamento

## 4) Comparacao com o fluxo SVG

Aderencia geral alta.

Implementado:
- Entrada WhatsApp -> webhook
- Menu inicial e bifurcacao 1/2
- Fluxo 1 completo
- Fluxo 2 completo
- Transferencia para humano
- Persistencia de estado

Divergencias atuais:
- `ai_fallback` existe, mas nao e caminho principal
- Textos de algumas mensagens foram simplificados
- ReceitaFace ainda pode depender de sessao web em ambiente sem API oficial

## 5) O que falta para producao

1. Confirmar endpoint oficial do Dix para envio de mensagem
- Motivo: hoje o cliente usa caminho configuravel, mas precisa homologar com doc oficial do cliente.

2. Confirmar API oficial ReceitaFace por token
- Motivo: remover dependencia de cookie/sessao.

3. Integrar pagamento real ponta a ponta
- Motivo: validar cobranca e falhas reais.

4. Deploy com HTTPS e webhook publico
- Motivo: recebimento real de mensagens do CRM.

5. Hardening de seguranca e operacao
- Motivo: readiness de producao.

## 6) Percentual de Avanco

- Core tecnico: 95%
- Testes: 92%
- Integracoes reais: 65%
- Readiness de producao: 72%
- Projeto geral: 88%

## 7) Variaveis de Ambiente (resumo)

CRM/WhatsApp:
- `CRM_PROVIDER=dix`
- `CRM_BASE_URL`
- `CRM_TOKEN`
- `CRM_SEND_MESSAGE_PATH`

Fallbacks:
- `DIX_BASE_URL`
- `DIX_TOKEN`
- `DIX_SEND_MESSAGE_PATH`
- `MEDIPHARMA_BASE_URL`
- `MEDIPHARMA_TOKEN`

Receitas:
- `RECEITAFACE_TOKEN` (modo oficial)
- `RECEITAFACE_USE_SESSION=true`
- `RECEITAFACE_SESSION_COOKIE`
- `RECEITAFACE_CSRF_TOKEN`

Pagamento:
- `PAYMENT_GATEWAY_URL`
- `PAYMENT_TOKEN`

LLM:
- `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`

## 8) Comandos de Validacao

```bash
pytest tests -v
uvicorn main:app --reload --port 8000
```
