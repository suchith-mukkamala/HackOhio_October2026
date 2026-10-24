"""AI features, using OpenAI: draft weekly logs from commits, and read resumes.

The student always edits and confirms a draft before it's published.
"""

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


class ResumeParse(BaseModel):
    entries: list[ResumeEntry]


LOG_INSTRUCTIONS = f"""You help a university student write an honest weekly progress log for a team project.

From the commits, changed files and README you're given, return:
- title: a short, specific headline for the week (under 70 characters)
- built: 3-5 bullets on what changed, in plain language a classmate would understand
- learned: 2-3 bullets naming concepts or skills the work required
- stuck: 0-3 likely open problems, inferred from TODOs, reverts, repeated fixes or "wip" commits. Empty if none.
- skills: skills shown by this week's work, chosen only from this list: {", ".join(SKILLS)}

Only describe work the commits show. Don't invent features, and don't oversell."""

RESUME_INSTRUCTIONS = (
    "Extract every job, internship, research position and school from this resume, newest first. "
    'kind is "work" or "education". For education, title is the degree and org is the school. '
    'Copy dates as written; use "Present" for ongoing roles and "" when missing. '
    "summary is one plain sentence on what they did, taken from the resume. Don't invent anything."
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


def parse_resume(pdf_b64: str) -> list[ResumeEntry]:
    """Pull jobs and schools out of a resume PDF, newest first."""
    content = [
        {"type": "input_file", "filename": "resume.pdf", "file_data": f"data:application/pdf;base64,{pdf_b64}"},
        {"type": "input_text", "text": "Extract the work experience and education."},
    ]
    return _parse(RESUME_INSTRUCTIONS, content, ResumeParse).entries
