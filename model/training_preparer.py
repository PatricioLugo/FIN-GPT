import json
import os

class TrainingPreparer:
    
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer
    
    def convert_to_training_text(self, json_file, output_file):

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                training_data = json.load(f)
        except FileNotFoundError:
            print(f"Archivo {json_file} no encontrado")
            return None
        except json.JSONDecodeError:
            print(f"Error decodificando desde {json_file}")
            return None
        
        training_texts = []
        for item in training_data:
            conversation = f"Usuario: {item['input']}\nAsistente: {item['output']}\n\n"
            training_texts.append(conversation)
        
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(training_texts)
        
        print(f"Archivo de entrenamiento creado: {output_file}")
        print(f"Numero de conversaciones: {len(training_texts)}")
        
        return output_file

def prepare_training_data():

    from model.chatbot_model import FinancialChatbot
    
    try:
        chatbot = FinancialChatbot()
        
        preparer = TrainingPreparer(tokenizer=None) 
        
        input_file = "data/training/financial_education_dataset.json"
        output_file = "data/training/training_conversations.txt"
        
        result = preparer.convert_to_training_text(input_file, output_file)
        
        if result:
            print("Preparacion de datos completada")
            return output_file
        else:
            print("Error en la preparacion de datos")
            return None
            
    except Exception as e:
        print(f"Error durante la preparacion: {e}")
        return None

if __name__ == "__main__":
    prepare_training_data()