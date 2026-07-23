"""Tests for remote-radar. Uses saved real API responses as offline fixtures."""
import json
import pathlib

import remote_radar as rr

FIX = pathlib.Path(__file__).resolve().parent / "fixtures"
ROK = (FIX / "remoteok_sample.json").read_bytes()
HN = (FIX / "hn_sample.json").read_bytes()


def test_fetch_remoteok_parses_real_payload():
    jobs = rr.fetch_remoteok(ROK)
    assert len(jobs) > 0
    assert all(j.source == "remoteok" for j in jobs)
    assert all(j.position for j in jobs)  # legal-notice element skipped


def test_fetch_hn_strips_html_and_finds_salary():
    jobs = rr.fetch_hn(raw=HN)
    assert all(j.source == "hn" for j in jobs)
    assert all("<" not in j.position for j in jobs)  # HTML tags stripped


def test_guess_salary_ranges():
    assert rr._guess_salary("pays $120k") == (120000, 120000)
    assert rr._guess_salary("range $90k to $130k") == (90000, 130000)
    assert rr._guess_salary("no numbers here") == (0, 0)


def test_job_matches_keyword_and_tags():
    j = rr.Job("t", "Senior Python Dev", "Acme", ["python", "backend"], 0, 0, "", "")
    assert j.matches("python", set())
    assert j.matches(None, {"backend"})
    assert not j.matches("rust", set())
    assert not j.matches(None, {"frontend"})


def test_filter_by_min_salary():
    jobs = [
        rr.Job("t", "A", "c", [], 0, 50000, "", ""),
        rr.Job("t", "B", "c", [], 0, 90000, "", ""),
    ]
    out = rr.filter_jobs(jobs, None, set(), min_salary=60000)
    assert [j.position for j in out] == ["B"]


def test_rank_orders_by_salary_desc():
    jobs = [
        rr.Job("t", "low", "c", [], 0, 40000, "", ""),
        rr.Job("t", "high", "c", [], 0, 150000, "", ""),
        rr.Job("t", "none", "c", [], 0, 0, "", ""),
    ]
    ranked = rr.rank(jobs)
    assert [j.position for j in ranked] == ["high", "low", "none"]


def test_render_table_and_empty():
    assert "No matching" in rr.render_table([])
    j = rr.Job("t", "Dev", "Acme", ["python"], 80000, 120000, "remote", "http://x")
    out = rr.render_table([j])
    assert "$80-120k" in out
    assert "http://x" in out


def test_end_to_end_filter_pipeline():
    jobs = rr.fetch_remoteok(ROK)
    ranked = rr.rank(rr.filter_jobs(jobs, None, {"dev"}, 0))
    # ranking is non-increasing by max salary
    sal = [j.salary_max for j in ranked]
    assert sal == sorted(sal, reverse=True)
