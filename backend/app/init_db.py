import uuid
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy.orm import Session
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

from sqlalchemy.orm import close_all_sessions

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

    finally:
        db.close()

if __name__ == "__main__":
    init_db()
