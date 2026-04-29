# Requisitos Tecnicos Para Integracao Com Plataforma De Receitas

Este documento descreve as informacoes necessarias para integrar o NanoAssist com a API oficial da plataforma de receitas.

## 1. Objetivo Da Integracao

O NanoAssist precisa consultar receitas cadastradas na plataforma a partir de dados enviados pelo cliente via WhatsApp.

Os criterios de busca previstos sao:

- ID da receita
- CPF do paciente/titular
- Nome completo do paciente

A API deve retornar os dados necessarios para o bot confirmar a receita com o cliente e seguir para a etapa de pagamento/orcamento.

## 2. Ambientes Necessarios

Precisamos das informacoes abaixo para cada ambiente:

- Sandbox/homologacao
- Producao

Para cada ambiente, enviar:

- URL base
- Credenciais de acesso
- Documentacao dos endpoints
- Dados ficticios para teste
- Regras de rate limit
- Politica de timeout/retry recomendada

Exemplo:

```text
Sandbox base URL: https://sandbox.exemplo.com.br
Production base URL: https://api.exemplo.com.br
```

## 3. Autenticacao

Informar o metodo oficial de autenticacao da API.

Preferencia:

```http
Authorization: Bearer <token>
```

Precisamos confirmar:

- Tipo de autenticacao: Bearer token, API key, OAuth2 ou outro
- Header exato esperado
- Como gerar o token
- Como renovar o token
- Tempo de expiracao
- Escopos/permissoes necessarios
- Se ha tokens separados para sandbox e producao
- Se ha restricao por IP allowlist

Exemplo esperado:

```http
GET /api/recipes/search?q=RX-001 HTTP/1.1
Host: api.exemplo.com.br
Authorization: Bearer TOKEN
Accept: application/json
```

## 4. Endpoint De Busca De Receita

Precisamos do endpoint oficial para busca de receita por ID, CPF ou nome.

Informar:

- Metodo HTTP
- Path
- Parametros aceitos
- Parametros obrigatorios
- Parametros opcionais
- Formato da resposta
- Codigos de erro

Exemplo de contrato desejado:

```http
GET /api/recipes/search?q={query}
```

Ou, se forem endpoints separados:

```http
GET /api/recipes/{id}
GET /api/recipes?cpf={cpf}
GET /api/recipes?patient_name={nome}
```

## 5. Request Esperado

Enviar exemplos reais de request para os seguintes casos:

- Buscar por ID da receita
- Buscar por CPF
- Buscar por nome completo
- Busca sem resultado
- Busca com multiplos resultados
- Token invalido ou expirado
- Plataforma temporariamente indisponivel

Exemplo:

```http
GET /api/recipes/search?q=123456
Authorization: Bearer TOKEN
Accept: application/json
```

## 6. Response Esperado

Precisamos de um JSON padronizado contendo os dados minimos da receita.

Campos desejados:

```json
{
  "found": true,
  "recipe": {
    "id": "RX-001",
    "patient": {
      "name": "Maria Silva",
      "cpf": "12345678900"
    },
    "status": "active",
    "formula": "Progesterona 100mg + DHEA 25mg",
    "dosage": "1 capsula ao dia pela manha",
    "items": [
      {
        "name": "Progesterona",
        "concentration": "100mg",
        "quantity": "30 capsulas",
        "instructions": "Tomar 1 capsula ao dia"
      }
    ],
    "prescriber": {
      "name": "Dr. Exemplo",
      "registry": "CRM 00000"
    },
    "created_at": "2026-04-24T10:00:00-03:00",
    "expires_at": "2026-05-24T23:59:59-03:00"
  }
}
```

Se houver multiplos resultados, informar se a API retorna lista:

```json
{
  "found": true,
  "recipes": [
    {
      "id": "RX-001",
      "patient_name": "Maria Silva",
      "status": "active",
      "created_at": "2026-04-24T10:00:00-03:00"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 1
  }
}
```

## 7. Status Da Receita

Informar todos os status possiveis da receita e o significado operacional de cada um.

Exemplos esperados:

- `active`: receita ativa e pode seguir no atendimento
- `expired`: receita expirada
- `cancelled`: receita cancelada
- `used`: receita ja utilizada
- `pending`: receita pendente de validacao
- `blocked`: receita bloqueada

Tambem precisamos saber quais status permitem seguir para pagamento e quais devem transferir para atendimento humano.

## 8. Tratamento De Erros

Enviar o padrao oficial de erro da API.

Precisamos mapear pelo menos:

- `400`: request invalida
- `401`: token ausente, invalido ou expirado
- `403`: sem permissao
- `404`: receita nao encontrada
- `429`: rate limit
- `500`: erro interno
- `502`, `503`, `504`: indisponibilidade temporaria

Exemplo desejado:

```json
{
  "error": {
    "code": "recipe_not_found",
    "message": "Receita nao encontrada",
    "details": null
  }
}
```

## 9. Busca Por CPF Ou Nome

Confirmar comportamento da API quando a busca nao for por ID unico.

Perguntas tecnicas:

- Busca por CPF retorna uma ou varias receitas?
- Busca por nome retorna uma ou varias receitas?
- Existe paginacao?
- Existe filtro por data?
- Existe filtro por status?
- Qual ordenacao padrao?
- Como identificar a receita mais recente?
- CPF deve ser enviado com ou sem mascara?
- Nome aceita busca parcial ou precisa ser exato?

## 10. Dados Sensiveis E LGPD

Como a integracao lida com dados de saude e dados pessoais, precisamos confirmar:

- Quais campos podem ser retornados pela API
- Se CPF deve vir completo ou mascarado
- Se dados medicos podem ser exibidos no WhatsApp
- Se ha necessidade de consentimento previo
- Por quanto tempo o integrador pode armazenar os dados
- Se existe endpoint com dados minimos para atendimento automatizado
- Se ha auditoria de acesso por token/usuario

## 11. Rate Limit, Timeout E Resiliencia

Informar:

- Limite de requisicoes por minuto/hora
- Timeout recomendado
- Politica recomendada de retry
- Se a API possui idempotencia
- Se ha janela de manutencao
- SLA esperado
- Webhook/status page para indisponibilidade

O NanoAssist precisa diferenciar:

- Receita nao encontrada
- Token expirado
- Plataforma indisponivel
- Timeout
- Rate limit

Isso e necessario para decidir se o bot pede nova informacao ao cliente ou transfere para atendimento humano.

## 12. Dados De Teste

Solicitamos dados ficticios de homologacao para cobrir:

- Receita encontrada por ID
- Receita encontrada por CPF
- Receita encontrada por nome
- Receita expirada
- Receita cancelada
- Receita ja utilizada
- Receita com multiplos itens
- Receita sem posologia
- Receita inexistente
- Token invalido
- Rate limit ou erro temporario

Exemplo:

```text
ID valido: RX-TEST-001
CPF valido: 12345678900
Nome valido: Maria Teste
ID inexistente: RX-NOT-FOUND
```

## 13. Criterios De Aceite Da Integracao

A integracao sera considerada pronta quando:

- A consulta funcionar sem cookie ou sessao de navegador
- A autenticacao oficial estiver documentada
- A busca por ID, CPF e nome estiver homologada
- Os erros estiverem mapeados
- Houver ambiente sandbox com dados de teste
- O contrato de response estiver estavel
- O bot conseguir diferenciar receita encontrada, nao encontrada e falha tecnica
- O fluxo estiver validado em ambiente de producao com credenciais reais

## 14. Pergunta Principal

Caso seja necessario priorizar, precisamos principalmente do contrato oficial da API para consultar receita por ID, CPF ou nome via token, com exemplos de request, response e erros.

Resumo do pedido:

```text
Precisamos do endpoint oficial de consulta de receitas por ID/CPF/nome, autenticado por token, com exemplos de request/response, codigos de erro, dados de homologacao e regras de seguranca/rate limit.
```
