# LabelWise — Architecture & Product Plan

*A label-scanning health companion app. Working name "LabelWise" — swap freely.*

## 1. Product summary

**Job to be done:** a shopper stands in an aisle, scans a packaged food's label, and in seconds understands: what's actually in it, whether it fits their diet and health profile, and what to do about it — all delivered through a friendly, game-like guide rather than a wall of nutrition jargon.

**Core loop**
1. Scan → OCR + ingredient parsing
2. Analyze → ingredient classification, sugar/additive scoring, personalized diet-fit check
3. Explain → plain-language verdict + AI agent walkthrough
4. Act → save/compare/get alternatives, earn progress (streaks, "Label Literacy" XP, badges)

## 2. Users & personalization inputs

Account profile collected at onboarding (all optional but improve suggestions):
- **Diet type** (single-select, mutually exclusive):
  - Vegan
  - Vegan — no roots/alliums (Jain-style: excludes onion, garlic, ginger, and other root/bulb vegetables)
  - Vegetarian
  - Vegetarian + eggs (ovo-vegetarian)
  - Non-vegetarian, with meat sub-preferences (multi-select): white meat, red meat, chicken, pork, seafood
- **Health flags** (multi-select): diabetes/blood sugar management, hypertension, high cholesterol, kidney condition, pregnancy, weight management goal, none
- **Allergens/intolerances** (multi-select + free text): nuts, gluten, lactose, soy, shellfish, etc.
- **Sugar sensitivity threshold** (slider — used to tune "added sugar" warnings)
- **Age band, sex, activity level** — used only to contextualize daily-value % (e.g., sugar/sodium as % of a sensible daily target), never stored as diagnostic data.

This profile is the single source of truth the AI agent conditions its suggestions on. It's editable anytime from Settings, and every suggestion screen shows *why* it's saying what it's saying, tied back to the specific profile field.

## 3. High-level architecture

```
┌─────────────────────────┐
│   React Native App      │  Camera capture, onboarding, profile,
│   (iOS + Android)        │  scan history, gamified results UI
└───────────┬──────────────┘
            │ HTTPS / JSON (REST) + WebSocket (agent streaming)
┌───────────▼──────────────┐
│  Node.js API Gateway      │  Auth, users, profiles, scan history,
│  (Express/Fastify + TS)   │  diet-rule engine, push notifications,
│                            │  rate limiting, orchestrates AI service
└───────────┬──────────────┘
            │ internal HTTP (gRPC optional)
┌───────────▼──────────────┐
│  Python AI Service        │  OCR pipeline, ingredient NLP parsing,
│  (FastAPI)                │  ingredient classification & scoring,
│                            │  LLM agent (Claude) for explanations,
│                            │  alternative-product suggestions
└───────────┬──────────────┘
            │
   ┌────────┴─────────┐
   │  Postgres (users,  │
   │  scans, profiles)  │
   │  Redis (cache/     │
   │  sessions/queues)  │
   │  S3 (label images) │
   │  Vector DB          │
   │  (ingredient KB,    │
   │  optional RAG)      │
   └────────────────────┘
```

**Why split Node.js and Python** rather than one stack: Node is a good fit for the API gateway, auth, real-time/session concerns, and mobile-facing REST contract. Python owns OCR/ML/LLM-agent orchestration where the ecosystem (Tesseract/PaddleOCR, spaCy, pandas, the Anthropic Python SDK) is strongest. The Node service never touches raw images or model calls directly — it proxies to the Python service, which keeps concerns cleanly separated and lets you scale/deploy them independently (the AI service is the one that needs GPU/CPU-heavy autoscaling; the gateway doesn't).

## 4. Scan → analysis pipeline (the core feature)

1. **Capture** — app opens camera in a guided frame ("fit the label in the box"), takes 1–3 shots (front + ingredients panel + nutrition panel), does on-device basic sharpness/glare check before upload.
2. **Upload** — image(s) sent to Node `/scans` endpoint → stored in S3 → Node enqueues a job (Redis/BullMQ) and returns a `scanId` immediately so the app can show the animated "scanning" state without blocking.
3. **OCR** (Python service):
   - Preprocess (deskew, denoise, adaptive threshold) with OpenCV.
   - Text extraction with a hybrid approach: Tesseract for general text; a cloud OCR API (Google Vision / AWS Textract) as a fallback for low-quality images, since packaged food labels are often small, glossy, and curved.
   - Segment extracted text into two zones: **Ingredients list** and **Nutrition Facts table** (regex + layout heuristics, since Nutrition Facts panels follow a fairly standard grid format in most regions).
4. **Ingredient parsing (NLP)**:
   - Tokenize the ingredients string (comma/parenthesis-aware, since sub-ingredients nest in parentheses).
   - Normalize each ingredient against a curated **ingredient knowledge base** (name variants, E-numbers, INCI-style synonyms — e.g., "sucrose," "high fructose corn syrup," "dextrose" all tag as *added sugar*).
   - Classify each ingredient into categories: added sugar, artificial sweetener, preservative, emulsifier/additive (with E-number if applicable), allergen, animal-derived, root/allium, colorant, other.
   - Animal-derived and root/allium tagging is what powers the diet-fit check (vegan/vegetarian/no-root logic below).
5. **Nutrition scoring**:
   - Parse the Nutrition Facts numbers (sugar per serving, added sugar, sodium, saturated fat, fiber, protein).
   - Compute a **added-sugar-per-serving vs. WHO/FDA daily guidance** percentage, and similarly for sodium/saturated fat.
   - Roll into a single 0–100 "Label Score" plus category sub-scores (Sugar, Additives, Diet Fit, Allergens) — the score is always shown next to its plain-language reasoning, never as an opaque number.
6. **Diet-fit rule engine** (deterministic, not LLM — correctness matters here):
   - Vegan: flag any animal-derived ingredient (dairy, egg, gelatin, honey, animal-derived E-numbers like E120/E441/E542).
   - Vegan, no roots: vegan rules **plus** flag onion, garlic, ginger, leek, shallot, and other root/bulb ingredients (including powdered/extract forms, which are the ones people most often miss on a label).
   - Vegetarian: flag meat/fish/poultry/gelatin, allow dairy/honey.
   - Vegetarian + eggs: as above, but eggs allowed.
   - Non-vegetarian with sub-prefs: flag only the excluded categories the user selected (e.g., user allows chicken/white meat but excludes red meat/pork → flag beef, pork, lamb ingredients specifically).
   - Each rule set is a versioned JSON ruleset in Postgres so it can be updated without a redeploy, and every flag cites which specific ingredient triggered it.
7. **AI agent explanation layer**:
   - Once the deterministic parsing + scoring + diet-fit steps are done, an LLM agent (Claude, via the Anthropic API) is given the *structured* results (not raw OCR text) and generates: a plain-language summary, a "what this means for you" paragraph personalized to the user's health flags, and 2–3 concrete suggestions (e.g., "swap for a lower-sodium version," "fine occasionally, not daily given your sugar goal").
   - The agent can optionally use tools: a product-alternatives lookup (search a packaged-goods database or the web for a lower-sugar/allergen-safe alternative in the same category) and a "explain this ingredient" lookup for follow-up questions.
   - Keeping scoring deterministic and only using the LLM for *explanation and suggestions* avoids the failure mode of an LLM inventing or missing a health-relevant classification — critical for a health-adjacent app.
8. **Response** streamed back to the app over WebSocket/SSE so the "AI agent walking you through the label" feels conversational and live rather than a spinner-then-dump.

## 5. Data model (core tables)

```
users(id, email, password_hash, created_at, ...)
profiles(user_id, diet_type, diet_subprefs[], health_flags[], allergens[],
         sugar_sensitivity, age_band, sex, activity_level, updated_at)
scans(id, user_id, image_urls[], status, ocr_raw_text, created_at)
scan_results(scan_id, label_score, sugar_score, additive_score, diet_fit_score,
             flags jsonb, ai_summary, ai_suggestions jsonb, created_at)
ingredients_kb(id, canonical_name, synonyms[], category, e_number,
               animal_derived bool, root_allium bool, notes)
diet_rulesets(id, diet_type, version, rules jsonb)
scan_history_events(id, user_id, scan_id, xp_earned, badge_unlocked, created_at)
```

## 6. Gamified UI/UX layer

The brief asks for a "game-like guide," which should shape the interaction model, not just decoration:

- **Onboarding = character/profile setup**, not a form: diet and health choices are presented as tappable cards with icons, one decision per screen, with a progress ring (not a % form-completion bar).
- **Scan = the core "move"**: a guided viewfinder with a scan-line animation; a satisfying reveal animation when OCR completes (label "unfolds" into its parsed parts).
- **Result = a readable "verdict card"**, styled after a nutrition-facts panel (ruled lines, bold numbers) so it still *reads like a label*, with a score meter and 2–3 tappable flags, each expandable into the AI agent's explanation.
- **Progression**: streaks for scanning before buying, a "Label Literacy" XP track with milestones (e.g., "Sugar Detective," "Ingredient Reader"), and light, optional badges — always framed around learning/awareness, never around weight or appearance, to keep this genuinely health-supportive rather than diet-culture-flavored.
- **AI agent as a guide character**, not a chat window bolted on: it narrates the scan ("Reading the ingredients panel... found 14 ingredients, 3 flagged for you") and answers follow-up questions inline on the result card.

An interactive HTML/React prototype of this flow is provided separately so you can see and click through the actual feel before any native build starts.

## 7. Tech stack summary

| Layer | Choice | Why |
|---|---|---|
| Mobile | React Native + Expo, TypeScript, React Navigation, Reanimated/Lottie for the game-like motion | One codebase for iOS/Android per your preference; Expo speeds up camera/permissions handling |
| API Gateway | Node.js, Express or Fastify, TypeScript, Prisma ORM | Familiar, fast to build, strong ecosystem for auth/session/rate-limiting |
| Auth | JWT access + refresh tokens, bcrypt/argon2 password hashing, optional OAuth (Google/Apple sign-in — expected on mobile) | Standard, secure, App Store/Play Store friendly |
| AI/OCR service | Python, FastAPI, OpenCV, Tesseract (+ cloud OCR fallback), spaCy for NLP normalization, Anthropic Python SDK for the agent | Best ecosystem for CV/NLP/agent orchestration |
| Data | Postgres (source of truth), Redis (cache, session, job queue via BullMQ), S3-compatible storage (label images) | Standard, scalable, cheap to start |
| Ingredient KB | Curated table seeded from Open Food Facts (open dataset) + manual curation for E-numbers/diet tags | Open Food Facts gives a strong free starting dataset of ingredients/products |
| Infra | Docker Compose for local dev; Node service and Python service as separate deployable containers (e.g., on Fly.io/Render/AWS ECS) | Matches the two-service split; independent scaling |

## 8. Build order (suggested milestones)

1. **M1 — Skeleton**: auth (signup/login), profile creation flow, empty scan screen, Node ↔ Python service talking to each other with a stubbed "fake OCR" response. *(This is what the code scaffold gives you.)*
2. **M2 — Real OCR + parsing**: wire real Tesseract/cloud OCR, build the ingredient KB (seed from Open Food Facts), implement the deterministic diet-fit rule engine and scoring.
3. **M3 — AI agent layer**: connect the Anthropic API for explanations/suggestions, streaming responses to the app.
4. **M4 — Gamification & polish**: XP/streaks/badges, the animated scan/reveal sequences, history and comparison screens.
5. **M5 — Hardening**: accessibility pass, offline/poor-scan handling, App Store/Play Store submission prep, privacy review (health data is sensitive — see below).

## 9. Privacy & compliance notes (important, not optional)

- Health flags and diet data are sensitive personal data. Store them encrypted at rest, minimize what's sent to any third-party LLM call (send only the structured, de-identified profile fields needed for personalization, not the user's name/email), and give users a clear in-app way to view/delete their data.
- This app should **not** present itself as medical advice — suggestion text should consistently use framing like "may not fit your goal" rather than diagnostic or prescriptive medical language, and should recommend consulting a doctor/dietitian for specific conditions (diabetes, kidney disease, pregnancy).
- If you plan to operate in the EU/UK/California, plan for GDPR/CCPA data-subject rights (export/delete) from the start — much cheaper than retrofitting.

---
Next in this package: `/backend-node` and `/ai-service-python` scaffolds implementing M1, and an interactive prototype of the mobile UI/UX described in section 6.
