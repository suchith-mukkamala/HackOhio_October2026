"""Auto-docs: turn a week of commits into a draft progress log with Claude.

The student always edits and confirms the draft before it's published.
"""

from anthropic import Anthropic
from pydantic import BaseModel

from ..config import settings
from .skills import SKILLS


class LogDraft(BaseModel):
    title: str
    built: list[str]
    learned: list[str]
    stuck: list[str]
    skills: list[str]


SYSTEM = f"""You help a university student write an honest weekly progress log for a team project.

From the commits, changed files and README you're given, return:
- title: a short, specific headline for the week (under 70 characters)
- built: 3-5 bullets on what changed, in plain language a classmate would understand
- learned: 2-3 bullets naming concepts or skills the work required
- stuck: 0-3 likely open problems, inferred from TODOs, reverts, repeated fixes or "wip" commits. Empty if none.
- skills: skills shown by this week's work, chosen only from this list: {", ".join(SKILLS)}

Only describe work the commits show. Don't invent features, and don't oversell."""


def draft_log(project_title: str, description: str, commits: list[dict], readme: str) -> LogDraft:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    commit_lines = "\n".join(
        f"- {c['date'][:10]} {c['author']}: {c['message'].splitlines()[0]} "
        f"(+{c['additions']}/-{c['deletions']}; files: {', '.join(c['files'][:8])})"
        for c in commits
    )
    prompt = (
        f"Project: {project_title}\n{description}\n\n"
        f"README (truncated):\n{readme or '(none)'}\n\n"
        f"Commits this week:\n{commit_lines or '(no commits)'}"
    )

    client = Anthropic(api_key=settings.anthropic_api_key)
    # Server-side fallback: if the model declines, the API reroutes the same request.
    response = client.beta.messages.parse(
        model=settings.claude_model,
        max_tokens=4000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_format=LogDraft,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError("Claude couldn't draft this log; write it manually")
    draft = response.parsed_output
    draft.skills = [s for s in draft.skills if s in SKILLS]
    return draft
