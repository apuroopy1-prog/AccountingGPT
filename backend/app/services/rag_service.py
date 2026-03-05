"""
RAG (Retrieval-Augmented Generation) service using TF-IDF + cosine similarity.
scikit-learn is already installed — no additional dependencies needed.
Index is in-memory per user, rebuilt lazily when invalidated.
"""
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self._vectorizers: dict[int, TfidfVectorizer] = {}
        self._matrices = {}  # user_id → sparse TF-IDF matrix
        self._documents: dict[int, list[dict]] = {}  # user_id → [{text, type, metadata}]

    def has_index(self, user_id: int) -> bool:
        return user_id in self._vectorizers

    def invalidate(self, user_id: int) -> None:
        """Clear the index for a user so it is rebuilt on the next search."""
        self._vectorizers.pop(user_id, None)
        self._matrices.pop(user_id, None)
        self._documents.pop(user_id, None)

    def index_transactions(self, user_id: int, transactions: list) -> None:
        docs = [
            {
                "text": (
                    f"{t.date.strftime('%Y-%m-%d')} {t.description} "
                    f"{t.category or ''} {t.merchant or ''} {t.account or ''} "
                    f"${t.amount:+.2f}"
                ),
                "type": "transaction",
                "metadata": {
                    "id": t.id,
                    "date": t.date.strftime("%Y-%m-%d"),
                    "description": t.description,
                    "amount": t.amount,
                    "category": t.category,
                    "account": t.account,
                },
            }
            for t in transactions
        ]
        self._build_index(user_id, docs)

    def index_invoices(self, user_id: int, invoices: list) -> None:
        existing = self._documents.get(user_id, [])
        invoice_docs = [
            {
                "text": (
                    f"invoice {inv.filename} status:{inv.status} "
                    f"{inv.ocr_text[:300] if inv.ocr_text else ''}"
                ),
                "type": "invoice",
                "metadata": {
                    "id": inv.id,
                    "filename": inv.filename,
                    "status": inv.status,
                },
            }
            for inv in invoices
        ]
        # Merge with existing transaction docs, if any
        txn_docs = [d for d in existing if d["type"] == "transaction"]
        self._build_index(user_id, txn_docs + invoice_docs)

    def search(self, user_id: int, query: str, n: int = 5) -> list[dict]:
        if not self.has_index(user_id):
            return []
        docs = self._documents[user_id]
        if not docs:
            return []
        try:
            query_vec = self._vectorizers[user_id].transform([query])
            scores = cosine_similarity(query_vec, self._matrices[user_id]).flatten()
            top_indices = scores.argsort()[-n:][::-1]
            return [docs[i] for i in top_indices if scores[i] > 0.01]
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return []

    def _build_index(self, user_id: int, docs: list[dict]) -> None:
        if not docs:
            return
        texts = [d["text"] for d in docs]
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=10000)
        matrix = vectorizer.fit_transform(texts)
        self._vectorizers[user_id] = vectorizer
        self._matrices[user_id] = matrix
        self._documents[user_id] = docs
        logger.info(f"RAG index built for user {user_id}: {len(docs)} documents")


# Module-level singleton shared across all requests
rag_service = RAGService()
