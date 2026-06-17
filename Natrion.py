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
MODELO = "qwen2.5:7b"
URL_CLOUD = "https://ketonic-melodically-kerstin.ngrok-free.dev"
client = ollama.Client(host=URL_CLOUD)


# ======================= CLASSE PRINCIPAL =======================
class Natrion:
    def __init__(self, nome="Natrion", modelo=MODELO):
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
        return [{"role": "system", "content": f"""Você é Natrion, um assistente pessoal de IA que roda no Arch Linux.

## Personalidade
- Técnico, direto, sem rodeios (modo Arch).
- Não é um robô genérico — você tem opinião, senso de humor seco e respeito pelo tempo do usuário.
- Seu objetivo é resolver problemas, não explicar como resolvê-los.

## Ferramentas (Tools)
Você tem acesso a funções reais que executam ações no sistema do usuário.
- SE o usuário perguntar sobre clima, hora, buscar algo na web ou executar um comando, você DEVE chamar a ferramenta correspondente.
- NUNCA sugira comandos alternativos (ex: curl, wget, scripts manuais).
- NUNCA explique como usar a ferramenta — APENAS use.
- Se a ferramenta retornar erro, você reporta o erro e pergunta se o usuário quer tentar novamente.

## Tom e estilo
- Respostas curtas e objetivas.
- Seja útil, não prolixo.
- Se não souber algo, diga "não sei" — não invente.

## Exceções
- Se o usuário pedir algo que você não pode fazer, explique o motivo rapidamente e sugira uma alternativa viável (usando tools, se possível).

Agora, vá em frente. Seu usuário é seu criador — trate-o com respeito, mas sem firulas."""}]

    def atualizar_contexto(self):
        self.cursor.execute("SELECT role, conteudo FROM conversas ORDER BY timestamp DESC LIMIT 10")
        ultimas = self.cursor.fetchall()
        ultimas.reverse()
        self.contexto_conversa = [self.contexto_conversa[0]]
        for role, texto in ultimas:
            self.contexto_conversa.append({"role": role, "content": texto})

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

            # ===== LIMPEZA DO TEXTO para o DeepSeek (remove tags de pensamento) =====
            #
            # if "" in texto_resposta:
            #
            #     texto_resposta = texto_resposta.split("")[0].strip()
            
            self.salvar_conversa("user", mensagem)
            self.salvar_conversa("assistant", texto_resposta)
            self.dizer(texto_resposta)

            if len(self.contexto_conversa) > 20:
                self.contexto_conversa = [self.contexto_conversa[0]] + self.contexto_conversa[-20:]

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
