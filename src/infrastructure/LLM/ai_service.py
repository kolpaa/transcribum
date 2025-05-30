import random
import string
from typing import List, Optional
import chromadb
import ollama

from src.domain.interfaces import IAIService

class AIService(IAIService):
    def __init__(
        self,
        embedding_model: str = "mxbai-embed-large",
        generation_model: str = "llama3.2",
    ):
        self.client = chromadb.Client()
        self.embedding_model = embedding_model
        self.generation_model = generation_model

    def make_embedding_collection(self, file_path: str) -> str:
        """Читает текстовый файл и создает коллекцию эмбеддингов в ChromaDB."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                lines = [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            raise ValueError(f"File not found: {file_path}")

        collection_name = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
        collection = self.client.create_collection(name=collection_name)

        for i, text in enumerate(lines):
            try:
                response = ollama.embeddings(model=self.embedding_model, prompt=text)
                collection.add(
                    ids=[str(i)],
                    embeddings=[response["embedding"]],
                    documents=[text]
                )
            except Exception as e:
                print(f"Error processing line {i}: {e}")
        return collection_name

    def generate_answer(self, prompt: str, collection_name: str) -> str:
        """Генерирует ответ на основе промпта и данных из коллекции."""
        collection = self.client.get_collection(name=collection_name)
        if not collection:
            raise ValueError("Collection not initialized. Call prepare_text_for_embedding() first.")

        try:
            # Поиск релевантного текста
            embedding_response = ollama.embeddings(
                model=self.embedding_model,
                prompt=prompt
            )
            results = collection.query(
                query_embeddings=[embedding_response["embedding"]],
                n_results=1
            )
            context = results['documents'][0][0]

            # Генерация ответа
            generation_response = ollama.generate(
                model=self.generation_model,
                prompt=f"Context: {context}\n\nQuestion: {prompt}\nAnswer:"
            )
            return generation_response['response']
        except Exception as e:
            raise RuntimeError(f"Error generating answer: {e}")

    def cleanup(self, collection_name) -> None:
        """Удаляет коллекцию ChromaDB и освобождает ресурсы."""
        self.client.delete_collection(collection_name)


