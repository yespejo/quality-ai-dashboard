"""
main.py
-------
Entry point for the daily snapshot pipeline.

Execution flow:
  1. load_pod_config()    — read pod/repo definitions from config/pods.json
  2. collect_metrics()    — call CodeScene API for each repo in each pod
  3. save_snapshot()      — write data/snapshots/YYYY-MM-DD.json + data/latest.json
  4. update_history()     — append today's aggregated point to data/history.json

Run manually:
  CODESCENE_TOKEN=<token> python src/main.py

Triggered automatically by the GitHub Actions scheduled workflow.

config/pods.json shape:
  [
    {
      "name": "AI POD 1",
      "repos": [
        { "name": "nx-bff-loyalty-customerhub", "projectId": "67203" },
        { "name": "nx-al-comm-mercury-events",  "projectId": "67202" }
      ]
    },
    ...
  ]
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from codescene_client import get_metrics as codescene_get_metrics
from models import (
    CodeSceneMetrics,
    DailySnapshot,
    PodHistory,
    PodSnapshot,
    RepoSnapshot,
    SnykMetrics,
)

# ── Constants ────────────────────────────────────────────────────────────────

DATA_DIR      = "data"
SNAPSHOTS_DIR = os.path.join(DATA_DIR, "snapshots")
LATEST_FILE   = os.path.join(DATA_DIR, "latest.json")
HISTORY_FILE  = os.path.join(DATA_DIR, "history.json")
CONFIG_FILE   = os.path.join("config", "pods.json")


# ── Step 0: Load pod configuration ──────────────────────────────────────────

def load_pod_config() -> list[dict]:
    """
    Read pod/repo definitions from config/pods.json.

    Validates that each pod has at least one repo and that every repo
    provides both 'name' and 'projectId'.

    Raises:
        FileNotFoundError: if config/pods.json does not exist.
        ValueError:        if a pod or repo entry is missing required fields.
    """
    with open(CONFIG_FILE) as f:
        pods = json.load(f)

    for pod in pods:
        if not pod.get("name"):
            raise ValueError(f"A pod entry is missing the 'name' field in {CONFIG_FILE}.")
        repos = pod.get("repos", [])
        if not repos:
            raise ValueError(
                f"Pod '{pod['name']}' has no repos defined in {CONFIG_FILE}."
            )
        for repo in repos:
            if not repo.get("name") or not repo.get("projectId"):
                raise ValueError(
                    f"Repo entry in pod '{pod['name']}' is missing 'name' or "
                    f"'projectId' in {CONFIG_FILE}."
                )

    return pods


# ── Step 1: Collect metrics ──────────────────────────────────────────────────

# ── Mock data keyed by repo name ────────────────────────────────────────────
# Mirrors the structure of config/pods.json so that running the pipeline
# without a CODESCENE_TOKEN still produces realistic, repo-level data.
# Replace each entry with real API values once the token is available.

MOCK_CODESCENE: dict[str, CodeSceneMetrics] = {
    "Nx-bff-loyalty-customerhub": CodeSceneMetrics(health=9.17, coverage=99.42),
    "Nx-al-comm-mercury-events":  CodeSceneMetrics(health=8.50, coverage=81.00),
    "Nx-bff-order-mobile":        CodeSceneMetrics(health=7.80, coverage=74.50),
}

MOCK_SNYK: dict[str, SnykMetrics] = {
    "Nx-bff-loyalty-customerhub": SnykMetrics(critical=0, high=2, medium=5),
    "Nx-al-comm-mercury-events":  SnykMetrics(critical=1, high=3, medium=8),
    "Nx-bff-order-mobile":        SnykMetrics(critical=2, high=5, medium=11),
}

# Fallback values used for any repo not listed above.
_FALLBACK_CODESCENE = CodeSceneMetrics(health=0.0, coverage=0.0)
_FALLBACK_SNYK      = SnykMetrics(critical=0, high=0, medium=0)


def collect_repo_metrics(repo: dict) -> RepoSnapshot:
    """
    Fetch CodeScene and Snyk metrics for a single repo.

    - If CODESCENE_TOKEN is set  → calls the real CodeScene API.
    - If CODESCENE_TOKEN is unset → uses MOCK_CODESCENE / MOCK_SNYK,
      which are keyed by repo name to match config/pods.json exactly.

    Args:
        repo: dict with 'name' and 'projectId' (matching config/pods.json).

    Returns:
        RepoSnapshot with per-repo CodeScene and Snyk data.
    """
    repo_name  = repo["name"]
    project_id = repo["projectId"]

    # ── CodeScene ────────────────────────────────────────────────────────────
    if os.environ.get("CODESCENE_TOKEN"):
        # Real API: component_name matches the repo name in config/pods.json.
        codescene: CodeSceneMetrics = codescene_get_metrics(
            project_id=project_id,
            component_name=repo_name,
        )
    else:
        print(f"  [mock] CODESCENE_TOKEN not set — using mock data for '{repo_name}'")
        codescene = MOCK_CODESCENE.get(repo_name, _FALLBACK_CODESCENE)

    # ── Snyk ─────────────────────────────────────────────────────────────────
    # TODO: replace with snyk_client.get_vulnerabilities(repo["snykProjectId"])
    # Mock is keyed by repo name, same as config/pods.json.
    snyk: SnykMetrics = MOCK_SNYK.get(repo_name, _FALLBACK_SNYK)

    return RepoSnapshot(name=repo_name, codescene=codescene, snyk=snyk)


def collect_pod_metrics(pod_config: dict) -> PodSnapshot:
    """
    Fetch metrics for every repo in a pod and return the pod-level snapshot.

    The PodSnapshot aggregates automatically via its @property methods:
      - codescene.health   → average across all repos
      - codescene.coverage → average across all repos
      - snyk.*             → sum across all repos

    Args:
        pod_config: one pod entry from config/pods.json.

    Returns:
        PodSnapshot containing one RepoSnapshot per repo.
    """
    pod = PodSnapshot(name=pod_config["name"])

    for repo_config in pod_config["repos"]:
        repo_snapshot = collect_repo_metrics(repo_config)
        pod.repos.append(repo_snapshot)
        print(
            f"  [repo] {repo_snapshot.name}: "
            f"health={repo_snapshot.codescene.health}  "
            f"coverage={repo_snapshot.codescene.coverage}%  "
            f"vuln(C/H/M)={repo_snapshot.snyk.critical}/"
            f"{repo_snapshot.snyk.high}/{repo_snapshot.snyk.medium}"
        )

    return pod


# ── Step 2: Save daily snapshot ──────────────────────────────────────────────

def _snapshot_to_dict(snapshot: DailySnapshot) -> dict:
    """
    Serialize a DailySnapshot to a plain dict ready for json.dump().

    Output shape:
    {
      "date": "YYYY-MM-DD",
      "pods": [
        {
          "name": "AI POD 1",
          "codescene": { "health": 8.5, "coverage": 76.3 },   # aggregated
          "snyk":      { "critical": 1, "high": 4, "medium": 9 },  # aggregated
          "repos": [
            {
              "name": "nx-bff-loyalty-customerhub",
              "codescene": { "health": 9.17, "coverage": 99.42 },
              "snyk":      { "critical": 0, "high": 0, "medium": 0 }
            },
            ...
          ]
        }
      ]
    }
    """
    return {
        "date": snapshot.date,
        "pods": [
            {
                "name": pod.name,
                # Pod-level aggregates (averages / sums)
                "codescene": {
                    "health":   pod.codescene.health,
                    "coverage": pod.codescene.coverage,
                },
                "snyk": {
                    "critical": pod.snyk.critical,
                    "high":     pod.snyk.high,
                    "medium":   pod.snyk.medium,
                },
                # Per-repo detail
                "repos": [
                    {
                        "name": repo.name,
                        "codescene": {
                            "health":   repo.codescene.health,
                            "coverage": repo.codescene.coverage,
                        },
                        "snyk": {
                            "critical": repo.snyk.critical,
                            "high":     repo.snyk.high,
                            "medium":   repo.snyk.medium,
                        },
                    }
                    for repo in pod.repos
                ],
            }
            for pod in snapshot.pods
        ],
    }


def save_snapshot(snapshot: DailySnapshot) -> None:
    """Write the daily snapshot to data/snapshots/YYYY-MM-DD.json and data/latest.json."""
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    data = _snapshot_to_dict(snapshot)

    snapshot_path = os.path.join(SNAPSHOTS_DIR, f"{snapshot.date}.json")
    with open(snapshot_path, "w") as f:
        json.dump(data, f, indent=4)

    with open(LATEST_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print(f"[snapshot] saved → {snapshot_path}")
    print(f"[snapshot] saved → {LATEST_FILE}")


# ── Step 3: Update history ───────────────────────────────────────────────────

def _load_history() -> dict[str, PodHistory]:
    """
    Load data/history.json and return a dict of pod_name → PodHistory.
    Returns an empty dict if the file does not exist yet.
    """
    if not os.path.exists(HISTORY_FILE):
        return {}

    with open(HISTORY_FILE) as f:
        raw = json.load(f)

    result = {}
    for pod_name, series in raw.get("pods", {}).items():
        result[pod_name] = PodHistory(
            dates=    series.get("dates",    []),
            health=   series["codescene"].get("health",   []),
            coverage= series["codescene"].get("coverage", []),
            critical= series["snyk"].get("critical", []),
            high=     series["snyk"].get("high",     []),
            medium=   series["snyk"].get("medium",   []),
        )
    return result


def _save_history(histories: dict[str, PodHistory]) -> None:
    """Serialize and write the full history dict to data/history.json."""
    data = {
        "pods": {
            pod_name: {
                "dates": h.dates,
                "codescene": {
                    "health":   h.health,
                    "coverage": h.coverage,
                },
                "snyk": {
                    "critical": h.critical,
                    "high":     h.high,
                    "medium":   h.medium,
                },
            }
            for pod_name, h in histories.items()
        }
    }
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print(f"[history] updated → {HISTORY_FILE}")


def update_history(snapshot: DailySnapshot) -> None:
    """Append today's aggregated pod data to data/history.json."""
    histories = _load_history()

    for pod in snapshot.pods:
        if pod.name not in histories:
            histories[pod.name] = PodHistory()
        # append() is a no-op if this date is already present — safe to re-run.
        histories[pod.name].append(snapshot.date, pod)

    _save_history(histories)


# ── Pipeline ─────────────────────────────────────────────────────────────────

def generate_snapshot() -> None:
    pods_config = load_pod_config()
    today       = str(datetime.now().date())
    snapshot    = DailySnapshot(date=today)

    for pod_config in pods_config:
        print(f"[pod] {pod_config['name']}")
        pod = collect_pod_metrics(pod_config)
        snapshot.pods.append(pod)
        print(
            f"[pod] {pod.name} aggregate → "
            f"health={pod.codescene.health}  "
            f"coverage={pod.codescene.coverage}%  "
            f"vuln(C/H/M)={pod.snyk.critical}/{pod.snyk.high}/{pod.snyk.medium}"
        )

    save_snapshot(snapshot)
    update_history(snapshot)
    print("[pipeline] done.")


if __name__ == "__main__":
    generate_snapshot()
