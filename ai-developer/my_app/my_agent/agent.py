import os


from my_agent.utils.state import scaffold_project_structure
from my_agent.utils.tools import build_tools

from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import TodoListMiddleware, ModelCallLimitMiddleware
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from my_agent.utils.nodes import ORCHESTRATOR_PROMPT

def orchestration_factory(model, base_url):
    if model == "ollama":
        return ChatOllama(
            base_url=base_url,
            model=model,
            temperature=0,
        )
    else:
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=1.0,  # Gemini 3.0+ defaults to 1.0
            max_tokens=None,
            google_api_key=os.environ["GOOGLE_API_KEY"],
            timeout=None,
            max_retries=2,
            # other params...
        )


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


    tools = build_tools(coder_llm=coder_llm, output_dir=output_dir)

    return create_agent(
        orchestration_factory("", base_url),
        tools=tools,
        system_prompt=ORCHESTRATOR_PROMPT,
        debug=True,
        middleware=[
            # ModelCallLimitMiddleware(run_limit=5),
            TodoListMiddleware(),
            FilesystemMiddleware(
                backend=FilesystemBackend(
                    root_dir=output_dir,
                    virtual_mode=True,
                ),
            ),
        ],
    )


graph = build_graph()
