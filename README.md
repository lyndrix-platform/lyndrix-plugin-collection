# lyndrix-plugin-collection

This repository stores a generated plugin directory for Lyndrix.

## Plugin directory files

- `plugin-directory/plugins.json` (canonical source for Lyndrix plugin manager)
- `plugin-directory/plugins.csv` (optional export for spreadsheet/reporting use)

## How it is updated

The workflow at `.github/workflows/sync-plugin-directory.yml` runs daily and on demand.
It fetches repositories for the owner, filters plugin repositories by prefix, and commits refreshed
directory files back to this repository only when data has changed.
