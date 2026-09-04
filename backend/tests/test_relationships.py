import pytest
import os
import uuid
os.environ["USE_SQLITE"] = "true"

from sqlalchemy import inspect
from app.database import engine, SessionLocal
from app.init_db import init_db
from app.models import (
    User, Restaurant, Rider, Customer, Order, Delivery,
    Evidence, Dispute, DispatcherOverride, AuditLog
)

@pytest.fixture(autouse=True)
def setup_db():
    init_db(reset=True)

def test_all_10_domain_tables_exist():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_10_tables = [
        "users",
        "restaurants",
        "riders",
        "customers",
        "orders",
        "deliveries",
        "evidence",
        "disputes",
        "dispatcher_overrides",
        "audit_logs"
    ]
    
    for table_name in required_10_tables:
        assert table_name in tables, f"Required domain table '{table_name}' is missing from database schema!"

def test_foreign_key_relationships():
    db = SessionLocal()
    try:
        # 1. Fetch user & profile
        restaurant = db.query(Restaurant).first()
        assert restaurant is not None
        assert restaurant.user.role.value == "restaurant"
        
        # 2. Restaurant -> Orders
        orders = restaurant.orders
        assert len(orders) >= 1
        
        # 3. Order -> Delivery
        order_1 = orders[0]
        deliveries = order_1.deliveries
        assert len(deliveries) >= 1
        
        # 4. Delivery -> Evidence
        delivery_3 = db.query(Delivery).filter(Delivery.id == "DEL-1003").first()
        assert delivery_3 is not None
        assert delivery_3.evidence is not None
        assert delivery_3.evidence.total_quality_score == 87.5
        
        # 5. Delivery -> Dispute
        assert len(delivery_3.disputes) >= 1
        assert delivery_3.disputes[0].reason == "Blurry photo attached as proof of delivery"
        
        # 6. Delivery -> Dispatcher Override
        assert len(delivery_3.overrides) >= 1
        assert delivery_3.overrides[0].reason_code == "BLURRY_PHOTO_VALIDATED"

    finally:
        db.close()

def test_audit_logs_append_only_protection():
    if engine.dialect.name != "postgresql":
        pytest.skip("Audit log append-only trigger is PostgreSQL specific")
    db = SessionLocal()
    try:
        audit = db.query(AuditLog).first()
        assert audit is not None
        
        # Test 1: Update protection
        audit.action = "ILLEGAL_MUTATION"
        with pytest.raises(Exception, match="append-only"):
            db.commit()
        db.rollback()
        
        # Test 2: Delete protection
        db.delete(audit)
        with pytest.raises(Exception, match="append-only"):
            db.commit()
        db.rollback()

    finally:
        db.close()
