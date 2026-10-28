# ScanBite — DFD & Workflow

Companion to [`architecture-diagram.md`](architecture-diagram.md). This file
covers the two views that document is missing: a classical **Data Flow Diagram**
(context + Level 1) and the **end-to-end workflow** across all three services.

**Notation legend** (Mermaid has no native DFD symbols, so shapes are mapped):

| DFD element | Mermaid shape | Example |
|---|---|---|
| External entity | rectangle | `["Shopper"]` |
| Process | stadium `([...])` | `P1([...])` |
| Data store | parallelogram `[/ /]` | `D1[/"users"/]` |
| Data flow | labelled arrow | `-- "label photos" -->` |

Components that are planned but not yet implemented (Phase 3) are drawn with
dashed borders.

---

## 1. DFD — Level 0 (context diagram)

The whole system as one process, showing what crosses its boundary.

```mermaid
flowchart LR
    SHOPPER["🧑‍🍳 Shopper<br/><i>mobile app user</i>"]

    subgraph SYS["ScanBite system (Node :4000 + Python :8000 + Postgres)"]
        P0(["P0 · ScanBite<br/>food-label analysis system"])
    end

    OLLAMA[("Ollama<br/>local model server")]

    SHOPPER -- "credentials<br/>{email, password}" --> P0
    SHOPPER -- "diet / health profile<br/>{dietType, healthFlags, allergens}" --> P0
    SHOPPER -- "label photos<br/>1–3 JPEG images" --> P0
    SHOPPER -- "follow-up question<br/>{question}" --> P0

    P0 -- "auth tokens<br/>{accessToken, refreshToken}" --> SHOPPER
    P0 -- "analysis result<br/>{scanId, scores, flags, summary, suggestions}" --> SHOPPER
    P0 -- "plain-language answer" --> SHOPPER

    P0 -- "structured facts only<br/>scores, flags, profile context<br/><b>never raw OCR text</b>" --> CLAUDE
    CLAUDE -- "{summary, suggestions[]}" --> P0
```

**Key boundary rule:** only structured, de-identified facts are sent to the
local Ollama model; raw OCR text and user identity never are (see
`ARCHITECTURE.md` §9).

---

## 2. DFD — Level 1

The system decomposed into its seven processes and seven data stores.
Read alongside the numbered flows.

```mermaid
flowchart TB
    %% ── External entities ──
    SHOPPER["🧑‍🍳 Shopper<br/>(React Native app)"]
    OLLAMA[("Ollama<br/>local model server")]

    %% ── Processes ──
    P1(["P1 · Auth &amp; session<br/>signup · login · refresh<br/><i>Node</i>"])
    P2(["P2 · Profile mgmt<br/>validate · upsert<br/><i>Node</i>"])
    P3(["P3 · Scan orchestration<br/>persist · award XP · history<br/><i>Node</i>"])
    P4(["P4 · OCR<br/>OpenCV preprocess → Tesseract<br/>section split<br/><i>Python</i>"])
    P5(["P5 · Ingredient parsing<br/>&amp; classification<br/><i>Python</i>"])
    P6(["P6 · Diet-fit rules<br/>&amp; scoring — deterministic<br/><i>Python</i>"])
    P7(["P7 · AI explanation<br/>&amp; follow-up Q&amp;A<br/><i>Python</i>"])

    %% ── Data stores ──
    D1[/"D1 · users<br/>credentials, hash"/]
    D2[/"D2 · profiles<br/>diet, health, allergens"/]
    D3[/"D3 · scans<br/>images, status, ocr_raw_text"/]
    D4[/"D4 · scan_results<br/>scores, flags, summary"/]
    D5[/"D5 · scan_history_events<br/>XP, badges"/]
    D6[/"D6 · ingredient KB<br/>35 entries in code →<br/>ingredients_kb table <i>(Phase 1)</i>"/]
    D7[/"D7 · diet rulesets<br/>in code → diet_rulesets<br/>table <i>(Phase 1)</i>"/]

    %% ── Flows: shopper ↔ auth / profile ──
    SHOPPER -- "F1 signup/login<br/>{email, password, displayName}" --> P1
    P1 -- "F2 tokens + user<br/>{accessToken, refreshToken}" --> SHOPPER
    P1 <--> D1
    SHOPPER -- "F3 profile upsert<br/>{dietType, meatSubprefs,<br/>healthFlags, allergens}" --> P2
    P2 <--> D2

    %% ── Flows: scan ──
    SHOPPER -- "F4 label photos<br/>multipart, Bearer JWT" --> P3
    D2 == "F5 profile row<br/><i>loaded per scan</i>"==> P3
    P3 -- "F6 images + profile JSON<br/>internal HTTP POST /analyze" --> P4
    P4 -- "F7 raw label text<br/>{ingredients_text, nutrition_text}" --> P5
    D6 -. "F8 synonym / category lookup" .-> P5
    P5 -- "F9 classified ingredients<br/>[{name, category, animal_derived, …}]" --> P6
    D7 -. "F10 rules (in-code today)" .-> P6
    P6 -- "F11 deterministic result<br/>{scores, flags, nutrition,<br/>dietFit, classifiedIngredients}" --> P7
    P7 <--> CLAUDE
    P7 -- "F12 analysis result<br/>+ summary + suggestions" --> P3

    %% ── Flows: persistence & response ──
    P3 --> D3
    P3 --> D4
    P3 --> D5
    P3 -- "F13 scan response<br/>{scanId, ...analysis}" --> SHOPPER
    SHOPPER -- "F14 follow-up question<br/>{question} on scanId" --> P3
    P3 -- "F15 question + stored result" --> P7

    classDef planned stroke-dasharray: 5 5,opacity:0.6
    class D6,D7 planned
```

### Flow table

| # | Data flow | From → To | Contents |
|---|---|---|---|
| F1 | Credentials | Shopper → P1 | email, password, displayName |
| F2 | Auth tokens | P1 → Shopper | accessToken (15 min), refreshToken (30 d) |
| F3 | Profile upsert | Shopper → P2 | dietType, meatSubprefs, healthFlags, allergens |
| F4 | Label photos | Shopper → P3 | 1–3 images, ≤ 8 MB each, Bearer JWT |
| F5 | Profile row | D2 → P3 | diet_type, health_flags, allergens (per scan) |
| F6 | Analyze request | P3 → P4 | images[] + profile JSON (multipart) |
| F7 | Raw label text | P4 → P5 | ingredients_text, nutrition_text |
| F8 | KB lookup | D6 → P5 | synonyms, category, animal_derived flags |
| F9 | Classified ingredients | P5 → P6 | name, category, e_number, root_allium |
| F10 | Diet rules | D7 → P6 | per-diet rules (hardcoded `if/elif` today) |
| F11 | Structured analysis | P6 → P7 | scores, flags, nutrition — **no prose** |
| F12 | Analysis + prose | P7 → P3 | F11 + summary + suggestions |
| F13 | Scan response | P3 → Shopper | scanId + full analysis |
| F14 | Follow-up question | Shopper → P3 | `{question}`, scanId |
| F15 | Q&A context | P3 → P7 | question + stored scan result |

**Trust boundary:** F11 is the deterministic/LLM seam. P7 receives only
already-computed facts (F11) — it never sees raw OCR text (F7) and never
recomputes a score or diet verdict.

---

## 3. Workflow — scan → verdict (swimlane)

The happy path end to end, including onboarding and the follow-up Q&A loop.

```mermaid
flowchart TB
    subgraph LANE_U["👤 Shopper / Mobile App"]
        A1(["Open app"]) --> A2{"Valid token<br/>in AsyncStorage?"}
        A2 -- "no" --> A3["Login / signup"]
        A3 --> A4{"Profile<br/>set up?"}
        A2 -- "yes" --> A4
        A4 -- "no" --> A5["Onboarding: diet cards,<br/>health flags, allergens"]
        A5 --> A6
        A4 -- "yes" --> A6["Scan screen<br/>guided viewfinder"]
        A6 --> A7["Capture 1–3 label photos<br/>on-device sharpness check"]
        A7 --> A8["POST /scans (multipart,<br/>Bearer JWT) — show scanning state"]
        A15["Render verdict card:<br/>score meter + tappable flags"] --> A16{"Question<br/>about an ingredient?"}
        A16 -- "yes" --> A17["POST /scans/:id/ask"]
        A16 -- "no" --> A18(["Scan another · earn XP"])
        A17 --> A15
        A18 --> A6
    end

    subgraph LANE_N["⚙️ Node Gateway :4000"]
        B1["requireAuth — verify<br/>JWT signature <b>and type</b>*"] --> B2["Load profile from Postgres"]
        B2 --> B3["POST /analyze to Python<br/>images + profile (sync, 30 s)"]
        B9["Receive analysis"] --> B10["INSERT scans<br/>INSERT scan_results<br/>INSERT scan_history_events (+10 XP)"]
        B10 --> B11["Respond {scanId, ...analysis}"]
        B12["Forward question +<br/>stored result"] --> B13["Return AI answer"]
    end

    subgraph LANE_P["🧠 Python AI service :8000"]
        C1["P4 OCR: grayscale →<br/>bilateral filter → adaptive<br/>threshold → Tesseract"] --> C2["Split into ingredients /<br/>nutrition sections"]
        C2 --> C3["P5 paren-aware comma split<br/>→ normalize each ingredient"]
        C3 --> C4["Classify vs ingredient KB<br/>(35 entries + fuzzy fallback)"]
        C4 --> C5{"P6 deterministic checks"}
        C5 --> C6["Diet-fit rules<br/>+ allergen match → flags"]
        C5 --> C7["Sugar / additive / label<br/>scores 0–100"]
        C6 & C7 --> C8["P7 build structured result"]
        C8 --> C9["Ollama: summary +<br/>2–3 suggestions"]
        C9 --> C10["Return full analysis"]
        C11["Ollama: answer<br/>follow-up question"] --> C12["Return answer"]
    end

    subgraph LANE_D["🗄️ Postgres"]
        D1[("profiles")]
        D2[("scans · scan_results ·<br/>scan_history_events")]
    end

    subgraph LANE_C["🖥️ Local model"]
        E1["Ollama<br/><i>structured facts only</i>"]
    end

    A8 ==> B1
    B2 -. "F5" .-> D1
    B3 ==> C1
    C8 -. "F11 — no raw OCR" .- E1
    E1 -. "summary + suggestions" .- C9
    C10 ==> B9
    B10 -.-> D2
    B11 ==> A15
    A17 ==> B12
    B12 ==> C11
    C11 -.-> E1
    C12 ==> B13
    B13 ==> A15

    style LANE_U fill:#eef4fd,stroke:#3B6FB6
    style LANE_N fill:#eef6f0,stroke:#2F6B4F
    style LANE_P fill:#fdf4e6,stroke:#C98A2C
    style LANE_D fill:#f4f0fa,stroke:#6B4FA0
    style LANE_C fill:#fdf0f0,stroke:#B04A4A
```

`==>` = synchronous HTTP call (blocking); `-.->` = data read/write or
out-of-band context flow.

\* **Bug note:** today `middleware/auth.js` verifies the signature but never
checks `payload.type`, so a refresh token authenticates protected routes —
drawn as *should be*, see README "Known issues" #1.

### Workflow summary

1. **Enter** — cold start → login (or restored session) → onboarding if no profile.
2. **Capture** — guided camera, 1–3 shots, on-device quality check.
3. **Orchestrate** — Node validates JWT, loads the profile row (F5), proxies
   images + profile to Python (F6).
4. **Analyze (Python, synchronous)** — OCR → parse → classify → deterministic
   diet rules & scores → local Ollama explanation → return.
5. **Persist** — Node writes `scans`, `scan_results`, `scan_history_events`
   (+10 XP), responds with `scanId` + analysis.
6. **Present** — verdict card with score meter and expandable flags.
7. **Loop** — ask follow-ups (F14/F15) or scan again.

### Error paths (not drawn)

- **Ollama is stopped or the model is missing** → P7 returns a clear service
  error; start Ollama and download the configured model (default: `llama3.2`).
- **Hosted provider selected (`LLM_PROVIDER=openai`)** → same clear errors for a
  missing/invalid `OPENAI_API_KEY`, an unreachable `OPENAI_BASE_URL`, or an
  unknown `OPENAI_MODEL`; each names the env var to fix.
- **OCR finds no "Ingredients:" / "Nutrition Facts" marker** → empty sections →
  scores default, low-confidence result.
- **Unknown ingredient** → `unclassified`, no rule fires (silent pass — known
  issue #3).
- **No profile row** → defaults to `vegetarian` silently (known issue #5).
