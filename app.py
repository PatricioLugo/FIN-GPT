import json
import os
import sys
from flask import Flask, request, jsonify, Response
from twilio.twiml.messaging_response import MessagingResponse
import datetime  
import pandas as pd
import joblib 
from model.chatbot_model import FinancialChatbot

app = Flask(__name__)

MAP_UBICACION = {
    'Chiapas': 0, 'Puebla': 1, 'Guanajuato': 2, 'Sonora': 3, 'Jalisco': 4,
    'Veracruz': 5, 'Oaxaca': 6, 'Michoacan': 7, 'Sinaloa': 8, 'Hidalgo': 9,
    'Ciudad de México': 10, 'Nuevo León' : 11, 'Guerrero': 12, 'Tamaulipas':13,
    'Zacatecas': 14, 'San Luis Potosí': 15, 'Nayarit': 16, 'Otros': 17
}
MAP_TIPO_NEGOCIO = {
    'Ganaderia - Aves': 0, 'Otras actividades pecuarias': 1, 'Hortalizas': 2,
    'Granos': 3, 'Ganaderia - Bovinos': 4, 'Frutales': 5, 'Ganaderia - Porcinos': 6,
    'Cultivos industriales/perennes': 7, 'Agricultura mixta': 8, 'Servicios y transformacion': 9
}
MAP_TAMANO_OPERACION = {'Pequeño': 0, 'Mediano': 1, 'Grande': 2}
MAP_FRECUENCIA_INGRESOS = {'Constante': 0, 'Estacional': 1}
MAP_ESCOLARIDAD = {
    'Primaria': 0, 'Secundaria': 1, 'Preparatoria': 2,
    'Universidad': 3, 'Sin estudios': 4
}
MAP_SCORE_NAMES = {0: 'Bueno', 1: 'Regular', 2: 'Malo'}
SCORING_FEATURES_ORDER = [
    'Edad', 'Ubicacion_Estado', 'Dependientes_Economicos', 'Tipo_Negocio',
    'Tamano_Hectareas', 'Tamano_Operacion', 'Frecuencia_Ingresos',
    'Ingresos_Anuales_Estimados', 'Escolaridad', 'Anos_Experiencia',
    'Score_Buro_Credito'
]
SCORING_QUESTIONS = [
    {'key': 'Edad', 'question': '1/11: ¿Cuál es tu edad?', 'type': 'numeric'},
    {'key': 'Ubicacion_Estado', 'question': '2/11: ¿En qué estado vives?',
     'type': 'categorical', 'options': MAP_UBICACION},
    {'key': 'Dependientes_Economicos', 'question': '3/11: ¿Cuántas personas dependen económicamente de ti?', 'type': 'numeric'},
    {'key': 'Tipo_Negocio', 'question': '4/11: ¿Cuál es tu principal actividad?',
     'type': 'categorical', 'options': MAP_TIPO_NEGOCIO},
    {'key': 'Tamano_Hectareas', 'question': '5/11: ¿Cuántas hectáreas trabajas?', 'type': 'numeric'},
    {'key': 'Tamano_Operacion', 'question': '6/11: ¿Consideras tu operación Pequeña, Mediana o Grande?',
     'type': 'categorical', 'options': MAP_TAMANO_OPERACION},
    {'key': 'Frecuencia_Ingresos', 'question': '7/11: ¿Tus ingresos son todo el año (Constante) o solo por temporadas (Estacional)?',
     'type': 'categorical', 'options': MAP_FRECUENCIA_INGRESOS},
    {'key': 'Ingresos_Anuales_Estimados', 'question': '8/11: ¿Cuál es tu ingreso anual estimado? (Escribe solo el número, ej. 50000)', 'type': 'numeric'},
    {'key': 'Escolaridad', 'question': '9/11: ¿Cuál es tu último nivel de estudios?',
     'type': 'categorical', 'options': MAP_ESCOLARIDAD},
    {'key': 'Anos_Experiencia', 'question': '10/11: ¿Cuántos años de experiencia tienes en el campo?', 'type': 'numeric'},
    {'key': 'Score_Buro_Credito',
     'question': "11/11: ¿Sabes tu Score de Buró de Crédito actual? (Escribe el número, o 'No' si no lo sabes)",
     'type': 'buro_special'}
]

class AdvancedFinancialAssistant:

    def __init__(self):

        self.model_path = "./fine-tuned-financial-chatbot" 
        self.prototype_path = "./prototype-chatbot"
        try:
            if os.path.exists(self.model_path):
                print(f"Cargando modelo de IA desde: {self.model_path}")
                self.chatbot = FinancialChatbot(self.model_path)
            elif os.path.exists(self.prototype_path):
                print(f"Modelo  no encontrado. Usando PROTOTIPO desde: {self.prototype_path}")
                self.chatbot = FinancialChatbot(self.prototype_path)
            else:
                print("Ni CALIDAD ni PROTOTIPO encontrados. Usando modelo BASE.")
                self.chatbot = FinancialChatbot()
        except Exception as e:
            print(f"❌ Error cargando modelo de IA: {e}")
            self.chatbot = None


        self.scoring_model_path = "credit_scoring_model.pkl"
        try:
            self.scoring_model = joblib.load(self.scoring_model_path)
            print(f"🎯 Cargando modelo de SCORING desde: {self.scoring_model_path}")
        except FileNotFoundError:
            print(f"❌ ERROR: Modelo de SCORING '{self.scoring_model_path}' no encontrado.")
            self.scoring_model = None
        except Exception as e:
            print(f"❌ Error cargando modelo de SCORING: {e}")
            self.scoring_model = None


        self.ACCOUNTS = {
            "ACC001": {"holder": "Sergio Rock", "balance": 1000.00},
            "ACC002": {"holder": "Emilio Pinelo", "balance": 500.00}
        }
        
        self.user_sessions = {}

    def get_greeting(self):

        message = "¡Hola! Soy tu asistente financiero agrícola. 🌱\n\nEstoy aquí para ayudarte con:"
        options = [
            "1.  Educación financiera",
            "2.  Realizar transferencias",
            "3.  Calcular mi perfil de crédito"
        ]
        return message + "\n\n" + "\n".join(options)

    def handle_educational_request(self, user_message, user_id):
        if not self.chatbot: return self._get_fallback_response(user_message)
        if user_id not in self.user_sessions or self.user_sessions[user_id].get('mode') != 'educational':
            self.user_sessions[user_id] = {"mode": "educational", "history": []}
        self.user_sessions[user_id]["history"].append(f"Usuario: {user_message}")
        prompt_message = user_message
        
        if user_message.strip() == '1': 
            prompt_message = "Háblame de educación financiera"
            
        prompt = self._build_educational_prompt(prompt_message, user_id)
        response = self.chatbot.generate_response(prompt, max_length=400)
        self.user_sessions[user_id]["history"].append(f"Asistente: {response}")
        return response

    def _build_educational_prompt(self, user_message, user_id):
        session = self.user_sessions[user_id]
        history = "\n".join(session["history"][-4:])
        base_context = "Eres un especialista en educación financiera para agricultores..."
        prompt = f"{base_context}\n\nHistorial:\n{history}\n\nUsuario: {user_message}\nAsistente:"
        return prompt

    def _get_fallback_response(self, user_message):
        return "Como asistente financiero agrílogo, puedo ayudarte con..."

    def _format_question(self, question_data):
        question_text = question_data['question']
        if question_data['type'] == 'categorical':
            options_list = [f"{i + 1}. {name}" for i, name in enumerate(question_data['options'].keys())]
            question_text += "\n\n" + "\n".join(options_list)
            question_text += "\n\nResponde solo con el número de la opción."
        return question_text

    def start_scoring_flow(self, user_id):
        if not self.scoring_model:
            return "Lo siento, el servicio de cálculo de crédito no está disponible."
        self.user_sessions[user_id] = {'mode': 'scoring', 'step': 0, 'answers': {}}
        return self._format_question(SCORING_QUESTIONS[0])

    def handle_scoring_flow(self, user_answer, user_id):
        session = self.user_sessions.get(user_id)
        if not session or session.get('mode') != 'scoring': return self.get_greeting()
        
        if user_answer.lower() in ['cancelar', 'salir', 'menu', 'exit']:
            self.user_sessions[user_id] = {"mode": "educational", "history": []}
            return "Cálculo de perfil cancelado. Volviendo al menú principal."
        
        current_step = session['step']
        question_data = SCORING_QUESTIONS[current_step]
        key_to_save = question_data['key']
        
        try:
            if question_data['type'] == 'numeric':
                float(user_answer)
                session['answers'][key_to_save] = user_answer
            elif question_data['type'] == 'categorical':
                choice_index = int(user_answer) - 1
                options_list = list(question_data['options'].keys())
                if 0 <= choice_index < len(options_list):
                    session['answers'][key_to_save] = options_list[choice_index]
                else:
                    return "Opción no válida.\n\n" + self._format_question(question_data)
            elif question_data['type'] == 'buro_special':
                if user_answer.lower() == 'no':
                    session['answers'][key_to_save] = -1
                else:
                    float(user_answer)
                    session['answers'][key_to_save] = user_answer
        except ValueError:
            return "Respuesta inválida.\n\n" + self._format_question(question_data)
        
        # Siguiente paso
        session['step'] += 1
        if session['step'] >= len(SCORING_QUESTIONS):
            print(f"Respuestas completas de {user_id}: {session['answers']}")
            response_text = self.get_credit_score(session['answers'])
            self.user_sessions[user_id] = {"mode": "educational", "history": []}
        else:
            response_text = self._format_question(SCORING_QUESTIONS[session['step']])
        return response_text

    def get_credit_score(self, answers_dict):
        if not self.scoring_model: return "Error: El modelo de scoring no está cargado."
        try:
            df = pd.DataFrame([answers_dict])
            num_cols = ['Edad', 'Dependientes_Economicos', 'Tamano_Hectareas', 'Ingresos_Anuales_Estimados', 'Anos_Experiencia', 'Score_Buro_Credito']
            for col in num_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            df['Ubicacion_Estado'] = df['Ubicacion_Estado'].map(MAP_UBICACION).fillna(-1)
            df['Tipo_Negocio'] = df['Tipo_Negocio'].map(MAP_TIPO_NEGOCIO).fillna(-1)
            df['Tamano_Operacion'] = df['Tamano_Operacion'].map(MAP_TAMANO_OPERACION).fillna(-1)
            df['Frecuencia_Ingresos'] = df['Frecuencia_Ingresos'].map(MAP_FRECUENCIA_INGRESOS).fillna(-1)
            df['Escolaridad'] = df['Escolaridad'].map(MAP_ESCOLARIDAD).fillna(-1)
            df = df[SCORING_FEATURES_ORDER]
            
            prediction_proba = self.scoring_model.predict_proba(df)
            prediction = prediction_proba.argmax(axis=1)[0]
            confidence = prediction_proba.max() * 100
            score_name = MAP_SCORE_NAMES.get(prediction, "Indeterminado")
            
            return (f"¡Gracias! 📈\nTu clasificación crediticia es: **{score_name.upper()}**.\n"
                    f"(Confianza: {confidence:.2f}%)\n\nRecuerda, es una estimación.")
        except Exception as e:
            print(f"❌ ERROR al predecir el score: {e}")
            return "Lo siento, tuve un problema al calcular tu perfil."


    def _log_transaction(self, user_id, clabe, amount):
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f"[{timestamp}] User: {user_id}, Destino: {clabe}, Monto: {amount}\n"
        try:
            with open("transactions.log", "a", encoding="utf-8") as f:
                f.write(log_entry)
            print(f"✅ Transacción registrada: {log_entry.strip()}")
        except Exception as e:
            print(f"❌ ERROR al registrar transacción: {e}")

    def process_transfer(self, from_acc, to_acc, amount):
        self.ACCOUNTS[from_acc]["balance"] -= amount
        self.ACCOUNTS[to_acc]["balance"] += amount
        result = "✅ Transferencia Exitosa\n\n"
        result += f"Se transfirieron ${amount:.2f} de {self.ACCOUNTS[from_acc]['holder']} a {self.ACCOUNTS[to_acc]['holder']}\n\n"
        result += "Saldos Actualizados:\n"
        result += f"• {from_acc}: ${self.ACCOUNTS[from_acc]['balance']:.2f}\n"
        return result

    def start_transfer_flow(self, user_id):
        self.user_sessions[user_id] = {
            'mode': 'transfer',
            'transfer_step': 'WAITING_FOR_SOURCE',
            'transfer_data': {}
        }
        return "Iniciemos una transferencia.\n\n¿Desde qué número de cuenta deseas transferir? (Ej. ACC001 o ACC002)"

    def handle_transfer_flow(self, user_answer, user_id):
        session = self.user_sessions.get(user_id)
        if not session or session.get('mode') != 'transfer':
             return self.get_greeting()

        if user_answer.lower() in ['cancelar', 'salir', 'menu', 'exit']:
            self.user_sessions[user_id] = {"mode": "educational", "history": []}
            return "Transferencia cancelada. Volviendo al menú principal."

        state = session.get('transfer_step', 'START')
        data = session.get('transfer_data', {})

        if state == 'WAITING_FOR_SOURCE':
            account_number = user_answer.upper()
            if account_number not in self.ACCOUNTS:
                return f"Cuenta {account_number} no encontrada. Por favor, usa 'ACC001' o 'ACC002'."
            else:
                data['from_account'] = account_number
                session['transfer_step'] = 'WAITING_FOR_DESTINATION'
                return "Perfecto. ¿A qué número de cuenta deseas transferir?"

        elif state == 'WAITING_FOR_DESTINATION':
            account_number = user_answer.upper()
            from_account = data.get('from_account')
            if account_number not in self.ACCOUNTS:
                return f"Cuenta {account_number} no encontrada. Por favor, usa 'ACC001' o 'ACC002'."
            elif account_number == from_account:
                return "No puedes transferir a la misma cuenta. Por favor, ingresa un número de cuenta diferente:"
            else:
                data['to_account'] = account_number
                session['transfer_step'] = 'WAITING_FOR_AMOUNT'
                from_balance = self.ACCOUNTS[from_account]['balance']
                return f"¿Qué monto deseas transferir?\n(Saldo disponible: ${from_balance:.2f})"

        elif state == 'WAITING_FOR_AMOUNT':
            try:
                amount = float(user_answer.replace("$", "").strip())
                from_account = data.get('from_account')
                
                if amount <= 0:
                    return "El monto debe ser mayor a cero. Por favor, ingresa un monto válido:"
                elif amount > self.ACCOUNTS[from_account]['balance']:
                    available = self.ACCOUNTS[from_account]['balance']
                    return f"Fondos insuficientes. Saldo disponible: ${available:.2f}\nPor favor, ingresa un monto válido:"
                else:
                    data['amount'] = amount
                    session['transfer_step'] = 'WAITING_FOR_CONFIRMATION'
                    
                    from_acc = data['from_account']
                    to_acc = data['to_account']
                    summary = "\nResumen de la Transferencia\n"
                    summary += f"Desde: {self.ACCOUNTS[from_acc]['holder']} ({from_acc})\n"
                    summary += f"Para: {self.ACCOUNTS[to_acc]['holder']} ({to_acc})\n"
                    summary += f"Monto: ${amount:.2f}\n"
                    summary += "━━━━━━━━━━━━━━━━━━━━━\n\n"
                    summary += "Por favor, confirma esta transferencia.\nResponde SÍ para confirmar o NO para cancelar."
                    return summary
            except ValueError:
                return "Monto inválido. Por favor, ingresa un número (ej: 100 o 100.50):"

        elif state == 'WAITING_FOR_CONFIRMATION':
            confirmation = user_answer.lower()
            
            if confirmation in ['sí', 'si', 's', 'confirmar']:
                from_acc = data['from_account']
                to_acc = data['to_account']
                amount = data['amount']
                
                result = self.process_transfer(from_acc, to_acc, amount)
                self._log_transaction(user_id, to_acc, amount)
                
                result += "\n\nResponde 'menu' para volver al menú."
                self.user_sessions[user_id] = {"mode": "educational", "history": []}
                return result
            
            elif confirmation in ['no', 'n', 'cancelar']:
                self.user_sessions[user_id] = {"mode": "educational", "history": []}
                return "Transferencia cancelada.\n\nResponde 'hola' para volver al menú."
            
            else:
                return "Por favor, responde 'SÍ' para confirmar o 'NO' para cancelar:"
        
        self.user_sessions[user_id] = {"mode": "educational", "history": []}
        return "Algo salió mal. Volviendo al menú principal."


assistant = AdvancedFinancialAssistant()

@app.route('/')
def home():
    return jsonify({
        "status": "Chatbot Financiero Agrícola activo",
        "version": "1.0",
        "modelo_IA_cargado": "Sí" if assistant.chatbot else "No (Modo Fallback)",
        "modelo_Scoring_cargado": "Sí" if assistant.scoring_model else "No"
    })

@app.route("/webhook", methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    user_id = request.values.get('From', 'default_twilio_user')
    print(f"📨 Mensaje de WhatsApp de {user_id}: {incoming_msg}")

    response_text = ""
    session = assistant.user_sessions.get(user_id, {})


    if session.get('mode') == 'scoring':
        response_text = assistant.handle_scoring_flow(incoming_msg, user_id)
    elif session.get('mode') == 'transfer':
        response_text = assistant.handle_transfer_flow(incoming_msg, user_id)
    
    else:
        incoming_msg_lower = incoming_msg.lower()
        
        edu_keywords = ['1', 'educación', 'aprender', 'háblame', 'habrame', 'enseñame', 'dime', 'info']
        
        if not incoming_msg_lower or incoming_msg_lower in ['hola', 'hi', 'inicio', 'start', 'menu']:
            response_text = assistant.get_greeting()
        
        elif any(keyword in incoming_msg_lower for keyword in edu_keywords):
            response_text = assistant.handle_educational_request(incoming_msg, user_id)
        
        elif any(keyword in incoming_msg_lower for keyword in ['2', 'transferencia', 'pago']):
            response_text = assistant.start_transfer_flow(user_id) 
        elif any(keyword in incoming_msg_lower for keyword in ['3', 'crédito', 'calcular', 'perfil']):
            response_text = assistant.start_scoring_flow(user_id)
        else:

            response_text = assistant.handle_educational_request(incoming_msg, user_id)

    resp = MessagingResponse()
    resp.message(response_text)
    xml_response = str(resp)
    return Response(xml_response, mimetype='application/xml')


@app.route('/chat', methods=['POST'])
def chat():
    """Este endpoint recibe JSON (para pruebas con Thunder Client)"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        user_id = data.get('user_id', 'default_user')
        print(f"📨 Mensaje de PRUEBA (JSON) de {user_id}: {user_message}")

        session = assistant.user_sessions.get(user_id, {})
        response_text = ""

        if session.get('mode') == 'scoring':
            response_text = assistant.handle_scoring_flow(user_message, user_id)
        elif session.get('mode') == 'transfer':
            response_text = assistant.handle_transfer_flow(user_message, user_id)
        else:
            user_message_lower = user_message.lower()

            if not user_message_lower or user_message_lower in ['hola', 'hi', 'inicio', 'start', 'menu']:
                response_text = assistant.get_greeting()

            elif any(keyword in user_message_lower for keyword in ['1', 'educación', 'aprender', 'háblame', 'habrame', 'enseñame', 'dime', 'info']):
                response_text = assistant.handle_educational_request(user_message, user_id)
            elif any(keyword in user_message_lower for keyword in ['2', 'transferencia']):
                response_text = assistant.start_transfer_flow(user_id)
            elif any(keyword in user_message_lower for keyword in ['3', 'crédito', 'calcular', 'perfil']):
                response_text = assistant.start_scoring_flow(user_id)
            else:
                response_text = assistant.handle_educational_request(user_message, user_id)
        
        return jsonify({"response": response_text, "session_id": user_id})

    except Exception as e:
        print(f"❌ Error en /chat: {e}")
        return jsonify({"response": "Error interno", "error": str(e)}), 500

# --- Main (Corregido) ---
if __name__ == '__main__':
    print("🌱 Iniciando Chatbot Financiero Agrícola...")
    print("📍 Servidor disponible en: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)