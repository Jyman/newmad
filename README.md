# remote-radar

Aggregate remote developer jobs from public sources into one ranked view. Pulls
live listings from RemoteOK and Hacker News "Who is hiring" threads, normalizes
them into a single schema, filters by keyword/tag/salary, and prints a ranked
table or JSON. No API keys required.

## Install

```bash
git clone <this-repo>
cd remote-radar
python remote_radar.py --help
```

Requires Python 3.10+. No third-party runtime dependencies (standard library only).

## Usage

```bash
# Python backend roles paying at least $60k
python remote_radar.py --tags python,backend --min-salary 60000

# Anything mentioning rust, as JSON
python remote_radar.py --keyword rust --json

# Search a specific HN "who is hiring" query, cap the output
python remote_radar.py --hn-query golang --limit 20
```

### Options

| Flag | Purpose |
|---|---|
| `--keyword` | Substring match on title / company / tags |
| `--tags` | Comma-separated tags that must be present |
| `--min-salary` | Minimum of the listing's max salary, in USD |
| `--hn-query` | Search term for HN "Who is hiring" comments |
| `--json` | Emit JSON instead of a table |
| `--limit` | Cap the number of rows (default 40) |

## Sources

| Source | Endpoint | Notes |
|---|---|---|
| RemoteOK | `remoteok.com/api` | First array element is a legal notice, skipped |
| Hacker News | `hn.algolia.com` Algolia search | Salaries parsed heuristically from free text |

## Tests

Offline, deterministic — real captured API responses live in `fixtures/`.

```bash
python -m pytest -q
```

## Files

| Path | Purpose |
|---|---|
| `remote_radar.py` | Core: fetch, normalize, filter, rank, CLI |
| `test_remote_radar.py` | 8 tests over saved real payloads |
| `fixtures/` | Captured RemoteOK + HN responses for tests |

## License

MIT
