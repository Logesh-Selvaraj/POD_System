# Architectural Decisions and Incremental Project Changelog

This document maintains the architectural decision records (ADRs) and incremental change history for the **Standardised Proof-of-Delivery (POD) System**.

> [!NOTE]
> This document documents design decisions and engineering changes. It does NOT modify or interact with the runtime immutable audit trail (`audit_logs` table), which is append-only and cryptographically protected at the database tier.

---

## Part 1: Architectural Decision Records (ADRs)

### ADR-01: Decoupling Physical Delivery Entities from Commercial Orders
- **Status:** Accepted & Implemented
- **Context:** Food delivery platforms traditionally conflate the commercial order (items ordered, pricing, restaurant billing) with the physical fulfillment event (courier route, delivery attempts, evidence capture). When a courier encounters an issue (e.g. wrong address, absent customer), canceling or updating the order directly introduces accounting errors and destroys delivery telemetry.
- **Decision:** Separate the database entities into `Order` (commercial state: items, bill, payment) and `Delivery` (physical execution: courier assigned, target coordinates, OTP code, live status, evidence reference).
- **Consequences:**
  - Multiple delivery attempts can be linked to a single order if redelivery is required.
  - Delivery verification logic operates strictly on the `Delivery` lifecycle (`ASSIGNED` -> `IN_TRANSIT` -> `DELIVERED` / `NEEDS_REVIEW` / `DISPUTED`).
  - Strict 3NF relational data model without duplicate billing attributes in fulfillment tables.

---

### ADR-02: Multi-Factor Evidence Quality Engine (EQE) with Tri-Band Routing
- **Status:** Accepted & Implemented
- **Context:** Single-factor delivery proof (e.g. standard photo upload) has an extremely high failure rate in practice due to dark, blurry, or fake images. Binary pass/fail decisions lead to high customer friction and false dispute accusations against honest couriers.
- **Decision:** Implement a deterministic, explainable 0–100 weighted rubric combining five independent modalities:
  1. **Photo Verification (25 pts):** OpenCV variance-of-Laplacian blur check (threshold 100.0) + mean pixel intensity brightness check (40.0 to 220.0).
  2. **GPS Geofence Match (25 pts):** Haversine distance between device coordinates and order delivery target (≤ 150m threshold).
  3. **Timestamp Validity (20 pts):** Verified presence and chronological validity of client capture timestamp.
  4. **Recipient Digital Signature (20 pts):** Captured HTML5 canvas signature encoded in PNG base64 format.
  5. **One-Time Password (OTP) Verification (10 pts):** Direct 4-digit numeric match against recipient security token.
- **Tri-Band Triage Rule:**
  - `Score >= 90`: **ACCEPTED** -> Delivery automatically transitions to `DELIVERED`.
  - `70 <= Score < 90`: **NEEDS_MANUAL_REVIEW** -> Delivery transitions to `NEEDS_REVIEW` and routes to Dispatcher Console.
  - `Score < 70`: **DISPUTE** -> Delivery transitions to `DISPUTED` with priority review and dispute logging.
- **Consequences:** Eliminates subjective dispute judgements; couriers delivering indoors with no GPS still receive 75 points and are routed to manual review rather than false dispute accusation.

---

### ADR-03: Append-Only Immutable Audit Trail via Database-Level Trigger
- **Status:** Accepted & Implemented
- **Context:** In dispute arbitrations and legal compliance, audit logs must provide non-repudiation. Application-level logging alone is vulnerable to accidental SQL updates or administrative tampering.
- **Decision:** Implement an `audit_logs` table accompanied by an active PostgreSQL trigger (`audit_log_protect_trg`) that raises an exception on any attempt to execute `UPDATE` or `DELETE` on existing rows.
- **Consequences:**
  - Guarantees true write-once, read-many (WORM) immutability for all logged events.
  - All dispatcher overrides, status transitions, and evidence evaluations are permanently preserved.

---

### ADR-04: Offline-First Client Architecture with Idempotency Keys
- **Status:** Accepted & Implemented
- **Context:** Couriers regularly complete deliveries in elevator lobbies, basements, high-rise concrete corridors, or underground parking structures where cellular connectivity drops completely.
- **Decision:**
  - Store pending evidence locally in the browser/client using **IndexedDB** (`pod_offline_db`).
  - Generate a client-side UUID v4 `idempotency_key` upon evidence creation.
  - Background `SyncManager` watches network status (`navigator.onLine`) and drains the offline queue once reconnected.
  - Backend `/api/v1/evidence/submit` checks `Evidence.idempotency_key`: if an entry with the key exists, it returns the existing evidence without creating duplicate records or double-evaluating scores.
- **Consequences:** Seamless courier user experience without data loss or duplicate delivery confirmations.

---

### ADR-05: Controlled Human-in-the-Loop Dispatcher Override Workflow
- **Status:** Accepted & Implemented
- **Context:** Edge cases (severe weather, network outages, elderly customers unable to sign) require human discretion, but unconstrained overrides lead to corruption and lack of accountability.
- **Decision:** Restrict status overrides to authenticated Dispatcher and Admin roles via `/api/v1/dispatcher/overrides`. Require an explicit `reason_code` (from a validated enum: `CUSTOMER_CONFIRMED_RECEIPT`, `GPS_UNAVAILABLE`, `NETWORK_FAILURE`, `SIGNATURE_UNAVAILABLE`, `EVIDENCE_EXCEPTION`, `OPERATIONAL_EXCEPTION`, `OTHER`). If `OTHER` is selected, enforce a minimum 10-character descriptive justification. Automatically commit an `AuditLog` entry for every override.
- **Consequences:** Balances operational flexibility with complete audit accountability.

---

## Part 2: Incremental Milestone Changelog

### Phase 0: System Inception & Problem Formulation
- Formulated project scope focusing on last-mile food delivery coordination between Restaurants, Riders, and Customers.
- Identified research gaps in current commercial delivery apps: lack of real-time image validation, unverified geofencing, absence of multi-factor scoring, and brittle offline handling.

### Phase 1: Requirements Engineering & Database Design
- Formulated IEEE-compliant Software Requirements Specification (SRS):
  - 26 Functional Requirements (`FR-01` to `FR-26`).
  - 10 Non-Functional Requirements (`NFR-01` to `NFR-10`).
  - 9 Business Rules (`BR-01` to `BR-09`).
- Designed relational schema in Third Normal Form (3NF) comprising 10 domain entities:
  `users`, `restaurants`, `riders`, `customers`, `orders`, `deliveries`, `evidence`, `disputes`, `dispatcher_overrides`, `audit_logs`, `sync_queue_items`.
- Established database indexes on `delivery_id`, `idempotency_key`, and `created_at` for high-performance querying.

### Phase 2: Core Backend Engine & Scoring Implementation
- Developed FastAPI modular backend with clean architecture: `routers`, `models`, `schemas`, `services`, `core`.
- Implemented `opencv_validator.py` with Laplacian variance for image blur detection and mean intensity for lighting checks.
- Implemented `haversine.py` for high-precision spherical distance calculation between coordinates.
- Implemented `quality_engine.py` evaluating the multi-factor rubric and tri-band classification.
- Implemented role-based access control (RBAC) with JWT bearer tokens across 5 distinct roles (`admin`, `dispatcher`, `rider`, `restaurant`, `customer`).

### Phase 3: Frontend PWA & Offline Engine
- Developed responsive client interface using React 19, TypeScript, and TailwindCSS.
- Integrated HTML5 canvas for high-fidelity recipient signatures.
- Implemented client-side IndexedDB persistence and `SyncManager` for offline storage and reconnection synchronization.
- Built dedicated role workspaces: Courier Delivery Hub, Recipient Tracking View, Dispatcher Queue, and Admin Analytics Console.

### Phase 4: Review-1 Feedback & Evaluation Hardening (Current Release)
- **Real Benchmark Experiment Seeding:** Seeded `RUN-BENCHMARK-01` on database initialization with 50 realistic test scenarios evaluated under both baseline and proposed systems.
- **Dashboard Metric Integration:** Integrated **Evidence Completeness** and **Disputes Resolved** metrics into the dashboard KPI comparison grid.
- **Stakeholder Validation Suite:** Seeded cross-role usability questionnaire responses and built an interactive Validation Summary, Limitations Report, and Demo Media Hub.
- **End-to-End Test Suite:** Implemented `tests/test_e2e_scenarios.py` with explicit HTTP-level testing for missing GPS, blurred photo (both review and dispute paths), and offline queue sync with dispatcher override.
- **CI Pipeline:** Added `.github/workflows/ci.yml` running both backend test suites and frontend production builds.
- **Documentation:** Added top-level `README.md` and `docs/DECISIONS_AND_CHANGELOG.md`.
