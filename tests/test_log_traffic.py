"""Tests for src/log_traffic.py."""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers to build fake GitHub API objects
# ---------------------------------------------------------------------------

def _make_traffic_item(date_str: str, count: int, uniques: int):
    obj = MagicMock()
    obj.timestamp = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    obj.count = count
    obj.uniques = uniques
    return obj


def _make_referrer(referrer: str, count: int, uniques: int):
    obj = MagicMock()
    obj.referrer = referrer
    obj.count = count
    obj.uniques = uniques
    return obj


def _make_path(path: str, title: str, count: int, uniques: int):
    obj = MagicMock()
    obj.path = path
    obj.title = title
    obj.count = count
    obj.uniques = uniques
    return obj


# ---------------------------------------------------------------------------
# Import the module under test after helpers are ready
# ---------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import log_traffic  # noqa: E402  (import after sys.path change)


# ---------------------------------------------------------------------------
# Tests for _read_existing_dates
# ---------------------------------------------------------------------------

class TestReadExistingDates:
    def test_returns_empty_set_when_file_missing(self, tmp_path):
        csv_file = tmp_path / "missing.csv"
        assert log_traffic._read_existing_dates(csv_file, "date") == set()

    def test_returns_dates_from_existing_file(self, tmp_path):
        csv_file = tmp_path / "views.csv"
        csv_file.write_text("date,total,unique\n2024-01-01,10,5\n2024-01-02,20,8\n")
        result = log_traffic._read_existing_dates(csv_file, "date")
        assert result == {"2024-01-01", "2024-01-02"}


# ---------------------------------------------------------------------------
# Tests for _append_rows
# ---------------------------------------------------------------------------

class TestAppendRows:
    def test_creates_file_with_header_when_new(self, tmp_path):
        csv_file = tmp_path / "out.csv"
        rows = [{"date": "2024-01-01", "total": 5, "unique": 3}]
        written = log_traffic._append_rows(csv_file, ["date", "total", "unique"], rows)
        assert written == 1
        content = csv_file.read_text()
        assert "date,total,unique" in content
        assert "2024-01-01,5,3" in content

    def test_appends_without_duplicate_header(self, tmp_path):
        csv_file = tmp_path / "out.csv"
        csv_file.write_text("date,total,unique\n2024-01-01,5,3\n")
        rows = [{"date": "2024-01-02", "total": 8, "unique": 4}]
        log_traffic._append_rows(csv_file, ["date", "total", "unique"], rows)
        lines = csv_file.read_text().splitlines()
        # Only one header line expected
        assert lines.count("date,total,unique") == 1
        assert any("2024-01-02" in line for line in lines)

    def test_returns_zero_for_empty_rows(self, tmp_path):
        csv_file = tmp_path / "out.csv"
        written = log_traffic._append_rows(csv_file, ["date", "total", "unique"], [])
        assert written == 0
        assert not csv_file.exists()


# ---------------------------------------------------------------------------
# Tests for log_views
# ---------------------------------------------------------------------------

class TestLogViews:
    def test_writes_new_dates(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_traffic, "VIEWS_FILE", tmp_path / "views.csv")
        repo = MagicMock()
        repo.get_views_traffic.return_value = {
            "views": [
                _make_traffic_item("2024-01-01", 10, 5),
                _make_traffic_item("2024-01-02", 20, 8),
            ]
        }
        written = log_traffic.log_views(repo)
        assert written == 2

    def test_skips_already_recorded_dates(self, tmp_path, monkeypatch):
        views_file = tmp_path / "views.csv"
        views_file.write_text("date,total,unique\n2024-01-01,10,5\n")
        monkeypatch.setattr(log_traffic, "VIEWS_FILE", views_file)
        repo = MagicMock()
        repo.get_views_traffic.return_value = {
            "views": [
                _make_traffic_item("2024-01-01", 10, 5),  # already exists
                _make_traffic_item("2024-01-02", 20, 8),  # new
            ]
        }
        written = log_traffic.log_views(repo)
        assert written == 1


# ---------------------------------------------------------------------------
# Tests for log_clones
# ---------------------------------------------------------------------------

class TestLogClones:
    def test_writes_new_dates(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_traffic, "CLONES_FILE", tmp_path / "clones.csv")
        repo = MagicMock()
        repo.get_clones_traffic.return_value = {
            "clones": [_make_traffic_item("2024-01-01", 3, 2)]
        }
        written = log_traffic.log_clones(repo)
        assert written == 1

    def test_skips_already_recorded_dates(self, tmp_path, monkeypatch):
        clones_file = tmp_path / "clones.csv"
        clones_file.write_text("date,total,unique\n2024-01-01,3,2\n")
        monkeypatch.setattr(log_traffic, "CLONES_FILE", clones_file)
        repo = MagicMock()
        repo.get_clones_traffic.return_value = {
            "clones": [_make_traffic_item("2024-01-01", 3, 2)]
        }
        written = log_traffic.log_clones(repo)
        assert written == 0


# ---------------------------------------------------------------------------
# Tests for log_referrers
# ---------------------------------------------------------------------------

class TestLogReferrers:
    def test_writes_referrers_with_today_date(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_traffic, "REFERRERS_FILE", tmp_path / "referrers.csv")
        repo = MagicMock()
        repo.get_top_referrers.return_value = [
            _make_referrer("example-source-1", 50, 30),
            _make_referrer("example-source-2", 20, 15),
        ]
        written = log_traffic.log_referrers(repo)
        assert written == 2
        content = (tmp_path / "referrers.csv").read_text()
        assert "example-source-1" in content
        assert "example-source-2" in content


# ---------------------------------------------------------------------------
# Tests for log_paths
# ---------------------------------------------------------------------------

class TestLogPaths:
    def test_writes_paths_with_today_date(self, tmp_path, monkeypatch):
        monkeypatch.setattr(log_traffic, "PATHS_FILE", tmp_path / "paths.csv")
        repo = MagicMock()
        repo.get_top_paths.return_value = [
            _make_path("/README.md", "README", 100, 60),
        ]
        written = log_traffic.log_paths(repo)
        assert written == 1
        content = (tmp_path / "paths.csv").read_text()
        assert "/README.md" in content
        assert "README" in content


# ---------------------------------------------------------------------------
# Tests for main() — environment variable validation
# ---------------------------------------------------------------------------

class TestMain:
    def test_exits_when_token_missing(self, monkeypatch):
        monkeypatch.delenv("TRAFFIC_GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("TRAFFIC_REPO", "owner/repo")
        with pytest.raises(SystemExit) as exc_info:
            log_traffic.main()
        assert exc_info.value.code == 1

    def test_exits_when_repo_missing(self, monkeypatch):
        monkeypatch.setenv("TRAFFIC_GITHUB_TOKEN", "fake-token")
        monkeypatch.delenv("TRAFFIC_REPO", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            log_traffic.main()
        assert exc_info.value.code == 1

    def test_runs_all_loggers(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TRAFFIC_GITHUB_TOKEN", "fake-token")
        monkeypatch.setenv("TRAFFIC_REPO", "owner/repo")
        monkeypatch.setattr(log_traffic, "DATA_DIR", tmp_path)
        monkeypatch.setattr(log_traffic, "VIEWS_FILE", tmp_path / "views.csv")
        monkeypatch.setattr(log_traffic, "CLONES_FILE", tmp_path / "clones.csv")
        monkeypatch.setattr(log_traffic, "REFERRERS_FILE", tmp_path / "referrers.csv")
        monkeypatch.setattr(log_traffic, "PATHS_FILE", tmp_path / "paths.csv")

        fake_repo = MagicMock()
        fake_repo.get_views_traffic.return_value = {
            "views": [_make_traffic_item("2024-01-01", 10, 5)]
        }
        fake_repo.get_clones_traffic.return_value = {
            "clones": [_make_traffic_item("2024-01-01", 2, 1)]
        }
        fake_repo.get_top_referrers.return_value = [_make_referrer("github.com", 5, 3)]
        fake_repo.get_top_paths.return_value = [_make_path("/README.md", "README", 10, 8)]

        with patch.object(log_traffic, "Github") as MockGithub, \
             patch.object(log_traffic, "Auth"):
            mock_gh_instance = MagicMock()
            mock_gh_instance.get_repo.return_value = fake_repo
            MockGithub.return_value = mock_gh_instance

            log_traffic.main()

        assert (tmp_path / "views.csv").exists()
        assert (tmp_path / "clones.csv").exists()
        assert (tmp_path / "referrers.csv").exists()
        assert (tmp_path / "paths.csv").exists()
