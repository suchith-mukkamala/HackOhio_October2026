"""AI features: OpenAI drafts weekly logs from commits; Claude reads resumes.

The student always edits and confirms a draft before it's published.
"""

from anthropic import Anthropic
from openai import OpenAI
from pydantic import BaseModel

from ..config import settings
from .skills import SKILLS


class LogDraft(BaseModel):
    title: str
    built: list[str]
    learned: list[str]
    stuck: list[str]
    skills: list[str]


class ResumeEntry(BaseModel):
    kind: str  # "work" or "education"
    title: str
    org: str
    start: str
    end: str
    summary: str
    skills: list[str]


class ResumeParse(BaseModel):
    entries: list[ResumeEntry]
    major: str  # field of study for the current or latest degree
    bio: str  # one-line summary, used only if the profile has no bio


LOG_INSTRUCTIONS = f"""You help a university student write an honest weekly progress log for a team project.

From the commits, changed files and README you're given, return:
- title: a short, specific headline for the week (under 70 characters)
- built: 3-5 bullets on what changed, in plain language a classmate would understand
- learned: 2-3 bullets naming concepts or skills the work required
- stuck: 0-3 likely open problems, inferred from TODOs, reverts, repeated fixes or "wip" commits. Empty if none.
- skills: skills shown by this week's work, chosen only from this list: {", ".join(SKILLS)}

Only describe work the commits show. Don't invent features, and don't oversell."""

RESUME_INSTRUCTIONS = (
    "Extract every job, internship, research position, project and school from this resume, newest first. "
    'kind is "work" or "education". For education, title is the degree and org is the school. '
    'Copy dates as written; use "Present" for ongoing roles and "" when missing. '
    "summary is one plain sentence on what they did, taken from the resume. "
    f"skills are the skills that entry shows, chosen only from this list: {', '.join(SKILLS)}. "
    "Put skills from a general Skills section on the most recent entry. "
    'major is the field of study of the current or latest degree ("" if none). '
    'bio is one short first-person sentence summarizing them, under 140 characters ("" if the resume gives too little). '
    "Don't invent anything."
)


def _parse(instructions: str, content: list[dict], fmt: type[BaseModel]):
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    response = OpenAI(api_key=settings.openai_api_key).responses.parse(
        model=settings.openai_model,
        instructions=instructions,
        input=[{"role": "user", "content": content}],
        text_format=fmt,
    )
    if response.output_parsed is None:
        raise RuntimeError("The AI couldn't read this; try again or fill it in manually")
    return response.output_parsed


def draft_log(project_title: str, description: str, commits: list[dict], readme: str) -> LogDraft:
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
    draft = _parse(LOG_INSTRUCTIONS, [{"type": "input_text", "text": prompt}], LogDraft)
    draft.skills = [s for s in draft.skills if s in SKILLS]
    return draft


def parse_resume(pdf_b64: str) -> ResumeParse:
    """Pull jobs and schools out of a resume PDF with Claude, newest first."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    response = Anthropic(api_key=settings.anthropic_api_key).beta.messages.parse(
        model=settings.claude_model,
        max_tokens=8000,
        # If the model declines, the API reroutes the same request to another model
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low"},
        system=RESUME_INSTRUCTIONS,
        messages=[{"role": "user", "content": [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
            {"type": "text", "text": "Extract the work experience and education."},
        ]}],
        output_format=ResumeParse,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError("Couldn't read this resume")
    parsed = response.parsed_output
    for e in parsed.entries:
        e.skills = [s for s in dict.fromkeys(e.skills) if s in SKILLS]
    return parsed
