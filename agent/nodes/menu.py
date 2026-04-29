from agent.state import AgentState, ConversationStep

GREETING = """Olá! Eu sou o *NanoAssist*, assistente virtual da *Nanofármacos*. 🌿

Para agilizarmos seu atendimento, escolha uma opção:

*1️⃣* - Já possuo receita na plataforma e desejo realizar o pedido.
*2️⃣* - Desejo solicitar um novo orçamento.

Digite 1 ou 2."""

INVALID_OPTION = """Opção inválida. Por favor, digite *1* ou *2* para continuar.

*1️⃣* - Receita na plataforma
*2️⃣* - Novo orçamento"""

ASK_ID = """Para localizar sua formulação, informe um dos dados abaixo:

📋 *ID da Receita*
🪪 *CPF do Titular*
👤 *Nome Completo Cadastrado*"""

ASK_DATA = """Para elaborar seu orçamento, envie os dados abaixo em *uma mensagem* e anexe a *receita em PDF*:

━━━━━━━━━━━━━━━
👤 *Nome:*
🎂 *Idade:*
⚖️ *Peso (kg):*
📏 *Altura (cm):*
🪪 *CPF:*
📧 *E-mail:*
📱 *Celular:*
📮 *CEP:*
🏠 *Endereço (Rua, Nº):*
🏘️ *Bairro:*
🏢 *Complemento:*
🌆 *Cidade:*
🗺️ *Estado (UF):*
━━━━━━━━━━━━━━━"""

async def node_menu(state: AgentState) -> AgentState:
    step = state["step"]
    msg = state["message"].strip()

    if step == ConversationStep.INITIAL:
        return {**state, "response": GREETING, "step": ConversationStep.MENU}

    if step == ConversationStep.MENU:
        if msg == "1":
            return {**state, "response": ASK_ID, "step": ConversationStep.F1_AGUARDANDO_ID}
        elif msg == "2":
            return {**state, "response": ASK_DATA, "step": ConversationStep.F2_COLETANDO_DADOS}
        else:
            return {**state, "response": INVALID_OPTION, "step": ConversationStep.MENU}

    return state
