"""Pydantic response / request models. These shapes are what the dashboard consumes; see /docs."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Band = Literal["Low", "Medium", "High", "Critical"]
DecisionKind = Literal["accept", "escalate", "close"]
Status = Literal["open", "accepted", "escalated", "closed"]


class Comparison(BaseModel):
    peer_median: Optional[float] = Field(None, description="Median of the same feature in the player's peer group")
    own_baseline: Optional[float] = Field(None, description="The player's own prior-90-day value (per 30 days where relevant)")


class Reason(BaseModel):
    code: str = Field(..., examples=["INCOME_MISMATCH"])
    anomaly_type: str = Field(..., examples=["income_mismatch"])
    title: str
    detail: str = Field(..., description="Plain-language sentence built only from the evidence values")
    evidence: dict[str, Any]
    comparison: Comparison
    points: int = Field(..., description="Contribution to the 0-100 score (before per-type cap)")


class SecondaryAction(BaseModel):
    team: str
    action: str


class RecommendedAction(BaseModel):
    action: str
    team: str
    rationale: str
    secondary: list[SecondaryAction] = []


class Profile(BaseModel):
    age_band: str
    occupation: str
    income_band: str
    home_region: str
    signup_date: str


class LatestDecision(BaseModel):
    decision: DecisionKind
    note: str = ""
    reason: Optional[str] = None
    investigator: Optional[str] = None
    created_at: str


class AlertSummary(BaseModel):
    alert_id: str
    player_id: str
    rank: int
    score: int
    band: Band
    team: str
    anomaly_types: list[str]
    top_reason_code: str
    top_reason_title: str
    reason_count: int
    status: Status
    profile: Profile
    recommended_action: str
    created_at: str


class AlertList(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[AlertSummary]


class Alert(BaseModel):
    alert_id: str
    player_id: str
    rank: int
    score: int
    band: Band
    team: str
    anomaly_types: list[str]
    points_by_type: dict[str, int]
    top_reason_code: str
    status: Status
    created_at: str
    profile: Profile
    peer_group: str
    peer_group_size: int
    key_metrics: dict[str, float]
    reasons: list[Reason]
    recommended_action: RecommendedAction
    summary: str
    iforest_percentile: float
    raw_points: int = Field(..., description="Sum of reason points before caps; breaks ties between equal scores")
    latest_decision: Optional[LatestDecision] = None


class DecisionIn(BaseModel):
    decision: DecisionKind
    note: str = Field("", max_length=2000)
    reason: Optional[str] = Field(None, max_length=200, description="Override / close reason, e.g. 'benign household'")
    investigator: Optional[str] = Field(None, max_length=100)


class DecisionOut(LatestDecision):
    id: int
    alert_id: str
    status: Status


class Transaction(BaseModel):
    txn_id: str
    timestamp: str
    type: str
    amount_cad: float
    sport: Optional[str] = None
    market: Optional[str] = None
    odds: Optional[float] = None
    channel: str
    device_id: str
    ip_region: str
    payment_method_id: str
    event_id: Optional[str] = None
    selection: Optional[str] = None


class TransactionPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[Transaction]


class PlayerDetail(BaseModel):
    player_id: str
    profile: Profile
    score: int
    band: Band
    team: str
    alert_id: Optional[str]
    peer_group: str
    peer_group_size: int
    monthly_income_estimate: float
    features: dict[str, Any]
    recent_transactions: list[Transaction]


class PeerFeature(BaseModel):
    feature: str
    label: str
    value: float
    own_baseline: Optional[float]
    peer_median: Optional[float]
    peer_q1: Optional[float]
    peer_q3: Optional[float]
    peer_p90: Optional[float]
    z_score: Optional[float]
    percentile: Optional[float]
    flagged: bool


class PeerComparison(BaseModel):
    player_id: str
    peer_group: str
    peer_group_size: int
    z_threshold: float
    features: list[PeerFeature]


class TimelinePoint(BaseModel):
    week_start: str
    deposits: float
    withdrawals: float
    staked: float
    payouts: float
    net_loss: float
    bets: int
    night_share: float
    regions: list[str]
    window: Literal["baseline", "current", "earlier"]


class Timeline(BaseModel):
    player_id: str
    reference_date: str
    current_start: str
    baseline_start: str
    weeks: list[TimelinePoint]


class NetworkNode(BaseModel):
    id: str
    score: int
    band: Band
    is_focus: bool
    alert_id: Optional[str]


class NetworkEdge(BaseModel):
    source: str
    target: str
    shared: list[dict[str, str]]
    opposite_bets: int = 0


class Network(BaseModel):
    player_id: str
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    cluster_size: int
    cluster_avg_score: float
    summary: str


class Stats(BaseModel):
    reference_date: str
    players: int
    alerts: int
    by_band: dict[str, int]
    by_team: dict[str, int]
    by_type: dict[str, int]
    by_status: dict[str, int]
    score_histogram: list[dict[str, int]]
    synthetic: bool = True
