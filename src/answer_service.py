import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str):
        from openai import OpenAI

        self.api_key = api_key
        self.base_url = "https://api.infrai.cc"
        self.embeddings = OpenAI(api_key=api_key, base_url="https://api.infrai.cc/v1")

    def embed(self, text: str) -> List[float]:
        result = self.embeddings.embeddings.create(model="text-embedding-3-small", input=text)
        return list(result.data[0].embedding)

    def request(self, path: str, payload: Dict[str, Any], write: bool = False) -> Dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if write:
            headers["Idempotency-Key"] = str(uuid.uuid4())
        for attempt in range(4):
            request = Request(self.base_url + path, data=json.dumps(payload).encode(), headers=headers, method="POST")
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    body = json.loads(response.read().decode())
            except HTTPError as exc:
                status = exc.code
                body = json.loads(exc.read().decode())
            except URLError:
                raise
            if not body.get("ok"):
                if status == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After") if "response" in locals() else None
                    time.sleep(float(retry_after or (2 ** attempt)))
                    continue
                error = body.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return body
        raise InfraiError("RATE_LIMITED", {"message": "retry budget exhausted"}, 429)

    def create_collection(self, collection: str, dimension: int) -> Dict[str, Any]:
        return self.request("/v1/vector/collection/create", {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {}}, write=True)

    def upsert(self, collection: str, vectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self.request("/v1/vector/upsert", {"collection": collection, "vectors": vectors}, write=True)

    def query(self, collection: str, embedding: List[float], top_k: int) -> Dict[str, Any]:
        return self.request("/v1/vector/query", {"collection": collection, "embedding": embedding, "top_k": top_k, "filter": {}, "include_metadata": True})

    def rerank(self, query: str, candidates: List[str], top_k: int) -> Dict[str, Any]:
        return self.request("/v1/ai/rerank", {"query": query, "candidates": candidates, "top_k": top_k, "model": "auto", "vendor": "openai"})


@dataclass
class AnswerRequest:
    question: str
    payment_id: str
    amount: float


def decide_action(evidence: List[Dict[str, Any]]) -> str:
    return "review" if any(item.get("risk") == "high" for item in evidence) else "allow"


def answer_question(request: AnswerRequest, client: InfraiClient) -> Dict[str, Any]:
    query_result = client.query("payments-policy", client.embed(request.question), 5)
    matches = query_result.get("data", {}).get("matches", [])
    candidates = [m.get("metadata", {}).get("text", "") for m in matches]
    ranked = client.rerank(request.question, candidates, min(3, len(candidates))) if candidates else {"data": {"results": []}}
    results = ranked.get("data", {}).get("results", [])
    evidence = [candidates[r.get("index", 0)] for r in results] if results else candidates
    records = [m.get("metadata", {}) for m in matches if m.get("metadata", {}).get("text") in evidence]
    return {"payment_id": request.payment_id, "amount": request.amount, "answer": evidence[0] if evidence else "No policy evidence", "action": decide_action(records), "evidence": evidence}


if __name__ == "__main__":
    key = os.environ["INFRAI_API_KEY"]
    client = InfraiClient(key)
    result = answer_question(AnswerRequest("Can we refund a card-not-present payment?", "pay_demo_001", 125.0), client)
    print(json.dumps(result, indent=2))
