# lyndrix-plugin-collection

This repository stores a generated plugin directory for Lyndrix.

## Plugin list

`plugin-list.txt` in the repo root is the **source of truth** — one GitHub repository URL per line.
Add or remove URLs there to control which plugins appear in the directory.
Blank lines and lines starting with `#` are ignored.

## Plugin directory files

- `plugin-directory/plugins.json` (canonical source for Lyndrix plugin manager)
- `plugin-directory/plugins.csv` (optional export for spreadsheet/reporting use)

## How it is updated

The workflow at `.github/workflows/sync-plugin-directory.yml` runs daily and on demand.
It reads `plugin-list.txt`, fetches current metadata for each repository from the GitHub API,
and commits refreshed directory files back to this repository only when data has changed.
