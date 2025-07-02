import numpy as np

class SemanticRouter():
    def __init__(self, embedding, routes):
        self.routes = routes
        self.embedding = embedding
        self.routesEmbedding = {}

        for route in self.routes:
            self.routesEmbedding[
                route.name
            ] = self.embedding.encode(route.samples)

    def get_routes(self):
        return self.routes
    
    def guide(self, query):
        queryEmbedding = self.embedding.encode([query])
        queryEmbedding = queryEmbedding / np.linalg.norm(queryEmbedding)
        scores = []

        for route in self.routes:
            routeEmbedding = self.routesEmbedding[route.name]
            routeEmbedding = routeEmbedding / np.linalg.norm(routeEmbedding)
            score = np.mean(np.dot(routeEmbedding, queryEmbedding.T).flatten())
            scores.append((score, route.name))

        if not scores:
            print("⚠️ semanticRouter: No routes found.")
            return None

        scores.sort(reverse=True)
        return scores[0]
    def run(self, query, topic):
        # Encode query
        query_vector = self.embedding_model.encode(query).tolist()

        # Tìm top 5 đoạn văn trong DB có topic giống
        results = self.collection.aggregate([
            {
                "$match": {
                    "topic": topic.replace("-", " ")  # topic bị slugify, nên cần map lại
                }
            },
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": 100,
                    "limit": 5
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "content": 1,
                    "url": 1
                }
            }
        ])

        context = "\n".join([f"- {doc['content']}" for doc in results])
        return f"""Khách hỏi: "{query}"\n\nThông tin liên quan:\n{context}\n\nHãy trả lời rõ ràng và hữu ích."""