from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class StatusDistribution(BaseModel):
    status: str
    count: int

class ScoreDistribution(BaseModel):
    range: str
    count: int

class DailyTrendItem(BaseModel):
    day: str
    count: int

class DailyScoreTrendItem(BaseModel):
    day: str
    average_score: float

class RiderPerformanceItem(BaseModel):
    rider_id: int
    rider_name: str
    total_deliveries: int
    accepted_deliveries: int
    review_deliveries: int
    disputed_deliveries: int
    average_evidence_score: Optional[float]
    offline_captures: int

class ComponentAverages(BaseModel):
    photo: float
    gps: float
    timestamp: float
    signature: float
    otp: float

class ComponentMissingOrFailed(BaseModel):
    missing_gps_percentage: float
    gps_mismatch_percentage: float
    offline_capture_percentage: float
    low_quality_photo_percentage: float

class DisputeMetrics(BaseModel):
    total_disputes: int
    open_disputes: int
    in_review_disputes: int
    resolved_disputes: int
    rejected_disputes: int
    dispute_rate: float
    resolution_rate: float
    average_resolution_time_seconds: Optional[float]

class AdminAnalyticsResponse(BaseModel):
    total_deliveries: int
    accepted_deliveries: int
    manual_review_deliveries: int
    disputed_deliveries: int
    resolved_disputes: int
    unresolved_disputes: int
    average_evidence_score: Optional[float]
    dispute_rate: float
    evidence_acceptance_rate: float
    offline_capture_count: int
    gps_failure_count: int
    gps_mismatch_count: int
    
    status_distribution: List[StatusDistribution]
    evidence_score_distribution: List[ScoreDistribution]
    daily_delivery_counts: List[DailyTrendItem]
    daily_dispute_counts: List[DailyTrendItem]
    average_score_over_time: List[DailyScoreTrendItem]
    rider_performance: List[RiderPerformanceItem]
    evidence_component_performance: ComponentAverages
    evidence_component_flags: ComponentMissingOrFailed
    dispute_analytics: DisputeMetrics
