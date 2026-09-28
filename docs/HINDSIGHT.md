# Hindsight Persistent Agent Memory Specification & Architecture

## 1. What Hindsight Is

**Hindsight** is a state-of-the-art open-source memory system designed specifically for autonomous AI agents. Unlike standard RAG (Retrieval-Augmented Generation) which performs flat vector similarity searches over static text chunks, Hindsight provides:
- **Dedicated Memory Banks**: Isolated, tenant-specific memory stores (e.g. `flowdesk-feedback-bank`).
- **Structured Knowledge Hierarchy**: Manages World Facts, Experiences, and Consolidated Observations.
- **TEMPR Multi-Strategy Retrieval**: Runs temporal reasoning, entity graphs, semantic vectors, and keyword searches concurrently.
- **Continuous Observation Consolidation**: As similar memories are retained over time, Hindsight automatically consolidates them, deduplicates repetitive facts, tracks proof counts (e.g. *"Upload performance issue supported by 42 proofs"*), and updates beliefs without forgetting history.
- **Agentic Reflection (`reflect()`)**: Synthesizes reasoned answers over the memory bank rather than merely returning disjointed raw chunks.

---

## 2. Why We Use Hindsight in Product Feedback Intelligence

Product teams face a fundamental challenge with traditional LLMs: **statelessness**.
When a product manager asks:
> *"Did customer feedback about file uploads change after we shipped our optimization?"*

A traditional chatbot has no persistent awareness:
- It doesn't remember the 40 complaints submitted two weeks ago.
- It doesn't know when the engineering team deployed Release 3.2.
- It cannot correlate past customer statements with present outcomes.

Hindsight provides the agent with persistent long-term episodic memory, enabling it to act as an experienced product analyst that has followed the product lifecycle over months.

---

## 3. Memory vs. Database: The Core Distinction

| Dimension | Structured Database (PostgreSQL / SQLite) | Hindsight Agent Memory (`flowdesk-feedback-bank`) |
|---|---|---|
| **Role** | Ground-truth transactional record of every event | Episodic, semantic & temporal memory for reasoning |
| **Data Format** | Exact SQL rows (`id`, `rating`, `date`, `customer_id`, `text`) | High-signal synthesized observations & release milestones |
| **Typical Query** | `SELECT COUNT(*), AVG(rating) FROM feedbacks WHERE ...` | `recall("upload performance")` or `reflect("How have complaints evolved?")` |
| **Consolidation** | Rows are static once inserted | Deduplicated observations with growing proof counts |
| **Query Mechanism** | Deterministic relational algebra | TEMPR multi-strategy search + LLM reflection |

---

## 4. Memory Policy

### What We Store
1. **Recurring Customer Pain Points**:
   - High-urgency bugs and severe performance degradation (e.g. *"Recurring Customer Pain Point: File uploads fail or timeout on videos > 100MB"*).
2. **Key Feature Requests**:
   - User requests reaching significant interest (e.g. *"Customer Feature Request: Bulk export of tickets to CSV"*).
3. **Product Release Milestones**:
   - Dates, descriptions, and intended outcomes of product releases (e.g. *"Release 3.2: Chunked Upload Optimizer released on 2026-10-15"*).
4. **Observed Historical Outcomes**:
   - Statistical shifts observed before vs. after releases (e.g. *"Historical Release Outcome: Following Release 3.2, negative feedback regarding uploads dropped by 85%"*).

### What We Avoid Storing
- Routine greetings ("Hello", "Thanks", polite filler).
- Ephemeral UI session state.
- Sensitive credentials or personal PII (credit cards, passwords).
- Low-confidence noise.

### When Memories are Created
1. **During Feedback Triage**:
   - When a feedback item is classified with high or critical urgency, or marked as a recurring problem.
2. **When a Product Change is Registered**:
   - When a Product Manager records a release milestone via `/api/product-changes`.
3. **During Before/After Comparative Analysis**:
   - When the agent analyzes metric deltas before vs. after a release date and confirms an observable shift.

---

## 5. How Memories are Retrieved: TEMPR Search

When an agent or user queries Hindsight via `recall()`, Hindsight executes four search strategies in parallel:
1. **Temporal Reasoning**: Distinguishes between what happened *before* an event versus *after*.
2. **Entity Graphs**: Links customers, product modules, and error codes across independent feedback submissions.
3. **Meaning & Semantic Similarity**: Matches conceptual intent (e.g. "slow transfer" matches "bandwidth bottleneck").
4. **Keywords & Proof Counts**: Weighs consolidated observations backed by multiple proofs higher than isolated one-off mentions.

---

## 6. Before-Memory vs. After-Memory Comparison

| User Question | Without Hindsight (Stateless LLM) | With Hindsight Agent Memory |
|---|---|---|
| *"What are customers complaining about most?"* | Looks only at whatever immediate rows fit into the current prompt context window. | Recalls durable consolidated observations across weeks with exact evidence proof counts. |
| *"Have we seen this upload issue before?"* | Answers *"I don't have access to past session history."* | Recalls historical complaints from September and quotes specific customer statements. |
| *"Did customer feedback improve after Release 3.2?"* | Cannot connect the release milestone to customer statements without manual prompt engineering. | Correlates pre-release complaints, the release objective, and post-release sentiment shift into an evidence-backed timeline insight. |

---

## 7. Official Hindsight Python SDK Integration

Hindsight is integrated using the official `hindsight-client` Python package:

```python
from hindsight_client import Hindsight

# 1. Initialize client
client = Hindsight(
    base_url="https://api.hindsight.vectorize.io",
    api_key="your_hindsight_api_key",
)

# 2. Retain: Store a high-signal observation or release milestone
client.retain(
    bank_id="flowdesk-feedback-bank",
    content="Recurring Customer Pain Point: File uploads fail at 98% on large videos.",
    context="Support ticket by Sarah Connor on 2026-10-01",
    tags=["feedback", "pain_point", "file_uploads", "performance"],
    metadata={"urgency": "critical", "rating": "1"},
)

# 3. Recall: Multi-strategy TEMPR search
results = client.recall(
    bank_id="flowdesk-feedback-bank",
    query="What performance issues have been reported?",
    limit=5,
)
for memory in results.results:
    print(memory.text, memory.score)

# 4. Reflect: Synthesize reasoned answer over the bank
answer = client.reflect(
    bank_id="flowdesk-feedback-bank",
    query="Did file upload complaints change after our October 15 release?",
)
print(answer.response)
```

---

## 8. Configuration Parameters

In `.env`:
```bash
# Hindsight Configuration
HINDSIGHT_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=your_hindsight_api_key_here
HINDSIGHT_BANK_ID=flowdesk-feedback-bank
HINDSIGHT_API_LLM_PROVIDER=groq
HINDSIGHT_API_LLM_API_KEY=gsk_...
```
