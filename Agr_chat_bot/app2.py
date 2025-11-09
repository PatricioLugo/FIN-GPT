from flask import Flask, request, jsonify
import os
import sys

# agregar carpeta model al path
sys.path.append(os.path.join(os.path.dirname(__file__), 'model'))

from model.chatbot_model import FinancialChatbot
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)


class AdvancedFinancialAssistant:
    def __init__(self):
        # pon aquí la carpeta real de tu modelo
        self.model_path = "./"
        try:
            if os.path.exists(self.model_path):
                print("🎯 Cargando modelo fine-tuned...")
                self.chatbot = FinancialChatbot(self.model_path)
            else:
                print("⚠️ Modelo fine-tuned no encontrado, usando modelo base...")
                self.chatbot = FinancialChatbot()
        except Exception as e:
            print(f"❌ Error cargando el modelo: {e}")
            print("🔄 Usando modo de respuestas predefinidas...")
            self.chatbot = None

        self.user_sessions = {}

    def get_greeting(self):
        # devolvemos STRING, no dict
        message = "¡Hola! Soy tu asistente financiero agrícola. 🌱\n\nEstoy aquí para ayudarte con:"
        options = [
            "1. 📚 Educación financiera",
            "2. 💸 Realizar transferencias",
            "3. 🧮 Calcular mi perfil de crédito"
        ]
        return message + "\n\n" + "\n".join(options)
    
    def get_option_menu(self):
        # lo que quieres que salga cuando pones 1
        return (
            "Perfecto 👌 puedo ayudarte con:\n"
            "- ahorro\n"
            "- crédito\n"
            "- seguro\n"
            "- inversión\n\n"
            "Escríbeme una de esas palabras."
        )
    
    def handle_educational_request(self, user_message, user_id):
        if not self.chatbot:
            return self._get_fallback_response(user_message)

        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                "mode": "educational",
                "history": []
            }

        self.user_sessions[user_id]["history"].append(f"Usuario: {user_message}")

        prompt = self._build_educational_prompt(user_message, user_id)
        response = self.chatbot.generate_response(prompt, max_length=400)

        self.user_sessions[user_id]["history"].append(f"Asistente: {response}")

        if len(self.user_sessions[user_id]["history"]) > 6:
            self.user_sessions[user_id]["history"] = self.user_sessions[user_id]["history"][-6:]

        return response

    def _build_educational_prompt(self, user_message, user_id):
        session = self.user_sessions[user_id]
        history = "\n".join(session["history"][-4:])
        base_context = (
            "Eres un especialista en educación financiera para agricultores. "
            "Proporciona información práctica, clara y aplicable al contexto agrícola. "
            "Sé empático y alentador."
        )
        prompt = f"{base_context}\n\nHistorial:\n{history}\n\nUsuario: {user_message}\nAsistente:"
        return prompt

    def _get_fallback_response(self, user_message):
        fallback_responses = {
            "ahorro": "Para ahorrar como agricultor, te recomiendo separar al menos el 10% de cada venta. Crea un fondo para emergencias y otro para inversiones en tu tierra.",
            "crédito": "Los créditos agrícolas suelen requerir: historial de producción, plan de negocio y garantías. Existen créditos de avío para insumos y refaccionarios para inversiones.",
            "seguro": "Los seguros agrícolas protegen contra pérdidas por clima y plagas. Consulta con tu cooperativa sobre seguros de cosecha y de ingresos.",
            "inversión": "Invertir en agricultura puede incluir: mejoras en riego, maquinaria eficiente, o diversificación de cultivos. Comienza con inversiones pequeñas y escalables."
        }
        for keyword, response in fallback_responses.items():
            if keyword in user_message.lower():
                return response

        return "Puedo ayudarte con ahorro, créditos, seguros e inversiones. ¿Sobre qué tema quieres saber?"

    def handle_transfer_request(self, user_message):
        return "⏳ La funcionalidad de transferencias estará disponible pronto."

    def handle_calculator_request(self, user_message):
        return "⏳ La calculadora de créditos estará disponible en la próxima actualización."


assistant = AdvancedFinancialAssistant()


@app.route('/')
def home():
    return jsonify({
        "status": "Chatbot Financiero Agrícola activo",
        "version": "1.0",
        "modes": ["Educación financiera", "Transferencias", "Calculadora de créditos"]
    })


@app.route('/chat', methods=['POST'])
def chat():
    try:
        # 1. Intentar JSON
        data = request.get_json(silent=True)

        if data:
            user_message = data.get('message', '').strip()
            user_id = data.get('user_id', 'default_user')
            twilio_mode = False
        else:
            # 2. Twilio (form)
            user_message = (request.values.get('Body') or '').strip()
            user_id = request.values.get('From', 'twilio_user')
            twilio_mode = True

        print(f"📨 Mensaje recibido de {user_id}: {user_message}")

        # mensaje vacío o saludo
        if not user_message or user_message.lower() in ['hola', 'hi', 'inicio', 'start']:
            greeting = assistant.get_greeting()
            if twilio_mode:
                resp = MessagingResponse()
                resp.message(greeting)          # 👈 ahora sí es string
                return str(resp), 200, {'Content-Type': 'application/xml'}
            else:
                return jsonify({"response": greeting})

        # flujo
        text = user_message.lower()
        if any(k in text for k in ['1', 'aprender', 'educación', 'finanza', 'ahorro', 'inversión']):
            bot_response = assistant.handle_educational_request(user_message, user_id)
        elif any(k in text for k in ['2', 'transferencia', 'transferir', 'pago']):
            bot_response = assistant.handle_transfer_request(user_message)
        elif any(k in text for k in ['3', 'calculadora', 'crédito', 'calcular', 'préstamo']):
            bot_response = assistant.handle_calculator_request(user_message)
        else:
            bot_response = assistant.handle_educational_request(user_message, user_id)

        if twilio_mode:
            resp = MessagingResponse()
            resp.message(bot_response)
            return str(resp), 200, {'Content-Type': 'application/xml'}
        else:
            return jsonify({
                "response": bot_response,
                "session_id": user_id
            })

    except Exception as e:
        print(f"❌ Error en /chat: {e}")
        return jsonify({
            "response": "Lo siento, hubo un error procesando tu mensaje.",
            "error": str(e)
        }), 500


@app.route('/reset', methods=['POST'])
def reset_chat():
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id', 'default_user')

        if user_id in assistant.user_sessions:
            del assistant.user_sessions[user_id]

        return jsonify({
            "message": "Conversación reiniciada",
            "session_id": user_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    print("🌱 Iniciando Chatbot Financiero Agrícola...")
    print("📍 Servidor disponible en: http://localhost:5000")
    print("📚 Endpoints disponibles:")
    print("   POST /chat")
    print("   POST /reset")
    print("   GET  /")
    app.run(debug=True, host='0.0.0.0', port=5000)
