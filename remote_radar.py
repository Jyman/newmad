"""remote-radar: aggregate remote developer jobs from public sources.

Pulls live listings from RemoteOK and Hacker News "Who is hiring" threads,
normalizes them into a single schema, filters by keyword/tag, and prints a
ranked table (or JSON). No API keys required.

Usage:
    python remote_radar.py --tags python,backend --min-salary 60000
    python remote_radar.py --keyword rust --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from dataclasses import dataclass, asdict
from typing import Iterable

REMOTEOK_API = "https://remoteok.com/api"
HN_ALGOLIA = (
    "https://hn.algolia.com/api/v1/search_by_date"
    "?tags=comment&query={query}&hitsPerPage=100"
)
UA = "remote-radar/1.0 (+https://github.com/)"


@dataclass
class Job:
    source: str
    position: str
    company: str
    tags: list[str]
    salary_min: int
    salary_max: int
    location: str
    url: str

    def matches(self, keyword: str | None, tags: set[str]) -> bool:
        hay = f"{self.position} {self.company} {' '.join(self.tags)}".lower()
        if keyword and keyword.lower() not in hay:
            return False
        if tags and not tags & {t.lower() for t in self.tags}:
            return False
        return True


def _get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_remoteok(raw: bytes | None = None) -> list[Job]:
    """Parse RemoteOK's public API. First element is a legal notice, skip it."""
    data = json.loads(raw if raw is not None else _get(REMOTEOK_API))
    jobs: list[Job] = []
    for item in data:
        if not isinstance(item, dict) or "position" not in item:
            continue
        jobs.append(
            Job(
                source="remoteok",
                position=item.get("position", "").strip(),
                company=item.get("company", "").strip(),
                tags=[t for t in item.get("tags", []) if t],
                salary_min=int(item.get("salary_min") or 0),
                salary_max=int(item.get("salary_max") or 0),
                location=item.get("location", "").strip(),
                url=item.get("url", ""),
            )
        )
    return jobs


_SALARY_RE = re.compile(r"\$\s?(\d{2,3})\s?[kK]")


def _guess_salary(text: str) -> tuple[int, int]:
    """Pull a rough salary range from free-text HN comments ($120k, $90-130k)."""
    nums = [int(m) * 1000 for m in _SALARY_RE.findall(text)]
    if not nums:
        return 0, 0
    return min(nums), max(nums)


def fetch_hn(query: str = "remote", raw: bytes | None = None) -> list[Job]:
    """Parse HN 'Who is hiring' comments via the public Algolia API."""
    payload = raw if raw is not None else _get(HN_ALGOLIA.format(query=query))
    data = json.loads(payload)
    jobs: list[Job] = []
    for hit in data.get("hits", []):
        text = re.sub(r"<[^>]+>", " ", hit.get("comment_text") or "")
        text = re.sub(r"&#x27;", "'", text)
        if not text.strip():
            continue
        first_line = text.strip().split("\n")[0][:120]
        lo, hi = _guess_salary(text)
        jobs.append(
            Job(
                source="hn",
                position=first_line,
                company=hit.get("author", ""),
                tags=[],
                salary_min=lo,
                salary_max=hi,
                location="remote" if "remote" in text.lower() else "",
                url=f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            )
        )
    return jobs


def rank(jobs: Iterable[Job]) -> list[Job]:
    """Highest max-salary first; unpriced listings sink to the bottom."""
    return sorted(jobs, key=lambda j: (j.salary_max, j.salary_min), reverse=True)


def filter_jobs(
    jobs: Iterable[Job],
    keyword: str | None,
    tags: set[str],
    min_salary: int,
) -> list[Job]:
    out = []
    for j in jobs:
        if not j.matches(keyword, tags):
            continue
        if min_salary and j.salary_max < min_salary:
            continue
        out.append(j)
    return out


def render_table(jobs: list[Job]) -> str:
    if not jobs:
        return "No matching jobs found."
    rows = []
    for j in jobs:
        if j.salary_max:
            pay = f"${j.salary_min // 1000}-{j.salary_max // 1000}k"
        else:
            pay = "-"
        pos = j.position[:48]
        rows.append(f"{pay:>10}  {j.source:<9} {pos:<48} {j.url}")
    header = f"{'SALARY':>10}  {'SOURCE':<9} {'POSITION':<48} URL"
    return "\n".join([header, "-" * len(header), *rows])


def collect(keyword, tags, min_salary, hn_query) -> list[Job]:
    jobs: list[Job] = []
    errors = []
    for name, fn in (("remoteok", fetch_remoteok), ("hn", lambda: fetch_hn(hn_query))):
        try:
            jobs.extend(fn())
        except Exception as e:  # network is best-effort; report and continue
            errors.append(f"{name}: {e}")
    for e in errors:
        print(f"warning: source failed -> {e}", file=sys.stderr)
    return rank(filter_jobs(jobs, keyword, tags, min_salary))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Aggregate remote developer jobs.")
    p.add_argument("--keyword", help="substring match on title/company/tags")
    p.add_argument("--tags", default="", help="comma-separated tags to require")
    p.add_argument("--min-salary", type=int, default=0, help="min max-salary in USD")
    p.add_argument("--hn-query", default="remote", help="HN comment search query")
    p.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    p.add_argument("--limit", type=int, default=40)
    args = p.parse_args(argv)

    tags = {t.strip().lower() for t in args.tags.split(",") if t.strip()}
    jobs = collect(args.keyword, tags, args.min_salary, args.hn_query)[: args.limit]

    if args.json:
        print(json.dumps([asdict(j) for j in jobs], indent=2, ensure_ascii=False))
    else:
        print(render_table(jobs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
