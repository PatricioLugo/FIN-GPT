import fitz
import os
import re
import json
import numpy as np

class PDFProcessor:
    
    def __init__(self):
        self.processed_texts = []

    def extract_text_from_pdf(self, pdf_path):

        try:
            print(f"Extrayendo texto de: {pdf_path}")
            doc = fitz.open(pdf_path)
            text = ""
            for page_num, page in enumerate(doc):
                text += f"\n--- Página {page_num + 1} ---\n"
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            print(f"Error procesando {pdf_path}: {e}")
            return ""

    def clean_text(self, text):

        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        
        sentences = []
        current_sentence = ""
        for char in text:
            current_sentence += char
            if char in ['.', '!', '?', '\n']:
                if len(current_sentence.strip()) > 10:
                    sentences.append(current_sentence.strip())
                current_sentence = ""
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        paragraphs = []
        current_paragraph = ""
        for sentence in sentences:
            if len(sentence.split()) <= 3 or sentence.endswith(':'):
                if current_paragraph:
                    paragraphs.append(current_paragraph.strip())
                paragraphs.append(sentence.strip())
                current_paragraph = ""
            else:
                current_paragraph += " " + sentence
                if len(current_paragraph) > 200:
                    paragraphs.append(current_paragraph.strip())
                    current_paragraph = ""
        if current_paragraph:
            paragraphs.append(current_paragraph.strip())
            
        return [p for p in paragraphs if len(p.split()) > 5]

    def process_pdf_directory(self, pdf_directory):

        all_paragraphs = []
        for filename in os.listdir(pdf_directory):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(pdf_directory, filename)
                print(f"\nProcesando: {filename}")
                raw_text = self.extract_text_from_pdf(pdf_path)
                if raw_text:
                    paragraphs = self.clean_text(raw_text)
                    all_paragraphs.extend(paragraphs)
                    print(f"Extraídos {len(paragraphs)} párrafos de {filename}")
        return all_paragraphs

    def save_training_data(self, training_data, output_file):

        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, ensure_ascii=False, indent=2)
        print(f"Guardados {len(training_data)} ejemplos en {output_file}")
        return training_data
            
    def create_training_data_knowledge(self, paragraphs):

        training_data = []
        for paragraph in paragraphs:
            if len(paragraph.split()) > 6:
                knowledge_chunk = self.extract_knowledge_essence(paragraph)
                if knowledge_chunk:
                    knowledge_examples = self.create_knowledge_examples(knowledge_chunk)
                    training_data.extend(knowledge_examples)
        print(f"Creados {len(training_data)} ejemplos de entrenamiento variables")
        return training_data

    def extract_knowledge_essence(self, paragraph):

        sentences = [s.strip() for s in paragraph.split('.') if s.strip() and len(s.split()) > 4]
        if not sentences: return None
        
        main_knowledge = sentences[0]
        supporting_info = sentences[1] if len(sentences) > 1 else ""
        
        return {
            'main_knowledge': main_knowledge,
            'supporting_info': supporting_info,
            'topic': self.identify_topic(main_knowledge)
        }

    def create_knowledge_examples(self, knowledge):

        generic_templates = [
            "¿Qué sabes sobre {topic}?", "Explícame qué es {topic}",
            "Necesito ayuda con {topic}", "¿Me puedes dar información de {topic}?",
            "Quiero aprender de {topic}", "Háblame de {topic}",
            "Enséñame sobre conceptos financieros", "Proporciona información financiera importante",
            "¿Qué es {topic}?", "dame info de {topic}"
        ]
        
        topic_name = knowledge['topic'].split(' ')[0]
        
        filled_templates = [
            f"¿Qué sabes sobre {topic_name}?", f"Explícame qué es un {topic_name}",
            f"Necesito ayuda con {topic_name}", f"¿Me puedes dar información de {topic_name}?",
            f"Quiero aprender de {topic_name}", f"Háblame de {topic_name}",
            f"¿Qué onda con {topic_name}?", f"dame detalles de {topic_name}"
        ]
        
        all_inputs = generic_templates + filled_templates
        
        num_examples = 4
        selected_inputs = np.random.choice(all_inputs, num_examples, replace=False)
        
        examples = []
        main_output = knowledge['main_knowledge'] + (f". {knowledge['supporting_info']}" if knowledge['supporting_info'] else "")
        
        for input_text in selected_inputs:
            examples.append({"input": input_text, "output": main_output})

        return examples

    def identify_topic(self, text):

        text_lower = text.lower()
        if 'crédito' in text_lower or 'préstamo' in text_lower or 'financiamiento' in text_lower:
            return "créditos y financiamiento"
        elif 'ahorro' in text_lower or 'inversión' in text_lower or 'fondo' in text_lower:
            return "ahorro e inversión"
        elif 'tasa' in text_lower or 'interés' in text_lower or 'cat' in text_lower:
            return "tasas e intereses"
        elif 'seguro' in text_lower or 'plaga' in text_lower or 'cosecha' in text_lower:
            return "seguros agrícolas"
        else:
            return "conceptos financieros"

def process_pdfs():
    processor = PDFProcessor()
    pdf_directory = "data/knowledge_base/"
    
    if not os.path.exists(pdf_directory):
        print(f"El directorio {pdf_directory} no existe")
        return None
    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("No se encontraron archivos PDF en el directorio")
        return None
    
    print(f"📚 Encontrados {len(pdf_files)} archivos PDF")
    paragraphs = processor.process_pdf_directory(pdf_directory)
    print(f"\n📊 Total de párrafos extraídos: {len(paragraphs)}")
    
    # Usamos el NUEVO método de conocimiento
    training_data = processor.create_training_data_knowledge(paragraphs)
    
    output_file = "data/training/financial_education_dataset.json"
    processor.save_training_data(training_data, output_file)
    
    return training_data

if __name__ == "__main__":
    print("Iniciando procesamiento de PDFs")
    process_pdfs()