from agent.state import AgentState, ConversationStep
from agent.tools.crm import crm_client
from agent.tools.payment import payment_client
from agent.utils import mask_cpf, mask_cpf_in_text
from config.settings import settings


def _payment_options_msg() -> str:
    discount_pct = int(settings.pix_discount_pct)
    return f"""*Formas de Pagamento:*
- PIX: {discount_pct}% de desconto exclusivo
- Link: Debito, Credito ou PIX

*Parcelamento:*
- R$200+ -> ate 4x sem juros
- R$1.000+ -> ate 8x (min. R$200/parcela)

Como deseja pagar?
*1* - PIX (com {discount_pct}% de desconto)
*2* - Link de Pagamento"""


CONFIRM_FINAL = """Pedido confirmado e encaminhado ao laboratório!

*Proximos Passos:*
1) Manipulacao com padroes de alta precisao
2) Notificacao quando o pedido for postado
3) Prazo estimado: *5 dias uteis*

Obrigado por escolher a *Nanofarmacos*!"""


async def node_f1_buscar(state: AgentState) -> AgentState:
    result = await crm_client.search_recipe(state["message"].strip())
    error = result.get("error")

    if error in {"session_expired", "unauthorized"}:
        return {
            **state,
            "response": (
                "Nao consegui acessar a base de receitas no momento. "
                "Vou transferir seu atendimento para um especialista humano continuar por aqui."
            ),
            "step": ConversationStep.AGUARDANDO_HUMANO,
        }

    if error in {"service_unavailable", "timeout", "upstream_unavailable"}:
        return {
            **state,
            "response": (
                "O sistema de receitas esta indisponivel no momento. "
                "Vou transferir seu atendimento para um especialista humano."
            ),
            "step": ConversationStep.AGUARDANDO_HUMANO,
        }

    if error == "recipe_expired":
        return {
            **state,
            "response": (
                "Esta receita esta expirada. Solicite uma nova receita ao seu medico "
                "e entre em contato novamente."
            ),
            "step": ConversationStep.INITIAL,
        }

    if error == "recipe_used":
        return {
            **state,
            "response": (
                "Esta receita ja foi utilizada anteriormente e nao pode ser reutilizada. "
                "Em caso de duvidas, entre em contato com nossa equipe."
            ),
            "step": ConversationStep.INITIAL,
        }

    if error == "recipe_cancelled":
        return {
            **state,
            "response": (
                "Esta receita foi cancelada. "
                "Entre em contato com seu medico para mais informacoes."
            ),
            "step": ConversationStep.INITIAL,
        }

    if error == "recipe_pending":
        return {
            **state,
            "response": (
                "Sua receita esta aguardando validacao do medico prescritor. "
                "Vou transferir para um especialista acompanhar sua situacao."
            ),
            "step": ConversationStep.AGUARDANDO_HUMANO,
        }

    if result.get("found") and result.get("recipe"):
        r = result["recipe"]

        # Mascara CPF antes de armazenar — nunca persiste dado sensível em claro
        recipe_stored = {
            **r,
            "cpf": mask_cpf(r.get("cpf", "")),
        }

        response = f"""Receita encontrada!

ID: {r['id']}
Paciente: {r['patient']}
Formula: {r['formula']}
Dosagem: {r['dosage']}

A receita esta correta?
*SIM* para confirmar | *NAO* para alterar"""

        # Salvaguarda: remove qualquer CPF que possa ter vindo em campos livres
        response = mask_cpf_in_text(response)

        return {
            **state,
            "response": response,
            "step": ConversationStep.F1_CONFIRMANDO_RECEITA,
            "user_data": {**state["user_data"], "recipe": recipe_stored},
        }

    return {
        **state,
        "response": "Nao encontramos receita com os dados informados. Verifique e tente novamente, ou entre em contato com nossa equipe.",
        "step": ConversationStep.F1_AGUARDANDO_ID,
    }


async def node_f1_confirmar(state: AgentState) -> AgentState:
    msg = state["message"].strip().upper()
    if msg == "SIM":
        return {**state, "response": _payment_options_msg(), "step": ConversationStep.F1_AGUARDANDO_PAGAMENTO}
    if msg in ("NAO", "NO", "NÃO"):
        return {
            **state,
            "response": "Entendido. Vou transferir para um especialista realizar as correcoes necessarias.\n\nAtendimento encerrado. Em caso de duvidas, entre em contato novamente.",
            "step": ConversationStep.INITIAL,
        }
    return {
        **state,
        "response": "Responda *SIM* para confirmar a receita ou *NAO* para solicitar alteracao.",
        "step": ConversationStep.F1_CONFIRMANDO_RECEITA,
    }


async def node_f1_pagamento(state: AgentState) -> AgentState:
    msg = state["message"].strip()
    if msg not in ("1", "2"):
        return {
            **state,
            "response": "Digite *1* para PIX ou *2* para Link de Pagamento.",
            "step": ConversationStep.F1_AGUARDANDO_PAGAMENTO,
        }

    payment_type = "PIX" if msg == "1" else "LINK"
    recipe = state["user_data"].get("recipe", {})

    # Usa o valor da receita (quando disponível) ou o padrão configurado em .env
    amount = float(state["user_data"].get("amount") or settings.payment_default_amount)

    result = await payment_client.create_charge(recipe.get("patient", ""), amount, payment_type)

    if result.get("error"):
        return {
            **state,
            "response": (
                "Nao foi possivel gerar o pagamento no momento. "
                "Vou transferir para um especialista continuar seu atendimento."
            ),
            "step": ConversationStep.AGUARDANDO_HUMANO,
        }

    if payment_type == "PIX":
        response = f"""PIX gerado!

Valor com desconto: R$ {result.get('amount', amount):.2f}

Codigo PIX:
{result.get('pix_code', '---')}

Apos pagar, envie o comprovante aqui."""
    else:
        response = f"""Link de pagamento gerado!

{result.get('payment_url', '---')}
Valor: R$ {result.get('amount', amount):.2f}

Apos pagar, envie o comprovante aqui."""

    return {
        **state,
        "response": response,
        "step": ConversationStep.F1_AGUARDANDO_COMPROVANTE,
        "user_data": {**state["user_data"], "payment_type": payment_type, "payment": result},
    }


async def node_f1_comprovante(state: AgentState) -> AgentState:
    recipe = state["user_data"].get("recipe", {})
    payment_type = state["user_data"].get("payment_type", "---")
    response = f"""Comprovante recebido!

Confirme o resumo do pedido:

Paciente: {recipe.get('patient', '---')}
ID: {recipe.get('id', '---')}
Pagamento: {'PIX (' + str(int(settings.pix_discount_pct)) + '% desconto)' if payment_type == 'PIX' else 'Link de Pagamento'}

Digite *CONFIRMAR* para enviar ao laboratorio.
Digite *ALTERAR* para corrigir algum dado."""
    return {**state, "response": response, "step": ConversationStep.F1_CONFIRMACAO_FINAL}


async def node_f1_finalizar(state: AgentState) -> AgentState:
    msg = state["message"].strip().upper()
    if msg == "CONFIRMAR":
        return {**state, "response": CONFIRM_FINAL, "step": ConversationStep.INITIAL}
    if msg == "ALTERAR":
        return {
            **state,
            "response": "Vou transferir para um especialista realizar as alteracoes.\n\nAtendimento encerrado.",
            "step": ConversationStep.INITIAL,
        }
    return {
        **state,
        "response": "Digite *CONFIRMAR* para finalizar ou *ALTERAR* para corrigir.",
        "step": ConversationStep.F1_CONFIRMACAO_FINAL,
    }
