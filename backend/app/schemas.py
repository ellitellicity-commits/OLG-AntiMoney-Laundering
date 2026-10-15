"""Pydantic models for the API. These shapes are what /docs shows."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Band = Literal["Low", "Medium", "High", "Critical"]
Team = Literal["AML", "Fraud", "Safer Gambling"]
Status = Literal["New", "In review", "Escalated", "Closed"]


class Reason(BaseModel):
    code: str
    anomaly_type: str
    team: Team | None
    title: str
    detail: str = Field(description="Plain-language sentence built only from the evidence values")
    evidence: dict[str, Any]
    comparison: dict[str, Any] = Field(description="peer_median and/or own_baseline for the same metric")
    points: int


class RecommendedAction(BaseModel):
    action: str
    team: Team
    rationale: str


class TopReason(BaseModel):
    code: str
    title: str


class AlertSummary(BaseModel):
    alert_id: str
    player_id: str
    score: int
    band: Band
    team: Team
    status: Status
    anomaly_types: list[str]
    anomaly_type_labels: list[str]
    top_reason: TopReason
    recommended_action: str
    last_activity: str | None
    ml_probability: float | None = Field(None, description="Supervised model probability (out-of-fold)")


class AlertList(BaseModel):
    total: int
    alerts: list[AlertSummary]


class Profile(BaseModel):
    age_band: str
    occupation: str
    income_band: str
    home_region: str
    signup_date: str


class Decision(BaseModel):
    decision: Literal["accept", "escalate", "close", "assign"]
    note: str = ""
    team: Team | None = None
    investigator: str = ""
    status: Status
    recorded_at: str


class MLDriver(BaseModel):
    feature: str
    label: str
    value: float
    impact: float = Field(description="SHAP contribution to the log-odds of 'risky'")


class MLInfo(BaseModel):
    probability: float
    drivers: list[MLDriver]
    model: str
    scoring: str


class AlertDetail(BaseModel):
    alert_id: str
    player_id: str
    score: int
    band: Band
    team: Team
    status: Status
    anomaly_types: list[str]
    anomaly_type_labels: list[str]
    top_reason: TopReason
    reasons: list[Reason]
    points_total: int = Field(description="Sum of reason points; the score is this capped at 100")
    recommended_action: RecommendedAction
    profile: Profile
    peer_group: str
    peer_group_level: str
    peer_group_size: int
    last_activity: str | None
    window: dict[str, Any]
    synthetic: bool
    decisions: list[Decision]
    ml: MLInfo | None = None


class DecisionIn(BaseModel):
    decision: Literal["accept", "escalate", "close", "assign"]
    note: str = Field("", max_length=1000, description="Required when closing")
    team: Team | None = Field(None, description="Required when assigning")
    investigator: str = Field("", max_length=100)


class DecisionOut(BaseModel):
    alert_id: str
    status: Status
    team: Team
    decision: Decision


class Transaction(BaseModel):
    txn_id: str
    timestamp: str
    type: str
    amount_cad: float
    sport: str | None
    market: str | None
    odds: float | None
    channel: str
    device_id: str | None
    ip_region: str | None
    payment_method_id: str | None
    flags: list[str] = Field(default_factory=list, description="TXN_FLAGS codes; labels are in /meta")


class PlayerDetail(BaseModel):
    player_id: str
    profile: Profile
    peer_group: str
    score: int
    band: Band
    alert_id: str | None
    summary: dict[str, Any] = Field(description="Key 30-day and baseline figures")
    transactions_total: int
    transactions: list[Transaction]
    synthetic: bool = True


class PeerStats(BaseModel):
    n: int
    active_only: bool = Field(description="True when only peers active in the window are included")
    median: float
    q1: float
    q3: float
    p05: float
    p95: float


class PeerMetric(BaseModel):
    feature: str
    label: str
    unit: Literal["money", "number", "percent"]
    current: float
    baseline: float | None
    z: float | None
    peer: PeerStats


class PeerComparison(BaseModel):
    player_id: str
    peer_group: str
    peer_group_level: str
    peer_group_size: int
    metrics: list[PeerMetric]


class SharedIdentifier(BaseModel):
    identifier_type: str
    identifier_value: str


class LinkedPlayer(BaseModel):
    player_id: str
    score: int
    band: Band
    alert_id: str | None
    shared: list[SharedIdentifier]


class Network(BaseModel):
    player_id: str
    cluster_id: str
    cluster_size: int
    linked_players: list[LinkedPlayer]


class Meta(BaseModel):
    synthetic: bool
    window_start: str
    window_end: str
    players: int
    alerts: int
    bands: list[str]
    teams: list[str]
    anomaly_types: dict[str, str]
    statuses: list[str]
    transaction_flags: dict[str, str]
    ai: dict[str, Any]


class TimelineWeek(BaseModel):
    week_start: str
    deposits: float
    withdrawals: float
    turnover: float
    net_loss: float
    bets: int
    night_share: float
    outside_ontario_txns: int
    flagged_txns: int


class Timeline(BaseModel):
    player_id: str
    current_window_start: str
    baseline_start: str
    weeks: list[TimelineWeek]


class AISummary(BaseModel):
    text: str
    source: Literal["llm", "template"]
    provider: str | None
    model: str | None
    verified: bool = Field(description="Every number in the text was found in the case file")
    unverified_numbers: list[str]
    label: str
    generated_at: str
    note: str | None = None
    cached: bool = False


class AskIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    history: list[dict[str, str]] = Field(default_factory=list, description="Earlier turns: {role, content}")


class AskOut(BaseModel):
    answer: str
    source: Literal["llm", "offline", "error"]
    provider: str | None
    model: str | None
    verified: bool
    unverified_numbers: list[str]


class SearchIn(BaseModel):
    query: str = Field(..., min_length=1, max_length=300)


class SearchOut(BaseModel):
    query: str
    filters: dict[str, Any]
    explanation: str
    source: Literal["llm", "keywords"]
    provider: str | None
    model: str | None
    total: int
    alerts: list[AlertSummary]
