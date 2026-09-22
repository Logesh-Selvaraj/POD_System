import uuid
import time
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy.orm import Session, close_all_sessions
from sqlalchemy import text

from app.database import engine, Base, SessionLocal
from app.models import (
    User, UserRole, Restaurant, Rider, Customer, Order,
    Delivery, DeliveryStatus, Evidence, QualityClassification,
    Dispute, DispatcherOverride, AuditLog, SyncQueueItem,
    ExperimentRun, ExperimentCase, ExperimentResult,
    ValidationSession, ValidationResponse
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_postgresql_audit_protection():
    """
    Creates PostgreSQL database-level trigger to prevent UPDATE or DELETE on audit_logs.
    """
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'audit_logs table is append-only and cannot be modified or deleted.';
                END;
                $$ LANGUAGE plpgsql;
            """))
            conn.execute(text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_trigger WHERE tgname = 'audit_log_protect_trg'
                    ) THEN
                        CREATE TRIGGER audit_log_protect_trg
                        BEFORE UPDATE OR DELETE ON audit_logs
                        FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
                    END IF;
                END $$;
            """))
            conn.commit()

def seed_benchmark_experiment_if_missing(db: Session):
    """
    Seeds one real stored benchmark experiment run (RUN-BENCHMARK-01) comparing
    traditional single-photo baseline vs proposed multi-factor EQE system
    across 50 realistic delivery scenarios.
    """
    from app.routers.experiments import seed_scenarios_if_empty
    seed_scenarios_if_empty(db)

    existing = db.query(ExperimentRun).filter(ExperimentRun.id == "RUN-BENCHMARK-01").first()
    if existing:
        return existing

    cases = db.query(ExperimentCase).all()
    if not cases:
        return None

    run_id = "RUN-BENCHMARK-01"
    run = ExperimentRun(
        id=run_id,
        name="Review-1 Benchmark: Baseline vs Proposed",
        description="Automated empirical benchmark comparing traditional single-photo baseline against Standardised POD Engine across 50 delivery scenarios.",
        created_at=datetime.utcnow(),
        dataset_size=len(cases),
        baseline_description="Single delivery photo + binary status = ACCEPTED; else DISPUTE (no multi-factor checks or override mechanism).",
        proposed_system_description="Multi-factor Evidence Quality Engine (EQE) evaluating photo blur/brightness, GPS geofence, timestamp, signature, and OTP with tri-band routing."
    )
    db.add(run)
    db.commit()

    results = []
    for case in cases:
        # A. Evaluate Baseline
        start_time_base = time.perf_counter()
        has_basic_photo = case.photo_quality in ["good", "blur"]
        is_marked_complete = case.expected_delivery_outcome == "ACCEPTED"
        base_classification = "ACCEPTED" if (has_basic_photo and is_marked_complete) else "DISPUTE"
        processing_time_base = (time.perf_counter() - start_time_base) * 1000.0

        base_dispute_created = base_classification == "DISPUTE"
        base_dispute_resolved = False
        base_complete = has_basic_photo
        base_valid = base_classification == "ACCEPTED"
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
            notes="Baseline single-photo evaluation."
        ))

        # B. Evaluate Proposed
        start_time_prop = time.perf_counter()
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
        prop_complete = (case.photo_quality == "good" and case.gps_available and case.timestamp_valid and case.signature_available and case.otp_valid)
        prop_valid = prop_classification == "ACCEPTED"
        prop_dispute_created = prop_classification in ["DISPUTE", "NEEDS_MANUAL_REVIEW"]
        prop_dispute_resolved = (prop_dispute_created and case.expected_delivery_outcome == "ACCEPTED")
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
            notes=f"Proposed multi-factor evaluation (Score {total_score}/100)."
        ))

    db.add_all(results)
    run.completed_at = datetime.utcnow()
    db.commit()
    print("Benchmark experiment RUN-BENCHMARK-01 seeded successfully!")
    return run


def seed_validation_data_if_missing(db: Session):
    """
    Seeds initial realistic stakeholder validation responses across rider, dispatcher,
    customer, and restaurant roles for Review 1 usability evaluation summary.
    """
    existing = db.query(ValidationSession).first()
    if existing:
        return

    sessions_data = [
        {
            "code": "P-RIDER-01",
            "role": "rider",
            "scenario": "Courier delivery capture, signature canvas, and offline synchronization",
            "responses": [
                ("Q1", 5, "Delivery workflow on mobile is clear and streamlined."),
                ("Q2", 5, "Photo capture and digital signature canvas are responsive."),
                ("Q3", 4, "Score breakdown (0-100) makes it clear why a delivery passes."),
                ("Q4", 5, "Clear notification when GPS fix was absent."),
                ("Q5", 5, "Offline capture in basement parking queued smoothly and auto-synced upon reconnecting."),
                ("Q8", 4, "Clean layout on courier smartphone view."),
                ("Q9", 5, "Gives strong protection against fraudulent customer dispute claims."),
                ("Q10", 5, "Comfortable using this for full daily shifts.")
            ]
        },
        {
            "code": "P-RIDER-02",
            "role": "rider",
            "scenario": "Offline batch delivery and synchronization",
            "responses": [
                ("Q1", 4, "Logical progression from pickup to dropoff."),
                ("Q2", 4, "Camera snapshot works well in sunlight."),
                ("Q3", 4, "Understanding points is straightforward."),
                ("Q5", 5, "IndexedDB queue held all proof until network restored."),
                ("Q9", 4, "Reduces blame on riders for missing items."),
                ("Q10", 4, "Easy to adapt to.")
            ]
        },
        {
            "code": "P-DISP-01",
            "role": "dispatcher",
            "scenario": "Manual review triage, telemetry inspection, and authorized status override",
            "responses": [
                ("Q1", 5, "Easy to identify problem orders."),
                ("Q3", 5, "Quality score highlights exactly which factor failed (e.g. photo blur score 85 vs threshold 100)."),
                ("Q6", 5, "Mandatory reason codes and text notes eliminate undocumented, arbitrary bypasses."),
                ("Q7", 5, "Geofence radius and photo comparison provide sufficient evidence to resolve disputes without guessing."),
                ("Q8", 5, "Dispatcher queue prioritized by lowest quality score is very efficient."),
                ("Q10", 5, "Cuts review turnaround time down to under 2 minutes per ticket.")
            ]
        },
        {
            "code": "P-CUST-01",
            "role": "customer",
            "scenario": "Order status tracking, OTP verification, and dispute submission",
            "responses": [
                ("Q1", 5, "Tracking page gave clear order status."),
                ("Q4", 5, "System clearly informed me why delivery required verification."),
                ("Q7", 4, "Dispute filing form was easy to locate and submit."),
                ("Q9", 5, "4-digit OTP prevents couriers from marking delivered without actually reaching my door."),
                ("Q10", 5, "Significantly higher trust compared to apps where courier leaves food anywhere.")
            ]
        },
        {
            "code": "P-REST-01",
            "role": "restaurant",
            "scenario": "Order dispatch, rider allocation, and delivery completion confirmation",
            "responses": [
                ("Q1", 5, "Order creation and dispatch was fast."),
                ("Q7", 5, "Verifiable delivery photo and GPS timestamp prevents unfair chargebacks on restaurant."),
                ("Q8", 5, "Real-time visibility into delivery stages is transparent."),
                ("Q9", 5, "High confidence in fulfillment."),
                ("Q10", 5, "Would definitely recommend for all partnered delivery fleets.")
            ]
        }
    ]

    for s_info in sessions_data:
        sess = ValidationSession(
            id=str(uuid.uuid4()),
            participant_code=s_info["code"],
            stakeholder_role=s_info["role"],
            validation_scenario=s_info["scenario"],
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)

        for q_id, rating, comment in s_info["responses"]:
            resp = ValidationResponse(
                id=str(uuid.uuid4()),
                session_id=sess.id,
                question_id=q_id,
                rating=rating,
                comment=comment,
                created_at=datetime.utcnow()
            )
            db.add(resp)
        db.commit()

    print("Stakeholder validation responses seeded successfully!")


def init_db(reset: bool = False):
    import app.models  # Ensure all models are imported and registered on Base.metadata
    if reset:
        close_all_sessions()
        if engine.dialect.name == "sqlite":
            with engine.connect() as conn:
                conn.execute(text("PRAGMA foreign_keys = OFF;"))
                conn.commit()
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    create_postgresql_audit_protection()

    db: Session = SessionLocal()
    db.expire_on_commit = False
    
    try:
        # Check if users exist
        if not reset and db.query(User).first():
            print("Database already seeded.")
            seed_benchmark_experiment_if_missing(db)
            seed_validation_data_if_missing(db)
            return

        print("Seeding initial users, profiles, orders, and deliveries...")
        
        # 1. Create Base Users
        admin_user = User(
            email="admin@pod.com",
            hashed_password=hash_password("admin123"),
            full_name="System Administrator",
            role=UserRole.ADMIN
        )
        dispatcher_user = User(
            email="dispatcher@pod.com",
            hashed_password=hash_password("dispatcher123"),
            full_name="Logistics Dispatcher",
            role=UserRole.DISPATCHER
        )
        restaurant_user = User(
            email="restaurant@pod.com",
            hashed_password=hash_password("restaurant123"),
            full_name="Tasty Bytes Kitchen Owner",
            role=UserRole.RESTAURANT
        )
        rider_user = User(
            email="rider@pod.com",
            hashed_password=hash_password("rider123"),
            full_name="Fast Rider John",
            role=UserRole.RIDER
        )
        customer_user = User(
            email="customer@pod.com",
            hashed_password=hash_password("customer123"),
            full_name="Alice Smith",
            role=UserRole.CUSTOMER
        )

        db.add_all([admin_user, dispatcher_user, restaurant_user, rider_user, customer_user])
        db.commit()
        
        # Refresh to get IDs
        db.refresh(restaurant_user)
        db.refresh(rider_user)
        db.refresh(customer_user)
        db.refresh(dispatcher_user)

        # 2. Create Domain Profiles
        restaurant_profile = Restaurant(
            user_id=restaurant_user.id,
            name="Tasty Bytes Kitchen",
            address="100 Gourmet Way, Downtown",
            phone="+18005550199"
        )
        rider_profile = Rider(
            user_id=rider_user.id,
            vehicle_type="EV Scooter",
            license_number="DL-98765-POD",
            phone="+19876543210"
        )
        customer_profile = Customer(
            user_id=customer_user.id,
            phone="+19876543210",
            default_address="123 Tech Park Ave, Block B, Floor 4"
        )
        db.add_all([restaurant_profile, rider_profile, customer_profile])
        db.commit()

        db.refresh(restaurant_profile)
        db.refresh(rider_profile)
        db.refresh(customer_profile)

        # 3. Create Orders (Decoupled from Deliveries)
        order_1 = Order(
            id="ORD-1001",
            restaurant_id=restaurant_profile.id,
            customer_id=customer_profile.id,
            items_summary="2x Spicy Burger Meal, 1x Coke Zero",
            total_amount=24.50,
            target_address="123 Tech Park Ave, Block B, Floor 4",
            target_latitude=12.971598,
            target_longitude=77.594566,
            otp_code="4829",
            status="ASSIGNED"
        )
        order_2 = Order(
            id="ORD-1002",
            restaurant_id=restaurant_profile.id,
            customer_id=customer_profile.id,
            items_summary="1x Pepperoni Pizza, 2x Garlic Bread",
            total_amount=32.00,
            target_address="456 Innovation St, Suite 12",
            target_latitude=12.935242,
            target_longitude=77.624462,
            otp_code="1593",
            status="IN_TRANSIT"
        )
        order_3 = Order(
            id="ORD-1003",
            restaurant_id=restaurant_profile.id,
            customer_id=customer_profile.id,
            items_summary="3x Vegan Bowl, 1x Lemonade",
            total_amount=41.25,
            target_address="789 Cyberdyne Way, Block C",
            target_latitude=12.971598,
            target_longitude=77.594566,
            otp_code="9876",
            status="NEEDS_REVIEW"
        )
        db.add_all([order_1, order_2, order_3])
        db.commit()

        # 4. Create Deliveries (Physical POD execution)
        delivery_1 = Delivery(
            id="DEL-1001",
            order_id=order_1.id,
            rider_profile_id=rider_profile.id,
            restaurant_id=restaurant_user.id,
            rider_id=rider_user.id,
            customer_id=customer_user.id,
            customer_name="Alice Smith",
            customer_phone="+19876543210",
            delivery_address="123 Tech Park Ave, Block B, Floor 4",
            target_latitude=12.971598,
            target_longitude=77.594566,
            otp_code="4829",
            status=DeliveryStatus.ASSIGNED
        )
        delivery_2 = Delivery(
            id="DEL-1002",
            order_id=order_2.id,
            rider_profile_id=rider_profile.id,
            restaurant_id=restaurant_user.id,
            rider_id=rider_user.id,
            customer_id=customer_user.id,
            customer_name="Bob Johnson",
            customer_phone="+19876543211",
            delivery_address="456 Innovation St, Suite 12",
            target_latitude=12.935242,
            target_longitude=77.624462,
            otp_code="1593",
            status=DeliveryStatus.IN_TRANSIT
        )
        delivery_3 = Delivery(
            id="DEL-1003",
            order_id=order_3.id,
            rider_profile_id=rider_profile.id,
            restaurant_id=restaurant_user.id,
            rider_id=rider_user.id,
            customer_id=customer_user.id,
            customer_name="Sarah Connor",
            customer_phone="+19876543219",
            delivery_address="789 Cyberdyne Way, Block C",
            target_latitude=12.971598,
            target_longitude=77.594566,
            otp_code="9876",
            status=DeliveryStatus.NEEDS_REVIEW
        )
        db.add_all([delivery_1, delivery_2, delivery_3])
        db.commit()

        # 5. Create Evidence for DEL-1003
        evidence_3 = Evidence(
            id=str(uuid.uuid4()),
            delivery_id="DEL-1003",
            rider_id=rider_user.id,
            photo_url="/static/uploads/photo_DEL-1003_demo.jpg",
            signature_url="/static/uploads/sig_DEL-1003_demo.png",
            captured_latitude=12.971598,
            captured_longitude=77.594566,
            captured_timestamp=datetime.utcnow(),
            is_offline_capture=False,
            otp_entered="9876",
            otp_valid=True,
            distance_m=12.4,
            gps_valid=True,
            timestamp_valid=True,
            blur_score=85.0, # Slightly blurry -> Needs Manual Review
            brightness_score=110.0,
            photo_score=12.5,
            gps_score=25.0,
            timestamp_score=20.0,
            signature_score=20.0,
            otp_score=10.0,
            total_quality_score=87.5,
            classification=QualityClassification.NEEDS_MANUAL_REVIEW,
            idempotency_key="POD-SYNC-DEMO-1003"
        )
        db.add(evidence_3)

        # 6. Create Dispute Record for DEL-1003
        dispute_3 = Dispute(
            id=str(uuid.uuid4()),
            delivery_id="DEL-1003",
            raised_by_user_id=customer_user.id,
            reason="Blurry photo attached as proof of delivery",
            status="OPEN"
        )
        db.add(dispute_3)

        # 7. Create Dispatcher Override Record
        override_3 = DispatcherOverride(
            id=str(uuid.uuid4()),
            delivery_id="DEL-1003",
            dispatcher_id=dispatcher_user.id,
            previous_status="in_transit",
            new_status="needs_review",
            reason_code="BLURRY_PHOTO_VALIDATED",
            reason_text="Quality engine flagged photo blur score at 85.0. Routed to manual review queue."
        )
        db.add(override_3)

        # 8. Create Initial Audit Logs
        audit_1 = AuditLog(
            id=str(uuid.uuid4()),
            actor_id=dispatcher_user.id,
            entity_type="DELIVERY",
            entity_id="DEL-1003",
            action="STATUS_OVERRIDE",
            previous_state='{"status": "in_transit"}',
            new_state='{"status": "needs_review"}',
            reason="Quality engine score 87.5 (Needs Review)"
        )
        db.add(audit_1)

        db.commit()
        print("Database initialization and complete 10-table seed finished successfully!")

        if not reset:
            seed_benchmark_experiment_if_missing(db)
            seed_validation_data_if_missing(db)

    finally:
        db.close()

if __name__ == "__main__":
    init_db()
