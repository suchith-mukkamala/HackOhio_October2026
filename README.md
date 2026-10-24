# Keystone

**A portfolio AI can't fake.** Students build in public, AI turns their commits into a weekly progress log, industry mentors give 5–15 minute feedback, and every skill on a profile is backed by real code or a real person who vouched for it.

Built at **HackOHI/O 2026** for the **Honda Research Institute × 99P Labs Bridge Builder Challenge**: *design a platform where students learn together and connect with industry.*

> Working name. Rename freely, but update the `<title>` in `frontend/index.html` and the header in `frontend/src/components/Layout.tsx`.

---

## Why this exists

AI now writes most resumes, so a list of skills says almost nothing about what someone can actually do. The strongest record is one **earned from others**: work shipped, help given, feedback received.

Keystone makes that record visible:

| Evidence tier | Where it comes from | How it looks on the skill graph |
|---|---|---|
| Claimed | Student lists it on their profile | Gray node |
| Code | Shows up in published progress logs and project tags | Blue node |
| Peer | A teammate or classmate endorses it | Green node |
| Mentor-verified | An industry mentor or faculty member endorses it after helping | Gold ring |

## The demo flow

This is the one flow we polish end to end. Each step maps to a rung of the challenge's ladder.

1. **Sign in with GitHub.** The profile fills itself from your repos, so it's useful before anyone else joins. *(Look around)*
2. **Push a project.** Pick a repo, add a description, tags, and the roles you're looking for. *(Join a project)*
3. **Generate this week's log.** The backend pulls commits since the last log, OpenAI drafts *what we built / what we learned / where we're stuck*, and the student edits and publishes it to the timeline and feed.
4. **Ask a mentor.** One click on a "stuck" item creates a help request with a time ask of 5, 15 or 30 minutes. *(Show up)*
5. **Mentor answers.** Mentors see requests ranked by skill match, answer in minutes, and can endorse the skill they saw.
6. **The record updates.** The student marks the answer helpful, and that skill turns gold on their graph with the evidence attached. The mentor gets "help given" credit. *(Give back)*

AI drafts, the student confirms, a mentor verifies. AI never writes the record by itself.

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Vite, React 19, TypeScript, Tailwind CSS v4, React Router, TanStack Query, `react-force-graph-2d` |
| Backend | Python, FastAPI, SQLModel on AWS RDS Postgres (no SQLite) |
| AI | Structured output from OpenAI (log drafts from commits) and Claude (resume reading) |
| Auth | GitHub OAuth, session in a signed JWT cookie, plus a demo persona picker |
| Deploy | Vercel (frontend + FastAPI backend as Vercel Services) with AWS RDS Postgres |

## Repo layout

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app; every route is under /api
│   │   ├── config.py          # reads backend/.env
│   │   ├── db.py              # engine + session dependency
│   │   ├── models.py          # all tables (mirror in frontend/src/lib/types.ts)
│   │   ├── auth.py            # session cookie + current_user dependency
│   │   ├── routers/
│   │   │   ├── auth.py        # GitHub OAuth, demo personas, logout
│   │   │   ├── users.py       # /me, profiles, skill graph, GitHub repo list
│   │   │   ├── projects.py    # projects, invites, archive, auto-docs logs
│   │   │   ├── help.py        # help requests, mentor inbox, answers, endorsements
│   │   │   └── social.py      # feed, posts, comments, search, DMs
│   │   └── services/
│   │       ├── github.py      # GitHub REST calls
│   │       ├── ai.py          # OpenAI: commits -> LogDraft; Claude: resume PDF -> experience
│   │       └── skills.py      # skill vocabulary + evidence-weighted graph
│   ├── seed_team.py           # adds the four team accounts + sample data (insert-only)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # routes
│   │   ├── components/        # Layout, Stub
│   │   ├── lib/               # api client, shared types, useMe()
│   │   └── pages/             # one file per screen
│   └── vite.config.ts         # proxies /api to localhost:8000
├── vercel.json                # Vercel Services: frontend at /, backend at /api
└── docs/
    └── PLAN.md                # full hackathon plan: scope, timeline, ownership, pitch
```

---

## Getting started

You need **Python 3.12+** and **Node 20+**.

### 1. One-time setup

Backend (keep the venv at `backend/.venv`; `npm run dev` looks for it there):

```bash
cd backend
python -m venv .venv
```

Activate it (`source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\activate` on Windows), then:

```bash
pip install -r requirements.txt
cp .env.example .env
```

Fill in the `DB_*` fields in `backend/.env` with the AWS RDS endpoint, port, database name, master username and password (ask Rohan or Adi). Everyone shares the one AWS database, and the app won't start without it.

Frontend:

```bash
cd frontend
npm install
```

### 2. Run the app

```bash
cd frontend
npm run dev
```

This one command starts both the backend and the frontend. Open **http://localhost:5173**. That's the only address you need, because Vite forwards `/api` to the backend behind the scenes. The landing page lists the seeded demo personas. Click one to sign in as that person.

Interactive API docs are at **http://localhost:5173/api/docs**, which is the source of truth for the API contract. Use `npm run dev:web` if you only want the frontend.

### 3. GitHub sign-in (optional for local dev)

The demo personas work without this. To use real GitHub sign-in:

1. Go to **GitHub → Settings → Developer settings → OAuth Apps → New OAuth App**.
2. Set the homepage URL to `http://localhost:5173` and the callback URL to `http://localhost:8000/api/auth/github/callback`.
3. Put the client ID and secret in `backend/.env`.

Create a second OAuth app for production with the deployed callback URL.

### 4. AI keys (log drafts and resume reading)

Add `OPENAI_API_KEY` to `backend/.env` for log drafts (platform.openai.com/api-keys; model `OPENAI_MODEL`, default `gpt-4o-mini`), and `ANTHROPIC_API_KEY` for resume reading (console.anthropic.com; model `CLAUDE_MODEL`, default `claude-opus-5-5`).

### Environment variables

| Variable | What it's for |
|---|---|
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | AWS RDS endpoint, port (5432), database name, master username and password |
| `JWT_SECRET` | Signs session cookies. Use a long random string. |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` / `GITHUB_REDIRECT_URI` | GitHub OAuth |
| `FRONTEND_URL` | Where sign-in redirects back to |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | Log drafts from commits |
| `ANTHROPIC_API_KEY` / `CLAUDE_MODEL` | Resume reading |
| `DEMO_MODE` | Leave `false`. Only real accounts can sign in. |
| `SECURE_COOKIES` | `true` behind HTTPS in production |

---

## API at a glance

All routes are prefixed with `/api`. See `/api/docs` for request and response shapes.

| Area | Routes |
|---|---|
| Auth | `GET /auth/github/login`, `GET /auth/github/callback`, `GET /auth/demo/personas`, `POST /auth/demo/{id}`, `POST /auth/logout` |
| Users | `GET /me`, `GET /users/{id}`, `GET /users/{id}/skills`, `GET /github/repos` |
| Projects | `GET/POST /projects`, `GET /projects/{id}`, `POST /projects/{id}/invite`, `POST /projects/{id}/archive` |
| Auto-docs | `POST /projects/{id}/logs/draft`, `POST /projects/{id}/logs`, `GET /projects/{id}/logs` |
| Help | `POST /help`, `GET /help/inbox`, `POST /help/{id}/answer`, `POST /help/{id}/helpful` |
| Social | `GET /feed`, `POST /posts`, `POST /comments`, `GET /search` |
| DMs | `GET/POST /threads`, `GET/POST /threads/{id}/messages` (clients poll every 3s) |

---

## Team

| Person | Owns |
|---|---|
| **Rohan** | Auth, app shell and routing, AWS deploy |
| **Neel** | Auto-docs (GitHub + OpenAI), project timeline, feed and posts |
| **Suchith** | Push projects, project page, profile and skill graph |
| **Adi** | Seed data, help requests and mentor inbox, search, DMs |

Unbuilt pages render a placeholder that names the owner and the endpoints to wire up. Delete the `<Stub>` once your page is real.

## How we work

- Everyone has a personal branch (`Adi`, `Neel`, `Rohan`, `Suchith`). Open a PR into `main` at least every 2 hours. Small merges beat one giant merge at hour 20.
- If you change a model in `backend/app/models.py`, update `frontend/src/lib/types.ts` in the same PR.
- The database is shared on AWS. New tables are created automatically on startup, but new columns on existing tables need a migration (see `backend/migrations/`). Never drop tables.
- **Feature freeze at H17.** After that, only bug fixes and polish.
- **Upload the video by H22.** Don't wait for the last few minutes.

The full plan (scope decisions, hour-by-hour timeline, demo script and risks) is in [docs/PLAN.md](docs/PLAN.md).

## Deploying

**Live site: https://keystone-hackohio.vercel.app**

Frontend and backend deploy together as one Vercel project using [Vercel Services](https://vercel.com/docs/services). The root `vercel.json` serves `frontend/` at `/` and runs the FastAPI app in `backend/` at `/api`, so everything is on one domain with no CORS or cookie setup. The database stays on AWS RDS, so every account works the same locally and live.

**Redeploy** from the repo root (Vercel CLI, signed in to the account that owns the project):

```bash
vercel deploy --prod
```

- **Settings live in Vercel, not in git.** Add or change them in Vercel → Project → Settings → Environment Variables: the five `DB_*` fields, `JWT_SECRET`, `ANTHROPIC_API_KEY`, `CLAUDE_MODEL`, `OPENAI_API_KEY`, `SECURE_COOKIES=true`, `FRONTEND_URL`, and the GitHub/Google client IDs, secrets and redirect URIs. Redeploy after changing them.
- **Sign-in callbacks** for the live site are `https://keystone-hackohio.vercel.app/api/auth/github/callback` and `.../google/callback`. Register them in the GitHub and Google OAuth apps.
- **`.vercelignore`** keeps `.env`, `password.txt` and local environments out of uploads. Never remove those lines.
- **"Commit author doesn't have permission"** means the GitHub account on your latest commit isn't linked to the Vercel account. Fix it in Vercel → Account Settings → Authentication → GitHub → Connect.
- **Limits** (Hobby plan): requests up to 4.5 MB (resume uploads are capped at 4 MB) and functions up to 60 seconds.
