from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os, traceback, re
from datetime import datetime
import openai
from rag.core import RAG
import google.generativeai as genai
from openai import OpenAI
from rag.core import RAG
from embeddings.sbert import SBERTEmbedding
from semantic_router import SemanticRouter, Route
from semantic_router.samples import productsSample, chitchatSample
from reflection import Reflection
from sentence_transformers import SentenceTransformer
import pymongo
from sentence_transformers.util import cos_sim
# === Load .env ===
load_dotenv()
MONGODB_URI = os.getenv('MONGODB_URI')
DB_NAME = os.getenv('DB_NAME')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL') or 'keepitreal/vietnamese-sbert'
OPEN_AI_KEY = os.getenv('OPEN_AI_KEY')
LLM_KEY = os.getenv('GEMINI_KEY')

# === MongoDB setup ===
client = pymongo.MongoClient(MONGODB_URI)
product_collection = client[DB_NAME]["embedding_for_vector_search"]
semantic_collection = client[DB_NAME]["all_embeddings"]

# === Embedding & LLM setup ===
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
sbertEmbedding = SBERTEmbedding(EMBEDDING_MODEL)
genai.configure(api_key=LLM_KEY)
llm = OpenAI(api_key=OPEN_AI_KEY)
openai_client = OpenAI(api_key=OPEN_AI_KEY)
reflection = Reflection(llm=openai_client)

# === RAG setup ===
rag = RAG(
    mongodbUri=MONGODB_URI,
    dbName=DB_NAME,
    dbCollection="all_embeddings",
    embeddingName=EMBEDDING_MODEL,
    llm=llm,
)
print("🧪 Has method run:", hasattr(rag, "run"))

# def slugify(text):
#     return re.sub(r'\W+', '-', text.lower()).strip('-')

def load_dynamic_samples(collection, sample_limit=200):
    print("=== Dynamic Topics from MongoDB ===")
    topic_samples = {}
    cursor = collection.find(
        {"content": {"$exists": True, "$ne": ""}, "topic": {"$exists": True, "$ne": ""}},
        {"_id": 0, "content": 1, "topic": 1}
    )
    for doc in cursor:
        topic = doc["topic"]
        content = doc["content"].strip()
        if not content or not topic:
            continue
        if topic not in topic_samples:
            topic_samples[topic] = []
        if len(topic_samples[topic]) < sample_limit:
            topic_samples[topic].append(content)
    return topic_samples

def create_routes_from_samples(samples_dict):
    return [Route(name=topic, samples=samples) for topic, samples in samples_dict.items()]

# === Semantic Router setup ===
static_routes = [
    Route(name="products", samples=productsSample),
    Route(name="chitchat", samples=chitchatSample),
]
dynamic_samples = load_dynamic_samples(semantic_collection)
dynamic_routes = create_routes_from_samples(dynamic_samples)
semanticRouter = SemanticRouter(sbertEmbedding, static_routes + dynamic_routes)

# === Flask App ===
app = Flask(__name__)
CORS(app)

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
    return list(product_collection.aggregate(pipeline))

def build_prompt(user_query, search_results):
    context = ""
    for i, item in enumerate(search_results, 1):
        title = item.get('title', 'N/A')
        price = item.get('current_price', 'Liên hệ')
        promo = item.get('product_promotion', '') or 'Không có'
        colors = ', '.join(item.get('color_options', [])) if isinstance(item.get('color_options'), list) else 'Không có'
        specs = item.get('product_specs', '').replace("<br>", "; ") if isinstance(item.get('product_specs'), str) else 'Không có'
        url = item.get('url', '')

        context += f"### {i}. **{title}**\n"
        context += f"- #### **Giá**: {price}\n"
        context += f"- #### **Ưu đãi**: {promo}\n"
        context += f"- #### **Màu sắc**: {colors}\n"
        context += f"- #### **Thông số**: {specs}\n"
        if url:
            context += f"- *[Xem chi tiết sản phẩm]({url})*\n"
        context += "\n"

    return f"""Bạn là chuyên gia tư vấn của **DBIZ**.
**Khách hỏi:** _{user_query}_

Dưới đây là sản phẩm phù hợp:

{context}
Hãy trả lời thân thiện, rõ ràng và gợi ý khách bấm vào link để xem thêm nếu cần.
"""

def save_chat_log(messages):
    try:
        client[DB_NAME]["chat_logs"].insert_one({
            "messages": messages,
            "timestamp": datetime.utcnow()
        })
    except Exception as e:
        print("❌ Failed to save chat log:", e)

def print_route_scores(router, query, top_k=5, sample_limit=10):
    print(f"🔍 Query: {query}")
    print("📌 Top route scores:")
    query_vec = embedding_model.encode(query)
    route_scores = []

    print("✅ All loaded routes:")
    for r in router.routes:
        print(f" - {r.name} ({len(r.samples)} samples)")

    for route in router.routes:
        if not route.samples:
            continue
        limited_samples = route.samples[:sample_limit]
        route_text = " ".join(limited_samples)
        if not route_text.strip():
            continue
        route_vec = embedding_model.encode(route_text)
        score = cos_sim(query_vec, route_vec)[0][0].item()
        route_scores.append((route.name, score))

    sorted_scores = sorted(route_scores, key=lambda x: x[1], reverse=True)
    for name, score in sorted_scores[:top_k]:
        print(f"🔎 {name}: {score:.4f}")
@app.route('/api/search', methods=['POST'])
def handle_query():
    try:
        data = list(request.get_json())
        query = data[-1]["parts"][0]["text"].strip()
        if not query:
            return jsonify({'error': 'No query provided'}), 400

        print_route_scores(semanticRouter, query)
        # scores = semanticRouter.guide(query)
        # guidedRoute = scores[1] if scores else "chitchat"
        query_vec = embedding_model.encode(query)
        best_score = -1
        guidedRoute = "chitchat"

        for route in semanticRouter.routes:
            if not route.samples:
                continue
            route_text = " ".join(route.samples[:10])
            if not route_text.strip():
                continue
            route_vec = embedding_model.encode(route_text)
            score = cos_sim(query_vec, route_vec)[0][0].item()
            if score > best_score:
                best_score = score
                guidedRoute = route.name

        print(f"📌 Best matched route: {guidedRoute} (score: {best_score:.4f})")

        # 1️⃣ Route: products
        if guidedRoute == 'products':
            query = reflection(data)
            search_results = vector_search(query)
            prompt = build_prompt(query, search_results)
            messages = [
                {"role": "system", "content": "Bạn là một trợ lý AI thông minh."},
                {"role": "user", "content": prompt}
            ]
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            save_chat_log(messages)
            return jsonify({"role": "model", "parts": [{"text": response.choices[0].message.content}]})

        # 2️⃣ Route: dynamic route (ví dụ: máy massage xung điện tốt nhất)
        elif guidedRoute not in {"products", "chitchat"}:
            print(f"🧠 Detected dynamic route: {guidedRoute}")
            query = reflection(data)
            # ✅ Use rag.run() with topic filter
            rag_prompt = rag.run(query, topic=guidedRoute)
            print(f"🧠 rag_response rag_response rag_response=======: {rag_prompt}")

            messages = [
                {"role": "system", "content": "Bạn là một trợ lý AI thông minh."},
                {"role": "user", "content": rag_prompt}
            ]

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            save_chat_log(messages)
            return jsonify({"role": "model", "parts": [{"text": response.choices[0].message.content}]})

        # 3️⃣ Route: chitchat
        else:
            chat_messages = [
                {
                    "role": "assistant" if m["role"] == "model" else m["role"],
                    "content": m["parts"][0]["text"]
                }
                for m in data
            ]
            response = llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=chat_messages
            )
            save_chat_log(chat_messages)
            return jsonify({"role": "model", "parts": [{"text": response.choices[0].message.content}]})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def save_feedback():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        feedback = data.get("feedback")
        if not message or feedback not in ["like", "dislike"]:
            return jsonify({"error": "Invalid feedback data"}), 400
        client[DB_NAME]["ai_feedback"].insert_one({
            "message": message,
            "feedback": feedback,
            "timestamp": datetime.utcnow()
        })
        return jsonify({"status": "success"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

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
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
