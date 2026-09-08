# ScanBite

**Scan a food label. Understand what's actually in it.**

Point your phone at a packaged food's ingredients panel. ScanBite runs OCR on it,
classifies every ingredient, checks the product against your diet and health
profile, scores it 0–100, and has an AI guide explain the result in plain
language — no nutrition jargon, no wall of numbers.

> **Naming:** the repository is `ScanBite`; the code and docs still use the
> original working name **LabelWise** throughout (package names, API titles, UI
> copy). Renaming is tracked as a Phase 0 task.

---

## Contents

- [What's in this repo](#whats-in-this-repo)
- [How it works](#how-it-works)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Verifying the stack](#verifying-the-stack)
- [Environment variables](#environment-variables)
- [API reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [What's real vs. stubbed](#whats-real-vs-stubbed)
- [Roadmap](#roadmap)

---

## What's in this repo

```
ScanBite/
├── ARCHITECTURE.md              Product plan & system design (start here)
├── labelwise-prototype.html     Clickable UI prototype — open in a browser
└── labelwise-scaffold/labelwise/
    ├── backend-node/            Express API gateway (auth, profiles, orchestration)
    ├── ai-service-python/       FastAPI service (OCR, NLP, scoring, AI agent)
    └── mobile-app/              React Native + Expo client
```

The prototype needs no build step — open `labelwise-prototype.html` in any
browser to click through the intended UX before running anything.

## How it works

```
 Camera ──photo──▶  POST /scans            (Node :4000, Bearer JWT)
                        │
                        ├─ load the user's diet/health profile from Postgres
                        └─ POST /analyze   (Python :8000, multipart)
                               │
                               │  1. OCR          OpenCV preprocess → Tesseract
                               │  2. Parse        paren-aware ingredient split
                               │  3. Classify     match against ingredient KB
                               │  4. Diet rules   deterministic, per-ingredient
                               │  5. Score        sugar / additives / overall
                               │  6. Explain      Claude turns facts into prose
                               │
                        ◀──────┘  { scores, flags, summary, suggestions }
                        │
                        ├─ persist scans + scan_results, award XP
                        └─▶ { scanId, ...analysis }
```

**Key design rule:** the LLM never decides diet-fit or computes scores. Those are
deterministic and traceable to a specific ingredient. The model only *explains*
facts that were already computed — which is what keeps a health-adjacent app from
silently mis-classifying gelatin as vegan.

📐 **Diagrams:** see
[`docs/architecture-diagram.md`](labelwise-scaffold/labelwise/docs/architecture-diagram.md)
for the system context, scan sequence, analysis pipeline, ER model, mobile
navigation and target (Phase 3) architecture.

---

## Prerequisites

Install these before you start. Versions are minimums, not exact pins.

| Tool | Version | Why |
|---|---|---|
| **Node.js** | 20 LTS (18+ required) | API gateway. Needs global `FormData`/`Blob`, added in Node 18. |
| **Python** | 3.10+ | AI service |
| **PostgreSQL** | 14+ (13+ required) | `gen_random_uuid()` became core in PG 13 |
| **Tesseract OCR** | 5.x | `pytesseract` shells out to this binary |
| **Anthropic API key** | — | Get one at [console.anthropic.com](https://console.anthropic.com) |
| **Expo Go** app | latest | Only if running on a physical phone |

### Installing Tesseract

macOS:

```bash
brew install tesseract
```

Debian / Ubuntu:

```bash
sudo apt-get install -y tesseract-ocr
```

Windows:

```bash
winget install --id UB-Mannheim.TesseractOCR
```

On Windows, Tesseract installs to `C:\Program Files\Tesseract-OCR` and is
**not** added to `PATH` automatically. Either add that folder to `PATH`, or
point `pytesseract` at it directly — see [Troubleshooting](#troubleshooting).

Verify with `tesseract --version`.

---

## Setup

Three services, started in this order: **Python → Node → mobile app**. Each
needs its own terminal, and each stays running.

### 1. Clone

```bash
git clone <your-remote-url> ScanBite
```

Every path below is relative to `labelwise-scaffold/labelwise/`.

### 2. Postgres database

Create the database:

```bash
createdb labelwise
```

If `createdb` isn't on your PATH, use `psql -U postgres -c "CREATE DATABASE labelwise;"`.

Apply the schema — 7 tables: `users`, `profiles`, `scans`, `scan_results`,
`ingredients_kb`, `diet_rulesets`, `scan_history_events`:

```bash
psql postgres://user:password@localhost:5432/labelwise -f backend-node/src/config/schema.sql
```

Substitute your own credentials. Re-running is safe — every statement is
`CREATE TABLE IF NOT EXISTS`.

### 3. Python AI service

Create and activate a virtual environment:

```bash
cd ai-service-python && python -m venv .venv && source .venv/bin/activate
```

On Windows PowerShell:

```bash
cd ai-service-python; python -m venv .venv; .\.venv\Scripts\Activate.ps1
```

Install dependencies and create the env file:

```bash
pip install -r requirements.txt && cp .env.example .env
```

Open `.env` and set your real key — `ANTHROPIC_API_KEY=sk-ant-...`. Then run it:

```bash
uvicorn app.main:app --reload --port 8000
```

Check <http://localhost:8000/health> for `{"status":"ok"}`, and
<http://localhost:8000/docs> for interactive API docs.

### 4. Node API gateway

In a **second terminal**:

```bash
cd backend-node && npm install && cp .env.example .env
```

Edit `.env`:

```
PORT=4000
DATABASE_URL=postgres://user:password@localhost:5432/labelwise
JWT_SECRET=<a long random string>
AI_SERVICE_URL=http://localhost:8000
```

Generate a real secret rather than inventing one by hand:

```bash
node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"
```

Run it:

```bash
npm run dev
```

Check <http://localhost:4000/health> for `{"status":"ok"}`.

### 5. Mobile app

In a **third terminal**:

```bash
cd mobile-app && npm install && npx expo start
```

Then press `i` for the iOS simulator, `a` for an Android emulator, or scan the
QR code with Expo Go on a physical phone.

**On a physical phone**, `localhost` means the phone itself, so the app cannot
reach your machine. Point it at your LAN IP:

```bash
cp .env.example .env
```

Set `EXPO_PUBLIC_API_URL=http://192.168.1.20:4000`, using your machine's actual
address (`ipconfig` on Windows, `ifconfig | grep inet` on macOS/Linux). Restart
`expo start` afterwards — `EXPO_PUBLIC_*` variables are inlined at build time.

The camera does not work in the iOS simulator or most Android emulators. Use a
real device to test scanning.

---

## Verifying the stack

You can exercise the whole pipeline from the terminal, without the app.

Create an account:

```bash
curl -s -X POST http://localhost:4000/auth/signup -H "Content-Type: application/json" -d "{\"email\":\"you@example.com\",\"password\":\"testpassword123\",\"displayName\":\"You\"}"
```

Copy the `accessToken` from the response into a `TOKEN` variable, then set a profile:

```bash
curl -s -X PUT http://localhost:4000/profile -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "{\"dietType\":\"vegan\",\"healthFlags\":[\"Diabetes\"],\"allergens\":[\"peanut\"]}"
```

Submit a label photo:

```bash
curl -s -X POST http://localhost:4000/scans -H "Authorization: Bearer $TOKEN" -F "images=@/path/to/label.jpg"
```

A successful response contains `scanId`, `scores`, `flags`, `summary` and
`suggestions`. For a first test, photograph any packaged food's ingredients
panel — the OCR heuristics key off the literal words "Ingredients:" and
"Nutrition Facts", so a label containing those works best.

---

## Environment variables

**`backend-node/.env`**

| Variable | Default | Notes |
|---|---|---|
| `PORT` | `4000` | Gateway listen port |
| `DATABASE_URL` | — | Required. Standard Postgres connection string. |
| `JWT_SECRET` | `dev_secret` | **Required in any shared environment.** The fallback is insecure. |
| `AI_SERVICE_URL` | `http://localhost:8000` | Where the Python service lives |

**`ai-service-python/.env`**

| Variable | Default | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required. Without it, `/analyze` fails at the explanation step. |

**`mobile-app/.env`**

| Variable | Default | Notes |
|---|---|---|
| `EXPO_PUBLIC_API_URL` | `http://localhost:4000` | Must be a LAN IP for physical devices |

Never commit `.env` files — the root `.gitignore` excludes them.

---

## API reference

All `/profile` and `/scans` routes require an `Authorization: Bearer <accessToken>` header.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/auth/signup` | `{email, password, displayName}` → user + tokens |
| `POST` | `/auth/login` | `{email, password}` → user + tokens |
| `POST` | `/auth/refresh` | `{refreshToken}` → new token pair |
| `GET` | `/profile` | Current diet/health profile |
| `PUT` | `/profile` | Create or update the profile (upsert) |
| `POST` | `/scans` | Multipart, up to 3 images, 8 MB each → full analysis |
| `GET` | `/scans` | 50 most recent scans for the user |
| `GET` | `/scans/:scanId` | One stored scan result |
| `POST` | `/scans/:scanId/ask` | `{question}` → AI follow-up answer |

Internal Python service, not exposed to clients: `POST /analyze`,
`POST /agent/ask`, `GET /health`.

**Diet types:** `vegan`, `vegan_no_roots`, `vegetarian`, `vegetarian_with_eggs`,
`non_vegetarian`.

**Meat sub-preferences** (only with `non_vegetarian`): `white_meat`, `red_meat`,
`chicken`, `pork`, `seafood`.

---

## Troubleshooting

**`TesseractNotFoundError`** — the Python package is installed but the binary
isn't on `PATH`. Add Tesseract's install folder to `PATH`, or set it explicitly
at the top of `ai-service-python/app/services/ocr.py`:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

**`Activate.ps1 cannot be loaded` (Windows)** — PowerShell's execution policy
blocks the activation script:

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**`function gen_random_uuid() does not exist`** — you're on PostgreSQL 12 or
older. Upgrade to 13+, or enable the extension:

```bash
psql $DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
```

**Scan returns 500, everything else works** — almost always a missing or invalid
`ANTHROPIC_API_KEY`. The AI explanation step currently has no fallback, so one
failed model call discards otherwise-valid OCR and scoring results. Check the
Python service logs.

**App shows "Network Error" on a physical phone** — `EXPO_PUBLIC_API_URL` is
still `localhost`, your firewall is blocking port 4000, or the phone is on a
different network. Confirm from the phone's browser that
`http://<your-ip>:4000/health` loads.

**`npx expo start` fails immediately** — run `npm install` first, and make sure
you're inside `mobile-app/`.

---

## What's real vs. stubbed

This is a **milestone-1 scaffold** — a correct skeleton, not a finished product.

**Working end to end:** JWT auth, the Postgres schema, the diet-fit rule engine
(all five diet types plus meat sub-preferences), paren-aware ingredient parsing,
the nutrition scoring formulas, the Node↔Python contract, and the Claude
explanation layer.

**Stubbed or needs tuning:**

- **Ingredient knowledge base** — 35 entries hardcoded in
  `ai-service-python/app/services/ingredients.py`. The `ingredients_kb` table
  exists but is unused. Seed it from [Open Food Facts](https://world.openfoodfacts.org/data).
- **Diet rules** — hardcoded `if/elif`; the `diet_rulesets` table is unused.
- **OCR** — Tesseract only. Real-world glossy, curved labels need a cloud OCR
  fallback (Google Vision / Textract) behind the existing `extract_text` seam.
- **Scan pipeline** — synchronous. No job queue, no S3 image storage
  (`scans.image_urls` is always empty), no SSE/WebSocket streaming.
- **Gamification** — XP rows are written on every scan but never displayed.
- **Tests** — none, in any service.

### Known issues to fix before shipping

These are real and worth reading before building on top of the scaffold:

1. **Refresh tokens work as access tokens.** `middleware/auth.js` verifies the
   signature but never checks `payload.type`, so a 30-day refresh token
   authenticates every protected route.
2. **`"coconut milk"` is classified as animal-derived.** The fuzzy fallback in
   `classify_ingredient` does a bare substring match, so a vegan product gets
   flagged as not vegan. Same bug for almond, soy and oat milk.
3. **Unknown ingredients pass silently.** Anything outside the 35-entry KB is
   `unclassified` and triggers no rule, so a diet check can report "fits" while
   having understood almost nothing on the label.
4. **Allergen matching is naive substring** — `"egg"` matches `"eggplant"`.
5. **A missing profile silently defaults to vegetarian** rather than prompting
   the user to set one up.

---

## Roadmap

| Phase | Focus | Outcome |
|---|---|---|
| **0** | Runnable & safe | Fix the auth bypass and the classification false positives; add Docker Compose and a pytest suite over the diet rules |
| **1** | Trustworthy classification | Real ingredient KB from Open Food Facts, word-boundary matching, coverage metric surfaced in the UI, rules moved into Postgres |
| **2** | OCR that survives real aisles | Cloud OCR fallback, bounding-box section splitting, on-device blur/glare checks, multi-shot capture |
| **3** | Async pipeline | S3 storage, BullMQ queue, SSE progress events, streaming agent narration |
| **4** | Product around the scan | History & comparison, editable profile, XP/streaks/badges, alternative-product suggestions, follow-up Q&A |
| **5** | Ship | Encryption at rest, GDPR/CCPA export & delete, compliance copy review, rate limiting, accessibility, store submission |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full product plan, data model and
privacy requirements, and
[docs/architecture-diagram.md](labelwise-scaffold/labelwise/docs/architecture-diagram.md)
for the system, sequence, pipeline, ER and navigation diagrams.

---

## Privacy note

Diet and health flags are sensitive personal data. Store them encrypted at rest,
send only de-identified structured fields to any third-party model, and give
users a clear way to view and delete their data. ScanBite is **not** a medical
device, and its suggestion copy must never read as diagnosis — see
`ARCHITECTURE.md` §9.
