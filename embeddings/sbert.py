# embeddings/sbert.py
from sentence_transformers import SentenceTransformer

class SBERTEmbedding:
    def __init__(self, model_name='keepitreal/vietnamese-sbert'):
        self.model = SentenceTransformer(model_name)

    def encode(self, texts):
        return self.model.encode(texts).tolist()
