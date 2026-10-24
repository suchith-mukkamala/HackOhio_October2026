"""GitHub REST helpers. All calls use the signed-in user's OAuth token."""

import httpx

API = "https://api.github.com"


def _client(token: str | None) -> httpx.Client:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=API, headers=headers, timeout=15)


def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> str:
    resp = httpx.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise ValueError(resp.json().get("error_description", "GitHub did not return a token"))
    return token


def get_viewer(token: str) -> dict:
    with _client(token) as gh:
        return gh.get("/user").raise_for_status().json()


def list_repos(token: str) -> list[dict]:
    with _client(token) as gh:
        repos = gh.get("/user/repos", params={"sort": "pushed", "per_page": 50}).raise_for_status().json()
    return [
        {
            "full_name": r["full_name"],
            "description": r["description"],
            "language": r["language"],
            "pushed_at": r["pushed_at"],
            "private": r["private"],
        }
        for r in repos
    ]


def repo_languages(token: str | None, full_name: str) -> dict[str, int]:
    """Bytes of code per language, e.g. {"Python": 12034, "TypeScript": 8800}."""
    with _client(token) as gh:
        return gh.get(f"/repos/{full_name}/languages").raise_for_status().json()


def recent_commits(token: str | None, full_name: str, since: str | None = None, limit: int = 30) -> list[dict]:
    """Commits with message + changed file names (no patch bodies, to keep prompts small)."""
    params = {"per_page": limit}
    if since:
        params["since"] = since
    out = []
    with _client(token) as gh:
        commits = gh.get(f"/repos/{full_name}/commits", params=params).raise_for_status().json()
        for c in commits:
            detail = gh.get(f"/repos/{full_name}/commits/{c['sha']}").raise_for_status().json()
            out.append(
                {
                    "sha": c["sha"],
                    "message": c["commit"]["message"],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"],
                    "files": [f["filename"] for f in detail.get("files", [])][:20],
                    "additions": detail.get("stats", {}).get("additions", 0),
                    "deletions": detail.get("stats", {}).get("deletions", 0),
                }
            )
    return out


def readme(token: str | None, full_name: str) -> str:
    with _client(token) as gh:
        resp = gh.get(f"/repos/{full_name}/readme", headers={"Accept": "application/vnd.github.raw+json"})
    return resp.text[:6000] if resp.status_code == 200 else ""
