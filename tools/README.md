# Plugin docs tooling

## `scaffold_plugin_docs.py`

Scaffolds a MkDocs/Zensical documentation site into each `lyndrix-plugin-*` repo,
mirroring the `lyndrix-core` docs pipeline so every plugin publishes to
`https://<slug>.docs.lyndrix.eu` via GitHub Actions + GitHub Pages.

```bash
python scaffold_plugin_docs.py                 # all plugins (skips existing files)
python scaffold_plugin_docs.py server-manager  # one or more by slug
python scaffold_plugin_docs.py --force          # overwrite existing files
```

It writes per repo: `mkdocs.yml`, `docs/{index,usage,configuration}.md`,
`docs/CNAME` (`<slug>.docs.lyndrix.eu`), and `.github/workflows/docs.yml`.

Plugin metadata (slug, display name, summary, features) lives in the `PLUGINS`
list at the top of the script — **add new plugins there**, then re-run. Summaries
are authoritative and intentionally taken from plugin manifests rather than the
repo READMEs (some READMEs are stale).

### One-time manual steps per plugin repo

The build/deploy is automated, but the hosting handshake is not:

1. **GitHub → Settings → Pages**: enable Pages and set the custom domain to
   `<slug>.docs.lyndrix.eu`.
2. **DNS**: add a `CNAME` record `<slug>.docs.lyndrix.eu → lyndrix-platform.github.io`.

Subdomains must use hyphens (`server-manager`), not underscores — underscores are
invalid in DNS hostnames.
