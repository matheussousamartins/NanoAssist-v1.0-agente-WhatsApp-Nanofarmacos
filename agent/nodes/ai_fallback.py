from pathlib import Path
from loguru import logger
from agent.state import AgentState
from config.settings import settings

SYSTEM_PROMPT = Path("prompts/system_prompt.md").read_text()

async def node_ai_fallback(state: AgentState) -> AgentState:
    try:
        if settings.anthropic_api_key:
            from langchain_anthropic import ChatAnthropic
            from langchain_core.messages import HumanMessage, SystemMessage
            llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=400,
                                api_key=settings.anthropic_api_key)
        elif settings.openai_api_key:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import HumanMessage, SystemMessage
            llm = ChatOpenAI(model="gpt-4o", max_tokens=400,
                             api_key=settings.openai_api_key)
        else:
            return {**state, "response": "Não consegui processar sua solicitação. Por favor, aguarde atendimento humano."}

        from langchain_core.messages import HumanMessage, SystemMessage
        result = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=state["message"])
        ])
        return {**state, "response": result.content}
    except Exception as e:
        logger.error(f"AI fallback error: {e}")
        return {**state, "response": "Não consegui processar sua solicitação. Por favor, aguarde atendimento humano."}
