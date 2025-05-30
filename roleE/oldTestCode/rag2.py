import spacy
from pinecone import Pinecone
import torch
from transformers import AutoTokenizer, AutoModel
import numpy as np

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Utilizando dispositivo: {device}")

# Carregar o modelo SciBERT do spaCy
nlp = spacy.load("en_core_sci_scibert")

# Carregar o modelo de embeddings BGE da HuggingFace
tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-small-en")
model = AutoModel.from_pretrained("BAAI/bge-small-en")
model.to(device)


class rag2:
    global model, tokenizer, nlp
    def __init__(self,index: str, key: str , top:int = 3):
        self.key = key
        self.pinecone = Pinecone(api_key=self.key)
        self.index = self.pinecone.Index("papers")
        self.topX = top


    def generate_embeddings(self,chunks):
        embeddings = []
        for chunk in chunks:
            inputs = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512)
            inputs = {key: value.to(device) for key, value in inputs.items()}
            with torch.no_grad():
                outputs = model(**inputs)
                embedding = outputs.last_hidden_state.mean(dim=1).squeeze().cpu().numpy()
                embeddings.append(embedding)
        return np.array(embeddings) if embeddings else np.zeros((0, 384))

    def split_into_chunks(self,text, max_length=150):  # Ajustado para RAG
        doc = nlp(text)
        chunks = []
        current_chunk = []
        current_length = 0

        for sent in doc.sents:
            sent_text = sent.text.strip()
            sent_tokens = len(tokenizer.tokenize(sent_text))
            if sent_tokens > max_length:
                words = sent_text.split()
                sub_chunk = []
                sub_length = 0
                for word in words:
                    word_tokens = len(self.tokenizer.tokenize(word))
                    if sub_length + word_tokens <= max_length:
                        sub_chunk.append(word)
                        sub_length += word_tokens
                    else:
                        if sub_chunk:
                            chunks.append(" ".join(sub_chunk))
                        sub_chunk = [word]
                        sub_length = word_tokens
                if sub_chunk:
                    chunks.append(" ".join(sub_chunk))
            else:
                if current_length + sent_tokens <= max_length:
                    current_chunk.append(sent_text)
                    current_length += sent_tokens
                else:
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                    current_chunk = [sent_text]
                    current_length = sent_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def query_pinecone(self,query_text):
        """Query Pinecone for the top-k most similar chunks."""
        # Generate query embedding
        query_chunks = self.split_into_chunks(query_text)
        query_embedding = self.generate_embeddings(query_chunks)
        if query_embedding.shape[0] == 0:
            print("No query embedding generated.")
            return []
        # Use the first chunk's embedding for simplicity (or average if multiple)
        query_vector = query_embedding[0].tolist() if query_embedding.shape[0] > 0 else np.zeros(384).tolist()

        # Query Pinecone
        results = self.index.query(vector=query_vector, top_k=self.topX, include_metadata=True)
        retrieved_chunks = []
        for match in results['matches']:
            """retrieved_chunks.append({
                "chunk_id": match['id'],
                "chunk_text": match['metadata']['chunk_text'],
                "score": match['score'],
                "title": match['metadata']['title'],
                "doi": match['metadata']['doi']
            })"""
            retrieved_chunks.append({
                "chunk_text": match['metadata']['chunk_text'],
                "title": match['metadata']['title'],
                "doi": match['metadata']['doi']
            })

        return retrieved_chunks
