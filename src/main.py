"""
main.py
-------
Entry point for the daily snapshot pipeline.

Execution flow:
  1. collect_metrics()   — call CodeScene + Snyk APIs (mocked until APIs are wired)
  2. save_snapshot()     — write data/snapshots/YYYY-MM-DD.json + data/latest.json
  3. update_history()    — append today's point to data/history.json

Run manually:
  python src/main.py

Later this will be triggered by a GitHub Actions scheduled workflow.
"""

import json
import os
from datetime import datetime

from models import (
    CodeSceneMetrics,
    DailySnapshot,
    PodHistory,
    PodSnapshot,
    SnykMetrics,
)

# ── Constants ────────────────────────────────────────────────────────────────

DATA_DIR      = "data"
SNAPSHOTS_DIR = os.path.join(DATA_DIR, "snapshots")
LATEST_FILE   = os.path.join(DATA_DIR, "latest.json")
HISTORY_FILE  = os.path.join(DATA_DIR, "history.json")

# Pods to collect metrics for.
# Each entry maps a pod name to its CodeScene project ID and Snyk org/project IDs.
# These IDs will be used once the real API clients are implemented.
PODS = [
    {
        "name":               "flights",
        "codescene_project":  None,   # TODO: fill in CodeScene project ID
        "snyk_project":       None,   # TODO: fill in Snyk project ID
    },
    {
        "name":               "ancillaries",
        "codescene_project":  None,
        "snyk_project":       None,
    },
    {
        "name":               "mobile-customer",
        "codescene_project":  None,
        "snyk_project":       None,
    },
]


# ── Step 1: Collect metrics ──────────────────────────────────────────────────

def collect_metrics(pod_config: dict) -> PodSnapshot:
    """
    Fetch today's metrics for one pod from CodeScene and Snyk.

    Currently returns mock data. Replace the body of each section with
    a real API client call when the credentials are available:
      - from codescene_client import get_health, get_coverage
      - from snyk_client import get_vulnerabilities
    """
    name = pod_config["name"]

    # ── CodeScene (mock) ─────────────────────────────────────────────────────
    # TODO: replace with codescene_client.get_metrics(pod_config["codescene_project"])
    mock_codescene = {
        "flights":         CodeSceneMetrics(health=7.8,  coverage=74.5),
        "ancillaries":     CodeSceneMetrics(health=6.9,  coverage=68.2),
        "mobile-customer": CodeSceneMetrics(health=8.4,  coverage=81.0),
    }
    codescene = mock_codescene.get(name, CodeSceneMetrics(health=0.0, coverage=0.0))

    # ── Snyk (mock) ──────────────────────────────────────────────────────────
    # TODO: replace with snyk_client.get_vulnerabilities(pod_config["snyk_project"])
    mock_snyk = {
        "flights":         SnykMetrics(critical=1, high=4, medium=9),
        "ancillaries":     SnykMetrics(critical=3, high=8, medium=14),
        "mobile-customer": SnykMetrics(critical=0, high=2, medium=6),
    }
    snyk = mock_snyk.get(name, SnykMetrics(critical=0, high=0, medium=0))

    return PodSnapshot(name=name, codescene=codescene, snyk=snyk)


# ── Step 2: Save daily snapshot ──────────────────────────────────────────────

def _snapshot_to_dict(snapshot: DailySnapshot) -> dict:
    """Serialize a DailySnapshot to a plain dict ready for json.dump()."""
    return {
        "date": snapshot.date,
        "pods": [
            {
                "name": pod.name,
                "codescene": {
                    "health":   pod.codescene.health,
                    "coverage": pod.codescene.coverage,
                },
                "snyk": {
                    "critical": pod.snyk.critical,
                    "high":     pod.snyk.high,
                    "medium":   pod.snyk.medium,
                },
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
    """Append today's snapshot data to data/history.json."""
    histories = _load_history()

    for pod in snapshot.pods:
        if pod.name not in histories:
            histories[pod.name] = PodHistory()
        # PodHistory.append() is a no-op if this date is already present,
        # so it's safe to run the pipeline more than once per day.
        histories[pod.name].append(snapshot.date, pod)

    _save_history(histories)


# ── Pipeline ─────────────────────────────────────────────────────────────────

def generate_snapshot() -> None:
    today    = str(datetime.now().date())
    snapshot = DailySnapshot(date=today)

    for pod_config in PODS:
        pod = collect_metrics(pod_config)
        snapshot.pods.append(pod)
        print(f"[collect] {pod.name}: health={pod.codescene.health} "
              f"coverage={pod.codescene.coverage} "
              f"critical={pod.snyk.critical} high={pod.snyk.high} medium={pod.snyk.medium}")

    save_snapshot(snapshot)
    update_history(snapshot)
    print("[pipeline] done.")


if __name__ == "__main__":
    generate_snapshot()
