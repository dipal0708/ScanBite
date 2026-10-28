# Deploying the Node.js API to Vercel

This service is the API gateway for ScanBite/LabelWise. It handles authentication, user profiles, and orchestrates scan requests to the Python AI service.

## Prerequisites

- [Vercel account](https://vercel.com)
- [PostgreSQL database](https://neon.tech) (or Render/Railway/Supabase)
- [Python AI service deployed](https://render.com) (or Railway/Fly.io)

## Quick Deploy

```bash
cd labelwise-scaffold/labelwise/backend-node

# Install Vercel adapter
npm install -D @vercel/node

# Login to Vercel
vercel login

# Deploy
vercel --prod
```

## Environment Variables

Set these in Vercel Dashboard → Project Settings → Environment Variables:

| Variable | Required | Example |
|----------|----------|---------|
| `DATABASE_URL` | ✅ | `postgres://user:pass@host:5432/labelwise` |
| `JWT_SECRET` | ✅ | `a1b2c3...` (48-byte hex) |
| `AI_SERVICE_URL` | ✅ | `https://your-ai-service.onrender.com` |
| `NODE_ENV` | ✅ | `production` |

### Generate JWT_SECRET

```bash
node -e "console.log(require('crypto').randomBytes(48).toString('hex'))"
```

## API Endpoints

All `/profile` and `/scans` routes require `Authorization: Bearer <token>`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/auth/signup` | Create account |
| POST | `/auth/login` | Login |
| POST | `/auth/refresh` | Refresh tokens |
| GET | `/profile` | Get user profile |
| PUT | `/profile` | Update profile |
| POST | `/scans` | Submit label images (multipart) |
| GET | `/scans` | List user's scans |
| GET | `/scans/:id` | Get scan result |
| POST | `/scans/:id/ask` | Ask AI follow-up |

## Local Development

```bash
cd backend-node
npm install
cp .env.example .env
# Edit .env with your local settings
npm run dev
```

Server runs on `http://localhost:4000`.

## Architecture

```
Mobile App / Web → Vercel (Node.js API) → Python AI Service → PostgreSQL
                      ↑                        ↑
                   JWT Auth              OCR + Scoring
```

The Node.js API:
- Authenticates users with JWT
- Stores user profiles and scan history in Postgres
- Forwards image analysis requests to the Python service
- Returns structured results to the client

## Troubleshooting

**503 from AI service:** Check that `AI_SERVICE_URL` is correct and the Python service is running.

**Database connection error:** Verify `DATABASE_URL` is correct and accessible from Vercel.

**JWT validation fails:** Ensure `JWT_SECRET` matches what was used to sign the token.

## Files

- `src/index.js` — Express app entry point
- `src/routes/` — API route handlers
- `src/middleware/auth.js` — JWT authentication middleware
- `src/controllers/` — Request handlers
- `vercel.json` — Vercel configuration
