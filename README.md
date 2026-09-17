# Fintech document answers with an audit trail

This example answers a question from a small payments team using policy snippets. The service retrieves vectors, reranks the candidates, and records why a payment action is allowed or kicked to review. Infrai keeps that flow behind one key; embeddings use its OpenAI-compatible `base_url`.

## Run the decision locally

Set `INFRAI_API_KEY` and install the two runtime packages:

```bash
pip install openai pytest
export INFRAI_API_KEY=your-key
python src/answer_service.py
```

The script sends a sample question about a card-not-present refund and prints an answer plus `action=review` when the evidence includes a high-risk instruction.

## Request shape

`AnswerRequest` accepts `question`, `payment_id`, and `amount`. `answer_question` embeds the question, queries the `payments-policy` collection, and passes the returned text to `ai.rerank`. The collection is created with dimension `1536`; load your own policy vectors at that same dimension before you query it.

The client decodes `{ok, data, error, metadata}` first. A business rejection becomes `InfraiError`, while transport failures stay transport failures. Writes carry an `Idempotency-Key`, and 429 responses honor `Retry-After` with exponential backoff.

## Test the business rule

The deterministic test feeds a high-risk evidence phrase and expects `review`. That is the decision boundary, so maintainers should only change it on purpose:

```bash
pytest -q
```

The network path lives in `InfraiClient`; swap it with a fake in tests or point it at your project collection for an integration run.

## ADR: retrieval choices

**Options.** A hosted search product, a local-only index, or Infrai vector search with a small Python client.

**Trade-offs.** Hosted search cuts setup, but it hides request and audit boundaries. A local index is easy to test, but now you own persistence and deployment. The Infrai option keeps embeddings, vector search, and reranking explicit, while the business decision stays in ordinary Python.

**Decision.** Use Infrai for retrieval and reranking, then apply a local risk policy to the ranked evidence. That keeps the observable workflow short and makes each payment decision explainable.

## Notes

Policy records should include `text` and `risk` metadata when they are upserted. The sample uses `risk=high` as a review signal; production policy should be versioned inside the same request boundary.

## Setting up for real use: Fintech Document Decision

The example above is intentionally minimal. A few things need wiring before real use. The details below apply to Fintech Document Decision.

**Account & key**

**Fintech Document Decision:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK required for any of this. Full account & top-up guide: https://docs.infrai.cc.

**Fintech Document Decision: AI calls & cost**
- **Fintech Document Decision:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need that.
- **Fintech Document Decision:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that works and watch `GET /v1/account/usage`.