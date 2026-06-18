# 🧠 Natrion — Assistente Pessoal com IA Local

**Natrion** é um assistente pessoal de IA que roda **100% local** (ou na nuvem, se preferir), com suporte a **ferramentas reais** (clima, hora, busca, reconhecimento de sites, terminal) e uma **interface web moderna com streaming**.

Ele foi construído para ser rápido, estável, com personalidade e sem depender de APIs pagas.

---

## ✨ Funcionalidades

| Categoria | Ferramentas |
|-----------|-------------|
| **🌤️ Clima** | Consulta em tempo real via `wttr.in` |
| **🕒 Hora** | Data e hora atuais do sistema |
| **🔍 Busca** | Pesquisa na web com DuckDuckGo |
| **💻 Terminal** | Execução de comandos (simulado ou real) |
| **🌐 Reconhecimento** | WHOIS, subdomínios, scan de portas, recon completo |
| **🧠 Memória** | Persistente com SQLite + FTS5 (busca semântica) |
| **🎨 Interface** | Web com streaming (SSE), design moderno e responsivo |
| **🎭 Personalidade** | Técnica, direta, com toque humano e em português |
| **🛠️ Extensível** | Fácil adicionar novas ferramentas |

---

## 🧪 Modelos Suportados

| Modelo | Suporte a Tools | Velocidade | Recomendação |
|--------|----------------|------------|--------------|
| **Mistral-Nemo** | ✅ Nativo | 🚀 Rápido | **Recomendado** |
| Qwen 2.5 7B | ✅ Nativo | 🟡 Médio | Alternativa estável |
| Llama 3.2 3B | ✅ Nativo | 🚀 Rápido | Para máquinas leves |
| DeepSeek-R1 8B | ⚠️ Limitado | 🔴 Lento | Não recomendado |

---

## 📦 Requisitos

- Python 3.10+
- [Ollama](https://ollama.com) instalado e rodando (local ou remoto)
- (Opcional) Ngrok para expor o servidor
- Dependências Python (veja `requirements.txt`)

---

## 🚀 Instalação e Execução

### 1. Clone o repositório

```bash
git clone https://github.com/Mekuze44/Natrion.git
cd Natrion
```

2. Crie um ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. Instale as dependências

```bash
pip install -r requirements.txt
```

4. Baixe um modelo (ex: Mistral-Nemo)

```bash
ollama pull mistral-nemo
```

5. Configure a URL do Ollama

No arquivo Natrion.py, ajuste:

```python
URL_CLOUD = "http://localhost:11434"  # ou URL do túnel (Colab/Ngrok)
MODELO = "mistral-nemo"
```

6. Execute o Natrion (terminal)

```bash
python Natrion.py
```

7. (Opcional) Execute a interface web

```bash
python app.py
```

Acesse http://localhost:5000 no navegador.

---

🛠️ Estrutura do Projeto

```
Natrion/
├── Natrion.py           # Classe principal do assistente
├── app.py               # Interface web com streaming
├── tools.py             # Ferramentas (clima, hora, recon, etc.)
├── tools_recon.py       # Ferramentas de reconhecimento
├── requirements.txt     # Dependências Python
├── templates/
│   └── index.html       # Frontend da interface web
└── README.md            # Este arquivo
```

---

🧩 Como Adicionar uma Nova Ferramenta

1. Defina a função em tools.py (ou em um módulo separado).
2. Adicione a ferramenta à lista TOOLS (com nome, descrição e parâmetros).
3. Adicione o mapeamento em FUNCTIONS_MAP.
4. Reinicie o Natrion.

Exemplo:

```python
def minha_tool(param: str) -> str:
    return f"Resultado: {param}"

TOOLS.append({
    "type": "function",
    "function": {
        "name": "minha_tool",
        "description": "Faz algo útil",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {"type": "string"}
            },
            "required": ["param"]
        }
    }
})

FUNCTIONS_MAP["minha_tool"] = minha_tool
```

---

🌐 Interface Web

A interface web usa Flask + Server-Sent Events (SSE) para streaming de respostas.

· Design moderno, responsivo e com tema escuro.
· Indicador de digitação.
· Mensagens com balões distintos para usuário e Natrion.

---

📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

---

🙌 Agradecimentos

· Ollama pela infraestrutura local de LLMs.
· Mistral AI pelo modelo mistral-nemo.
· A você, que está usando e contribuindo para o Natrion.

---

Feito com 🧠 e ☕ por Mekuze44

```

---