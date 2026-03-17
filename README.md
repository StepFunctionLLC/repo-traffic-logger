# repo-traffic-logger

Log historical GitHub repo traffic beyond the 14-day window provided by the
GitHub Traffic API. A GitHub Actions workflow runs daily, fetches the latest
traffic data, and appends new records to CSV files committed back to this
repository.

## What is tracked

| File | Contents |
|------|----------|
| `data/views.csv` | Daily page views (total + unique visitors) |
| `data/clones.csv` | Daily clone counts (total + unique cloners) |
| `data/referrers.csv` | Top referring sites snapshot (logged per run) |
| `data/paths.csv` | Top content paths snapshot (logged per run) |

Duplicate dates are automatically skipped, so re-running the workflow is safe.

## Setup

### 1. Fork or copy this repository

Create a copy of this repository in the GitHub account or organisation that
owns the repositories whose traffic you want to track.

### 2. Create a Personal Access Token

The GitHub Traffic API requires a token with the `repo` scope (specifically
`public_repo` for public repositories).

1. Go to **Settings → Developer settings → Personal access tokens**.
2. Generate a new **fine-grained** or **classic** token with at least the
   `repo` scope on the target repository.
3. Copy the token value.

### 3. Add the token as a repository secret

1. In this repository go to **Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name it `TRAFFIC_GITHUB_TOKEN` and paste the token value.

### 4. Enable the workflow

The workflow file is at `.github/workflows/log-traffic.yml`. It runs
automatically every day at 06:00 UTC. You can also trigger it manually via
**Actions → Log Repo Traffic → Run workflow**.

### 5. (Optional) Change the target repository

By default the workflow tracks traffic for the repository it lives in
(`${{ github.repository }}`). To track a different repository, edit the
`TRAFFIC_REPO` environment variable in the workflow file:

```yaml
env:
  TRAFFIC_GITHUB_TOKEN: ${{ secrets.TRAFFIC_GITHUB_TOKEN }}
  TRAFFIC_REPO: owner/other-repo
```

## Running locally

```bash
pip install -r requirements.txt

export TRAFFIC_GITHUB_TOKEN=ghp_...
export TRAFFIC_REPO=owner/repo

python src/log_traffic.py
```

## Running tests

```bash
pip install pytest
pytest tests/
```
