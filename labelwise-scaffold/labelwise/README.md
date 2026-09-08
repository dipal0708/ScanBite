# LabelWise — Scaffold

Milestone-1 scaffold for **ScanBite / LabelWise**, matching
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): auth, diet/health profiles, and a
scan pipeline wired end to end with stub-level OCR and knowledge-base data that
runs locally. A correct skeleton to build on, not a finished product.

> **Full install, setup and run instructions live in the [root README](../../README.md).**
> This file covers what's inside each folder and how the three services fit together.

## Folders

| Folder | Stack | Responsibility |
|---|---|---|
| `docs/` | — | Architecture & product plan, diagrams |
| `backend-node/` | Express, `pg`, JWT | API gateway: auth, profiles, scan orchestration, history, XP |
| `ai-service-python/` | FastAPI, OpenCV, Tesseract, Anthropic SDK | OCR, ingredient classification, diet rules, scoring, AI explanation |
| `mobile-app/` | React Native + Expo, TypeScript | Onboarding, login, camera scan, results, profile |

## Service map

```
backend-node/src/
├── index.js                    express app, /health, route mounting
├── config/
│   ├── db.js                   pg Pool
│   └── schema.sql              7 tables
├── middleware/
│   ├── auth.js                 Bearer JWT verification
│   └── errorHandler.js         catch-all → safe JSON error
├── routes/                     auth · profile · scan
├── controllers/
│   ├── auth.controller.js      signup / login / refresh, bcrypt + JWT
│   ├── profile.controller.js   diet taxonomy, zod validation, upsert
│   └── scan.controller.js      orchestrates a scan, persists, awards XP
└── services/aiService.js       axios → Python service

ai-service-python/app/
├── main.py                     FastAPI app, loads .env, mounts routers
├── routers/
│   ├── analyze.py              POST /analyze — the 5-step pipeline
│   └── agent.py                POST /agent/ask — follow-up questions
├── services/
│   ├── ocr.py                  preprocess + Tesseract + section split
│   ├── ingredients.py          paren-aware split + KB classification
│   ├── diet_rules.py           deterministic diet-fit + allergen checks
│   └── scoring.py              sugar / additive / overall 0–100 scores
└── agents/label_agent.py       Claude: explain_scan, answer_followup

mobile-app/
├── App.tsx                     StatusBar + RootNavigator
├── app.json                    Expo config (camera plugin, permissions)
└── src/
    ├── api/client.ts           axios + AsyncStorage token interceptor
    ├── navigation/             native-stack: Login → Onboarding → Scan → Result
    ├── screens/                Login · Onboarding · Scan · Result · Profile
    └── theme/theme.ts          design tokens (mirrors the HTML prototype)
```

## The design rule that matters

The LLM **never** decides diet-fit and never computes a score. `diet_rules.py`
and `scoring.py` are deterministic, and every flag cites the exact ingredient
that triggered it. `label_agent.py` receives the already-structured result and
only turns it into plain language.

This is deliberate: in a health-adjacent app, the failure mode you cannot accept
is a model silently mis-classifying a health-relevant ingredient. Keep new logic
on the correct side of that line.

## Service contract

Node → Python, `POST /analyze` (multipart):

- `images` — 1–3 files
- `profile` — JSON string of the Postgres `profiles` row (snake_case keys:
  `diet_type`, `meat_subprefs`, `health_flags`, `allergens`)

Response:

```json
{
  "ocrRawText": "...",
  "scores": { "label": 68, "sugar": 72, "additives": 85, "dietFit": 40 },
  "flags": [{ "ingredient": "Whey", "reason": "Not vegan — animal-derived." }],
  "dietFit": { "diet_type": "vegan", "fits": false, "flags": [] },
  "nutrition": { "sugar_g": 12, "sodium_mg": 230 },
  "classifiedIngredients": [{ "name": "Sugar", "category": "added_sugar" }],
  "summary": "...",
  "suggestions": ["...", "..."]
}
```

Node persists this into `scans` + `scan_results` and returns it to the app along
with a `scanId`.

## What's real vs. stubbed

**Real:** JWT auth, the Postgres schema, the diet-fit rule engine (vegan /
vegan-no-roots / vegetarian / vegetarian+eggs / non-veg with meat sub-prefs),
ingredient parsing, the scoring formulas, the Node↔Python contract.

**Stubbed or needs your keys:** OCR accuracy (Tesseract works, but real glossy
and curved labels need a cloud OCR fallback), the ingredient knowledge base
(~35 seed entries — plug in Open Food Facts), the Claude calls (need
`ANTHROPIC_API_KEY`), image storage (in-memory — wire to S3), gamification UI
(XP is written but never shown), and tests (there are none).

The root README's [Known issues](../../README.md#known-issues-to-fix-before-shipping)
section lists the specific bugs to fix before building further — including an
auth bypass and a classification false positive that marks vegan products as
non-vegan.

## Next steps

Diagrams: [`docs/architecture-diagram.md`](docs/architecture-diagram.md) — system
context, scan sequence, analysis pipeline, ER model, navigation, target state.

See the build order in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §8 and the
phased roadmap in the [root README](../../README.md#roadmap).
