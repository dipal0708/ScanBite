# Repository Guidance

## Project Context

- Read `README.md` and `ARCHITECTURE.md` at the repository root for setup, product goals, and system design.
- The runnable scaffold is under `labelwise-scaffold/labelwise/`. Its `README.md` describes the implemented services and Node-to-Python contract; `docs/ARCHITECTURE.md` contains the scaffold-specific design.
- The repository is named ScanBite, while packages and much of the implementation still use LabelWise. Preserve existing names unless a task explicitly includes the tracked rename.
- Distinguish planned architecture from implemented behavior. The scaffold README and source code are authoritative for what currently works.

## Service Boundaries

- `labelwise-scaffold/labelwise/backend-node/` is an Express API gateway using JavaScript ES modules. It owns authentication, profiles, scan orchestration, persistence, and the mobile-facing API.
- `labelwise-scaffold/labelwise/ai-service-python/` is a FastAPI service. It owns OCR, ingredient parsing/classification, deterministic diet rules, scoring, and explanation generation.
- `labelwise-scaffold/labelwise/mobile-app/` is a React Native + Expo TypeScript client. Keep API payloads and navigation consistent with existing contracts.
- When changing a cross-service payload, inspect and update both the caller and receiver, plus any client-facing types or docs.
- Diet-fit decisions and numeric scores must remain deterministic and traceable to specific ingredient/nutrition facts. The LLM may explain already-computed results; it must not classify ingredients, decide diet fit, or calculate scores.

## Development Commands

Run commands from the relevant service directory:

- Python service: `pip install -r requirements.txt`, then `uvicorn app.main:app --reload --port 8000`.
- Node gateway: `npm install`, then `npm run dev` (or `npm start`).
- Mobile app: `npm install`, then `npx expo start`.

The Node and mobile package manifests currently define no test or lint scripts, and the scaffold README reports no automated test suite. Do not imply a test suite exists; use focused smoke checks and report any verification limits. Consult the root README for environment variables, database setup, and full local startup instructions.

## Safety and Data Handling

- This is a health-adjacent product. Avoid diagnostic or prescriptive claims; preserve cautious user-facing language.
- Diet, allergen, and health-profile data are sensitive. Do not log secrets or unnecessary personal/profile data, and do not weaken authentication or data protections.
- Before extending the scaffold, read the root README's "Known issues to fix before shipping" section. It documents security and classification defects that must not be mistaken for intended behavior.
- Do not silently treat an unknown ingredient as verified safe. Preserve or improve uncertainty/coverage signaling when changing classification behavior.

## Change Practices

- Keep changes scoped to the service that owns the behavior and follow its existing conventions.
- Update relevant README or architecture documentation when a public contract, setup step, or system boundary changes.
- Treat `labelwise-prototype.html` as a clickable UI prototype, not the mobile application's source of truth.