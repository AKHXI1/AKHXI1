"""Update the Recently Updated Repositories list in README.md."""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

USERNAME = os.environ.get("GITHUB_USERNAME", "AKHXI1")
MAX_REPOS = 6
README_PATH = Path(__file__).resolve().parents[2] / "README.md"

START_MARKER = "<!-- RECENT_REPOS:START -->"
END_MARKER = "<!-- RECENT_REPOS:END -->"

EXCLUDED_REPOS = {
    "AKHXI1",
    "AKHXI11",
    "github-slideshow",
    "intro-html",
    "markdown-portfolio",
    # Temporarily excluded until committed .env secrets are rotated/purged:
    "journey-sync",
    "family-tree",
    "fraxal_NFT-Platform",
}
EXCLUDED_PREFIXES = ("skills-", "learningfest", "learning-fest")


def fetch_repos(username: str) -> list[dict]:
    """Fetch public repositories for a GitHub user sorted by most recent push."""
    url = f"https://api.github.com/users/{username}/repos?per_page=100&sort=pushed&direction=desc"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{username}-profile-updater",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_eligible(repo: dict) -> bool:
    """Return True for active, non-fork, non-tutorial source repositories."""
    name = repo.get("name", "")
    if repo.get("fork") or repo.get("archived") or repo.get("size", 0) == 0:
        return False
    if name in EXCLUDED_REPOS or name.lower().startswith(EXCLUDED_PREFIXES):
        return False
    return True


def clean_text(text: str | None) -> str:
    """Normalize whitespace in repository descriptions."""
    if not text:
        return ""
    return " ".join(text.split())


def format_list(repos: list[dict]) -> str:
    """Render the selected repositories inside a clean collapsible Markdown list."""
    lines = [
        "<details>",
        f"<summary><strong>View {len(repos)} most recently updated public repositories (auto-synced daily)</strong></summary>",
        "",
    ]
    for repo in repos:
        name = repo["name"]
        url = repo["html_url"]
        desc = clean_text(repo.get("description"))
        lang = clean_text(repo.get("language")) or "Other"
        updated = (repo.get("pushed_at") or "")[:10] or "—"
        homepage = (repo.get("homepage") or "").strip()

        if homepage.startswith(("http://", "https://")):
            primary_link = f"**[{name}]({homepage})**"
            extra_links = f"[Live Demo]({homepage}) · [Repo]({url})"
        else:
            primary_link = f"**[{name}]({url})**"
            extra_links = f"[Repo]({url})"

        summary_part = f" — {desc}" if desc else ""
        lines.append(f"- {primary_link} (`{lang}` · updated `{updated}`){summary_part} · {extra_links}")

    lines.append("")
    lines.append("</details>")
    return "\n".join(lines)


def update_readme(section_md: str) -> bool:
    """Replace the RECENT_REPOS block in README.md; return True if modified."""
    content = README_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"({re.escape(START_MARKER)})(.*?)({re.escape(END_MARKER)})",
        flags=re.DOTALL,
    )
    if not pattern.search(content):
        raise ValueError(f"Markers {START_MARKER} / {END_MARKER} not found in {README_PATH}")

    replacement = f"{START_MARKER}\n{section_md}\n{END_MARKER}"
    updated_content = pattern.sub(replacement, content, count=1)
    if updated_content == content:
        return False

    README_PATH.write_text(updated_content, encoding="utf-8")
    return True


def main() -> None:
    repos = [r for r in fetch_repos(USERNAME) if is_eligible(r)]
    repos.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    section_md = format_list(repos[:MAX_REPOS])
    changed = update_readme(section_md)
    print(f"Processed {len(repos[:MAX_REPOS])} repositories. README changed: {changed}")


if __name__ == "__main__":
    main()
