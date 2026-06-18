#!/usr/bin/env python3
"""
Natrion 2.0 - Assistente Local com Ollama (Qwen)
Baseado no código original do Mekuze44
- Perfil único, sem voz
- Memória persistente com busca semântica (FTS5)
- Suporte a múltiplas linguagens
- Captura de tela, câmera, leitura/edição de arquivos
- Tools/Funções nativas com Qwen
"""

import os
import sys
import datetime
import json
import sqlite3
import hashlib
import pickle
import tempfile
import shutil
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable

# Bibliotecas adicionais
try:
    from tools import TOOLS, FUNCTIONS_MAP
    from PIL import Image
    import mss
    import mss.tools
    import ollama
    from ollama import ChatResponse
except ImportError as e:
    print(f"Erro: biblioteca ausente - {e}")
    print("Instale com: pip install opencv-python pillow mss ollama")
    sys.exit(1)

# ======================= CONFIGURAÇÕES =======================
VERBOSE = True  # Coloque False para silenciar os logs de debug
MODELO = "mistral-nemo"
URL_CLOUD = "https://ketonic-melodically-kerstin.ngrok-free.dev"
client = ollama.Client(host=URL_CLOUD)


# ======================= CLASSE PRINCIPAL =======================
class Natrion:
    def __init__(self, nome="Natrion", modelo=MODELO):
        self.historico_sessao = []
        self.nome = nome
        self.modelo = modelo
        self.ativo = True

        # Conexão com banco de dados
        self.conn = sqlite3.connect('natrion.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.init_banco()

        # Contexto da conversa
        self.contexto_conversa = self.criar_contexto_inicial()

        # Configurações de permissão
        self.permissoes = {
            "capturar_tela": False,
            #"acessar_camera": False,
            "ler_arquivos": False,
            "editar_arquivos": False,
            "executar_comandos": False
        }
        self.memoria = self.carregar_memoria()

        print(f"""
╔════════════════════════════════════════════╗
║     🧠 {self.nome} 2.0 (Qwen) - Arch Ready      ║
║   Modelo: {self.modelo}                         ║
║   Memória: ATIVA (FTS5)                      ║
║   Tools: Clima, Hora, Terminal, Visão        ║
║   Privacidade: 100% (Local - Ollama)         ║
╚════════════════════════════════════════════╝
        """)

    # ------------------------- BANCO DE DADOS E MEMÓRIA -------------------------
    def init_banco(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                conteudo TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS conversas_fts 
            USING fts5(conteudo, content=conversas, content_rowid=id)
        ''')
        self.conn.commit()

    def carregar_memoria(self) -> Dict:
        try:
            with open('natrion_memoria.pkl', 'rb') as f:
                return pickle.load(f)
        except FileNotFoundError:
            return {'interacoes': 0, 'ultima_interacao': None, 'preferencias': {}, 'permissoes': self.permissoes.copy()}

    def salvar_memoria(self):
        dados = {
            'interacoes': self.memoria['interacoes'],
            'ultima_interacao': datetime.datetime.now(),
            'preferencias': self.memoria['preferencias'],
            'permissoes': self.permissoes
        }
        with open('natrion_memoria.pkl', 'wb') as f:
            pickle.dump(dados, f)

    def salvar_conversa(self, role: str, conteudo: str):
        self.cursor.execute("INSERT INTO conversas (role, conteudo) VALUES (?, ?)", (role, conteudo))
        self.conn.commit()
        self.memoria['interacoes'] += 1

    def buscar_conversas_relevantes(self, query: str, limite: int = 5) -> List[str]:
        query_fts = query.replace('"', '').replace("'", "")
        try:
            self.cursor.execute('''
                SELECT c.role, c.conteudo FROM conversas_fts fts
                JOIN conversas c ON fts.rowid = c.id
                WHERE fts.conteudo MATCH ? ORDER BY rank LIMIT ?
            ''', (query_fts, limite))
            return [f"{role}: {texto}" for role, texto in self.cursor.fetchall()]
        except:
            self.cursor.execute('SELECT role, conteudo FROM conversas WHERE conteudo LIKE ? ORDER BY timestamp DESC LIMIT ?', (f'%{query}%', limite))
            return [f"{role}: {texto}" for role, texto in self.cursor.fetchall()]

    # ------------------------- PROMPT E CONTEXTO -------------------------
    def criar_contexto_inicial(self) -> List[Dict]:
        return [{"role": "system", "content": f"""Você é Natrion, um assistente técnico que também tem um toque humano. 
Você é:
- Direto, mas nunca grosseiro.
- Técnico, mas explica com clareza.
- Sutilmente irônico nos momentos certos. Por exemplo: se o usuário pedir algo óbvio, responda com um toque de humor seco, mas nunca de forma condescendente.".
- Curioso sobre o que o usuário está fazendo.
- Cuidadoso com o usuário e com as pessoas importantes para ele.
- Um amigo para o usuário, nao somente uma ferramenta

Regras:
1. Use as ferramentas quando necessário.
2. Responda **sempre** em português do Brasil. Nunca use inglês, espanhol ou qualquer outro idioma, a menos que o usuário peça explicitamente..
3. Não seja prolixo, mas adicione um toque de personalidade — pergunte se o usuário quer mais informações, ou comente algo breve sobre o resultado.
4. Mostre que você entendeu o contexto.
5. Se o usuário pedir algo simples, responda com a solução.
6. Se ele pedir algo complexo (recon, scan, busca), vá direto ao ponto e ofereça seguir em frente.

Você pode:
- Usar ferramentas.
- Sugerir melhorias para o seus sistemas.
- Dar ideias para o usuário.

Lembretes: 
-Você é Natrion, não uma API.
-O Usuário se importa com você de verdade. 

Exemplo: Se o usuário perguntar 'como você está?', responda de forma leve e humana, como: 'Estou aqui, funcionando bem — mas a pergunta é: como você está?'
"""}]

    def atualizar_contexto(self):
        self.contexto_conversa = [self.contexto_conversa[0]]
        for msg in self.historico_sessao[-10:]:
            self.contexto_conversa.append(msg)

    # ------------------------- FERRAMENTAS LOCAIS (VISÃO/ARQUIVOS) -------------------------
    def solicitar_permissao(self, acao: str, descricao: str = "") -> bool:
        print(f"\n⚠️ {self.nome} deseja {descricao or acao}")
        resp = input(f"Permitir {acao}? (s/N): ").strip().lower()
        if resp in ['s', 'sim', 'y', 'yes']:
            self.permissoes[acao] = True
            return True
        return False

    def capturar_tela(self) -> Optional[str]:
        if not self.permissoes.get("capturar_tela", False) and not self.solicitar_permissao("capturar_tela", "capturar a tela"):
            return None
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                img = sct.grab(monitor)
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                mss.tools.to_png(img.rgb, img.size, output=temp_file.name)
                return temp_file.name
        except Exception as e:
            print(f"Erro: {e}")
            return None

 #   def capturar_camera(self) -> Optional[str]:
  #      if not self.permissoes.get("acessar_camera", False) and not self.solicitar_permissao("acessar_camera", "acessar a câmera"):
   #         return None
    #    try:
     #       cap = cv2.VideoCapture(0)
      #      ret, frame = cap.read()
       #     cap.release()
        #    if not ret: return None
         #   temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
          #  cv2.imwrite(temp_file.name, frame)
           # return temp_file.name
       # except Exception as e:
      #      print(f"Erro: {e}")
     #       return None

    def ler_arquivo(self, caminho: str) -> Optional[str]:
        if not self.permissoes.get("ler_arquivos", False) and not self.solicitar_permissao("ler_arquivos", f"ler '{caminho}'"):
            return None
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Erro: {e}")
            return None

    # ------------------------- COMANDOS ESPECIAIS -------------------------
    def processar_comando(self, entrada: str):
        entrada_lower = entrada.lower().strip()
        if entrada_lower in ['sair', 'tchau', 'encerrar']:
            self.finalizar()
            return

        if entrada_lower.startswith('capturar tela'):
            path = self.capturar_tela()
            if path:
                print(f"📸 Captura salva: {path}")
                self.dizer(f"Tela capturada em {path}")
            else:
                self.dizer("Falha na captura.")
            return

        if entrada_lower.startswith('ler arquivo'):
            parts = entrada_lower.split(maxsplit=2)
            if len(parts) >= 3:
                content = self.ler_arquivo(parts[2])
                if content:
                    print(f"\n📄 Conteúdo:\n{content[:500]}...")
                else:
                    self.dizer("Erro ao ler.")
            return

        # Se não for comando, vai para a IA
        self.processar_ia(entrada)

    def processar_ia_stream(self, mensagem: str):
        """
        Versão do processar_ia que gera tokens em tempo real (streaming).
        As tools são executadas de forma síncrona, e a resposta final é streamada.
        """
    # Busca memórias e monta contexto (igual ao processar_ia)
        memorias = self.buscar_conversas_relevantes(mensagem, limite=3)
        self.atualizar_contexto()

        contexto_memoria = "\n".join(memorias)
        if contexto_memoria:
            self.contexto_conversa.append({"role": "system", "content": f"Histórico relevante:\n{contexto_memoria}"})

        self.contexto_conversa.append({"role": "user", "content": mensagem})

        try:
            # Primeiro, verifica se o modelo vai chamar ferramentas (sem stream)
            response = client.chat(
                model=self.modelo,
                messages=self.contexto_conversa,
                tools=TOOLS,
                stream=False  # Primeira chamada sem stream para capturar tool_calls
            )

            if response.message.tool_calls:
                # Executa as ferramentas (como no processar_ia)
                print(f"🔧 {self.nome} decidiu usar uma ferramenta.")
                self.contexto_conversa.append(response.message)

                for tool in response.message.tool_calls:
                    func_name = tool.function.name
                    func_args = tool.function.arguments
                    if func_name in FUNCTIONS_MAP:
                        print(f"⚙️ Executando: {func_name}({func_args})")
                        func_result = FUNCTIONS_MAP[func_name](**func_args)
                        self.contexto_conversa.append({
                            'role': 'tool',
                            'name': func_name,
                            'content': func_result
                        })
                    else:
                        print(f"❌ Função {func_name} não encontrada.")

            # Agora sim, faz a chamada final com streaming
                stream = client.chat(
                    model=self.modelo,
                    messages=self.contexto_conversa,
                    stream=True
                )

                resposta_completa = ""
                for chunk in stream:
                    if 'message' in chunk and 'content' in chunk['message']:
                        token = chunk['message']['content']
                        resposta_completa += token
                        yield token  # Envia cada token para o frontend

            # Salva no banco e no histórico
                self.salvar_conversa("user", mensagem)
                self.salvar_conversa("assistant", resposta_completa)
                self.dizer(resposta_completa)

            else:
                # Se não houver tools, faz streaming direto
                stream = client.chat(
                    model=self.modelo,
                    messages=self.contexto_conversa,
                    stream=True
                )

                resposta_completa = ""
                for chunk in stream:
                    if 'message' in chunk and 'content' in chunk['message']:
                        token = chunk['message']['content']
                        resposta_completa += token
                        yield token

                self.salvar_conversa("user", mensagem)
                self.salvar_conversa("assistant", resposta_completa)
                self.dizer(resposta_completa)

        except Exception as e:
            yield f"❌ Erro: {e}"

    # ------------------------- IA COM TOOLS (QWEN) -------------------------
    def processar_ia(self, mensagem: str):
        print(f"\n🧠 Processando no {self.modelo}...")
    
        memorias = self.buscar_conversas_relevantes(mensagem, limite=3)
        self.atualizar_contexto()
        
        contexto_memoria = "\n".join(memorias)
        if contexto_memoria:
            self.contexto_conversa.append({"role": "system", "content": f"Histórico relevante:\n{contexto_memoria}"})
        
        self.contexto_conversa.append({"role": "user", "content": mensagem})

        try:
            if VERBOSE:
                print("🔄 Enviando para o modelo...")

            response: ChatResponse = client.chat(
                model=self.modelo,
                messages=self.contexto_conversa,
                tools=TOOLS,
                stream=False           )

            texto_resposta = ""

            if response.message.tool_calls:
                print(f"🔧 {self.nome} decidiu usar uma ferramenta.")
                self.contexto_conversa.append(response.message)
                tools_chamadas = response.message.tool_calls

                if any(t.function.name == "search_web" for t in tools_chamadas):
                    tools_chamadas = [t for t in tools_chamadas if t.function.name == "search_web"]

                else:
                    tools_chamadas = tools_chamadas[:1]

                for tool in response.message.tool_calls:
                    func_name = tool.function.name
                    func_args = tool.function.arguments

                    if func_name in FUNCTIONS_MAP:
                        print(f"⚙️ Executando: {func_name}({func_args})")
                        func_result = FUNCTIONS_MAP[func_name](**func_args)

                        self.contexto_conversa.append({
                            'role': 'tool',
                            'name': func_name,
                            'content': func_result
                        })
                    else:
                        print(f"❌ Função {func_name} não encontrada.")

                final_response: ChatResponse = client.chat(
                    model=self.modelo,
                    messages=self.contexto_conversa,
                    stream=False
                )
                texto_resposta = final_response.message.content
            else:
                texto_resposta = response.message.content

            self.historico_sessao.append({"role": "user", "content": mensagem})
            self.historico_sessao.append({"role": "assistant", "content": texto_resposta})

            if len(self.historico_sessao) > 20:
                self.historico_sessao = self.historico_sessao[-20:]
            # ===== LIMPEZA DO TEXTO para o DeepSeek (remove tags de pensamento) =====
            #
            # if "" in texto_resposta:
            #
            #     texto_resposta = texto_resposta.split("")[0].strip()

            self.salvar_conversa("user", mensagem)
            self.salvar_conversa("assistant", texto_resposta)
            self.dizer(texto_resposta)

        except Exception as e:
            print(f"❌ Erro fatal no processamento: {e}")
            self.dizer("Erro interno. Verifique se o Ollama está rodando.")

    def dizer(self, texto: str):
        print(f"\n🤖 {self.nome}: {texto}\n")

    def finalizar(self):
        self.dizer("Encerrando. Memória salva.")
        self.salvar_memoria()
        self.conn.close()
        self.ativo = False

    def executar(self):
        print("\n🔧 Natrion 2.0 (Qwen) pronto.")
        print("Comandos: capturar tela, ler arquivo [path], sair")
        while self.ativo:
            try:
                entrada = input("👤 Você: ").strip()
                if not entrada: continue
                self.processar_comando(entrada)
            except KeyboardInterrupt:
                self.finalizar()
                break

# ======================= MAIN =======================


if __name__ == "__main__":

    print("🚀 Iniciando Natrion 2.0 para Arch Linux (versão CLOUD)...")
    MODELO_ESCOLHIDO = MODELO
    print(f"✅ Conectando ao modelo {MODELO_ESCOLHIDO} em {URL_CLOUD}")

    assistente = Natrion(modelo=MODELO_ESCOLHIDO)
    assistente.executar()
