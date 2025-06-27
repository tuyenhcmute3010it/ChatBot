
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import traceback

# === Google & OpenAI SDK ===
import google.generativeai as genai
import openai
from openai import OpenAI

# === RAG system ===
from rag.core import RAG
from embeddings import OpenAIEmbedding
from embeddings.sbert import SBERTEmbedding
from semantic_router import SemanticRouter, Route
from semantic_router.samples import productsSample, chitchatSample
from reflection import Reflection

# === MongoDB & SBERT for vector search ===
from sentence_transformers import SentenceTransformer
import pymongo

# === Load .env ===
load_dotenv()
print("✅ OPEN_AI_KEY:", os.getenv('OPEN_AI_KEY'))

# === ENV CONFIG ===
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME')
DB_COLLECTION = os.getenv('DB_COLLECTION')
LLM_KEY = os.getenv('GEMINI_KEY')
OPEN_AI_KEY = os.getenv('OPEN_AI_KEY')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL') or 'keepitreal/vietnamese-sbert'

# === Embeddings & Routing ===
sbertEmbedding = SBERTEmbedding(EMBEDDING_MODEL)
semanticRouter = SemanticRouter(
    sbertEmbedding,
    routes=[
        Route(name='products', samples=productsSample),
        Route(name='chitchat', samples=chitchatSample)
    ]
)

# === LLMs ===
genai.configure(api_key=LLM_KEY)
llm = OpenAI(api_key=OPEN_AI_KEY)
gpt = openai.OpenAI(api_key=OPEN_AI_KEY)
reflection = Reflection(llm=gpt)

# === RAG ===
rag = RAG(
    mongodbUri=MONGODB_URI,
    dbName=DB_NAME,
    dbCollection=DB_COLLECTION,
    embeddingName=EMBEDDING_MODEL,
    llm=llm,
)

# === Mongo Vector Search for /ask ===
client = pymongo.MongoClient(os.getenv("MONGODB_URI"))
mongo_collection = client["hoanghamobilenew"]["embedding_for_vector_search"]
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
openai_client = OpenAI(api_key=OPEN_AI_KEY)

# === App setup ===
app = Flask(__name__)
CORS(app)

# === Helper for /ask ===
def get_embedding(text):
    return embedding_model.encode(text).tolist() if text.strip() else []

def vector_search(query, limit=5):
    embedding = get_embedding(query)
    pipeline = [
        {"$vectorSearch": {
            "index": "vector_index",
            "queryVector": embedding,
            "path": "embedding",
            "numCandidates": 300,
            "limit": limit,
        }},
        {"$unset": "embedding"},
        {"$project": {
            "_id": 0,
            "title": 1,
            "current_price": 1,
            "product_promotion": 1,
            "url": 1,
            "product_specs": 1,
            "color_options": 1,
            "score": {"$meta": "vectorSearchScore"},
        }}
    ]
    return list(mongo_collection.aggregate(pipeline))

def build_prompt(user_query, search_results):
    context = ""
    for i, item in enumerate(search_results, 1):
        title = item.get('title', 'N/A')
        price = item.get('current_price', 'Liên hệ')
        promotions = str(item.get('product_promotion', '')).strip() or 'Không có'
        colors = ', '.join(item.get('color_options', [])) if isinstance(item.get('color_options'), list) else 'Không có'
        specs = item.get('product_specs', '').replace("<br>", "; ") if isinstance(item.get('product_specs'), str) else 'Không có'
        url = item.get('url', '')

        context += f"### {i}. **{title}**\n"
        context += f"- **Giá**: {price}\n"
        context += f"- **Ưu đãi**: {promotions}\n"
        context += f"- **Màu sắc**: {colors}\n"
        context += f"- **Thông số**: {specs}\n"
        if url:
            context += f"- **[Xem chi tiết sản phẩm]({url})**\n"
        context += "\n"

    return f"""Bạn là một chuyên gia tư vấn bán điện thoại tại cửa hàng **DBIZ**.

**Câu hỏi của khách hàng:** _{user_query}_

Dưới đây là các sản phẩm liên quan:

{context}
Vui lòng trả lời khách một cách thân thiện, dễ hiểu và rõ ràng!  
Nếu khách hàng muốn biết thêm, hãy mời họ bấm vào link để xem chi tiết sản phẩm.
"""

# === Endpoint: /api/search (semantic + RAG + chitchat) ===
@app.route('/api/search', methods=['POST'])
def handle_query():
    try:
        data = list(request.get_json())
        query = data[-1]["parts"][0]["text"].lower()

        if not query:
            return jsonify({'error': 'No query provided'}), 400

        guidedRoute = semanticRouter.guide(query)[1]
        if guidedRoute == 'products':
            reflected_query = reflection(data)
            query = reflected_query
            source_information = rag.enhance_prompt(query).replace('<br>', '\n')
            combined_information = (
                f"Hãy trở thành chuyên gia tư vấn bán hàng cho một cửa hàng điện thoại. "
                f"Câu hỏi của khách hàng: {query}\n"
                f"Trả lời dựa vào các thông tin dưới đây: {source_information}."
            )
            data.append({
                "role": "user",
                "parts": [{"text": combined_information}]
            })

            response = rag.generate_content(data)
            return jsonify({'parts': [{'text': response.text}], 'role': 'model'})
        else:
            openai_messages = [
                {"role": m["role"], "content": m["parts"][0]["text"]}
                for m in data
            ]
            response = llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=openai_messages
            )
            return jsonify({
                'parts': [{'text': response.choices[0].message.content}],
                'role': 'model'
            })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# === Endpoint: /ask (Mongo vector search) ===
@app.route("/ask", methods=["POST"])
def ask():
    try:
        messages = request.get_json()
        user_message = next((m for m in reversed(messages) if m.get("role") == "user"), None)
        query = user_message["parts"][0]["text"] if user_message else ""
        if not query.strip():
            return jsonify({"error": "Empty query"}), 400

        search_results = vector_search(query, limit=5)
        prompt = build_prompt(query, search_results)
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý AI thông minh."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        return jsonify({
            "role": "model",
            "parts": [{"text": response.choices[0].message.content}]
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Processing error: {str(e)}"}), 500

# === Run server ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=False)
