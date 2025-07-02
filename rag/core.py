import pymongo
from IPython.display import Markdown
from embeddings import SentenceTransformerEmbedding, EmbeddingConfig
from sentence_transformers.util import cos_sim
import traceback

class RAG:
    def __init__(self, 
                 mongodbUri: str,
                 dbName: str,
                 dbCollection: str,
                 llm,
                 embeddingName: str = 'keepitreal/vietnamese-sbert'):
        self.client = pymongo.MongoClient(mongodbUri)
        self.db = self.client[dbName]
        self.collection = self.db[dbCollection]
        self.embedding_model = SentenceTransformerEmbedding(
            EmbeddingConfig(name=embeddingName)
        )
        self.llm = llm

    def get_embedding(self, text):
        if not text.strip():
            return []
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            print(f"❌ Error generating embedding: {e}")
            return []

    def vector_search(self, user_query: str, limit=5, topic=None):
        """
        Vector search using cosine similarity (manual method for Free Tier)
        """
        query_embedding = self.get_embedding(user_query)
        if not query_embedding:
            return []

        # Get all documents with embedding
        filter_query = {"embedding": {"$exists": True, "$type": "array"}}
        if topic:
            filter_query["topic"] = topic
        docs = list(self.collection.find(filter_query))

        # Calculate cosine similarity
        scored = []
        for doc in docs:
            score = cos_sim([query_embedding], [doc["embedding"]])[0][0].item()
            doc["score"] = score
            scored.append(doc)

        top_docs = sorted(scored, key=lambda d: d["score"], reverse=True)[:limit]
        for doc in top_docs:
            doc.pop("embedding", None)
        return top_docs

    def enhance_prompt(self, user_query: str):
        search_results = self.vector_search(user_query, limit=5)
        context = ""
        if isinstance(search_results, str):
            context = search_results
        else:
            for i, item in enumerate(search_results, 1):
                title = item.get('title', 'N/A')
                price = item.get('current_price', 'Liên hệ')
                promotions = str(item.get('product_promotion', '')).strip() or 'Không có'
                colors = ', '.join(item.get('color_options', [])) if isinstance(item.get('color_options'), list) else 'Không có'
                specs = item.get('product_specs', '').replace("<br>", "; ") if isinstance(item.get('product_specs'), str) else 'Không có'
                url = item.get('url', '')

                context += f"### {i}. **{title}**\n"
                context += f"- #### **Giá**: {price}\n"
                context += f"- #### **Ưu đãi**: {promotions}\n"
                context += f"- #### **Màu sắc**: {colors}\n"
                context += f"- #### **Thông số**: {specs}\n"
                if url:
                    context += f"- *[Xem chi tiết sản phẩm]({url})*\n"
                context += "\n"

        final_prompt = f"""Bạn là một chuyên gia tư vấn bán điện thoại tại cửa hàng **DBIZ**.

**Câu hỏi của khách hàng:** _{user_query}_

Dưới đây là chi tiết sản phẩm:

{context}
Vui lòng trả lời khách một cách thân thiện, dễ hiểu và rõ ràng!  
Nếu khách hàng muốn biết thêm, hãy mời họ bấm vào link để xem chi tiết sản phẩm.
"""
        return final_prompt

    def run(self, query, topic=None):
        try:
            print(f"🧠 [run()] Query: {query}")
            if topic:
                print(f"🧠 [run()] Topic: {topic}")

            query_embedding = self.get_embedding(query)
            if not query_embedding:
                print("⚠️ [run()] Failed to generate query embedding.")
                return "❌ Không thể tạo embedding cho câu hỏi."

            print(f"🧠 [run()] Embedding OK, length: {len(query_embedding)}")

            search_results = self.vector_search(query, limit=10, topic=topic)
            print(f"🧠 [run()] Retrieved {len(search_results)} results")

            context = "\n\n".join([
                f"{doc['content']} (Nguồn: {doc.get('url', 'không rõ')})"
                for doc in search_results if "content" in doc
            ])
            if not context:
                print("⚠️ [run()] No relevant documents found.")
                context = "Không tìm thấy thông tin phù hợp trong cơ sở dữ liệu."
                
            print("===================================================== {Start Data from Db} ========================================")
            print(context)
            print("===================================================== {End Data from Db} ========================================")
            print("===================================================== {Start Truyền dữ liệu lên LLM từ Prompt và Data trên DB} ========================================")
            prompt = f"""Khách hỏi: \"{query}\"\n\nDưới đây là một số thông tin liên quan:\n\n{context}\n\nTrả lời một cách tự nhiên và chi tiết."""
            print(prompt)
            print("===================================================== {End Truyền dữ liệu lên LLM từ Prompt và Data trên DB} ========================================")
            return prompt

        except Exception as e:
            print("❌ [run()] Exception occurred:", e)
            traceback.print_exc()
            return f"❌ Lỗi khi thực hiện tìm kiếm vector: {str(e)}"
