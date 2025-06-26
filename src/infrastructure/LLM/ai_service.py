import random
import string
from typing import List, Optional
import chromadb
import ollama
from yandex_cloud_ml_sdk import YCloudML

from src.domain.interfaces import IAIService
from src.domain.constants import LLMPrompts

class AIService(IAIService):
    def __init__(
        self,
        embedding_model: str = "mxbai-embed-large",
        generation_model: str = "deepseek-r1:8b",
	auth: str,
	folder_id: str
    ):
        self.client = chromadb.Client()
        self.embedding_model = embedding_model
        self.generation_model = generation_model
        self.sdk = YCloudML(folder_id=folder_id, auth=auth)
        self.WORDS_PER_CHUNK = 1500

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
                think=False,
                model=self.generation_model,
                prompt=f"Context: {context}\n\nQuestion: {prompt}\nAnswer:",
            )
            return generation_response['response']
        except Exception as e:
            raise RuntimeError(f"Error generating answer: {e}")

    def generate_remote_api_answer(self, file_path, prompt):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        print("📄 Разделение на части...")
        chunks = self.split_text_by_paragraphs(text)
        print(f"🔹 Найдено частей: {len(chunks)}")

        summaries = []
        for i, chunk in enumerate(chunks):
            print(f"🧠 Обработка части {i+1}/{len(chunks)}...")
            summary = self.summarize_chunk(self.sdk, chunk, prompt)
            summaries.append(summary)

        print("🧩 Объединение частичных summary в итоговое...")
        final_summary = self.summarize_all(self.sdk, summaries, prompt)

        print("\n✅ Готово. Итоговое краткое содержание:")
        print("-" * 50)
        print(final_summary)
        return final_summary 




    def cleanup(self, collection_name) -> None:
        """Удаляет коллекцию ChromaDB и освобождает ресурсы."""
        self.client.delete_collection(collection_name)

    def split_text_by_paragraphs(self, text: str) -> list[str]:
        paragraphs = text.split("\n\n")
        chunks = []
        current = []

        word_count = 0
        for para in paragraphs:
            words = para.split()
            if word_count + len(words) > self.WORDS_PER_CHUNK and current:
                chunks.append("\n\n".join(current))
                current = [para]
                word_count = len(words)
            else:
                current.append(para)
                word_count += len(words)

        if current:
            chunks.append("\n\n".join(current))

        return chunks


    def summarize_chunk(self, sdk: YCloudML, chunk: str, prompt) -> str:
        messages = [
            {"role": "system", "text": "Ты — помощник, для работы с текстом."},
            {"role": "user", "text": f"{prompt}:\n\n{chunk}"}
        ]
        result = (
            sdk.models.completions("yandexgpt").configure(temperature=0.5).run(messages)
        )
        print(result.alternatives[0].text)
        return result.alternatives[0].text


    def summarize_all(self, sdk: YCloudML, partial_summaries: list[str], prompt) -> str:
        merged = "\n\n".join(partial_summaries)
        if prompt == LLMPrompts.MAKE_POST:
            messages = [
                {"role": "system", "text": "Ты — помощник, составляющий пост для социальной сети на основе частей."},
                {"role": "user", "text": (
                    "Вот краткие содержания частей большого текста:\n\n"
                    f"{merged}\n\n"
                    "Составь интересный пост для социальной сети используя их"
                )}
            ]
        elif prompt == LLMPrompts.MAKE_SUMMARY:
            messages = [
                {"role": "system", "text": "Ты — помощник, составляющий итоговое краткое содержание на основе частей."},
                {"role": "user", "text": (
                    "Вот краткие содержания частей большого текста:\n\n"
                    f"{merged}\n\n"
                    "Составь единое, связное и краткое итоговое содержание текста, избегая повторов и несостыковок."
                )}
            ]
        result = (
            sdk.models.completions("yandexgpt").configure(temperature=0.5).run(messages)
        )
        print(result.alternatives[0].text)
        return result.alternatives[0].text
    
