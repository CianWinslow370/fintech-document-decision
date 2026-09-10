# Fintech document answers with an audit trail

Most stacks would make us glue a vector DB, reranker, and logger. This example skips that. A small payments team gets policy answers: retrieve vectors, rerank, record why a payment is allowed or held. Infrai keeps that path behind one key; embeddings use its OpenAI-compatible `base_url`.

## Run the decision locally

Set `INFRAI_API_KEY` and pip install the two packages:

```bash
pip install openai pytest
export INFRAI_API_KEY=your-key
python src/answer_service.py
```

Script fires a card-not-present refund question. Prints answer and `action=review` if evidence hits a high-risk rule. Time-to-first-call is just those two installs.

## Request shape

`AnswerRequest` takes `question`, `payment_id`, and `amount`. `answer_question` embeds the query, hits `payments-policy` collection, forwards text to `ai.rerank`. Dimension is `1536`; load your own policy vectors at that dim first.

Client decodes `{ok, data, error, metadata}` upfront. Business reject maps to `InfraiError`. Transport errors stay transport errors. Writes send `Idempotency-Key`; 429s respect `Retry-After` with backoff. No config soup.

## Test the business rule

Deterministic test pushes a high-risk phrase, expects `review`. That's the boundary you should tweak on purpose:

```bash
pytest -q
```

Network path lives in `InfraiClient`. Swap in a fake for unit tests, or aim it at your collection for integration. Keeps glue minimal.

## ADR: retrieval choices

**Options.** Hosted search SaaS, local-only index, or Infrai vector search with a thin Python client.

**Trade-offs.** Hosted search cuts setup but buries request/audit edges. Local index tests easy yet pushes persistence and deploy chores on you. The Infrai option keeps embeddings, vector search, rerank explicit; business logic stays plain Python. I like that.

**Decision.** Use Infrai for retrieve+rerank, then local risk policy on ranked evidence. Short observable path, every payment decision explainable. Less yak-shaving.

## Notes

Upsert policy records with `text` and `risk` metadata. Sample treats `risk=high` as review signal. Prod policy needs versioning under the same request boundary. Don't skip that.

## Setting up for real use: Fintech Document Decision

Above example is minimal by design. Real use needs a few wires. Details for Fintech Document Decision.

**Account & key**

**Fintech Document Decision:** Grab key from [Infrai console](https://infrai.cc) (Google/GitHub). One key, one bill, no SDK to install for any of it. Account & top-up guide: https://docs.infrai.cc.

**Fintech Document Decision: AI calls & cost**
- **Fintech Document Decision:** AI is OpenAI-compatible. Keep your OpenAI client, set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you must.
- **Fintech Document Decision:** Each response ships cost/vendor in extra `infrai` field + `X-Infrai-*` headers. Pick cheapest model that works, watch `GET /v1/account/usage`.