import os
import sys

def main():
    print("=== Iniciando entrenamiento ===")
    
    try:
        
        print("\n1. Procesando PDFs ...")
        from model.pdf_processer import process_pdfs
        training_data = process_pdfs()
        if not training_data:
            print("No se pudieron procesar los PDFs")
            return False


        print("\n2. Preparando datos de entrenamiento...")
        from model.training_preparer import prepare_training_data
        training_file = prepare_training_data()
        if not training_file:
            print("No se pudieron preparar los datos")
            return False
        

        print("\n3. Cargando modelo base...")
        from model.chatbot_model import FinancialChatbot
        chatbot = FinancialChatbot()
        

        print("\n4. Iniciando fine-tuning ...")
        success = chatbot.fine_tune(
            train_file=training_file,
            output_dir="./fine-tuned-financial-chatbot" 
        )
        
        if success:
            print("\n¡Entrenamiento completado")
            print("Modelo guardado en: ./fine-tuned-financial-chatbot")
            return True
        else:
            print("\nError durante el entrenamiento")
            return False
            
    except Exception as e:
        print(f"\nError general: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)