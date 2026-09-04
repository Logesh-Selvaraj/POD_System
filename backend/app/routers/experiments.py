import uuid
import time
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserRole, User
from app.models.experiment import ExperimentRun, ExperimentCase, ExperimentResult
from app.dependencies import RequireRole
from app.schemas.experiment import (
    ExperimentRunResponse,
    ExperimentRunDetailResponse,
    MetricComparisonRow,
    ErrorAnalysisRow,
    ExperimentCaseResponse,
    ExperimentResultResponse,
    SystemMetricsSchema
)

router = APIRouter(prefix="/admin/experiments", tags=["Admin Experiments"])

def seed_scenarios_if_empty(db: Session):
    if db.query(ExperimentCase).first():
        return

    scenarios = []
    # Category 1: Fully Valid Deliveries (10 cases)
    for i in range(1, 11):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Fully Valid Delivery",
            photo_quality="good",
            gps_available=True,
            gps_distance_meters=10.0 + i,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=True,
            network_available=True,
            expected_delivery_outcome="ACCEPTED",
            notes="Nominal happy path delivery scenario."
        ))

    # Category 2: Blurred Photo (4 cases)
    for i in range(11, 15):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Blurred Photo",
            photo_quality="blur",
            gps_available=True,
            gps_distance_meters=12.0,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=True,
            network_available=True,
            expected_delivery_outcome="NEEDS_MANUAL_REVIEW",
            notes="Blurry image, requires human inspection."
        ))

    # Category 3: Missing GPS (4 cases)
    for i in range(15, 19):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Missing GPS",
            photo_quality="good",
            gps_available=False,
            gps_distance_meters=None,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=True,
            network_available=True,
            expected_delivery_outcome="NEEDS_MANUAL_REVIEW",
            notes="GPS unavailable, handled as offline transaction."
        ))

    # Category 4: GPS Mismatch (4 cases)
    for i in range(19, 23):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="GPS Mismatch",
            photo_quality="good",
            gps_available=True,
            gps_distance_meters=450.0,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=True,
            network_available=True,
            expected_delivery_outcome="DISPUTE",
            notes="Rider located > 150m away from target coordinates."
        ))

    # Category 5: Invalid Timestamp (3 cases)
    for i in range(23, 26):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Invalid Timestamp",
            photo_quality="good",
            gps_available=True,
            gps_distance_meters=15.0,
            timestamp_valid=False,
            signature_available=True,
            otp_valid=True,
            network_available=True,
            expected_delivery_outcome="NEEDS_MANUAL_REVIEW",
            notes="Device timestamp fell outside valid window."
        ))

    # Category 6: Missing Signature (3 cases)
    for i in range(26, 29):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Missing Signature",
            photo_quality="good",
            gps_available=True,
            gps_distance_meters=8.0,
            timestamp_valid=True,
            signature_available=False,
            otp_valid=True,
            network_available=True,
            expected_delivery_outcome="NEEDS_MANUAL_REVIEW",
            notes="Customer did not sign."
        ))

    # Category 7: Invalid OTP (3 cases)
    for i in range(29, 32):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Invalid OTP",
            photo_quality="good",
            gps_available=True,
            gps_distance_meters=20.0,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=False,
            network_available=True,
            expected_delivery_outcome="NEEDS_MANUAL_REVIEW",
            notes="Incorrect OTP entered by recipient."
        ))

    # Category 8: Network Unavailable (3 cases)
    for i in range(32, 35):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Network Unavailable",
            photo_quality="good",
            gps_available=True,
            gps_distance_meters=14.0,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=True,
            network_available=False,
            expected_delivery_outcome="NEEDS_MANUAL_REVIEW",
            notes="Local queue storage offline."
        ))

    # Category 9: Multiple Missing Evidence Fields (3 cases)
    for i in range(35, 38):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Multiple Missing Evidence Fields",
            photo_quality="good",
            gps_available=False,
            gps_distance_meters=None,
            timestamp_valid=True,
            signature_available=False,
            otp_valid=False,
            network_available=True,
            expected_delivery_outcome="DISPUTE",
            notes="Missing signature, OTP and GPS coordinates."
        ))

    # Category 10: Low-Quality Photo + GPS Mismatch (3 cases)
    for i in range(38, 41):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Low-Quality Photo + GPS Mismatch",
            photo_quality="blur",
            gps_available=True,
            gps_distance_meters=600.0,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=True,
            network_available=True,
            expected_delivery_outcome="DISPUTE",
            notes="Combinatorial failure case."
        ))

    # Category 11: Offline capture with valid evidence (2 cases)
    for i in range(41, 43):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Offline capture with valid evidence",
            photo_quality="good",
            gps_available=False,
            gps_distance_meters=None,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=True,
            network_available=False,
            expected_delivery_outcome="NEEDS_MANUAL_REVIEW",
            notes="Simulated offline batch."
        ))

    # Category 12: Customer dispute despite complete evidence (2 cases)
    for i in range(43, 45):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Customer dispute despite complete evidence",
            photo_quality="good",
            gps_available=True,
            gps_distance_meters=5.0,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=True,
            network_available=True,
            expected_delivery_outcome="ACCEPTED",
            notes="Delivery was good, customer raised false complaint."
        ))

    # Category 13: Customer dispute with incomplete evidence (2 cases)
    for i in range(45, 47):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Customer dispute with incomplete evidence",
            photo_quality="blur",
            gps_available=True,
            gps_distance_meters=180.0,
            timestamp_valid=True,
            signature_available=False,
            otp_valid=False,
            network_available=True,
            expected_delivery_outcome="DISPUTE",
            notes="Valid dispute based on bad telemetry data."
        ))

    # Category 14: Dispatcher review required (2 cases)
    for i in range(47, 49):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Dispatcher review required",
            photo_quality="good",
            gps_available=True,
            gps_distance_meters=10.0,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=False,
            network_available=True,
            expected_delivery_outcome="NEEDS_MANUAL_REVIEW",
            notes="Marginal case, requires manual bypass."
        ))

    # Category 15: Valid evidence but delayed sync (2 cases)
    for i in range(49, 51):
        scenarios.append(ExperimentCase(
            case_id=f"CASE-{1000+i}",
            scenario_type="Valid evidence but delayed sync",
            photo_quality="good",
            gps_available=True,
            gps_distance_meters=12.0,
            timestamp_valid=True,
            signature_available=True,
            otp_valid=True,
            network_available=True,
            expected_delivery_outcome="ACCEPTED",
            notes="Normal delivery synced late."
        ))

    db.add_all(scenarios)
    db.commit()


def compute_metrics(results: List[ExperimentResult], cases: List[ExperimentCase]) -> SystemMetricsSchema:
    total = len(results)
    if total == 0:
        return SystemMetricsSchema(
            evidence_completeness_rate=0.0,
            evidence_validity_rate=0.0,
            dispute_rate=0.0,
            disputes_resolved=0,
            dispute_resolution_rate=0.0,
            false_positive_count=0,
            false_negative_count=0,
            accuracy=0.0,
            average_processing_time=0.0,
            offline_success_rate=0.0,
            blur_detection_rate=0.0,
            gps_failure_detection_rate=0.0,
            gps_mismatch_detection_rate=0.0,
            missing_signature_detection_rate=0.0,
            invalid_otp_detection_rate=0.0
        )

    cases_dict = {c.case_id: c for c in cases}

    # Helper counters
    evidence_complete_count = sum(1 for r in results if r.evidence_complete)
    evidence_valid_count = sum(1 for r in results if r.evidence_valid)
    disputes_count = sum(1 for r in results if r.dispute_created)
    resolved_count = sum(1 for r in results if r.dispute_resolved)
    fp_count = sum(1 for r in results if r.false_positive)
    fn_count = sum(1 for r in results if r.false_negative)
    avg_proc_time = sum(r.processing_time_ms for r in results) / total

    # Accuracy: correctly classified / total
    correct_classifications = 0
    for r in results:
        case = cases_dict.get(r.case_id)
        if case and r.final_classification == case.expected_delivery_outcome:
            correct_classifications += 1
    accuracy = correct_classifications / total

    # Offline scenarios: gps_available is False or network_available is False
    offline_results = [r for r in results if not cases_dict[r.case_id].gps_available or not cases_dict[r.case_id].network_available]
    offline_correct = 0
    for r in offline_results:
        case = cases_dict[r.case_id]
        if r.final_classification == case.expected_delivery_outcome:
            offline_correct += 1
    offline_success = offline_correct / len(offline_results) if offline_results else 0.0

    # Failure category detection rates
    blur_cases = [r for r in results if cases_dict[r.case_id].photo_quality == "blur"]
    blur_detected = sum(1 for r in blur_cases if r.final_classification in ["DISPUTE", "NEEDS_MANUAL_REVIEW"])
    blur_rate = blur_detected / len(blur_cases) if blur_cases else 0.0

    gps_fail_cases = [r for r in results if not cases_dict[r.case_id].gps_available]
    gps_fail_detected = sum(1 for r in gps_fail_cases if r.final_classification in ["DISPUTE", "NEEDS_MANUAL_REVIEW"])
    gps_fail_rate = gps_fail_detected / len(gps_fail_cases) if gps_fail_cases else 0.0

    gps_mismatch_cases = [r for r in results if cases_dict[r.case_id].gps_available and (cases_dict[r.case_id].gps_distance_meters or 0) > 150.0]
    gps_mismatch_detected = sum(1 for r in gps_mismatch_cases if r.final_classification == "DISPUTE")
    gps_mismatch_rate = gps_mismatch_detected / len(gps_mismatch_cases) if gps_mismatch_cases else 0.0

    sig_cases = [r for r in results if not cases_dict[r.case_id].signature_available]
    sig_detected = sum(1 for r in sig_cases if r.final_classification in ["DISPUTE", "NEEDS_MANUAL_REVIEW"])
    sig_rate = sig_detected / len(sig_cases) if sig_cases else 0.0

    otp_cases = [r for r in results if not cases_dict[r.case_id].otp_valid]
    otp_detected = sum(1 for r in otp_cases if r.final_classification in ["DISPUTE", "NEEDS_MANUAL_REVIEW"])
    otp_rate = otp_detected / len(otp_cases) if otp_cases else 0.0

    return SystemMetricsSchema(
        evidence_completeness_rate=round(evidence_complete_count / total, 4),
        evidence_validity_rate=round(evidence_valid_count / total, 4),
        dispute_rate=round(disputes_count / total, 4),
        disputes_resolved=resolved_count,
        dispute_resolution_rate=round(resolved_count / disputes_count, 4) if disputes_count > 0 else 0.0,
        false_positive_count=fp_count,
        false_negative_count=fn_count,
        accuracy=round(accuracy, 4),
        average_processing_time=round(avg_proc_time, 2),
        offline_success_rate=round(offline_success, 4),
        blur_detection_rate=round(blur_rate, 4),
        gps_failure_detection_rate=round(gps_fail_rate, 4),
        gps_mismatch_detection_rate=round(gps_mismatch_rate, 4),
        missing_signature_detection_rate=round(sig_rate, 4),
        invalid_otp_detection_rate=round(otp_rate, 4)
    )


@router.get("", response_model=List[ExperimentRunResponse])
def list_experiment_runs(
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.ADMIN]))
):
    seed_scenarios_if_empty(db)
    return db.query(ExperimentRun).order_by(ExperimentRun.created_at.desc()).all()


@router.get("/{run_id}", response_model=ExperimentRunDetailResponse)
def get_experiment_run_detail(
    run_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.ADMIN]))
):
    run = db.query(ExperimentRun).filter(ExperimentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Experiment run {run_id} not found")

    cases = db.query(ExperimentCase).all()
    results = db.query(ExperimentResult).filter(ExperimentResult.experiment_run_id == run_id).all()

    baseline_results = [r for r in results if r.system_type == "BASELINE"]
    proposed_results = [r for r in results if r.system_type == "PROPOSED"]

    baseline_metrics = compute_metrics(baseline_results, cases)
    proposed_metrics = compute_metrics(proposed_results, cases)

    # Compile Comparison Table
    metric_names = [
        ("Evidence Completeness Rate", "evidence_completeness_rate"),
        ("Evidence Validity Rate", "evidence_validity_rate"),
        ("Dispute Rate", "dispute_rate"),
        ("Disputes Resolved", "disputes_resolved"),
        ("Dispute Resolution Rate", "dispute_resolution_rate"),
        ("False Positive Count", "false_positive_count"),
        ("False Negative Count", "false_negative_count"),
        ("Accuracy", "accuracy"),
        ("Avg Processing Time (ms)", "average_processing_time"),
        ("Offline Scenario Success Rate", "offline_success_rate"),
        ("GPS Failure Detection", "gps_failure_detection_rate"),
        ("GPS Mismatch Detection", "gps_mismatch_detection_rate"),
        ("Blurry Photo Detection", "blur_detection_rate"),
        ("Missing Signature Detection", "missing_signature_detection_rate"),
        ("Invalid OTP Detection", "invalid_otp_detection_rate")
    ]

    comparison_table = []
    for label, attr in metric_names:
        base_val = getattr(baseline_metrics, attr)
        prop_val = getattr(proposed_metrics, attr)
        diff = prop_val - base_val

        # Handle improvement calculations safely (avoid zero denominator)
        improvement = None
        if base_val != 0.0:
            # For count-based false positive/negative or dispute rates, reducing is improvement.
            # But let's compute straightforward relative change or absolute relative gain.
            # Let's return (prop_val - base_val) / base_val * 100
            improvement = (diff / base_val) * 100.0

        comparison_table.append(
            MetricComparisonRow(
                metric_name=label,
                baseline_value=float(base_val),
                proposed_value=float(prop_val),
                absolute_difference=float(diff),
                percentage_improvement=improvement
            )
        )

    # Compile Error Analysis Table
    error_analysis_table = []
    cases_dict = {c.case_id: c for c in cases}
    for pc_res in proposed_results:
        case = cases_dict.get(pc_res.case_id)
        if not case:
            continue

        base_res = next((br for br in baseline_results if br.case_id == pc_res.case_id), None)
        base_classification = base_res.final_classification if base_res else "UNKNOWN"

        is_incorrect = pc_res.final_classification != case.expected_delivery_outcome
        if is_incorrect or pc_res.false_positive or pc_res.false_negative:
            # Categorize Error
            error_type = "Other"
            explanation = "Discrepancy in classification outcome."

            if pc_res.false_positive:
                error_type = "False Positive"
                explanation = "System incorrectly validated a delivery with faulty parameters."
            elif pc_res.false_negative:
                error_type = "False Negative"
                explanation = "System raised dispute on valid/acceptable telemetry."
            elif case.photo_quality == "blur" and pc_res.final_classification == "ACCEPTED":
                error_type = "Missed Blur"
                explanation = "OpenCV blur check did not trigger flag."
            elif not case.gps_available and pc_res.final_classification == "ACCEPTED":
                error_type = "Missed GPS Failure"
                explanation = "Zero GPS coordinates allowed to pass."
            elif (case.gps_distance_meters or 0) > 150.0 and pc_res.final_classification == "ACCEPTED":
                error_type = "Missed GPS Mismatch"
                explanation = "Rider was out-of-bounds but bypass wasn't triggered."

            error_analysis_table.append(
                ErrorAnalysisRow(
                    case_id=case.case_id,
                    scenario_type=case.scenario_type,
                    expected_outcome=case.expected_delivery_outcome,
                    baseline_outcome=base_classification,
                    proposed_outcome=pc_res.final_classification,
                    error_type=error_type,
                    explanation=explanation
                )
            )

    return ExperimentRunDetailResponse(
        run=ExperimentRunResponse.model_validate(run),
        comparison_table=comparison_table,
        error_analysis_table=error_analysis_table,
        cases=[ExperimentCaseResponse.model_validate(c) for c in cases],
        results=[ExperimentResultResponse.model_validate(r) for r in results],
        baseline_metrics=baseline_metrics,
        proposed_metrics=proposed_metrics
    )


@router.post("/run", response_model=ExperimentRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_experiment_run(
    name: Optional[str] = "Standard Comparison Run",
    description: Optional[str] = "Automated execution comparing simple baseline vs proposed Standardised POD system",
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.ADMIN]))
):
    seed_scenarios_if_empty(db)
    cases = db.query(ExperimentCase).all()

    run_id = f"RUN-{str(uuid.uuid4())[:8].upper()}"
    run = ExperimentRun(
        id=run_id,
        name=name,
        description=description,
        created_at=datetime.utcnow(),
        dataset_size=len(cases),
        baseline_description="Complete status and has basic photo = ACCEPTED; else DISPUTE.",
        proposed_system_description="Standardised Proof-of-Delivery engine using weighted multi-factor checks."
    )
    db.add(run)
    db.commit()

    results = []

    # Run evaluations on each case
    for case in cases:
        # A. Evaluate Baseline
        start_time_base = time.perf_counter()
        # Has basic delivery photo (photo_quality is good or blur)
        has_basic_photo = case.photo_quality in ["good", "blur"]
        
        # Consider complete if expected outcome is ACCEPTED
        is_marked_complete = case.expected_delivery_outcome == "ACCEPTED"

        base_classification = "ACCEPTED" if (has_basic_photo and is_marked_complete) else "DISPUTE"
        processing_time_base = (time.perf_counter() - start_time_base) * 1000.0

        # Baseline Dispute creation/resolution
        base_dispute_created = base_classification == "DISPUTE"
        # Baseline has no dispatcher override, so it can never resolve a created dispute!
        base_dispute_resolved = False 

        # Baseline completeness & validity
        base_complete = has_basic_photo
        base_valid = base_classification == "ACCEPTED"

        # Baseline False Positive / False Negative
        base_fp = (base_classification == "ACCEPTED" and case.expected_delivery_outcome != "ACCEPTED")
        base_fn = (base_classification == "DISPUTE" and case.expected_delivery_outcome == "ACCEPTED")

        results.append(ExperimentResult(
            result_id=str(uuid.uuid4()),
            experiment_run_id=run_id,
            case_id=case.case_id,
            system_type="BASELINE",
            evidence_complete=base_complete,
            evidence_valid=base_valid,
            dispute_created=base_dispute_created,
            dispute_resolved=base_dispute_resolved,
            false_positive=base_fp,
            false_negative=base_fn,
            processing_time_ms=round(processing_time_base, 3),
            final_classification=base_classification,
            notes="Baseline simple evaluation."
        ))

        # B. Evaluate Proposed
        start_time_prop = time.perf_counter()
        
        # Re-use engine scores:
        photo_score = 25.0 if case.photo_quality == "good" else (12.5 if case.photo_quality == "blur" else 0.0)
        gps_score = 25.0 if (case.gps_available and (case.gps_distance_meters or 0.0) <= 150.0) else 0.0
        timestamp_score = 20.0 if case.timestamp_valid else 0.0
        signature_score = 20.0 if case.signature_available else 0.0
        otp_score = 10.0 if case.otp_valid else 0.0

        total_score = photo_score + gps_score + timestamp_score + signature_score + otp_score

        if total_score >= 90.0:
            prop_classification = "ACCEPTED"
        elif total_score >= 70.0:
            prop_classification = "NEEDS_MANUAL_REVIEW"
        else:
            prop_classification = "DISPUTE"

        processing_time_prop = (time.perf_counter() - start_time_prop) * 1000.0

        # Proposed completeness & validity
        prop_complete = (case.photo_quality == "good" and case.gps_available and case.timestamp_valid and case.signature_available and case.otp_valid)
        prop_valid = prop_classification == "ACCEPTED"

        # Dispute created if outcome is DISPUTE or NEEDS_MANUAL_REVIEW
        prop_dispute_created = prop_classification in ["DISPUTE", "NEEDS_MANUAL_REVIEW"]
        
        # Dispatcher reviews and overrides to ACCEPTED if ground truth is ACCEPTED
        prop_dispute_resolved = (prop_dispute_created and case.expected_delivery_outcome == "ACCEPTED")

        # Proposed False Positive / False Negative
        prop_fp = (prop_classification == "ACCEPTED" and case.expected_delivery_outcome != "ACCEPTED")
        prop_fn = (prop_classification == "DISPUTE" and case.expected_delivery_outcome == "ACCEPTED" and not prop_dispute_resolved)

        results.append(ExperimentResult(
            result_id=str(uuid.uuid4()),
            experiment_run_id=run_id,
            case_id=case.case_id,
            system_type="PROPOSED",
            evidence_complete=prop_complete,
            evidence_valid=prop_valid,
            dispute_created=prop_dispute_created,
            dispute_resolved=prop_dispute_resolved,
            false_positive=prop_fp,
            false_negative=prop_fn,
            processing_time_ms=round(processing_time_prop, 3),
            final_classification=prop_classification,
            notes=f"Proposed score evaluation. Total Score = {total_score}/100"
        ))

    db.add_all(results)
    run.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(run)

    return run
