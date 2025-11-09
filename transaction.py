from flask import Flask, request, session
from twilio.twiml.messaging_response import MessagingResponse
#import os

app = Flask(__name__)
#app.secret_key = os.environ.get('SECRET_KEY', 'tu-clave-secreta-cambiar-en-produccion')


ACCOUNTS = {
    "ACC001": {"holder": "Sergio Rock", "balance": 1000.00},
    "ACC002": {"holder": "Emilio Pinelo", "balance": 500.00}
}


def process_transfer(from_acc, to_acc, amount):
    """Ejecuta la transferencia"""
    ACCOUNTS[from_acc]["balance"] -= amount
    ACCOUNTS[to_acc]["balance"] += amount
    
    result = "Transferencia Exitosa\n\n"
    result += f"Se transfirieron ${amount:.2f} de {ACCOUNTS[from_acc]['holder']} a {ACCOUNTS[to_acc]['holder']}\n\n"
    result += "Saldos Actualizados:\n"
    result += f"• {from_acc}: ${ACCOUNTS[from_acc]['balance']:.2f}\n"
    result += f"• {to_acc}: ${ACCOUNTS[to_acc]['balance']:.2f}\n"
    return result


@app.route("/webhook", methods=['POST'])
def webhook():
    incoming_msg = request.values.get('Body', '').strip()
    
    resp = MessagingResponse()
    msg = resp.message()
    
    if 'state' not in session:
        session['state'] = 'START'
    
    state = session.get('state', 'START')
    
    reset_keywords = ['iniciar', 'transferencia', 'nuevo', 'cancelar']
    
    if state == 'START' or incoming_msg.lower() in reset_keywords:
        session['state'] = 'WAITING_FOR_SOURCE'
        session.pop('from_account', None)
        session.pop('to_account', None)
        session.pop('amount', None)
        
        response_text = "Iniciemos una transferencia.\n\n¿Desde qué número de cuenta deseas transferir?"
        msg.body(response_text)
    
    elif state == 'WAITING_FOR_SOURCE':
        account_number = incoming_msg.upper()
        
        if account_number not in ACCOUNTS:
            msg.body(f"Cuenta {account_number} no encontrada. Por favor, ingresa un número de cuenta válido:")
        else:
            session['from_account'] = account_number
            session['state'] = 'WAITING_FOR_DESTINATION'
            
            response_text = "Perfecto. ¿A qué número de cuenta deseas transferir?"
            msg.body(response_text)
    
    elif state == 'WAITING_FOR_DESTINATION':
        account_number = incoming_msg.upper()
        
        if account_number not in ACCOUNTS:
            msg.body(f"Cuenta {account_number} no encontrada. Por favor, ingresa un número de cuenta válido:")
        elif account_number == session['from_account']:
            msg.body("No puedes transferir a la misma cuenta. Por favor, ingresa un número de cuenta diferente:")
        else:
            session['to_account'] = account_number
            session['state'] = 'WAITING_FOR_AMOUNT'
            
            from_balance = ACCOUNTS[session['from_account']]['balance']
            response_text = f"¿Qué monto deseas transferir?\n(Saldo disponible: ${from_balance:.2f})"
            msg.body(response_text)
    
    elif state == 'WAITING_FOR_AMOUNT':
        try:
            amount = float(incoming_msg.replace("$", "").strip())
            
            if amount <= 0:
                msg.body("El monto debe ser mayor a cero. Por favor, ingresa un monto válido:")
            elif amount > ACCOUNTS[session['from_account']]['balance']:
                available = ACCOUNTS[session['from_account']]['balance']
                msg.body(f"Fondos insuficientes. Saldo disponible: ${available:.2f}\nPor favor, ingresa un monto válido:")
            else:
                session['amount'] = amount
                session['state'] = 'WAITING_FOR_CONFIRMATION'
                
                from_acc = session['from_account']
                to_acc = session['to_account']
                
                summary = "\nResumen de la Transferencia\n"
                summary += f"Desde: {ACCOUNTS[from_acc]['holder']} ({from_acc})\n"
                summary += f"Para: {ACCOUNTS[to_acc]['holder']} ({to_acc})\n"
                summary += f"Monto: ${amount:.2f}\n"
                summary += "━━━━━━━━━━━━━━━━━━━━━\n\n"
                summary += "Por favor, confirma esta transferencia.\nResponde SÍ para confirmar o NO para cancelar."
                
                msg.body(summary)
        
        except ValueError:
            msg.body("Monto inválido. Por favor, ingresa un número (ej: 100 o 100.50):")
    
    elif state == 'WAITING_FOR_CONFIRMATION':
        confirmation = incoming_msg.lower()
        
        if confirmation in ['sí', 'si', 's', 'confirmar']:
            from_acc = session['from_account']
            to_acc = session['to_account']
            amount = session['amount']
            
            result = process_transfer(from_acc, to_acc, amount)
            result += "\nResponde 'INICIAR' para hacer otra transferencia."
            
            msg.body(result)
            
            session['state'] = 'START'
            session.pop('from_account', None)
            session.pop('to_account', None)
            session.pop('amount', None)
        
        elif confirmation in ['no', 'n', 'cancelar']:
            msg.body("Transferencia cancelada.\n\nResponde 'INICIAR' para comenzar una nueva transferencia.")
            
            session['state'] = 'START'
            session.pop('from_account', None)
            session.pop('to_account', None)
            session.pop('amount', None)
        
        else:
            msg.body("Por favor, responde 'SÍ' para confirmar o 'NO' para cancelar:")
    
    else:
        session['state'] = 'START'
        msg.body("Algo salió mal. Responde 'INICIAR' para comenzar una nueva transferencia.")
    
    return str(resp)


@app.route("/")
def index():
    return "<h1>Chatbot de Transferencias (Demo)</h1><p>El servidor está funcionando. Configura Twilio para apuntar a <code>/webhook</code>.</p>"


if __name__ == "__main__":
    app.run(debug=True, port=5000)