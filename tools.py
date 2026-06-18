import requests
import json
import datetime
from ddgs import DDGS
import subprocess


def listar_ferramentas() -> str:
    """Retorna a lista de ferramentas disponíveis (dinâmica)"""
    ferramentas = []
    for tool in TOOLS:
        ferramentas.append({
            "name": tool["function"]["name"],
            "description": tool["function"]["description"]
        })
    return json.dumps(ferramentas, indent=2, ensure_ascii=False)


def search_web(query: str) -> str:
    """
    Busca na web (implementação simples com DuckDuckGo)
    Requer `pip install duckduckgo-search`
    """
    try:
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
        response = requests.get(url, timeout=5)
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

# ---------- WHOIS ----------


def whois_lookup(domain: str) -> str:
    try:
        import whois
        w = whois.whois(domain)
        info = {
            "domain": w.domain_name,
            "registrar": w.registrar,
            "creation": str(w.creation_date),
            "expiration": str(w.expiration_date),
            "name_servers": w.name_servers,
            "emails": w.emails,
            "org": w.org,
        }
        return json.dumps(info, indent=2, default=str)
    except ImportError:
        return "Erro: biblioteca python-whois não instalada. Execute: pip install python-whois"
    except Exception as e:
        return f"Erro no WHOIS: {e}"

# ---------- SUBDOMÍNIOS (sublist3r) ----------


def subdomain_enum(domain: str) -> str:
    try:
        cmd = f"sublist3r -d {domain} --no-errors"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            subdomains = [line.strip() for line in lines if '.' in line and not line.startswith('[-]')]
            if subdomains:
                return "\n".join(subdomains[:20])
            return "Nenhum subdomínio encontrado."
        else:
            return f"Erro no sublist3r: {result.stderr}"
    except FileNotFoundError:
        return "Erro: sublist3r não está instalado. Instale com: pip install sublist3r"
    except Exception as e:
        return f"Erro: {e}"

# ---------- PORT SCAN (nmap) ----------


def port_scan_light(host: str) -> str:
    try:
        import nmap
        nm = nmap.PortScanner()
        nm.scan(host, arguments='-T4 -F')
        open_ports = []
        if host in nm.all_hosts():
            for proto in nm[host].all_protocols():
                for port in nm[host][proto].keys():
                    if nm[host][proto][port]['state'] == 'open':
                        open_ports.append(f"{port}/{proto}")
        if open_ports:
            return "Portas abertas: " + ", ".join(open_ports)
        return "Nenhuma porta aberta encontrada."
    except ImportError:
        return "Erro: python-nmap não instalado. Execute: pip install python-nmap"
    except Exception as e:
        return f"Erro no scan: {e}"

# ---------- RECON COMPLETO ----------


def recon_completo(domain: str) -> str:
    """Executa WHOIS, subdomínios e portas em sequência"""
    resultados = []
    resultados.append("=== WHOIS ===\n" + whois_lookup(domain))
    resultados.append("\n=== SUBDOMÍNIOS ===\n" + subdomain_enum(domain))
    resultados.append("\n=== PORTAS ===\n" + port_scan_light(domain))
    return "\n".join(resultados)

# Mapeamento de ferramentas no formato específico para Qwen/Modelos Gerais


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Obtem o clima de uma cidade",
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
            "description": "Executa comandos no terminal Linux(use com moderação).",
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
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "functions_list",
            "description": "Use esta ferramenta SEMPRE que o usuário perguntar sobre suas ferramentas, capacidades, o que você pode fazer, ou funcionalidades. NUNCA responda a essas perguntas com texto — use esta ferramenta.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        
        "type": "function",
        "function": {
            "name": "whois_lookup",
            "description": "Consulta informações WHOIS de um domínio (registrante, datas, servidores DNS)",
            "parameters": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]}
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subdomain_enum",
            "description": "Enumera subdomínios de um domínio usando sublist3r",
            "parameters": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]}
        },
    },
    {
        "type": "function",
        "function": {
            "name": "port_scan_light",
            "description": "Escaneia portas comuns (rápido) de um host",
            "parameters": {"type": "object", "properties": {"host": {"type": "string"}}, "required": ["host"]}
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recon_completo",
            "description": "Executa reconhecimento completo (WHOIS, subdomínios, portas) de um domínio. Pode demorar alguns segundos.",
            "parameters": {"type": "object", "properties": {"domain": {"type": "string"}}, "required": ["domain"]}
        },
    },
]


# Mapeamento nome_da_funcao -> função real
FUNCTIONS_MAP = {
    "get_current_weather": get_current_weather,
    "get_current_time": get_current_time,
    "search_web": search_web,
    "run_terminal_command": run_terminal_command,
    "functions_list": listar_ferramentas,
    "whois_lookup": whois_lookup,
    "subdomain_enum": subdomain_enum,
    "port_scan_light": port_scan_light,
    "recon_completo": recon_completo,
}
