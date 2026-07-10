import os

from langchain.agents import create_agent
from langchain_ollama import ChatOllama

from my_agent.utils.nodes import get_orchestrator_prompt
from my_agent.utils.state import scaffold_project_structure
from my_agent.utils.tools import build_tools


def build_graph():
    """Build and return the compiled LangChain agent graph."""
    base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    coder_model = os.getenv("OLLAMA_CODER", "qwen2.5-coder:7b")
    output_dir = os.getenv("OUTPUT_DIR", "/ai-generated-code")

    os.makedirs(output_dir, exist_ok=True)
    scaffold_project_structure(output_dir)

    coder_llm = ChatOllama(
        base_url=base_url,
        model=coder_model,
        temperature=0,
    )
    orchestrator_llm = ChatOllama(
        base_url=base_url,
        model=model,
        temperature=0,
    )

    tools = build_tools(coder_llm=coder_llm, output_dir=output_dir)

    return create_agent(
        orchestrator_llm,
        tools=tools,
        system_prompt=get_orchestrator_prompt(),
        debug=True,
    )


graph = build_graph()
