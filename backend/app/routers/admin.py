import json
from datetime import datetime, date, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.delivery import Delivery, DeliveryStatus
from app.models.evidence import Evidence
from app.models.dispute import Dispute
from app.dependencies import RequireRole
from app.schemas.admin_analytics import (
    AdminAnalyticsResponse,
    StatusDistribution,
    ScoreDistribution,
    DailyTrendItem,
    DailyScoreTrendItem,
    RiderPerformanceItem,
    ComponentAverages,
    ComponentMissingOrFailed,
    DisputeMetrics
)

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/analytics", response_model=AdminAnalyticsResponse)
def get_admin_analytics(
    from_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    to_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(RequireRole([UserRole.ADMIN]))
):
    # 1. Parse and validate dates
    from_date_dt: Optional[datetime] = None
    to_date_dt: Optional[datetime] = None

    if from_date:
        try:
            parsed_from = date.fromisoformat(from_date)
            from_date_dt = datetime.combine(parsed_from, time.min)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="from_date must be in YYYY-MM-DD format"
            )

    if to_date:
        try:
            parsed_to = date.fromisoformat(to_date)
            to_date_dt = datetime.combine(parsed_to, time.max)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="to_date must be in YYYY-MM-DD format"
            )

    if from_date_dt and to_date_dt and from_date_dt > to_date_dt:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="from_date cannot be after to_date"
        )

    # 2. Build queries with date filter
    del_query = db.query(Delivery)
    disp_query = db.query(Dispute)
    ev_query = db.query(Evidence).join(Delivery, Evidence.delivery_id == Delivery.id)

    if from_date_dt:
        del_query = del_query.filter(Delivery.created_at >= from_date_dt)
        disp_query = disp_query.filter(Dispute.created_at >= from_date_dt)
        ev_query = ev_query.filter(Delivery.created_at >= from_date_dt)
    if to_date_dt:
        del_query = del_query.filter(Delivery.created_at <= to_date_dt)
        disp_query = disp_query.filter(Dispute.created_at <= to_date_dt)
        ev_query = ev_query.filter(Delivery.created_at <= to_date_dt)

    deliveries = del_query.all()
    disputes = disp_query.all()
    evidences = ev_query.all()

    total_del = len(deliveries)
    accepted_del = sum(1 for d in deliveries if d.status == DeliveryStatus.DELIVERED)
    review_del = sum(1 for d in deliveries if d.status == DeliveryStatus.NEEDS_REVIEW)
    disputed_del = sum(1 for d in deliveries if d.status == DeliveryStatus.DISPUTED)

    resolved_disp = sum(1 for d in disputes if d.status in ["RESOLVED_REFUNDED", "RESOLVED_REJECTED"])
    unresolved_disp = sum(1 for d in disputes if d.status in ["OPEN", "IN_REVIEW"])

    # Average evidence score
    avg_score = float(sum(ev.total_quality_score for ev in evidences) / len(evidences)) if evidences else None

    # Dispute and acceptance rates
    dispute_rate = float(disputed_del / total_del) if total_del > 0 else 0.0
    acceptance_rate = float(accepted_del / total_del) if total_del > 0 else 0.0

    # Offline and GPS flags
    offline_count = sum(1 for ev in evidences if ev.is_offline_capture)
    gps_fail_count = sum(1 for ev in evidences if not ev.gps_valid or ev.distance_m is None)
    gps_mismatch_count = sum(1 for ev in evidences if not ev.is_offline_capture and not ev.gps_valid)

    # 3. Status distribution
    status_counts = {}
    for d in deliveries:
        status_counts[d.status.value] = status_counts.get(d.status.value, 0) + 1
    status_distribution = [
        StatusDistribution(status=k, count=v) for k, v in status_counts.items()
    ]

    # 4. Evidence score distribution
    score_ranges = {"0–69": 0, "70–89": 0, "90–100": 0}
    for ev in evidences:
        score = ev.total_quality_score
        if score < 70.0:
            score_ranges["0–69"] += 1
        elif score < 90.0:
            score_ranges["70–89"] += 1
        else:
            score_ranges["90–100"] += 1
    evidence_score_distribution = [
        ScoreDistribution(range=k, count=v) for k, v in score_ranges.items()
    ]

    # 5. Trends over time
    daily_deliveries = {}
    daily_disputes = {}
    daily_scores = {} # day -> [scores]

    for d in deliveries:
        day_str = d.created_at.strftime("%Y-%m-%d")
        daily_deliveries[day_str] = daily_deliveries.get(day_str, 0) + 1

    for disp in disputes:
        day_str = disp.created_at.strftime("%Y-%m-%d")
        daily_disputes[day_str] = daily_disputes.get(day_str, 0) + 1

    for ev in evidences:
        day_str = ev.created_at.strftime("%Y-%m-%d")
        if day_str not in daily_scores:
            daily_scores[day_str] = []
        daily_scores[day_str].append(ev.total_quality_score)

    daily_delivery_counts = sorted(
        [DailyTrendItem(day=k, count=v) for k, v in daily_deliveries.items()],
        key=lambda x: x.day
    )
    daily_dispute_counts = sorted(
        [DailyTrendItem(day=k, count=v) for k, v in daily_disputes.items()],
        key=lambda x: x.day
    )
    average_score_over_time = sorted(
        [DailyScoreTrendItem(day=k, average_score=sum(v)/len(v)) for k, v in daily_scores.items()],
        key=lambda x: x.day
    )

    # 6. Rider performance
    riders = db.query(User).filter(User.role == UserRole.RIDER).all()
    rider_performance_list = []
    
    for r in riders:
        # Deliveries for this rider
        r_deliveries = [d for d in deliveries if d.rider_id == r.id]
        r_total = len(r_deliveries)
        
        # If rider has no deliveries ever, skip or include if in active deliveries
        # The prompt requires: "Sort riders by total deliveries descending."
        # We can calculate performance for riders who have at least one delivery.
        if r_total == 0:
            continue

        r_accepted = sum(1 for d in r_deliveries if d.status == DeliveryStatus.DELIVERED)
        r_review = sum(1 for d in r_deliveries if d.status == DeliveryStatus.NEEDS_REVIEW)
        r_disputed = sum(1 for d in r_deliveries if d.status == DeliveryStatus.DISPUTED)

        # Evidences for this rider
        r_evidences = [ev for ev in evidences if ev.rider_id == r.id]
        r_avg_score = sum(ev.total_quality_score for ev in r_evidences) / len(r_evidences) if r_evidences else None
        r_offline = sum(1 for ev in r_evidences if ev.is_offline_capture)

        rider_performance_list.append(
            RiderPerformanceItem(
                rider_id=r.id,
                rider_name=r.full_name,
                total_deliveries=r_total,
                accepted_deliveries=r_accepted,
                review_deliveries=r_review,
                disputed_deliveries=r_disputed,
                average_evidence_score=r_avg_score,
                offline_captures=r_offline
            )
        )

    # Sort riders by total deliveries descending
    rider_performance_list.sort(key=lambda x: x.total_deliveries, reverse=True)

    # 7. Component averages
    comp_photo = sum(ev.photo_score for ev in evidences) / len(evidences) if evidences else 0.0
    comp_gps = sum(ev.gps_score for ev in evidences) / len(evidences) if evidences else 0.0
    comp_timestamp = sum(ev.timestamp_score for ev in evidences) / len(evidences) if evidences else 0.0
    comp_signature = sum(ev.signature_score for ev in evidences) / len(evidences) if evidences else 0.0
    comp_otp = sum(ev.otp_score for ev in evidences) / len(evidences) if evidences else 0.0

    component_performance = ComponentAverages(
        photo=round(comp_photo, 2),
        gps=round(comp_gps, 2),
        timestamp=round(comp_timestamp, 2),
        signature=round(comp_signature, 2),
        otp=round(comp_otp, 2)
    )

    # Component missing/flags
    missing_gps_pct = (sum(1 for ev in evidences if ev.captured_latitude is None or ev.captured_longitude is None) / len(evidences)) * 100.0 if evidences else 0.0
    gps_mismatch_pct = (gps_mismatch_count / len(evidences)) * 100.0 if evidences else 0.0
    offline_pct = (offline_count / len(evidences)) * 100.0 if evidences else 0.0
    low_photo_pct = (sum(1 for ev in evidences if ev.photo_score < 25.0) / len(evidences)) * 100.0 if evidences else 0.0

    component_flags = ComponentMissingOrFailed(
        missing_gps_percentage=round(missing_gps_pct, 2),
        gps_mismatch_percentage=round(gps_mismatch_pct, 2),
        offline_capture_percentage=round(offline_pct, 2),
        low_quality_photo_percentage=round(low_photo_pct, 2)
    )

    # 8. Dispute metrics
    total_disputes = len(disputes)
    open_disputes = sum(1 for disp in disputes if disp.status == "OPEN")
    in_review_disputes = sum(1 for disp in disputes if disp.status == "IN_REVIEW")
    resolved_disputes = sum(1 for disp in disputes if disp.status == "RESOLVED_REFUNDED")
    rejected_disputes = sum(1 for disp in disputes if disp.status == "RESOLVED_REJECTED")

    dispute_rate_calc = total_disputes / total_del if total_del > 0 else 0.0
    resolution_rate_calc = (resolved_disputes + rejected_disputes) / total_disputes if total_disputes > 0 else 0.0

    # Dispute resolution time
    res_times = []
    for disp in disputes:
        if disp.resolved_at and disp.created_at:
            res_times.append((disp.resolved_at - disp.created_at).total_seconds())
    avg_res_time = sum(res_times) / len(res_times) if res_times else None

    dispute_analytics = DisputeMetrics(
        total_disputes=total_disputes,
        open_disputes=open_disputes,
        in_review_disputes=in_review_disputes,
        resolved_disputes=resolved_disputes,
        rejected_disputes=rejected_disputes,
        dispute_rate=round(dispute_rate_calc, 4),
        resolution_rate=round(resolution_rate_calc, 4),
        average_resolution_time_seconds=round(avg_res_time, 2) if avg_res_time is not None else None
    )

    return AdminAnalyticsResponse(
        total_deliveries=total_del,
        accepted_deliveries=accepted_del,
        manual_review_deliveries=review_del,
        disputed_deliveries=disputed_del,
        resolved_disputes=resolved_disp,
        unresolved_disputes=unresolved_disp,
        average_evidence_score=round(avg_score, 2) if avg_score is not None else None,
        dispute_rate=round(dispute_rate, 4),
        evidence_acceptance_rate=round(acceptance_rate, 4),
        offline_capture_count=offline_count,
        gps_failure_count=gps_fail_count,
        gps_mismatch_count=gps_mismatch_count,
        status_distribution=status_distribution,
        evidence_score_distribution=evidence_score_distribution,
        daily_delivery_counts=daily_delivery_counts,
        daily_dispute_counts=daily_dispute_counts,
        average_score_over_time=average_score_over_time,
        rider_performance=rider_performance_list,
        evidence_component_performance=component_performance,
        evidence_component_flags=component_flags,
        dispute_analytics=dispute_analytics
    )
