# NanoAssist - Documento Operacional Atualizado

## 1) Visao Geral

NanoAssist e um agente de atendimento WhatsApp da Nanofarmacos.
A solucao recebe mensagens pelo webhook, processa o estado da conversa via LangGraph e responde no canal do CRM.

Stack atual:
- Python 3.13 (local) / alvo 3.11 em container
- FastAPI
- LangGraph
- SQLite em desenvolvimento / PostgreSQL recomendado em producao
- httpx
- Next.js para simulador/admin local

## 2) Arquitetura Implementada (estado real)

Entrada:
- Cliente WhatsApp
- CRM -> `POST /webhook`
- Simulador frontend -> `POST /webhook/test`

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
- SQLite local por padrao
- PostgreSQL suportado via `DATABASE_URL=postgresql://...`
- fallback para `InMemorySaver` quando necessario

Integracoes:
- CRM/WhatsApp: Dix como padrao
- Compatibilidade legada: MediPharma
- Receitas: NanoCare API oficial por token ou fallback legado por sessao ReceitaFace
- Gateway de pagamento: Rede/e.Rede com PIX e link de pagamento
- Mocks em desenvolvimento para receitas, WhatsApp e pagamento

## 3) Status de Implementacao

- Fase 1 (Core): concluida
- Fase 2 (Testes): concluida (`51 passed`)
- Fase 3 (Integracao real e deploy): em andamento

## 4) Comparacao com o fluxo operacional

Aderencia geral alta.

Implementado:
- Entrada WhatsApp -> webhook
- Menu inicial e bifurcacao 1/2
- Fluxo 1 completo
- Camada de seguranca no Fluxo 1: CPF do titular + codigo/ID da receita
- Fluxo 2 completo
- Transferencia para humano por mensagem/estado
- Persistencia de estado
- Pagamento PIX/link via cliente Rede

Divergencias atuais:
- `ai_fallback` existe, mas nao e caminho principal
- Textos de algumas mensagens foram simplificados
- Fallback por sessao ReceitaFace nao atende a validacao segura CPF + codigo; para producao, usar API oficial
- Confirmacao de comprovante ainda e conversacional; nao ha conciliacao automatica do pagamento

## 5) Regra Critica Do Fluxo 1

O Fluxo 1 nao deve liberar dados da receita somente com nome, CPF isolado ou codigo isolado.

Entrada esperada do cliente:

```text
Codigo: RX-001
CPF: 123.456.789-00
```

Comportamento esperado:
- Extrair CPF e codigo/ID da mesma mensagem.
- Chamar validacao segura no CRM/API de receitas.
- Prosseguir apenas se a receita existir, estiver ativa e o CPF informado pertencer ao titular.
- Em falha, retornar mensagem generica sem indicar se o CPF ou o codigo esta incorreto.
- Se a API nao retornar CPF no detalhe da receita, transferir para humano por falta de validacao segura.

Contrato tecnico detalhado: `INTEGRACAO_RECEITAS.md`.

## 6) O que falta para producao

1. Homologar CRM/WhatsApp Dix
- Confirmar payload real de entrada no `POST /webhook`.
- Confirmar endpoint real de envio de mensagem (`CRM_BASE_URL`, `CRM_TOKEN`, `CRM_SEND_MESSAGE_PATH`).
- Confirmar se o CRM envia assinatura HMAC compativel com `WEBHOOK_SECRET`.

2. Homologar API oficial de receitas
- Confirmar `NANOCARE_API_URL` e `NANOCARE_API_TOKEN`.
- Confirmar endpoint seguro CPF + codigo/ID da receita.
- Garantir que o response de sucesso inclui `patient.cpf`.
- Remover dependencia operacional de cookie/sessao ReceitaFace em producao.

3. Integrar pagamento real ponta a ponta
- Validar credenciais `REDE_PV` e `REDE_INTEGRATION_TOKEN`.
- Homologar PIX real.
- Homologar endpoint real de link de pagamento com a documentacao Rede.
- Definir origem do valor real da receita; hoje ha fallback em `PAYMENT_DEFAULT_AMOUNT`.

4. Persistencia e deploy
- Usar PostgreSQL em producao (`DATABASE_URL=postgresql://...`).
- Deploy com HTTPS e webhook publico.
- Configurar healthcheck `/health`.

5. Hardening de seguranca e operacao
- `APP_ENV=production`.
- `WEBHOOK_SECRET` forte e obrigatorio.
- `RECEITAFACE_MOCK_ENABLED=false`.
- `CORS_ORIGINS` restrito.
- Rate limit revisado para volume real.
- Logs/monitoramento e procedimento de handoff humano.

## 7) Percentual de Avanco

- Core tecnico: 95%
- Testes: 95%
- Integracoes reais: 65%
- Readiness de producao: 72%
- Projeto geral: 88%

## 8) Variaveis de Ambiente (resumo)

Ambiente:
- `APP_ENV=development|production`
- `LOG_LEVEL=INFO`
- `DATABASE_URL`
- `CORS_ORIGINS`

CRM/WhatsApp:
- `CRM_PROVIDER=dix`
- `CRM_BASE_URL`
- `CRM_TOKEN`
- `CRM_SEND_MESSAGE_PATH`
- `DIX_BASE_URL`
- `DIX_TOKEN`
- `DIX_SEND_MESSAGE_PATH`

Fallback legado:
- `MEDIPHARMA_BASE_URL`
- `MEDIPHARMA_TOKEN`

Receitas:
- `NANOCARE_API_URL`
- `NANOCARE_API_TOKEN`
- `RECEITAFACE_MOCK_ENABLED=false` em producao
- `RECEITAFACE_USE_SESSION=false` em producao, salvo contingencia aprovada
- `RECEITAFACE_SESSION_COOKIE`
- `RECEITAFACE_CSRF_TOKEN`

Pagamento:
- `REDE_PV`
- `REDE_INTEGRATION_TOKEN`
- `PAYMENT_DEFAULT_AMOUNT`
- `PIX_DISCOUNT_PCT`

Seguranca:
- `WEBHOOK_SECRET`
- `WEBHOOK_RATE_LIMIT`

LLM:
- `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`

## 9) Comandos de Validacao

Backend:

```bash
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Teste local do Fluxo 1 com mock:

```text
oi
1
Codigo: RX-001 CPF: 123.456.789-00
```
