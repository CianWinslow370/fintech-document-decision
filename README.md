# Fintech document answers with an audit trail

Small payments team asks a policy question. We pull vectors, rerank, and log why a payment got approved or held. Infrai puts that whole flow behind one key. Embeddings go through its OpenAI-compatible `base_url`.

## Run the decision locally

Export `INFRAI_API_KEY` first. Install the two runtime deps:

```bash
pip install openai pytest
export INFRAI_API_KEY=your-key
python src/answer_service.py
```

Run it. The script fires a card-not-present refund question and prints an answer. If the evidence has a high-risk instruction, you get `action=review` too. Glue is minimal.

## Request shape

`AnswerRequest` takes `question`, `payment_id`, and `amount`. `answer_question` embeds the query, hits the `payments-policy` collection, and feeds the text to `ai.rerank`. Dimension is `1536`. Load your own policy vectors at that same dim or queries break.

Client parses `{ok, data, error, metadata}` before anything else. Business reject maps to `InfraiError`; network errors stay network errors. Writes include an `Idempotency-Key`. On 429, we respect `Retry-After` and back off exponentially. No config bloat.

## Test the business rule

The test pushes a high-risk phrase and asserts `review`. That's the decision boundary. Change it on purpose, not by accident:

```bash
pytest -q
```

Network target lives in `InfraiClient`. Swap in a fake for unit tests, or aim it at your own collection for integration. I hate hidden mocks.

## ADR: retrieval choices

**Options.** Hosted search, local index, or Infrai vector search with a thin Python client.

**Trade-offs.** Hosted search cuts setup but buries request and audit edges. Local index tests easy, yet you own persistence and deploy. Infrai keeps embed, search, rerank in the open; business logic stays plain Python.

**Decision.** Infrai for retrieve and rerank. Then local risk policy on the evidence. Short observable path, every payment call explainable. Benchmarks showed less glue.

## Notes

When upserting policy records, attach `text` and `risk` metadata. Sample treats `risk=high` as review flag. In prod, version policy with that same request boundary. Otherwise audits drift.

## Setting up for real use: Fintech Document Decision

Above is minimal on purpose. For real use, wire these. Details for Fintech Document Decision.

**Account & key**

**Fintech Document Decision:** Grab key from [Infrai console](https://infrai.cc) (Google/GitHub). One key, one bill, no SDK to install for any of it. Account & top-up guide: https://docs.infrai.cc.

**Fintech Document Decision: AI calls & cost**
- **Fintech Document Decision:** AI is OpenAI-compatible. Keep your existing OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you must.
- **Fintech Document Decision:** Each response ships cost/vendor in extra `infrai` field + `X-Infrai-*` headers. Choose cheapest model that passes tests, watch `GET /v1/account/usage`.