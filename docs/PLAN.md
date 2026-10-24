# Hackathon plan

HackOHI/O 2026 · Bridge Builder Challenge (Honda Research Institute × 99P Labs)

> **The challenge:** Design and build one part of a community platform that connects students with each other and with industry, so they learn by doing real work together. Pick one part and build a working demo of it.

This document is the single source of truth for scope, ownership and timing. If you're about to build something that isn't in here, check with the team first.

---

## 1. The one rule

**If a feature isn't in demo flow steps 1–6, it doesn't start until the H10 gate passes.**

The judging doc says *"One complete flow beats five half-built features"*, and **Completeness** is scored on whether the demo shows one full flow. The whiteboard has about 15 features. We build one flow that works perfectly, and make everything around it simple.

## 2. The pitch

> **A portfolio AI can't fake.** Students build in public. AI turns their commits into a progress log, mentors give 5–15 minute feedback, and every skill on the profile is backed by code or by a person who vouched for it.

We dropped the whiteboard's "an app for students to create their own apps" framing because it doesn't answer the prompt. The challenge's core point is that AI-written resumes make skill lists meaningless, so a record earned from others matters more.

**How we talk about AI.** The doc says AI is welcome *"when it helps people connect and learn, not when it generates polish."* Auto-docs could look like polish, so we always frame it as **AI drafts → student confirms → mentor verifies.** Its real job is to surface blockers and route them to a mentor.

## 3. The demo flow

| Step | What happens | Ladder rung | Priority |
|---|---|---|---|
| 1 | Sign in with GitHub. The profile fills itself from repos and languages. | Look around | P0 |
| 2 | Push a project: pick a repo, add description, tags, "looking for". | Join a project | P0 |
| 3 | Generate a log: commits → Claude draft → student edits → publish to timeline and feed. | (core) | P0 |
| 4 | "Ask a mentor" on a stuck item creates a help request with a 5/15/30 min time ask. | Show up | P0 |
| 5 | Switch to mentor persona. Inbox ranked by skill match; answer and endorse. | (industry) | P0 |
| 6 | Student marks it helpful. The skill turns gold on the graph with evidence. | Give back | P0 |
| 7 | Student comments on a peer's project and earns "help given" credit. | Give back | Bonus |

### How this hits the judging criteria

| Criterion | Our answer |
|---|---|
| Problem solving | Steps 4–6: a student gets unstuck in minutes, and the mentor's time is respected |
| Creativity | A tiered, evidence-backed skill graph, and AI that routes people to help instead of writing polish |
| Clarity | The 3-minute script in section 9 |
| Completeness | Steps 1–6 work end to end with no fake screens |

### How it answers "Things to Consider"

| Consideration | Our answer |
|---|---|
| Solve the empty room | GitHub import makes your profile and log useful on day one, even if nobody else has joined |
| Respect everyone's time | Mentors pick 5, 15 or 30 minute asks; AI turns blockers into short, specific questions |
| Community, not a job board | No job listings or applicant rankings; the record is built from helping and building |
| Make growth visible | The skill graph shows *who* vouched for each skill and *what* they saw |
| Think big, start small | One complete flow; the rest of the platform is sketched in the pitch |

---

## 4. Scope decisions (from the whiteboard)

| Feature | Decision |
|---|---|
| Create account / auth | **P0.** GitHub OAuth for students, plus a demo persona picker for mentors and faculty |
| Push projects | **P0** |
| Profile (GitHub) + skill node graph | **P0.** This is our differentiator |
| Auto-documentation | **P0, code only.** Hardware info is cut |
| Timeline | **P0.** It's the output of auto-docs |
| Request help / respond to requests | **P0.** The mentor half of the flow |
| View projects | **P0** |
| LinkedIn-style posts / feed | **P1.** Published logs become posts automatically |
| Search projects / students | **P1.** Text match plus tag filters |
| DMs | **P1.** Poll every 3s; no websockets |
| Comment on projects | **P1** |
| Invite to join project | **P2.** Creates a pending invite |
| Archive projects | **P2.** A status flag |
| Faculty role | Same as mentor, with a "Faculty" badge |
| Streamlit | **Dropped.** Can't make a social app look good |
| AWS | **P1, not P0.** The judged artifact is a video; deploy after the flow works |

---

## 5. Architecture

```
Browser (Vite + React)
   │  /api/*  (Vite proxy in dev, Vercel rewrite in prod)
   ▼
FastAPI  ──► SQLite (local) / RDS Postgres (prod)
   │
   ├──► GitHub REST API  (repos, languages, commits, README)
   └──► Claude API       (commits → structured LogDraft)
```

- One origin for frontend and API, so there are no CORS or cross-site cookie issues.
- The session is a signed JWT in an httpOnly cookie.
- The GitHub token is stored server-side only and never returned by the API (`PublicUser` strips it).

### Data model

All tables live in `backend/app/models.py`. Lists are JSON columns.

| Table | Key fields |
|---|---|
| `User` | role (student/mentor/faculty), name, major, year, company, title, bio, github_username, expertise_tags |
| `Project` | owner_id, title, description, repo_full_name, tags, looking_for, status, start/end dates |
| `ProjectMember` | project_id, user_id, role |
| `Invite` | project_id, from_id, to_id, status |
| `LogEntry` | project_id, author_id, week_label, title, built, learned, stuck, skills, commit_shas, source |
| `Post` | author_id, project_id?, log_entry_id?, body, type |
| `Comment` | author_id, post_id? or project_id?, body |
| `HelpRequest` | project_id, requester_id, question, tags, minutes, status, mentor_id, answer, helpful |
| `Endorsement` | from_id, to_id, skill, project_id?, help_request_id?, note |
| `Thread` / `ThreadMember` / `Message` | 1:1 DMs |

### Key mechanics

**Auto-docs** (`services/github.py`, `services/claude.py`)
1. Fetch commits since the last log, with changed file names and line stats (no patch bodies).
2. Add the README and project description.
3. Claude returns a `LogDraft`: `title`, `built`, `learned`, `stuck`, `skills` (from a fixed vocabulary).
4. The student edits the draft, then publishes. Each `stuck` bullet gets an "Ask a mentor" button.
5. **Pre-generate logs for every seeded project** so the demo never waits on an API call.

**Skill graph** (`services/skills.py`)
- Score = log(1 + code evidence) + 2 × peer endorsements + 3 × mentor endorsements + 1 × helpful answers given.
- Tier = strongest evidence: claimed → code → peer → mentor.
- Edges connect skills used together in the same project.
- Top 12 skills only, so the graph stays readable.

**Mentor matching** (`routers/help.py`)
- Score = overlap between request tags and mentor expertise, plus a small bonus for 5 and 15 minute asks.

---

## 6. Ownership

| Person | Hours | Work |
|---|---|---|
| **Rohan** | H0–2 | Repo conventions, env setup for everyone, confirm skeleton runs on all laptops |
| | H2–5 | GitHub OAuth app (local), test real sign-in end to end |
| | H5–9 | App shell polish: nav, role-based links, landing page design |
| | H12–16 | Dockerfile → ECR → App Runner, RDS, Vercel rewrite, production OAuth app |
| | H16+ | Deploy fixes, bug bash |
| **Neel** | H0–2 | Tune the Claude prompt against 2–3 real repos |
| | H2–6 | Draft + publish endpoints, cache drafts by latest commit SHA |
| | H6–10 | Draft editor UI and project **timeline** component, "Ask a mentor" hand-off |
| | H10–13 | Feed page, post composer, comments |
| | H16+ | Pre-generate logs for seed projects, timeline polish |
| **Suchith** | H0–3 | Skill vocabulary + scoring (extend with GitHub language bytes) |
| | H3–7 | Repo picker + create project flow, project page (minus timeline) |
| | H7–12 | Profile page and **skill graph** with tiers and evidence panel |
| | H12–15 | Invite, archive, project cards for explore and feed |
| **Adi** | H0–3 | Grow `seed.py`: ~12 students, 5 mentors, 2 faculty, 6 projects, real repos |
| | H3–8 | Help request form, mentor inbox, answer + endorse, "helpful" |
| | H8–11 | Explore / search page |
| | H11–14 | DMs |
| | H14+ | Help with AWS, bug bash |
| **Pitch owner** | H14+ | Pick one person now. Write the script at H14, not H20 |

---

## 7. Timeline

Assumes about 24 hours. Shift the H-numbers to real clock times at kickoff.

| Hour | Milestone |
|---|---|
| **H0–1** | Lock scope. **Post in the Honda channel on the HackOHI/O Discord to tell Ryan & Tony we're doing this challenge** (required). Everyone runs the skeleton locally. |
| H1–4 | GitHub OAuth, Claude prompt prototype, bigger seed data, frontend pages on real endpoints |
| **H4 gate** | Sign in → see a seeded profile from the real database |
| H4–10 | P0 build: project create, log draft and publish, timeline, help request → inbox → answer, skill graph |
| **H10 gate** | **Click through steps 1–6 on localhost.** If anything breaks, everyone fixes the flow before new features. |
| H10–16 | P1: feed, search, DMs, comments. Sleep in shifts, two people at a time, about 3 hours each. |
| H14–17 | Deploy (Rohan + Adi). Pitch owner writes the script. |
| **H17** | **Feature freeze.** Bug fixes and visual polish only. |
| H17–20 | Bug bash, perfect the demo data, rehearse the flow three times |
| H20–22 | Record screen capture and voiceover, edit |
| **H22** | **Upload the video.** |
| H22–24 | Buffer, README, submit links |

---

## 8. Seed data

What fixes the empty room in the demo:

- **12 students** across majors (CSE, ME, ECE, Design, Business, Data Analytics) with believable bios and years
- **5 industry mentors** (e.g. Honda R&D software engineer, 99P Labs data scientist, startup PM, hardware engineer) and **2 faculty**
- **6 projects**, 4–6 weeks each, with 3–4 timeline entries, linked to **real public repos we control** so GitHub calls work
- About 20 posts, 15 comments, 8 help requests (mixed open and answered), 15 endorsements, 3 DM threads
- **The demo student** starts with a modest graph, so the before/after change is obvious on camera

---

## 9. Video pitch (~3 minutes)

| Time | Content |
|---|---|
| 0:00–0:20 | Team intros. The problem: AI writes resumes now, so a list of skills says almost nothing. |
| 0:20–0:40 | Our part of the platform: the proof layer. Every skill is backed by shipped code or a person who vouched for it. Mentors give minutes, not weeks. |
| 0:40–2:15 | Live demo of steps 1–6, switching personas with the picker. Cut dead time in editing. |
| 2:15–2:35 | Connection (matched help), Learning (weekly reflection), Momentum (log → ask → feedback every week), Trust (tiered skill graph). Empty room: GitHub import makes it useful on day one. |
| 2:35–2:55 | What we learned building it. Be specific: OAuth, prompt tuning, graph scoring. |
| 2:55–3:00 | Repo and demo link on screen |

Tools from the whiteboard: Slides Go, Canva or Google Slides for the few title cards.

---

## 10. Risks and fallbacks

| Risk | Fallback |
|---|---|
| GitHub rate limits or OAuth breaks on camera | Cache GitHub responses; record with the demo persona picker |
| Claude is slow or fails during recording | Pre-generated logs for seed projects; return the cached draft first |
| AWS takes too long | Hard cutoff at H17 → Render/Railway, or record on localhost |
| Skill graph looks messy | Top 12 skills only; fixed node size per tier |
| Integration hell at the end | H4 and H10 gates are mandatory; PR into `main` at least every 2 hours |
| Video upload is late | Upload a rough cut at H21 and replace it if there's time |

---

## 11. First-hour checklist

- [ ] Post in the Honda Discord channel
- [ ] Agree on the product name (ideas: Keystone, Proof, Buckeye Build)
- [ ] Everyone runs backend + frontend locally (see README)
- [ ] Create the local GitHub OAuth app; share the client ID and secret privately, never in the repo
- [ ] Share an Anthropic API key privately for `backend/.env`
- [ ] Pick the 6 real repos for seed projects
- [ ] Pick the pitch owner

## Contacts

Challenge questions go to Ryan Lingo and Tony Fontana (99P Labs / Honda) in the Honda channel on the HackOHI/O Discord.
