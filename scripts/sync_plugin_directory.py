#!/usr/bin/env python3
"""Sync plugin directory from an explicit list of GitHub repository URLs.

Reads plugin-list.txt (one GitHub URL per line, blank lines and # comments ignored),
fetches metadata for each repo from the GitHub API, and writes plugin-directory/plugins.json
and plugin-directory/plugins.csv.
"""
from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# The list of plugin repos lives alongside this script's sibling file in the repo root.
PLUGIN_LIST_FILE = Path(__file__).parent.parent / "plugin-list.txt"

OUTPUT_DIR = Path("plugin-directory")
JSON_FILE = OUTPUT_DIR / "plugins.json"
CSV_FILE = OUTPUT_DIR / "plugins.csv"

# Prefix stripped from the repo name to produce a human-friendly slug.
# e.g. "lyndrix-discord-notifier" -> slug "discord-notifier"
SLUG_PREFIX = os.getenv("SLUG_PREFIX", "lyndrix-")

GITHUB_API_BASE = "https://api.github.com"


def github_api_get(url: str, token: str | None) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "lyndrix-plugin-directory-sync",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    with urlopen(request) as response:  # nosec B310 - URL is validated to the GitHub API domain
        return json.load(response)


def read_plugin_urls() -> list[str]:
    """Return non-empty, non-comment lines from plugin-list.txt."""
    if not PLUGIN_LIST_FILE.exists():
        raise FileNotFoundError(f"Plugin list not found: {PLUGIN_LIST_FILE}")

    urls: list[str] = []
    for raw in PLUGIN_LIST_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def parse_github_url(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub URL such as https://github.com/owner/repo."""
    parts = url.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse GitHub URL: {url!r}")
    return parts[-2], parts[-1]


def fetch_repo_metadata(owner: str, repo: str, token: str | None) -> dict[str, Any]:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    return github_api_get(url, token)


def _semver_key(tag: str) -> list[int]:
    """Sort key from a tag's numeric components (e.g. 'v1.2.0' -> [1, 2, 0])."""
    return [int(part) for part in re.split(r"[^0-9]+", tag.lstrip("v")) if part]


def fetch_repo_tags(owner: str, repo: str, token: str | None) -> list[str]:
    """Return the repo's tag names, newest first.

    Tags are cached in plugins.json so the app can populate version pickers
    without hitting the GitHub API on every interaction. Failures are
    non-fatal — an empty list just means the app falls back to a live lookup.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/tags?per_page=100"
    try:
        tags = github_api_get(url, token)
    except HTTPError as exc:
        print(f"  WARN  tags for {owner}/{repo} — GitHub API {exc.code}")
        return []
    names = [t["name"] for t in tags if isinstance(t, dict) and "name" in t]
    return sorted(names, key=_semver_key, reverse=True)


def to_plugin_entry(repo: dict[str, Any], version_tags: list[str]) -> dict[str, Any]:
    name: str = repo["name"]
    slug = name[len(SLUG_PREFIX):] if name.startswith(SLUG_PREFIX) else name
    return {
        "slug": slug,
        "name": name,
        "full_name": repo["full_name"],
        "description": repo.get("description"),
        "html_url": repo["html_url"],
        "clone_url": repo["clone_url"],
        "default_branch": repo["default_branch"],
        "topics": repo.get("topics", []),
        "version_tags": version_tags,
        "stargazers_count": repo["stargazers_count"],
        "forks_count": repo["forks_count"],
        "open_issues_count": repo["open_issues_count"],
        "archived": repo["archived"],
        "disabled": repo["disabled"],
        "pushed_at": repo["pushed_at"],
        "updated_at": repo["updated_at"],
    }


def write_outputs(plugins: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    payload = {
        "slug_prefix": SLUG_PREFIX,
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
        "version_tags",
        "stargazers_count",
        "forks_count",
        "open_issues_count",
        "archived",
        "disabled",
        "pushed_at",
        "updated_at",
    ]
    list_fields = {"topics", "version_tags"}
    with CSV_FILE.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for plugin in plugins:
            row = {
                field: (";".join(plugin.get(field, [])) if field in list_fields else plugin.get(field))
                for field in fieldnames
            }
            writer.writerow(row)


def main() -> int:
    token = os.getenv("GITHUB_TOKEN")
    urls = read_plugin_urls()
    print(f"Found {len(urls)} plugin(s) in {PLUGIN_LIST_FILE}")

    plugins: list[dict[str, Any]] = []
    errors: list[str] = []

    for url in urls:
        try:
            owner, repo = parse_github_url(url)
        except ValueError as exc:
            print(f"  SKIP  {url} — {exc}")
            errors.append(url)
            continue

        try:
            metadata = fetch_repo_metadata(owner, repo, token)
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            print(f"  ERROR {url} — GitHub API {exc.code}: {message}")
            errors.append(url)
            continue

        version_tags = fetch_repo_tags(owner, repo, token)
        entry = to_plugin_entry(metadata, version_tags)
        plugins.append(entry)
        print(f"  OK    {entry['full_name']}  ({entry['slug']}, {len(version_tags)} tag(s))")

    plugins.sort(key=lambda p: p["full_name"].lower())
    write_outputs(plugins)

    print(f"\nWrote {len(plugins)} plugin(s) to {JSON_FILE} and {CSV_FILE}")
    if errors:
        print(f"WARNING: {len(errors)} URL(s) failed: {errors}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
