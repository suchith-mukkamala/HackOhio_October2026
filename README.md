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
3. **Generate this week's log.** The backend pulls commits since the last log, Claude drafts *what we built / what we learned / where we're stuck*, and the student edits and publishes it to the timeline and feed.
4. **Ask a mentor.** One click on a "stuck" item creates a help request with a time ask of 5, 15 or 30 minutes. *(Show up)*
5. **Mentor answers.** Mentors see requests ranked by skill match, answer in minutes, and can endorse the skill they saw.
6. **The record updates.** The student marks the answer helpful, and that skill turns gold on their graph with the evidence attached. The mentor gets "help given" credit. *(Give back)*

AI drafts, the student confirms, a mentor verifies. AI never writes the record by itself.

---

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | Vite, React 19, TypeScript, Tailwind CSS v4, React Router, TanStack Query, `react-force-graph-2d` |
| Backend | Python, FastAPI, SQLModel (SQLite locally, Postgres in production) |
| AI | Claude via the Anthropic Python SDK, structured output into a `LogDraft` model |
| Auth | GitHub OAuth, session in a signed JWT cookie, plus a demo persona picker |
| Deploy | Frontend on Vercel; backend in Docker on AWS App Runner with RDS Postgres |

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
│   │       ├── claude.py      # commit history -> LogDraft
│   │       └── skills.py      # skill vocabulary + evidence-weighted graph
│   ├── seed.py                # resets the DB with demo data
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # routes
│   │   ├── components/        # Layout, Stub
│   │   ├── lib/               # api client, shared types, useMe()
│   │   └── pages/             # one file per screen
│   ├── vite.config.ts         # proxies /api to localhost:8000
│   └── vercel.json            # rewrites /api to the backend in production
└── docs/
    └── PLAN.md                # full hackathon plan: scope, timeline, ownership, pitch
```

---

## Getting started

You need **Python 3.12+** and **Node 20+**.

### 1. Backend

```bash
cd backend
python -m venv .venv
```

Activate it (`source .venv/bin/activate` on macOS/Linux, `.venv\Scripts\activate` on Windows), then:

```bash
pip install -r requirements.txt
cp .env.example .env
python seed.py
uvicorn app.main:app --reload
```

The API runs at http://localhost:8000. Interactive docs are at **http://localhost:8000/api/docs**, which is the source of truth for the API contract.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The landing page lists the seeded demo personas. Click one to sign in as that person.

### 3. GitHub sign-in (optional for local dev)

The demo personas work without this. To use real GitHub sign-in:

1. Go to **GitHub → Settings → Developer settings → OAuth Apps → New OAuth App**.
2. Set the homepage URL to `http://localhost:5173` and the callback URL to `http://localhost:8000/api/auth/github/callback`.
3. Put the client ID and secret in `backend/.env`.

Create a second OAuth app for production with the deployed callback URL.

### 4. Claude (for auto-docs)

Add `ANTHROPIC_API_KEY` to `backend/.env`. The model defaults to `claude-opus-5-5`. Set `CLAUDE_MODEL=claude-haiku-5-5` if you want faster, cheaper drafts while iterating. Requests opt into server-side refusal fallbacks, so a declined request is retried on another model automatically.

### Environment variables

| Variable | What it's for |
|---|---|
| `DATABASE_URL` | `sqlite:///./keystone.db` locally, `postgresql+psycopg://...` in production |
| `JWT_SECRET` | Signs session cookies. Use a long random string. |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` / `GITHUB_REDIRECT_URI` | GitHub OAuth |
| `FRONTEND_URL` | Where sign-in redirects back to |
| `ANTHROPIC_API_KEY` / `CLAUDE_MODEL` | Auto-docs drafts |
| `DEMO_MODE` | `true` shows the persona picker. Keep it on for the video. |
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
| **Neel** | Auto-docs (GitHub + Claude), project timeline, feed and posts |
| **Suchith** | Push projects, project page, profile and skill graph |
| **Adi** | Seed data, help requests and mentor inbox, search, DMs |

Unbuilt pages render a placeholder that names the owner and the endpoints to wire up. Delete the `<Stub>` once your page is real.

## How we work

- Everyone has a personal branch (`Adi`, `Neel`, `Rohan`, `Suchith`). Open a PR into `main` at least every 2 hours. Small merges beat one giant merge at hour 20.
- If you change a model in `backend/app/models.py`, update `frontend/src/lib/types.ts` in the same PR.
- Run `python seed.py` after pulling model changes. It drops and recreates every table.
- **Feature freeze at H17.** After that, only bug fixes and polish.
- **Upload the video by H22.** Don't wait for the last few minutes.

The full plan (scope decisions, hour-by-hour timeline, demo script and risks) is in [docs/PLAN.md](docs/PLAN.md).

## Deploying

1. **Backend:** build `backend/Dockerfile`, push to ECR, and create an App Runner service on port 8000 with the production env vars (`SECURE_COOKIES=true`, an RDS `DATABASE_URL`).
2. **Frontend:** import `frontend/` into Vercel and replace `REPLACE-WITH-APP-RUNNER-URL` in `frontend/vercel.json` with the App Runner URL. The rewrite keeps the frontend and API on one origin, so there are no CORS or cookie problems.
3. **Fallback:** if AWS isn't working by H17, deploy the backend to Render or Railway, or record the demo on localhost. The judges score the video.
