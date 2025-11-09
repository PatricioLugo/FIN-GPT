from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from transformers import TextDataset, DataCollatorForLanguageModeling
import torch
import os

class FinancialChatbot:

    def __init__(self, model_name="microsoft/DialoGPT-medium"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(model_name)

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model.to(self.device)
            print("Modelo cargado")

        except Exception as e:
            print(f"Error cargando modelo: {e}")
            raise

    def prepare_dataset(self, file_path):
        try:
            dataset = TextDataset(
                tokenizer=self.tokenizer,
                file_path=file_path,
                block_size=128
            )
            return dataset
        except Exception as e:
            print(f"Error preparando dataset: {e}")
            raise

    def fine_tune(self, train_file, output_dir="./fine-tuned-model"):

        if not os.path.exists(train_file):
            print(f"Archivo no encontrado: {train_file}")
            return False
        
        try:
            train_dataset = self.prepare_dataset(train_file)
            
            data_collator = DataCollatorForLanguageModeling(
                tokenizer=self.tokenizer,
                mlm=False
            )
            
            # Parametros de entrenamiento, duracion aproximada de 8-10 horas. Nos hubiera gustado mas tiempo de
            # entrenamiento, sin embargo no nos adecuamos al tiempo del hack.
            training_args = TrainingArguments(
                output_dir=output_dir,
                overwrite_output_dir=True,
                num_train_epochs=3,             
                per_device_train_batch_size=2,  
                save_steps=1000,                  
                save_total_limit=2,               
                prediction_loss_only=True,
                remove_unused_columns=False,
                warmup_steps=500,  
                logging_steps=100,
            )
            
            trainer = Trainer(
                model=self.model,
                args=training_args,
                data_collator=data_collator,
                train_dataset=train_dataset,
            )
            
            trainer.train()
            trainer.save_model()
            self.tokenizer.save_pretrained(output_dir)
            print(f"Modelo guardado en {output_dir}")
            return True
            
        except Exception as e:
            print(f"Error en el entrenamiento: {e}")
            return False

    def generate_response(self, prompt, max_length=300):
        try:
            formatted_prompt = f"Usuario: {prompt}\nAsistente:"
            
            inputs = self.tokenizer(
                formatted_prompt, 
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=len(inputs['input_ids'][0]) + max_length, 
                    num_return_sequences=1,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    no_repeat_ngram_size=2
                )
            
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            if "Asistente:" in response:
                response = response.split("Asistente:")[-1].strip()
            
            return response
            
        except Exception as e:
            print(f"Error generando respuesta: {e}")
            return "Lo siento, hubo un error procesando tu pregunta."
