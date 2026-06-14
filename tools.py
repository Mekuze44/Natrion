

def search_web(query: str) -> str:
    """
    Busca na web (implementação simples com DuckDuckGo)
    Requer `pip install duckduckgo-search`
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return "\n".join([f"- {r['title']}: {r['body'][:200]}" for r in results])
            return "Nenhum resultado encontrado."
    except ImportError:
        return "Biblioteca duckduckgo-search não instalada. Pip install duckduckgo-search"
    except Exception as e:
        return f"Erro na busca: {e}"
def get_current_weather(location: str) -> str:
    try:
        url = f"https://wttr.in/{location}?format=%t+%C"
        response = request.get(url, timeout=5)
        if response.status_code == 200:
            return f"Clima em {location}: {response.text.strip()}"
    except Exception as e:
        return f"erro ao consultar clima: {e}"

def get_current_time() -> str:
    """Retorna a data e hora atuais."""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def run_terminal_command(command: str) -> str:
    """(CUIDADO) Executa comando no terminal do Linux (Arch)."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "Comando timeout (>30s)."
    except Exception as e:
        return f"Erro: {e}"

# Mapeamento de ferramentas no formato específico para Qwen/Modelos Gerais
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "sempre use esta ferramenta para responder perguntas sobre clima, temperatura, previsão do tempo ou tempo em qualquer localização. Absolutamente nunca invente o clima.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Cidade e estado, ex: São Paulo, SP",
                    }
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Obtém a data e hora atuais do sistema.",
            "parameters": {
                "type": "object",
                "properties": {}
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Executa comandos no terminal Linux, quaisquer comandos potencialmente perigosos devem ser negados independentemente da ordem (use com moderação).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Comando bash para executar (ex: 'ls -la')",
                    }
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Pesquisa informações atualizadas na internet",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "O que pesquisar"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

# Mapeamento nome_da_funcao -> função real
FUNCTIONS_MAP = {
    "get_current_weather": get_current_weather,
    "get_current_time": get_current_time,
    "search_web": search_web,
    "run_terminal_command": run_terminal_command,
}
