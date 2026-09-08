# LabelWise — Scaffold

This is a milestone-1 scaffold matching `docs/ARCHITECTURE.md`: auth, profile
(diet/health), and a scan pipeline wired end-to-end with **stub-level** OCR/AI
logic that runs locally. It's meant to be a correct skeleton to build on, not
a finished product — see the architecture doc's "Build order" section for
what's next (real OCR accuracy tuning, a real ingredient KB, gamification UI).

## Folders

- `docs/` — architecture & product plan
- `backend-node/` — Express API gateway: auth, profiles, scan orchestration
- `ai-service-python/` — FastAPI service: OCR, ingredient classification,
  diet-fit rules, nutrition scoring, and the Claude-powered explanation agent
- `mobile-app/` — React Native (Expo) app skeleton: onboarding, login, scan,
  results, profile screens

## Running locally

**1. Python AI service**
```bash
cd ai-service-python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```
Tesseract must also be installed on your machine (`brew install tesseract` /
`apt install tesseract-ocr`) since `pytesseract` calls out to it.

**2. Node API gateway**
```bash
cd backend-node
npm install
cp .env.example .env   # set DATABASE_URL, JWT_SECRET
psql $DATABASE_URL -f src/config/schema.sql
npm run dev
```

**3. Mobile app**
```bash
cd mobile-app
npm install
npx expo start
```
Point `src/api/client.ts`'s `API_URL` at your running Node service
(use your machine's LAN IP, not `localhost`, when testing on a physical phone).

## What's stubbed vs. real

- **Real**: JWT auth, Postgres schema, the diet-fit rule engine (vegan / vegan-no-roots
  / vegetarian / vegetarian+eggs / non-veg with meat sub-prefs), ingredient parsing
  logic, nutrition scoring formulas, the Node↔Python service contract.
- **Stubbed / needs your keys or tuning**: OCR accuracy (Tesseract works but will need
  a cloud OCR fallback for real-world glare/curved-label photos), the ingredient
  knowledge base (seeded with ~30 entries — plug in Open Food Facts), the Claude
  agent calls (need `ANTHROPIC_API_KEY`), image storage (currently in-memory —
  wire to S3).
