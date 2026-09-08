# ScanBite — Architecture Diagrams

Companion to [`ARCHITECTURE.md`](ARCHITECTURE.md). These diagrams describe the
system **as currently built** (milestone-1 scaffold). Components that are
planned but not yet implemented are drawn with dashed borders.

---

## 1. System context

```mermaid
flowchart TB
    subgraph client["Client tier"]
        RN["React Native + Expo<br/><i>iOS · Android</i><br/>camera · onboarding · results"]
    end

    subgraph gateway["API tier — Node :4000"]
        EX["Express app"]
        AUTH["auth<br/>signup · login · refresh"]
        PROF["profile<br/>diet · health · allergens"]
        SCAN["scans<br/>orchestration · history · XP"]
        JWT["JWT middleware"]
    end

    subgraph ai["AI tier — Python FastAPI :8000"]
        OCR["ocr.py<br/>OpenCV + Tesseract"]
        ING["ingredients.py<br/>parse + classify"]
        RULES["diet_rules.py<br/><b>deterministic</b>"]
        SCORE["scoring.py<br/><b>deterministic</b>"]
        AGENT["label_agent.py<br/>Claude explanation"]
    end

    subgraph data["Data tier"]
        PG[("PostgreSQL<br/>7 tables")]
        REDIS[("Redis<br/>queue · cache")]
        S3[("S3<br/>label images")]
    end

    ANTHROPIC{{"Anthropic API"}}

    RN -->|"HTTPS · JSON · multipart"| EX
    EX --> JWT
    JWT --> AUTH & PROF & SCAN
    AUTH & PROF & SCAN <--> PG
    SCAN -->|"internal HTTP<br/>images + profile"| OCR
    OCR --> ING --> RULES --> SCORE --> AGENT
    AGENT <-->|"structured facts only"| ANTHROPIC

    SCAN -.->|"planned"| REDIS
    SCAN -.->|"planned"| S3

    classDef planned stroke-dasharray: 5 5,opacity:0.55
    class REDIS,S3 planned
```

**Why two backend services:** Node owns the mobile-facing REST contract, auth,
and sessions. Python owns OCR/NLP/LLM orchestration, where the ecosystem is
strongest. They scale independently — the AI service is the CPU-heavy one.

---

## 2. Scan request sequence

The single most important flow in the app.

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant App as Mobile App
    participant API as Node :4000
    participant PG as Postgres
    participant AI as Python :8000
    participant C as Claude

    U->>App: taps shutter
    App->>App: takePictureAsync(quality 0.8)
    App->>API: POST /scans (multipart, Bearer JWT)
    API->>API: requireAuth — verify JWT
    API->>PG: SELECT * FROM profiles WHERE user_id
    PG-->>API: diet_type, health_flags, allergens

    API->>AI: POST /analyze (images[], profile JSON)

    activate AI
    AI->>AI: 1. OCR — preprocess + Tesseract
    AI->>AI: 2. split ingredients / nutrition sections
    AI->>AI: 3. classify each ingredient vs KB
    AI->>AI: 4. diet-fit + allergen rules (deterministic)
    AI->>AI: 5. sugar / additive / label scores
    AI->>C: structured result only — no raw OCR
    C-->>AI: {summary, suggestions[]}
    deactivate AI

    AI-->>API: scores, flags, summary, suggestions

    API->>PG: INSERT scans
    API->>PG: INSERT scan_results
    API->>PG: INSERT scan_history_events (+10 XP)
    API-->>App: {scanId, ...analysis}

    App->>API: GET /scans/:scanId
    API-->>App: stored result
    App-->>U: score card + flags + suggestions
```

> **Known inefficiency:** step 1 is fully synchronous — one blocking call with a
> 30 s axios timeout — and the app discards the analysis it already received in
> order to re-fetch by id. Phase 3 replaces this with a job queue plus SSE
> progress events.

---

## 3. The analysis pipeline

Where the domain logic actually lives, and where the deterministic/LLM boundary sits.

```mermaid
flowchart LR
    IMG["label photo<br/>(bytes)"] --> PRE

    subgraph ocrp["ocr.py"]
        PRE["grayscale →<br/>bilateral filter →<br/>adaptive threshold"] --> TESS["pytesseract"]
        TESS --> SPLIT["regex section split"]
    end

    SPLIT --> ITEXT["ingredients_text"]
    SPLIT --> NTEXT["nutrition_text"]

    subgraph det["Deterministic — traceable, testable"]
        ITEXT --> PARSE["paren-aware<br/>comma split"]
        PARSE --> CLASS["classify vs<br/>INGREDIENT_KB<br/>(35 entries)"]
        CLASS --> DF["check_diet_fit()"]
        CLASS --> AL["check_allergens()"]
        CLASS --> SA["score_additives()"]
        NTEXT --> NUM["parse_nutrition_numbers()"]
        NUM --> SS["score_sugar()"]
        SA & SS & DF & AL --> SL["score_label()<br/>0–100"]
    end

    subgraph llm["LLM — explanation only"]
        EXP["explain_scan()<br/>Claude"]
    end

    SL --> EXP
    DF --> EXP
    AL --> EXP
    EXP --> OUT["summary +<br/>2–3 suggestions"]

    style det fill:#eef6f0,stroke:#2F6B4F
    style llm fill:#fdf4e6,stroke:#C98A2C
```

**Scoring formulas** — deliberately simple so they can be explained to a user:

| Score | Formula |
|---|---|
| Sugar | `100 − (added_g ÷ 25 g) × 100` |
| Additives | `100 − 15 × count(sweetener, preservative, colorant, flavor enhancer)` |
| Label | `mean(sugar, additives)` − 20 if diet mismatch − 30 if allergen hit |

---

## 4. Data model

```mermaid
erDiagram
    users ||--o| profiles : "has one"
    users ||--o{ scans : "creates"
    scans ||--|| scan_results : "produces"
    users ||--o{ scan_history_events : "earns"
    scans ||--o{ scan_history_events : "triggers"

    users {
        uuid id PK
        text email UK
        text password_hash
        text display_name
        timestamptz created_at
    }
    profiles {
        uuid user_id PK_FK
        text diet_type
        text_array meat_subprefs
        text_array health_flags
        text_array allergens
        numeric sugar_sensitivity
        text age_band
        text sex
        text activity_level
    }
    scans {
        uuid id PK
        uuid user_id FK
        text_array image_urls "always empty — no S3 yet"
        text status
        text ocr_raw_text
        timestamptz created_at
    }
    scan_results {
        uuid scan_id PK_FK
        numeric label_score
        numeric sugar_score
        numeric additive_score
        numeric diet_fit_score
        jsonb flags
        text ai_summary
        jsonb ai_suggestions
    }
    scan_history_events {
        uuid id PK
        uuid user_id FK
        uuid scan_id FK
        int xp_earned
        text badge_unlocked
    }
    ingredients_kb {
        uuid id PK
        text canonical_name
        text_array synonyms
        text category
        text e_number
        bool animal_derived
        bool root_allium
    }
    diet_rulesets {
        uuid id PK
        text diet_type
        int version
        jsonb rules
    }
```

`ingredients_kb` and `diet_rulesets` are created by the schema but **no code
reads or writes them** — that data currently lives as hardcoded Python dicts.
Migrating it into these tables is Phase 1 of the roadmap.

---

## 5. Mobile navigation

```mermaid
stateDiagram-v2
    [*] --> Login
    Login --> Onboarding : signup
    Login --> Scan : login
    Onboarding --> Scan : PUT /profile
    Scan --> Result : POST /scans
    Result --> Scan : scan another
    Scan --> Profile
    Result --> Profile
    Profile --> Scan
```

A flat native-stack — no tab bar and no persisted-session check, so the app
always cold-starts at `Login` even when a valid token exists in AsyncStorage.

---

## 6. Target architecture (Phase 3+)

What the synchronous pipeline above becomes once the queue and streaming land.

```mermaid
flowchart LR
    App["Mobile App"] -->|"POST /scans"| API["Node Gateway"]
    API -->|"202 {scanId, processing}"| App
    API --> S3[("S3<br/>images")]
    API --> Q[["BullMQ<br/>on Redis"]]
    Q --> W["Worker"]
    W --> AI["Python AI service"]
    AI --> C{{"Claude<br/>streaming"}}
    C -.->|"tokens"| W
    W --> PG[("Postgres")]
    W -.->|"SSE progress<br/>'found 14 ingredients…'"| App

    style Q stroke-dasharray: 5 5
    style W stroke-dasharray: 5 5
```

The SSE channel is what makes the agent narration in
[`labelwise-prototype.html`](../../../labelwise-prototype.html) real: today those
lines are a 650 ms `setInterval`; they should be actual pipeline stage events.
