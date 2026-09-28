# Product Feedback Intelligence Agent (FlowDesk)
## Phase 1: System Architecture & Design Specification

---

### 1. Executive Summary & Problem Statement

Modern product teams receive thousands of unstructured feedback items across diverse channels: support tickets, app reviews, NPS surveys, sales calls, and social posts. Traditional tooling either:
1. Stores feedback as flat, static rows in a database without deep temporal comprehension, or
2. Runs one-off stateless LLM queries that have no memory of past customer pain points or past product updates.

**Product Feedback Intelligence Agent** solves this by bridging structured operational data (PostgreSQL/SQLAlchemy) with state-of-the-art **persistent agent memory (Hindsight)** and ultra-fast LLM reasoning (**Groq**).

The agent acts as an autonomous Product Intelligence Analyst that remembers:
- Historical customer complaints and recurring bugs.
- Major product releases, bug fixes, and feature launches.
- Sentiment shifts and trend trajectory before vs. after releases.
- Evolution of customer requests across versions.

---

### 2. Workspace & Environment Inspection Findings

| Component | Status | Details |
|---|---|---|
| **Workspace Directory** | Clean | `c:\Users\HP\Desktop\Hackthons\Hackwithhyderabhad2` (Empty initialized root) |
| **Python** | Installed | Python 3.14.2 with `pip 26.1.2` |
| **Key Python Packages** | Ready | `fastapi 0.141.1`, `pydantic 2.13.4`, `sqlalchemy 2.0.46`, `httpx 0.28.1`, `pandas 3.0.0` |
| **Groq Client** | Verified | `groq 1.7.0` (tested installability on Python 3.14) |
| **Hindsight Client** | Verified | `hindsight-client 0.10.1` (official Python SDK with `retain`, `recall`, `reflect`) |
| **Node.js & npm** | Installed | Node `v24.15.0` & npm `11.12.1` available locally |
| **Docker** | Installed | Docker `29.8.0` (Docker Desktop) |
| **Database** | Configured | Dual-mode: SQLite for zero-setup local dev; PostgreSQL for Docker Compose |
| **API Keys / Env** | Unset | Will create `.env.example` with clear instructions for `GROQ_API_KEY`, `HINDSIGHT_API_KEY`, etc. |

---

### 3. Core System Architecture

```mermaid
flowchart TD
    subgraph Client_Layer ["Client Layer (React + Vite + Tailwind + Recharts)"]
        UI_Dash["Dashboard & KPIs"]
        UI_Feed["Feedback & CSV Ingestion"]
        UI_Issues["Emerging Issues & Themes"]
        UI_Changes["Product Releases & Changes"]
        UI_BeforeAfter["Before / After Analysis"]
        UI_Memory["Hindsight Memory Inspector"]
        UI_Chat["AI Product Intelligence Chat"]
    end

    subgraph Backend_Layer ["API Layer (FastAPI + Pydantic v2)"]
        API_Gateway["FastAPI Gateway & CORS"]
        Router_Feedback["/api/feedback & /upload"]
        Router_Analytics["/api/dashboard & /issues"]
        Router_Changes["/api/product-changes & /comparison"]
        Router_Agent["/api/chat & /agent/query"]
        Router_Memory["/api/memory (Hindsight Inspector)"]
    end

    subgraph Intelligence_Layer ["AI Agent & Intelligence Layer"]
        Agent_Orchestrator["Product Intelligence Agent"]
        Tool_Registry["Agent Toolset (Function Calling)"]
        Groq_LLM["Groq LLM Engine (openai/gpt-oss-120b)"]
        Triage_Pipeline["Feedback Analyzer & Summarizer"]
    end

    subgraph Storage_Layer ["Data & Long-Term Memory Layer"]
        subgraph Structured_DB ["Structured Business DB (PostgreSQL / SQLite)"]
            DB_Feedback[("Feedback Records")]
            DB_Customers[("Customers")]
            DB_Products[("Products")]
            DB_Changes[("Product Changes")]
            DB_Analysis[("Analysis Results")]
        end

        subgraph Hindsight_Memory ["Hindsight Persistent Memory Bank (flowdesk-bank)"]
            HS_Retain["retain() - Recurring Issues & Releases"]
            HS_Recall["recall() - TEMPR Multi-Strategy Search"]
            HS_Reflect["reflect() - Temporal Reasoning & Synthesis"]
            HS_Observations["Consolidated Observations & Proofs"]
        end
    end

    %% Client to Backend
    Client_Layer -->|REST / JSON| API_Gateway
    API_Gateway --> Router_Feedback
    API_Gateway --> Router_Analytics
    API_Gateway --> Router_Changes
    API_Gateway --> Router_Agent
    API_Gateway --> Router_Memory

    %% Backend to Ingestion & DB
    Router_Feedback --> Triage_Pipeline
    Triage_Pipeline --> Groq_LLM
    Router_Feedback --> DB_Feedback
    Router_Analytics --> Structured_DB
    Router_Changes --> DB_Changes

    %% Backend to Agent & Tools
    Router_Agent --> Agent_Orchestrator
    Agent_Orchestrator --> Groq_LLM
    Agent_Orchestrator --> Tool_Registry
    Tool_Registry --> Structured_DB
    Tool_Registry --> Hindsight_Memory

    %% Ingestion to Hindsight Memory
    Triage_Pipeline -.->|High-signal memories| HS_Retain
    Router_Changes -.->|Release milestones| HS_Retain
    Router_Memory --> Hindsight_Memory
```

---

### 4. Memory vs. Database Strategy

A pivotal requirement of this project is avoiding the misconception that Hindsight replaces PostgreSQL, or vice versa:

| Dimension | PostgreSQL / SQLite (Structured Storage) | Hindsight (Persistent Agent Memory) |
|---|---|---|
| **Purpose** | ACID transactional store for operational application data | Episodic & semantic memory for AI agent reasoning across time |
| **Typical Data** | Exact row ID, timestamp, customer email, raw text, star rating, product FK | "Customers in Q3 frequently report slow uploads on files > 50MB." |
| **Query Pattern** | `SELECT COUNT(*), AVG(rating) FROM feedback WHERE ...` | Multi-strategy TEMPR search + LLM reflection on trends |
| **Retention Policy** | Every single feedback item (raw truth) | High-signal synthesized observations, release milestones, behavioral shifts |
| **Evolution** | Rows are static once inserted | Observations continuously refine, deduplicate, and track evidence count |

#### Hindsight Memory Policy:
1. **WHAT is stored**:
   - Significant recurring pain points (e.g., "File uploads timing out on large videos").
   - Feature requests reaching critical mass.
   - Product change events (e.g., "Release 3.2: Chunked Upload Optimizer released on 2026-10-15").
   - Observed outcome shifts (e.g., "Feedback post-Release 3.2 indicates upload complaints decreased by 75%").
2. **WHAT is NOT stored**:
   - Raw individual greetings ("Hi", "Thanks", trivial noise).
   - Sensitive PII (passwords, payment cards, tokens).
   - Temporary UI state or session cookies.
3. **WHEN it is stored**:
   - During feedback batch ingestion when sentiment is strongly negative or marked as high-urgency bug/feature request.
   - When a Product Manager records a new Product Change.
   - When the agent conducts a Before/After comparison analysis.

---

### 5. Proposed Folder Structure

```
Hackwithhyderabhad2/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── HINDSIGHT.md
│   ├── API_SPEC.md
│   └── DEMO_SCRIPT.md
├── data/
│   ├── sample_feedback.csv
│   └── generate_sample_data.py
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── feedback.py
│   │   │   ├── customer.py
│   │   │   ├── product.py
│   │   │   ├── product_change.py
│   │   │   └── analysis.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── feedback.py
│   │   │   ├── product_change.py
│   │   │   ├── dashboard.py
│   │   │   ├── chat.py
│   │   │   └── memory.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes_feedback.py
│   │   │   ├── routes_dashboard.py
│   │   │   ├── routes_product_changes.py
│   │   │   ├── routes_chat.py
│   │   │   └── routes_memory.py
│   │   ├── hindsight/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── memory_manager.py
│   │   │   └── bank_config.py
│   │   ├── groq/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   └── prompts.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── product_agent.py
│   │   │   └── tools.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── triage_service.py
│   │       ├── analytics_service.py
│   │       └── comparison_service.py
│   └── tests/
│       ├── test_feedback.py
│       ├── test_analytics.py
│       ├── test_hindsight.py
│       └── test_agent_tools.py
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx
        ├── index.css
        ├── api/
        │   └── client.ts
        ├── types/
        │   └── index.ts
        ├── layouts/
        │   ├── MainLayout.tsx
        │   ├── Sidebar.tsx
        │   └── Header.tsx
        ├── pages/
        │   ├── DashboardPage.tsx
        │   ├── FeedbackPage.tsx
        │   ├── UploadPage.tsx
        │   ├── IssuesPage.tsx
        │   ├── FeatureRequestsPage.tsx
        │   ├── ProductChangesPage.tsx
        │   ├── BeforeAfterPage.tsx
        │   ├── MemoryDemoPage.tsx
        │   └── AssistantPage.tsx
        └── components/
            ├── MetricCard.tsx
            ├── SentimentBadge.tsx
            ├── SentimentChart.tsx
            ├── VolumeChart.tsx
            ├── TopicsChart.tsx
            ├── MemoryCard.tsx
            ├── ChatWindow.tsx
            └── BeforeAfterCard.tsx
```

---

### 6. Database Design (Entity Relationship Model)

```mermaid
erDiagram
    PRODUCT ||--o{ CUSTOMER : has
    PRODUCT ||--o{ PRODUCT_CHANGE : undergoes
    PRODUCT ||--o{ FEEDBACK : receives
    CUSTOMER ||--o{ FEEDBACK : submits
    FEEDBACK ||--o| ANALYSIS_RESULT : has

    PRODUCT {
        string id PK
        string name
        string description
        datetime created_at
    }

    CUSTOMER {
        string id PK
        string name
        string email
        string company
        string tier "Free | Pro | Enterprise"
        datetime created_at
    }

    PRODUCT_CHANGE {
        string id PK
        string product_id FK
        string change_name
        string description
        string category "Performance | UI | Feature | BugFix"
        date release_date
        string expected_outcome
        datetime created_at
    }

    FEEDBACK {
        string id PK
        string product_id FK
        string customer_id FK
        string customer_name
        string source "App Review | Support Ticket | Survey | Email | Feature Request"
        text feedback_text
        int rating "1 to 5"
        date feedback_date
        string category
        string sentiment "positive | negative | neutral"
        float sentiment_score "-1.0 to 1.0"
        datetime created_at
    }

    ANALYSIS_RESULT {
        string id PK
        string feedback_id FK
        string topic
        string urgency "low | medium | high | critical"
        string issue_type "bug | feature_request | usability | pricing"
        boolean is_recurring
        text short_summary
        string entities "JSON array"
        datetime created_at
    }
```

---

### 7. REST API Design

| Method | Endpoint | Description | Status Codes |
|---|---|---|---|
| `POST` | `/api/feedback` | Ingest single feedback item (stores to DB + triages + selective Hindsight retain) | 201, 400 |
| `GET` | `/api/feedback` | Paginated, filtered list of feedback (by product, sentiment, source, category, date) | 200 |
| `GET` | `/api/feedback/{id}` | Retrieve individual feedback record with full AI analysis metadata | 200, 404 |
| `POST` | `/api/feedback/upload` | Upload CSV with progress stats (Total, Processed, Validated, Ingested) | 200, 400, 422 |
| `GET` | `/api/dashboard` | Aggregated metrics: sentiment breakdown, volume over time, top issues, sources | 200 |
| `GET` | `/api/issues` | Emerging and recurring issues with growth trajectory and sentiment impact | 200 |
| `GET` | `/api/feature-requests`| Top feature requests with mention count, sentiment, and sample quotes | 200 |
| `POST` | `/api/product-changes`| Log a new product change milestone (stores in DB + retains in Hindsight) | 201, 400 |
| `GET` | `/api/product-changes` | List product changes with associated metadata | 200 |
| `GET` | `/api/product-changes/{id}/comparison` | Before vs. After release statistical & AI-synthesized comparative analysis | 200, 404 |
| `POST` | `/api/chat` | AI Assistant query execution (Groq + Function Calling + Hindsight Memory) | 200, 500 |
| `GET` | `/api/memory` | Direct inspection of Hindsight memory bank observations, facts, and beliefs | 200 |
| `POST` | `/api/memory/search` | Search Hindsight memory bank via `recall()` | 200 |
| `POST` | `/api/memory/reflect` | Query Hindsight reasoning engine via `reflect()` | 200 |

---

### 8. AI Agent Workflow & Tooling

The AI Agent does **not** rely on brute-force context stuffing. Instead, it utilizes Groq Function Calling with safe deterministic tools:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend
    participant Agent as Product Intelligence Agent
    participant Groq as Groq LLM (openai/gpt-oss-120b)
    participant Tools as Agent Tool Registry
    participant DB as PostgreSQL / SQLite
    participant Hindsight as Hindsight Memory Bank

    User->>Frontend: Asks: "Did feedback on uploads improve after the 3.2 release?"
    Frontend->>Agent: POST /api/chat {message}
    Agent->>Groq: Chat Completion with available tools: [compare_before_after, recall_memory, get_feedback]
    Groq-->>Agent: Tool Call: compare_before_after(product_id, release_date) + recall_memory("upload performance")
    
    par Query Structured DB
        Agent->>Tools: execute compare_before_after()
        Tools->>DB: Query sentiment & volume metrics 30d before vs 30d after
        DB-->>Tools: Metrics: Before=42 neg, After=8 neg
        Tools-->>Agent: Structured comparison results
    and Query Hindsight Memory
        Agent->>Tools: execute recall_memory("upload performance")
        Tools->>Hindsight: recall(bank_id="flowdesk-bank", query="upload performance issues")
        Hindsight-->>Tools: Consolidated Observations & Quotes
        Tools-->>Agent: Memory items (historical complaints & release intention)
    end

    Agent->>Groq: Final Prompt: Context + Comparison Metrics + Hindsight Memories
    Groq-->>Agent: Contextual, evidence-backed answer noting post-release reduction without claiming unproven causation
    Agent-->>Frontend: Return formatted response + memory citations
    Frontend-->>User: Display rich answer with interactive metrics & memory proof
```

---

### 9. Demo Scenario & Fictional Company: "FlowDesk"

- **Company**: **FlowDesk** — Modern collaboration and asynchronous workflow suite for fast-moving engineering teams.
- **Product Modules**: Large file uploads, interactive reporting dashboard, Slack/Jira integration, notification engine.
- **Timeline Storyline**:
  - **T1 (Initial period)**: Flood of customer feedback: "Uploading screen recordings over 100MB times out", "Upload speed is agonizingly slow".
  - **T2 (Agent Retention)**: The agent ingests feedback and retains high-priority memory: *"Recurring customer pain point: Large file uploads fail or degrade performance."*
  - **T3 (Product Change)**: FlowDesk PM logs release: *"Release 3.2: Chunked Upload Optimizer & S3 Multipart Engine"* on 2026-10-15.
  - **T4 (Post-Release Feedback)**: New feedback arrives: "Uploads are blazing fast now", "Tested with a 2GB log file, uploaded in 10s".
  - **T5 (Intelligence Demonstration)**:
    - User asks: *"What recurring performance issues have customers raised historically, and how did Release 3.2 impact them?"*
    - The Agent retrieves both the historical complaint memory from Hindsight and statistical delta from the DB, delivering a cohesive timeline insight that no stateless LLM could achieve.

---

### 10. Hackathon Implementation Roadmap

- **PHASE 1**: System Architecture, Environment Configuration, and Design Specification (Current)
- **PHASE 2**: Database Schema, SQLAlchemy Models, and DB Engine Configuration
- **PHASE 3**: Feedback Ingestion Service & Validation
- **PHASE 4**: AI Feedback Triage & Automated Classification Pipeline
- **PHASE 5**: Groq LLM Client & Prompt Engineering Framework
- **PHASE 6**: Hindsight Persistent Memory Integration (`retain`, `recall`, `reflect`)
- **PHASE 7**: AI Agent Safe Function Calling Toolset
- **PHASE 8**: AI Conversational Assistant Engine & Chat API
- **PHASE 9**: SaaS Dashboard Aggregations & Analytics Services
- **PHASE 10**: Product Change Tracking & Release Milestone Manager
- **PHASE 11**: Before/After Statistical & AI Comparative Analysis
- **PHASE 12**: Dedicated Hindsight Memory & Learning Interactive Demo Interface
- **PHASE 13**: Automated Testing Suite (Backend Services, Tools & APIs)
- **PHASE 14**: Docker & Docker Compose Containerization
- **PHASE 15**: Production Hardening, CORS, Error Handling & Graceful Degradation
- **PHASE 16**: Comprehensive Documentation, HINDSIGHT.md, and OpenAPI Reference
- **PHASE 17**: Realistic Synthetic Dataset Generation & 3-5 Minute Demo Script
