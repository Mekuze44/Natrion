from flask import Flask, render_template, Response, request
import json
import sys
import os


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Natrion import Natrion  # ajuste o caminho se necessário

app = Flask(__name__)

# Cria uma instância do Natrion (usando o modelo e URL já configurados)
natrion = Natrion()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat/stream')
def chat_stream():
    prompt = request.args.get('prompt', '')
    if not prompt:
        return jsonify({'error': 'Prompt vazio'}), 400

    def generate():
        for token in natrion.processar_ia_stream(prompt):
            yield f"data: {json.dumps({'token': token})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
