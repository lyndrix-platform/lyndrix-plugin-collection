#!/usr/bin/env python3
"""Scaffold a MkDocs/Zensical documentation site into each Lyndrix plugin repo.

This mirrors the documentation setup used by ``lyndrix-core`` so every shipped
plugin gets its own site published to ``https://<slug>.docs.lyndrix.eu`` via the
same GitHub Actions + GitHub Pages pipeline.

For each plugin it writes (relative to the plugin repo root):

    mkdocs.yml                     Material theme, site_dir: .cache/site
    docs/index.md                  curated landing page (title + summary + links)
    docs/usage.md                  stub
    docs/configuration.md          stub
    docs/CNAME                     <slug>.docs.lyndrix.eu  (custom domain)
    .github/workflows/docs.yml     zensical build -> GitHub Pages deploy

Existing files are left untouched unless ``--force`` is given.

Usage::

    python scaffold_plugin_docs.py                 # scaffold all plugins
    python scaffold_plugin_docs.py server-manager  # one or more by slug
    python scaffold_plugin_docs.py --force          # overwrite existing files
    python scaffold_plugin_docs.py --plugins-root /path/to/lyndrix-dev

By default ``--plugins-root`` is the parent of the plugin-collection repo
(i.e. the ``lyndrix-dev`` workspace that holds all ``lyndrix-plugin-*`` repos).
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

GITHUB_ORG = "https://github.com/lyndrix-platform"
DOCS_APEX = "docs.lyndrix.eu"
CORE_DOCS = "https://docs.lyndrix.eu"


@dataclass
class Plugin:
    slug: str           # hyphenated; also the docs subdomain label
    repo: str           # repository directory name == GitHub repo name
    name: str           # display name
    summary: str        # one-paragraph description (authoritative — not from README)
    features: list[str] = field(default_factory=list)
    # Core component this plugin builds on, linked from the landing page.
    core_link: str | None = None


# Authoritative metadata. Descriptions come from each plugin manifest, NOT the
# repo README (two READMEs are stale copy-paste of meeting-bingo).
PLUGINS: list[Plugin] = [
    Plugin(
        slug="iac-orchestrator",
        repo="lyndrix-plugin-iac-orchestrator",
        name="IaC Orchestrator",
        summary=(
            "A GitOps controller for orchestrating Infrastructure-as-Code "
            "deployments with Terraform and Ansible, integrated with Lyndrix Core."
        ),
        features=[
            "Terraform and Ansible pipeline orchestration",
            "Webhook triggers for CI/CD, git sync, and commit/push",
            "Drift detection and parallel provisioning",
            "Notification endpoints (started, succeeded, failed, drift_detected)",
        ],
        core_link="core-components/sockets/",
    ),
    Plugin(
        slug="server-manager",
        repo="lyndrix-plugin-server-manager",
        name="Server Manager",
        summary=(
            "Central server inventory built around YAML/JSON hardware catalogs "
            "and combination rules, with event-bus hooks for downstream order workflows."
        ),
        features=[
            "Server inventory management with a guided configuration wizard",
            "Configurable hardware catalogs and combination/validation rules",
            "Event-driven hooks (server_created, status_changed, …)",
            "Dashboard widget, settings UI, and REST API",
        ],
    ),
    Plugin(
        slug="docker-manager",
        repo="lyndrix-plugin-docker-manager",
        name="Docker Manager",
        summary=(
            "Docker monitoring with runtime controls (start/stop/restart/logs/shell), "
            "built on the Lyndrix Core sockets layer."
        ),
        features=[
            "Container monitoring and runtime control",
            "Host management with Vault-backed persistence",
            "Dashboard widget and settings UI",
            "REST API for container operations",
        ],
        core_link="core-components/sockets/",
    ),
    Plugin(
        slug="monitoring",
        repo="lyndrix-plugin-monitoring",
        name="State Monitoring",
        summary=(
            "Native infrastructure and service monitoring with persistent, grouped "
            "status timelines for servers and services."
        ),
        features=[
            "Infrastructure and service state monitoring",
            "Passive monitoring-result ingestion with admin override",
            "Inventory sync from other plugins",
            "Modular UI with toolbar and preferences",
        ],
        core_link="core-components/notification-router/",
    ),
    Plugin(
        slug="external-services",
        repo="lyndrix-plugin-external-services",
        name="External Services",
        summary=(
            "Embed external web services (Home Assistant, Grafana, Netdata, …) "
            "directly into the Lyndrix UI as full-screen iframes with sidebar entries."
        ),
        features=[
            "iframe-based embedding of external services",
            "Managed service registry with DB persistence",
            "Event-driven service registration",
        ],
    ),
    Plugin(
        slug="discord-notifier",
        repo="lyndrix-plugin-discord-notifier",
        name="Discord Notifier",
        summary=(
            "Two-way Discord integration (bot API + webhook) implemented as a "
            "Lyndrix Messaging Gateway adapter; supports multiple channel instances."
        ),
        features=[
            "Dual-mode delivery: Discord bot API and webhooks",
            "Multiple independent Discord instances via env vars",
            "Messaging Gateway adapter with interactive actions",
        ],
        core_link="core-components/messaging/",
    ),
    Plugin(
        slug="meeting-bingo",
        repo="lyndrix-plugin-meeting-bingo",
        name="Meeting Bingo",
        summary=(
            "Multiplayer bullshit-bingo for long meetings — a reference/novelty "
            "plugin showcasing live sessions and Vault-backed persistence."
        ),
        features=[
            "Multiplayer bingo sessions with configurable board size",
            "Live session updates and an optional scoreboard",
            "Vault-backed persistence",
        ],
    ),
]


def mkdocs_yml(p: Plugin) -> str:
    return f"""\
site_name: Lyndrix {p.name}
site_description: Documentation for the Lyndrix {p.name} plugin
site_url: https://{p.slug}.{DOCS_APEX}
site_dir: .cache/site
repo_url: {GITHUB_ORG}/{p.repo}

theme:
  name: material
  palette:
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: emerald
      toggle:
        icon: material/weather-sunny
        name: Switch to light mode
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: emerald
      toggle:
        icon: material/weather-night
        name: Switch to dark mode

nav:
  - Home: index.md
  - Usage: usage.md
  - Configuration: configuration.md
"""


def index_md(p: Plugin) -> str:
    features = "\n".join(f"- {f}" for f in p.features) or "- _Documented in Usage._"
    core_ref = (
        f"\nThis plugin builds on the Lyndrix Core "
        f"[{p.core_link.strip('/').split('/')[-1].replace('-', ' ')}]"
        f"({CORE_DOCS}/{p.core_link}) extension point.\n"
        if p.core_link
        else ""
    )
    return f"""\
# Lyndrix {p.name}

{p.summary}

- **Repository:** [{GITHUB_ORG}/{p.repo}]({GITHUB_ORG}/{p.repo})
- **Platform docs:** [Lyndrix Core]({CORE_DOCS}) · [Plugin ecosystem]({CORE_DOCS}/ecosystem/)
{core_ref}
## Features

{features}

## Installation

Install **{p.name}** from the Lyndrix **Plugin Manager**, or declare it for
reconciliation on boot via `LYNDRIX_PLUGINS_DESIRED`:

```text
{GITHUB_ORG}/{p.repo}
```

See the [Plugin Development Guide]({CORE_DOCS}/plugins/) for the plugin model and
lifecycle, and [Usage](usage.md) / [Configuration](configuration.md) for details.
"""


def usage_md(p: Plugin) -> str:
    return f"""\
# Usage

> **TODO:** Document how to operate the {p.name} plugin — main screens, typical
> workflows, and any REST API endpoints it exposes under
> `/api/plugins/<plugin-id>/`.

For the platform context this plugin runs in, see the
[Lyndrix Core documentation]({CORE_DOCS}).
"""


def configuration_md(p: Plugin) -> str:
    return f"""\
# Configuration

> **TODO:** Document the {p.name} configuration surface — environment variables,
> Vault-backed secrets, and any operator-provided catalog/config files.

Secrets are stored in the plugin's own Vault namespace via `ctx.get_secret` /
`ctx.set_secret`; see [Plugin development → state and secrets]({CORE_DOCS}/plugins/).
"""


# Mirrors lyndrix-core/.github/workflows/docs.yml
DOCS_WORKFLOW = """\
name: Build and Deploy Documentation

on:
  push:
    branches:
      - main
    paths:
      - "docs/**"
      - "mkdocs.yml"
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: true

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install Zensical
        run: pip install zensical

      - name: Build Docs with Zensical
        run: zensical build

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: "./.cache/site"

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""


def write_file(path: Path, content: str, force: bool) -> str:
    if path.exists() and not force:
        return f"  skip   {path}  (exists)"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"  write  {path}"


def scaffold(p: Plugin, root: Path, force: bool) -> list[str]:
    repo = root / p.repo
    if not repo.is_dir():
        return [f"  MISS   {repo}  (repo directory not found — skipped)"]
    out = [f"[{p.slug}] -> {repo}"]
    out.append(write_file(repo / "mkdocs.yml", mkdocs_yml(p), force))
    out.append(write_file(repo / "docs" / "index.md", index_md(p), force))
    out.append(write_file(repo / "docs" / "usage.md", usage_md(p), force))
    out.append(write_file(repo / "docs" / "configuration.md", configuration_md(p), force))
    out.append(write_file(repo / "docs" / "CNAME", f"{p.slug}.{DOCS_APEX}\n", force))
    out.append(write_file(repo / ".github" / "workflows" / "docs.yml", DOCS_WORKFLOW, force))
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slugs", nargs="*", help="Plugin slugs to scaffold (default: all)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument(
        "--plugins-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Directory containing the lyndrix-plugin-* repos",
    )
    args = parser.parse_args(argv)

    selected = PLUGINS
    if args.slugs:
        by_slug = {p.slug: p for p in PLUGINS}
        unknown = [s for s in args.slugs if s not in by_slug]
        if unknown:
            parser.error(f"unknown slug(s): {', '.join(unknown)}")
        selected = [by_slug[s] for s in args.slugs]

    print(f"plugins-root: {args.plugins_root}")
    for p in selected:
        for line in scaffold(p, args.plugins_root, args.force):
            print(line)
    print(
        "\nNext (manual, once per repo):\n"
        "  - GitHub -> Settings -> Pages: enable, set custom domain "
        "<slug>.docs.lyndrix.eu\n"
        "  - DNS: CNAME <slug>.docs.lyndrix.eu -> lyndrix-platform.github.io"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
