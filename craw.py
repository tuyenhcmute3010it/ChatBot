from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import pymongo
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import uuid
import nltk
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
# 🧠 Cài NLTK
nltk.download('punkt')
nltk.download('punkt_tab')
from nltk.tokenize import sent_tokenize

# ✅ 1. Khởi tạo app
app = FastAPI()

# ✅ 2. Gắn CORS ngay sau khi khởi tạo app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # or ["*"] if dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 3. Khai báo các phần còn lại
# MongoDB setup
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
client = pymongo.MongoClient(MONGODB_URI)
db = client["hoanghamobilenew"]
collection = db["all_embeddings"]

# Embedding model
model = SentenceTransformer("keepitreal/vietnamese-sbert")

class URLPayload(BaseModel):
    urls: List[str]
    topic: str

def semantic_splitting(text, threshold=0.3):
    sentences = sent_tokenize(text)
    vectorizer = TfidfVectorizer().fit_transform(sentences)
    vectors = vectorizer.toarray()
    similarities = cosine_similarity(vectors)
    chunks = [[sentences[0]]]

    for i in range(1, len(sentences)):
        sim_score = similarities[i - 1, i]
        if sim_score >= threshold:
            chunks[-1].append(sentences[i])
        else:
            chunks.append([sentences[i]])
    return [' '.join(chunk) for chunk in chunks]

def parse_page(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.text, 'html.parser')
    content = ""

    review_title = soup.find('div', class_='review-title')
    if review_title:
        h1 = review_title.find('h1')
        if h1: content += h1.get_text(strip=True) + "\n"
        for p in review_title.find_all('p'):
            content += p.get_text(strip=True) + "\n"

    for ck in soup.find_all(class_='ck-content'):
        for el in ck.children:
            if el.name in ['h2', 'h3', 'p']:
                content += el.get_text(strip=True) + "\n"
            elif el.name == 'ul':
                for li in el.find_all('li'):
                    content += f"- {' '.join(li.stripped_strings)}\n"
    return content

# ✅ 4. Route đặt SAU middleware
@app.post("/crawl")
async def crawl_and_store(payload: URLPayload):
    for url in payload.urls:
        text = parse_page(url)
        chunks = semantic_splitting(text, threshold=0.1)
        for chunk in chunks:
            if not chunk.strip():
                continue
            embedding = model.encode(chunk).tolist()
            collection.insert_one({
                "chunk_id": str(uuid.uuid4()),
                "url": url,
                "content": chunk,
                "embedding": embedding,
                "topic": payload.topic
            })
    return {"status": "ok", "urls": payload.urls}
