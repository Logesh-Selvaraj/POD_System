from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ExperimentCaseResponse(BaseModel):
    case_id: str
    scenario_type: str
    photo_quality: str
    gps_available: bool
    gps_distance_meters: Optional[float]
    timestamp_valid: bool
    signature_available: bool
    otp_valid: bool
    network_available: bool
    expected_delivery_outcome: str
    notes: Optional[str]

    class Config:
        from_attributes = True


class ExperimentResultResponse(BaseModel):
    result_id: str
    experiment_run_id: str
    case_id: str
    system_type: str
    evidence_complete: bool
    evidence_valid: bool
    dispute_created: bool
    dispute_resolved: bool
    false_positive: bool
    false_negative: bool
    processing_time_ms: float
    final_classification: str
    notes: Optional[str]

    class Config:
        from_attributes = True


class ExperimentRunResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    dataset_size: int
    baseline_description: Optional[str]
    proposed_system_description: Optional[str]

    class Config:
        from_attributes = True


class SystemMetricsSchema(BaseModel):
    evidence_completeness_rate: float
    evidence_validity_rate: float
    dispute_rate: float
    disputes_resolved: int
    dispute_resolution_rate: float
    false_positive_count: int
    false_negative_count: int
    accuracy: float
    average_processing_time: float
    offline_success_rate: float

    # Verification Rates
    blur_detection_rate: float
    gps_failure_detection_rate: float
    gps_mismatch_detection_rate: float
    missing_signature_detection_rate: float
    invalid_otp_detection_rate: float


class MetricComparisonRow(BaseModel):
    metric_name: str
    baseline_value: float
    proposed_value: float
    absolute_difference: float
    percentage_improvement: Optional[float]  # null if baseline is 0


class ErrorAnalysisRow(BaseModel):
    case_id: str
    scenario_type: str
    expected_outcome: str
    baseline_outcome: str
    proposed_outcome: str
    error_type: Optional[str]  # "False Positive", "False Negative", "Missed Blur", etc.
    explanation: str


class ExperimentRunDetailResponse(BaseModel):
    run: ExperimentRunResponse
    comparison_table: List[MetricComparisonRow]
    error_analysis_table: List[ErrorAnalysisRow]
    cases: List[ExperimentCaseResponse]
    results: List[ExperimentResultResponse]
    baseline_metrics: SystemMetricsSchema
    proposed_metrics: SystemMetricsSchema
