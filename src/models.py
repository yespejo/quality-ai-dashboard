"""
models.py
---------
Dataclasses that represent the core domain objects of the dashboard.

These models are the single source of truth for the shape of the data
that flows from the API clients → snapshot service → JSON files → dashboard.

Data hierarchy:
  DailySnapshot
    └── PodSnapshot          (one per pod, e.g. "AI POD 1")
          ├── repos[]        (one RepoSnapshot per repo in the pod)
          │     ├── CodeSceneMetrics   (health, coverage from CodeScene API)
          │     └── SnykMetrics        (critical/high/medium from Snyk API)
          └── Aggregated CodeSceneMetrics / SnykMetrics
                (averaged health & coverage, summed vuln counts across all repos)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CodeSceneMetrics:
    """Metrics fetched from the CodeScene API for one repo on one day."""
    health:   float  # 0-10 score (higher is better)
    coverage: float  # percentage 0-100


@dataclass
class SnykMetrics:
    """Vulnerability counts fetched from the Snyk API for one repo on one day."""
    critical: int
    high:     int
    medium:   int


@dataclass
class RepoSnapshot:
    """Metrics for a single repository within a pod, captured on one day."""
    name:       str               # repo name as it appears in CodeScene
    codescene:  CodeSceneMetrics
    snyk:       SnykMetrics


@dataclass
class PodSnapshot:
    """
    All metrics for a single pod captured on a single day.

    - repos:      per-repo detail (used for drill-down views)
    - codescene:  pod-level aggregate — average health & coverage across all repos
    - snyk:       pod-level aggregate — summed vulnerability counts across all repos
    """
    name:      str
    repos:     list[RepoSnapshot] = field(default_factory=list)

    @property
    def codescene(self) -> CodeSceneMetrics:
        """Averaged health and coverage across all repos in this pod."""
        if not self.repos:
            return CodeSceneMetrics(health=0.0, coverage=0.0)
        health   = sum(r.codescene.health   for r in self.repos) / len(self.repos)
        coverage = sum(r.codescene.coverage for r in self.repos) / len(self.repos)
        return CodeSceneMetrics(health=round(health, 2), coverage=round(coverage, 2))

    @property
    def snyk(self) -> SnykMetrics:
        """Summed vulnerability counts across all repos in this pod."""
        if not self.repos:
            return SnykMetrics(critical=0, high=0, medium=0)
        return SnykMetrics(
            critical=sum(r.snyk.critical for r in self.repos),
            high=    sum(r.snyk.high     for r in self.repos),
            medium=  sum(r.snyk.medium   for r in self.repos),
        )


@dataclass
class DailySnapshot:
    """
    The full snapshot for one day — written to:
      - data/snapshots/YYYY-MM-DD.json   (archive)
      - data/latest.json                 (current state, read by the dashboard)
    """
    date: str                         # ISO format: "YYYY-MM-DD"
    pods: list[PodSnapshot] = field(default_factory=list)


@dataclass
class PodHistory:
    """
    Time-series data for one pod — stored inside data/history.json.
    Every array is parallel: dates[i] corresponds to health[i], coverage[i], etc.

    Aggregated values (averages for CodeScene, sums for Snyk) are stored
    so the dashboard can plot pod-level trends without re-aggregating.
    """
    dates:    list[str]   = field(default_factory=list)
    health:   list[float] = field(default_factory=list)
    coverage: list[float] = field(default_factory=list)
    critical: list[int]   = field(default_factory=list)
    high:     list[int]   = field(default_factory=list)
    medium:   list[int]   = field(default_factory=list)

    def append(self, date: str, pod: PodSnapshot) -> None:
        """
        Add one day's aggregated data point for this pod.
        Skips silently if the date is already recorded (idempotent).
        """
        if date in self.dates:
            return
        self.dates.append(date)
        self.health.append(pod.codescene.health)
        self.coverage.append(pod.codescene.coverage)
        self.critical.append(pod.snyk.critical)
        self.high.append(pod.snyk.high)
        self.medium.append(pod.snyk.medium)
