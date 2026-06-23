"""
models.py
---------
Dataclasses that represent the core domain objects of the dashboard.

These models are the single source of truth for the shape of the data
that flows from the API clients → snapshot service → JSON files → dashboard.
"""

from dataclasses import dataclass, field


@dataclass
class CodeSceneMetrics:
    """Metrics fetched from the CodeScene API for one pod on one day."""
    health:   float  # 0-10 score (higher is better)
    coverage: float  # percentage 0-100


@dataclass
class SnykMetrics:
    """Vulnerability counts fetched from the Snyk API for one pod on one day."""
    critical: int
    high:     int
    medium:   int


@dataclass
class PodSnapshot:
    """All metrics for a single pod captured on a single day."""
    name:       str
    codescene:  CodeSceneMetrics
    snyk:       SnykMetrics


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
    """
    dates:    list[str]   = field(default_factory=list)
    health:   list[float] = field(default_factory=list)
    coverage: list[float] = field(default_factory=list)
    critical: list[int]   = field(default_factory=list)
    high:     list[int]   = field(default_factory=list)
    medium:   list[int]   = field(default_factory=list)

    def append(self, date: str, pod: PodSnapshot) -> None:
        """Add one day's data point. Skips if the date is already recorded."""
        if date in self.dates:
            return
        self.dates.append(date)
        self.health.append(pod.codescene.health)
        self.coverage.append(pod.codescene.coverage)
        self.critical.append(pod.snyk.critical)
        self.high.append(pod.snyk.high)
        self.medium.append(pod.snyk.medium)
