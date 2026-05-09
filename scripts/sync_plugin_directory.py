#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


OUTPUT_DIR = Path("plugin-directory")
JSON_FILE = OUTPUT_DIR / "plugins.json"
CSV_FILE = OUTPUT_DIR / "plugins.csv"
PLUGIN_PREFIX = os.getenv("PLUGIN_PREFIX", "lyndrix-plugin-")
EXCLUDED_REPOSITORIES = set(
    value.strip()
    for value in os.getenv("EXCLUDED_REPOSITORIES", "lyndrix-plugin-collection").split(",")
    if value.strip()
)


def github_api_get(url: str, token: str | None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lyndrix-plugin-directory-sync",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    with urlopen(request) as response:  # nosec B310 - URL is fixed to GitHub API calls in this script
        return json.load(response)


def get_owner_repositories_url(owner: str, owner_type: str, page: int) -> str:
    if owner_type == "Organization":
        return f"https://api.github.com/orgs/{owner}/repos?type=public&per_page=100&page={page}"
    return f"https://api.github.com/users/{owner}/repos?type=public&per_page=100&page={page}"


def list_plugin_repositories(owner: str, token: str | None) -> list[dict[str, Any]]:
    repositories: list[dict[str, Any]] = []
    page = 1
    owner_data = github_api_get(f"https://api.github.com/users/{owner}", token)
    owner_type = owner_data.get("type", "User")

    while True:
        url = get_owner_repositories_url(owner, owner_type, page)
        data = github_api_get(url, token)
        if not isinstance(data, list):
            raise RuntimeError("Unexpected GitHub API response: expected a list of repositories.")
        if len(data) == 0:
            break

        repositories.extend(data)
        page += 1

    return filter_plugin_repositories(repositories)


def filter_plugin_repositories(repositories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for repo in repositories:
        repo_name = repo.get("name", "")
        if not repo_name.startswith(PLUGIN_PREFIX):
            continue
        if repo_name in EXCLUDED_REPOSITORIES:
            continue
        filtered.append(repo)

    filtered.sort(key=lambda repo: repo["full_name"].lower())
    return filtered


def load_repositories_from_file(path: str) -> list[dict[str, Any]]:
    content = Path(path).read_text(encoding="utf-8")
    data = json.loads(content)
    if not isinstance(data, list):
        raise RuntimeError("PLUGIN_REPOSITORIES_FILE must contain a JSON array of repositories.")
    return filter_plugin_repositories(data)


def get_repositories(owner: str, token: str | None) -> list[dict[str, Any]]:
    repositories_file = os.getenv("PLUGIN_REPOSITORIES_FILE")
    if repositories_file:
        return load_repositories_from_file(repositories_file)

    return list_plugin_repositories(owner, token)


def to_plugin_entry(repo: dict[str, Any]) -> dict[str, Any]:
    slug = repo["name"][len(PLUGIN_PREFIX) :]
    return {
        "slug": slug,
        "name": repo["name"],
        "full_name": repo["full_name"],
        "description": repo.get("description"),
        "html_url": repo["html_url"],
        "clone_url": repo["clone_url"],
        "default_branch": repo["default_branch"],
        "topics": repo.get("topics", []),
        "stargazers_count": repo["stargazers_count"],
        "forks_count": repo["forks_count"],
        "open_issues_count": repo["open_issues_count"],
        "archived": repo["archived"],
        "disabled": repo["disabled"],
        "pushed_at": repo["pushed_at"],
        "updated_at": repo["updated_at"],
    }


def write_outputs(owner: str, plugins: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "owner": owner,
        "plugin_prefix": PLUGIN_PREFIX,
        "plugin_count": len(plugins),
        "plugins": plugins,
    }

    JSON_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    fieldnames = [
        "slug",
        "name",
        "full_name",
        "description",
        "html_url",
        "clone_url",
        "default_branch",
        "topics",
        "stargazers_count",
        "forks_count",
        "open_issues_count",
        "archived",
        "disabled",
        "pushed_at",
        "updated_at",
    ]
    with CSV_FILE.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for plugin in plugins:
            row = {
                field: (";".join(plugin.get("topics", [])) if field == "topics" else plugin.get(field))
                for field in fieldnames
            }
            writer.writerow(row)


def main() -> int:
    owner = os.getenv("PLUGIN_OWNER", "marvin1309")
    token = os.getenv("GITHUB_TOKEN")

    try:
        repositories = get_repositories(owner, token)
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed ({exc.code}): {message}") from exc

    plugins = [to_plugin_entry(repo) for repo in repositories]
    write_outputs(owner, plugins)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
