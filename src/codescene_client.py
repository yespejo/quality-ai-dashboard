"""
codescene_client.py
-------------------
Fetches code health and coverage metrics from the CodeScene API v2.

API endpoint used:
  GET /v2/projects/{project_id}/analyses/latest/components/{component_name}

Required environment variable:
  CODESCENE_TOKEN — a valid CodeScene API bearer token.

Usage:
  from codescene_client import get_metrics
  metrics = get_metrics(project_id=67203, component_name="Nx-bb-loyalty-iagl")
  print(metrics.health, metrics.coverage)
"""

import os
import urllib.request
import urllib.error
import json
from typing import Union

from models import CodeSceneMetrics

# ── Constants ────────────────────────────────────────────────────────────────

CODESCENE_API_BASE = "https://api.codescene.io/v2"


# ── Public interface ─────────────────────────────────────────────────────────

def get_metrics(project_id: Union[int, str], component_name: str) -> CodeSceneMetrics:
    """
    Fetch the latest code health and coverage for one component (pod) from CodeScene.

    Args:
        project_id:     The CodeScene project ID (e.g. 67203 or "67203").
        component_name: The exact repo name as shown in CodeScene
                        (e.g. "nx-bff-loyalty-customerhub").

    Returns:
        CodeSceneMetrics with:
          - health:   current_score from system_health (0-10 scale)
          - coverage: overall_coverage from the first code_coverage metric (0-100 %)

    Raises:
        EnvironmentError: if CODESCENE_TOKEN is not set.
        RuntimeError:     if the API request fails or the response shape is unexpected.
    """
    token = os.environ.get("CODESCENE_TOKEN")
    if not token:
        raise EnvironmentError(
            "Missing CODESCENE_TOKEN environment variable. "
            "Set it before running the pipeline."
        )

    url = (
        f"{CODESCENE_API_BASE}/projects/{project_id}"
        f"/analyses/latest/components/{component_name}"
    )

    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"CodeScene API error for component '{component_name}': "
            f"{exc.code} {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach CodeScene API: {exc.reason}"
        ) from exc

    return _parse_response(data, component_name)


# ── Internal helpers ─────────────────────────────────────────────────────────

def _parse_response(data: dict, component_name: str) -> CodeSceneMetrics:
    """
    Extract health and coverage values from the raw CodeScene API response.

    Expected shape (relevant fields only):
    {
      "system_health": { "current_score": 9.17, ... },
      "code_coverage": {
        "overall_coverage": 99.41,
        "metrics": [ { "metric": "line-coverage", "overall_coverage": 99.41, ... }, ... ]
      }
    }
    """
    # ── Health (0-10) ────────────────────────────────────────────────────────
    system_health = data.get("system_health", {})
    health = float(system_health.get("current_score", 0.0))

    # ── Coverage (%) ─────────────────────────────────────────────────────────
    # Prefer the top-level overall_coverage; fall back to the first metrics entry.
    code_coverage = data.get("code_coverage") or {}
    coverage = float(code_coverage.get("overall_coverage", 0.0))

    # If top-level value is 0 but metrics entries exist, use the line-coverage metric.
    if coverage == 0.0 and code_coverage.get("metrics"):
        for m in code_coverage["metrics"]:
            if m.get("metric") == "line-coverage":
                coverage = float(m.get("overall_coverage", 0.0))
                break

    return CodeSceneMetrics(health=round(health, 2), coverage=round(coverage, 2))
