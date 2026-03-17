#!/usr/bin/env python3
"""Log GitHub repository traffic data to CSV files.

Fetches views, clones, referrers, and popular paths from the GitHub
Traffic API and appends new records to CSV files in the data/ directory.
Running this script daily preserves traffic history beyond the 14-day
window that the GitHub API exposes at any one time.
"""

import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from github import Auth, Github
from github.GithubException import GithubException


DATA_DIR = Path(__file__).parent.parent / "data"

VIEWS_FILE = DATA_DIR / "views.csv"
CLONES_FILE = DATA_DIR / "clones.csv"
REFERRERS_FILE = DATA_DIR / "referrers.csv"
PATHS_FILE = DATA_DIR / "paths.csv"

VIEWS_FIELDNAMES = ["date", "total", "unique"]
CLONES_FIELDNAMES = ["date", "total", "unique"]
REFERRERS_FIELDNAMES = ["logged_date", "referrer", "total", "unique"]
PATHS_FIELDNAMES = ["logged_date", "path", "title", "total", "unique"]


def _read_existing_dates(csv_file: Path, date_column: str) -> set:
    """Return the set of values already present in *date_column* of *csv_file*."""
    if not csv_file.exists():
        return set()
    with csv_file.open(newline="") as fh:
        reader = csv.DictReader(fh)
        return {row[date_column] for row in reader if date_column in row}


def _append_rows(csv_file: Path, fieldnames: list, rows: list) -> int:
    """Append *rows* to *csv_file*, writing a header when the file is new.

    Returns the number of rows written.
    """
    if not rows:
        return 0
    write_header = not csv_file.exists() or csv_file.stat().st_size == 0
    with csv_file.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def log_views(repo) -> int:
    """Fetch daily view counts and append any dates not yet recorded."""
    existing = _read_existing_dates(VIEWS_FILE, "date")
    traffic = repo.get_views_traffic()
    rows = []
    if traffic is not None:
        for view in traffic.views or []:
            date_str = view.timestamp.strftime("%Y-%m-%d")
            if date_str not in existing:
                rows.append({"date": date_str, "total": view.count, "unique": view.uniques})
    return _append_rows(VIEWS_FILE, VIEWS_FIELDNAMES, rows)


def log_clones(repo) -> int:
    """Fetch daily clone counts and append any dates not yet recorded."""
    existing = _read_existing_dates(CLONES_FILE, "date")
    traffic = repo.get_clones_traffic()
    rows = []
    if traffic is not None:
        for clone in traffic.clones or []:
            date_str = clone.timestamp.strftime("%Y-%m-%d")
            if date_str not in existing:
                rows.append({"date": date_str, "total": clone.count, "unique": clone.uniques})
    return _append_rows(CLONES_FILE, CLONES_FIELDNAMES, rows)


def log_referrers(repo) -> int:
    """Fetch top referrers and log a snapshot tagged with today's date."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    referrers = repo.get_top_referrers()
    rows = [
        {
            "logged_date": today,
            "referrer": r.referrer,
            "total": r.count,
            "unique": r.uniques,
        }
        for r in (referrers or [])
    ]
    return _append_rows(REFERRERS_FILE, REFERRERS_FIELDNAMES, rows)


def log_paths(repo) -> int:
    """Fetch top content paths and log a snapshot tagged with today's date."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    paths = repo.get_top_paths()
    rows = [
        {
            "logged_date": today,
            "path": p.path,
            "title": p.title,
            "total": p.count,
            "unique": p.uniques,
        }
        for p in (paths or [])
    ]
    return _append_rows(PATHS_FILE, PATHS_FIELDNAMES, rows)


def main() -> None:
    token = os.environ.get("TRAFFIC_GITHUB_TOKEN")
    repo_name = os.environ.get("TRAFFIC_REPO")

    if not token:
        print("Error: TRAFFIC_GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not repo_name:
        print("Error: TRAFFIC_REPO environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    auth = Auth.Token(token)
    gh = Github(auth=auth)

    try:
        repo = gh.get_repo(repo_name)
    except GithubException as exc:
        print(f"Error: could not access repository '{repo_name}': {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Logging traffic for {repo_name} …")

    views_written = log_views(repo)
    clones_written = log_clones(repo)
    referrers_written = log_referrers(repo)
    paths_written = log_paths(repo)

    print(
        f"Done. New rows — views: {views_written}, clones: {clones_written}, "
        f"referrers: {referrers_written}, paths: {paths_written}"
    )


if __name__ == "__main__":
    main()
