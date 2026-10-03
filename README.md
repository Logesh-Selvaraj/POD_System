# Standardised Proof-of-Delivery (POD) System with Evidence-Quality Checks

> **Food-Delivery Service Coordinating Restaurants, Riders, and Customers**  
> *Academic Engineering Project — Review 1: Planning, Requirements Engineering, Architecture & Core Verification*

[![CI](https://github.com/Logesh-Selvaraj/POD_System/actions/workflows/ci.yml/badge.svg)](https://github.com/Logesh-Selvaraj/POD_System/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19+-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9+-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL / SQLite](https://img.shields.io/badge/Database-PostgreSQL%20%7C%20SQLite-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 1. Project Overview

The **Standardised Proof-of-Delivery (POD) System** is a mission-critical platform designed to solve delivery confirmation ambiguity, fraudulent disputes, and lack of accountability in modern on-demand food delivery platforms.

In current commercial solutions, delivery confirmation is treated as an unverified single action—often a courier clicking a button or uploading a blurred, black, or irrelevant photo. The Standardised POD System transforms delivery confirmation into an explainable, multi-factor decision pipeline governed by an automated **Evidence Quality Engine (EQE)**:

1. **Multi-Factor Evidence Capture**:
   - High-resolution camera photograph with computer vision blur/brightness validation (OpenCV Laplacian variance).
   - Real-time device GPS coordinates verified against delivery destination geofence using the Haversine formula (≤ 150m threshold).
   - Recipient digital signature captured via HTML5 canvas.
   - Dynamic 4-digit recipient One-Time Password (OTP) verification.
   - Tamper-evident capture timestamps.
2. **Automated Evidence Quality Engine (EQE)**:
   - Scored on an objective **0–100 point rubric**: Photo (25 pts), GPS (25 pts), Timestamp (20 pts), Signature (20 pts), OTP (10 pts).
   - Deterministic tri-band triage:
     - **ACCEPTED** (Score ≥ 90): Instant automated completion.
     - **NEEDS MANUAL REVIEW** (Score 70–89): Routed to Dispatcher Queue (e.g. valid delivery with indoor GPS loss or minor blur).
     - **DISPUTE** (Score < 70): Flagged for investigation and dispute resolution.
3. **Offline-First Resilience**:
   - Progressive Web App (PWA) client with local IndexedDB queue for zero-connectivity environments (basements, elevators, underground parking).
   - Background Synchronization Manager with cryptographic idempotency keys preventing duplicate submissions.
4. **Controlled Human-in-the-Loop Override Workflow**:
   - Dedicated Dispatcher Workspace allowing manual status overrides with mandatory justification and reason codes.
5. **Append-Only Immutable Audit Trail**:
   - Complete state transitions, evaluations, and dispatcher actions recorded with database-level triggers preventing modification or deletion.

---

## 2. System Architecture

```
                                +-------------------------------------------+
                                |      Progressive Web App (React / TS)     |
                                |  - Courier Camera & Signature Canvas      |
                                |  - Customer Tracking & Dispute Raising    |
                                |  - Dispatcher Console & Admin Analytics   |
                                |  - IndexedDB Local Storage Queue          |
                                +---------------------+---------------------+
                                                      | HTTP / REST (JWT Auth)
                                                      v
                                +-------------------------------------------+
                                |          FastAPI Backend Service          |
                                |  - RBAC Security & Auth (JWT)             |
                                |  - Order & Delivery Lifecycle Routers     |
                                |  - Evidence Upload & S3/Local Storage     |
                                |  - Evidence Quality Engine (EQE)          |
                                |  - Dispatcher Override & Dispute Engine   |
                                |  - Experiment & Evaluation Service        |
                                |  - Stakeholder Validation API             |
                                +---------------------+---------------------+
                                                      | SQLAlchemy ORM
                                                      v
                                +-------------------------------------------+
                                |           Relational Database             |
                                |  - SQLite (Dev/Test) / PostgreSQL (Prod)  |
                                |  - 10 Domain Tables (3NF Schema)          |
                                |  - Append-Only Audit Log Triggers         |
                                +-------------------------------------------+
```

---

## 3. Quick Start (Automated Single Command)

Start both FastAPI backend and Vite frontend together with one command from the project root:

```bash
npm run dev
```

This concurrently starts:
- **Backend Service (FastAPI / Uvicorn)**: `http://localhost:8000/` (Swagger Docs: `http://localhost:8000/docs`)
- **Frontend PWA (React / Vite)**: `http://localhost:3000/`

You can also run services independently:
- Backend only: `npm run dev:backend`
- Frontend only: `npm run dev:frontend`

---

## 4. Backend Setup & Run (Manual / Standalone)

### Prerequisites
- Python 3.11, 3.12, or 3.13
- `pip` package manager
- (Optional) PostgreSQL 14+ for production environments (SQLite is used out-of-the-box for development and testing)

### Installation Steps

1. **Navigate to the backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**:
   Create a `.env` file or copy from `.env.example`:
   ```bash
   cp .env.example .env
   ```
   *Default `.env` settings:*
   ```ini
   SECRET_KEY=pod-super-secret-jwt-key-2026-secure-change-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=480
   USE_SQLITE=true
   DATABASE_URL=sqlite:///./pod_system.db
   LOCAL_STORAGE_DIR=./uploaded_evidence
   OPENCV_BLUR_THRESHOLD=100.0
   GPS_MISMATCH_THRESHOLD_METERS=150.0
   ```

5. **Initialize & Seed Database**:
   ```bash
   python -m app.init_db
   ```
   This creates all 10 domain tables and seeds base users, restaurants, riders, customers, initial orders, deliveries, real experiment benchmark run `RUN-BENCHMARK-01`, and stakeholder validation responses.

6. **Start the Backend Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
   - API Root: `http://localhost:8000/`
   - Interactive Swagger API Documentation: `http://localhost:8000/docs`
   - ReDoc Documentation: `http://localhost:8000/redoc`

7. **Run the Automated Test Suite**:
   ```bash
   python run_tests.py
   ```
   Runs all 9 test suites across authentication, deliveries, dispatcher, quality engine, relationships, admin, experiments, stakeholder validation, and end-to-end scenarios.

---

## 5. Frontend Setup & Run (Manual / Standalone)

### Prerequisites
- Node.js 18+ or 20+
- `npm` (Node Package Manager)

### Installation Steps

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node dependencies**:
   ```bash
   npm install
   ```

3. **Run Development Server**:
   ```bash
   npm run dev
   ```
   Opens Vite dev server at `http://localhost:3000/` (with API proxy automatically forwarding `/api` and `/static` calls to `http://localhost:8000`).

4. **Production Build & Verification**:
   ```bash
   npm run build
   ```
   Runs TypeScript type checking and generates the production PWA bundle in `dist/`.

---

## 6. Demo Credentials

The seeded database contains ready-to-use accounts for all 5 system roles:

| Role | Email | Password | Primary Workspace / Dashboard |
|---|---|---|---|
| **Administrator** | `admin@pod.com` | `admin123` | System Analytics, Real Benchmark Experiments, Stakeholder Usability Summary, Full Audit Trail |
| **Dispatcher** | `dispatcher@pod.com` | `dispatcher123` | Dispatcher Console, Needs Review & Dispute Queue, Override Dialog with Reason Codes |
| **Rider (Courier)** | `rider@pod.com` | `rider123` | Assigned Deliveries, Multi-Factor Camera / GPS / Signature / OTP Capture, Offline PWA Synch |
| **Restaurant Owner** | `restaurant@pod.com` | `restaurant123` | Order Creation, Courier Assignment, Real-Time Delivery Tracking |
| **Customer (Recipient)** | `customer@pod.com` | `customer123` | Order Tracking, Recipient OTP Confirmation, Dispute Filing |

---

## 7. Review 1 Academic Deliverables

All Review-1 academic documents, diagrams, slide decks, and data sheets are organized in the repository:

| Deliverable | File Path | Description |
|---|---|---|
| **Academic Project Report (Full)** | [`REVIEW_1_PROJECT_REPORT.md`](file:///c:/Users/logesh/Documents/CAT_PROJECT/REVIEW_1_PROJECT_REPORT.md) / [`review_1/Review_1_Project_Report.docx`](file:///c:/Users/logesh/Documents/CAT_PROJECT/review_1/Review_1_Project_Report.docx) | Comprehensive 800+ line academic report covering Abstract, Literature Survey, 3NF Data Dictionary, Architecture, and Testing. |
| **Software Requirements Specification (SRS)** | [`review_1/SRS_Proof_of_Delivery_System.docx`](file:///c:/Users/logesh/Documents/CAT_PROJECT/review_1/SRS_Proof_of_Delivery_System.docx) | IEEE-compliant SRS document detailing FR-01 to FR-26, NFR-01 to NFR-10, and Business Rules BR-01 to BR-09. |
| **Literature Survey Document** | [`review_1/Literature_Survey_POD_Project.docx`](file:///c:/Users/logesh/Documents/CAT_PROJECT/review_1/Literature_Survey_POD_Project.docx) | Critical analysis of existing patents, academic papers on sensor fusion, geofencing, and last-mile logistics. |
| **System Architecture Diagram** | [`review_1/System_Architecture_Diagram.png`](file:///c:/Users/logesh/Documents/CAT_PROJECT/review_1/System_Architecture_Diagram.png) | High-resolution diagram illustrating Client PWA, FastAPI Service, EQE, and Append-Only Data Store layers. |
| **Entity Relationship Diagram (ERD)** | [`review_1/ER_Diagram.png`](file:///c:/Users/logesh/Documents/CAT_PROJECT/review_1/ER_Diagram.png) | Detailed Crow's Foot ER diagram showing all 10 domain entities in Third Normal Form (3NF). |
| **UI Wireframes & Screen Flow** | [`review_1/UI_Wireframes.png`](file:///c:/Users/logesh/Documents/CAT_PROJECT/review_1/UI_Wireframes.png) | Visual layouts for Courier Capture, Recipient Tracking, Dispatcher Workspace, and Admin Analytics. |
| **Presentation Slide Deck** | [`review_1/Proof_of_Delivery_Review1.pptx`](file:///c:/Users/logesh/Documents/CAT_PROJECT/review_1/Proof_of_Delivery_Review1.pptx) | Review 1 presentation slides detailing problem context, proposed innovation, architecture, and prototype validation. |
| **Incremental Decisions & Changelog** | [`docs/DECISIONS_AND_CHANGELOG.md`](file:///c:/Users/logesh/Documents/CAT_PROJECT/docs/DECISIONS_AND_CHANGELOG.md) | Architectural Decision Records (ADRs) and incremental engineering changelog. |

---

## 7. Quality Assurance & Automated Testing

The backend test suite verifies core scoring algorithms, database integrity, role-based security, and operational edge cases:

```bash
cd backend
python run_tests.py
```

### Test Suites (49+ Automated Tests)
- `tests/test_auth.py`: JWT generation, password hashing (bcrypt), token expiration, role enforcement.
- `tests/test_deliveries.py`: Delivery status querying, courier assignment filtering, delivery detail lookups.
- `tests/test_dispatcher.py`: Queue filtering, override authorization, mandatory reason codes, immutable audit logging.
- `tests/test_quality_engine.py`: Scoring rubric (0–100), OpenCV blur detection, Haversine geofence calculations.
- `tests/test_relationships.py`: 10-table schema existence, foreign key integrity, append-only trigger protection.
- `tests/test_admin.py`: Analytics KPI aggregations, component rating distributions, date boundary validation.
- `tests/test_experiments.py`: 50-scenario baseline vs. proposed comparison evaluation engine and metric generation.
- `tests/test_validation.py`: Stakeholder Likert scoring, role validation, session tracking, summary statistics.
- `tests/test_otp_sms.py`: OTP SMS dispatch, sandbox/provider configuration, phone number validation.
- `tests/test_e2e_scenarios.py`: Explicit end-to-end API tests for missing GPS, blurred photos, and offline capture with dispatcher override.

For granular per-test documentation, see **[`docs/TESTING.md`](file:///c:/Users/logesh/Documents/CAT_PROJECT/docs/TESTING.md)**.

---

## 8. API Documentation

All endpoints are prefixed with `/api/v1`.  JWT Bearer token authentication is
required on all endpoints unless marked **Public**.

Interactive documentation: `http://localhost:8000/docs`

### Auth

| Method | Path | Purpose | Auth | Roles |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate and receive JWT | Public | — |
| `POST` | `/api/v1/auth/register` | Register a new user account | Public | — |
| `GET` | `/api/v1/auth/me` | Return the currently authenticated user | Bearer JWT | Any |

**Login request body:**
```json
{ "email": "rider@pod.com", "password": "rider123" }
```
**Login response:** `{ "access_token": "...", "token_type": "bearer", "user": { ... } }`

**Error responses:** `401` wrong credentials · `400` inactive account

---

### Deliveries

| Method | Path | Purpose | Auth | Roles |
|---|---|---|---|---|
| `POST` | `/api/v1/deliveries/` | Create a new delivery | Bearer JWT | restaurant, admin |
| `GET` | `/api/v1/deliveries/` | List deliveries (role-filtered) | Bearer JWT | Any |
| `GET` | `/api/v1/deliveries/assigned` | List deliveries assigned to current rider | Bearer JWT | rider, admin |
| `GET` | `/api/v1/deliveries/{delivery_id}` | Fetch a single delivery by ID | Bearer JWT | Any |
| `POST` | `/api/v1/deliveries/{delivery_id}/send-otp` | Dispatch OTP SMS to customer | Bearer JWT | Any |
| `PATCH` | `/api/v1/deliveries/{delivery_id}/status` | Update delivery status | Bearer JWT | Any |
| `DELETE` | `/api/v1/deliveries/{delivery_id}` | Delete a delivery | Bearer JWT | restaurant (own), admin, dispatcher |

**Create delivery body:** `id`, `customer_name`, `customer_phone`, `delivery_address`, `target_latitude`, `target_longitude`, `otp_code`, `rider_id` (optional), `customer_id` (optional)

**Status update body:** `{ "status": "delivered", "reason_code": "...", "reason_text": "..." }`

**Error responses:** `400` duplicate ID · `403` ownership · `404` not found · `422` validation · `503` SMS unconfigured · `502` SMS send failure

---

### Evidence

| Method | Path | Purpose | Auth | Roles |
|---|---|---|---|---|
| `POST` | `/api/v1/evidence/submit` | Submit delivery evidence (multipart/form-data) | Bearer JWT | rider, admin |
| `GET` | `/api/v1/evidence/{delivery_id}` | Fetch evidence record for a delivery | Bearer JWT | Any |

**Submit evidence form fields:** `delivery_id` (required), `idempotency_key` (required), `photo` (file, required), `captured_latitude` (optional float), `captured_longitude` (optional float), `captured_timestamp` (optional ISO-8601 string), `otp_entered` (optional string), `signature_base64` (optional string)

**Submit response:** Full evidence record including all EQE scores (`photo_score`, `gps_score`, `timestamp_score`, `signature_score`, `otp_score`, `total_quality_score`, `classification`).

**Idempotency:** Re-submitting the same `idempotency_key` returns the existing record (no duplicate created).

**Error responses:** `404` delivery not found · `403` wrong role

---

### Dispatcher

| Method | Path | Purpose | Auth | Roles |
|---|---|---|---|---|
| `GET` | `/api/v1/dispatcher/queue` | Return deliveries requiring manual review | Bearer JWT | dispatcher, admin |
| `POST` | `/api/v1/dispatcher/overrides` | Create a dispatcher override | Bearer JWT | dispatcher, admin |
| `GET` | `/api/v1/dispatcher/deliveries/{delivery_id}/history` | Full event history for a delivery | Bearer JWT | dispatcher, admin |

**Override request body:**
```json
{
  "delivery_id": "DEL-1003",
  "new_status": "delivered",
  "reason_code": "BLURRY_PHOTO_VALIDATED",
  "reason_text": "Customer confirmed receipt in person"
}
```
**Override response:** New `DispatcherOverride` record. Also writes an `AuditLog` entry.

**History response:** Chronologically sorted list of `OVERRIDE`, `AUDIT`, and `DISPUTE` events.

**Error responses:** `400` disallowed status transition · `403` wrong role · `404` delivery not found · `422` missing reason_code

---

### Admin

| Method | Path | Purpose | Auth | Roles |
|---|---|---|---|---|
| `GET` | `/api/v1/admin/analytics` | System-wide KPI analytics | Bearer JWT | admin |

**Query parameters:** `from_date` (YYYY-MM-DD), `to_date` (YYYY-MM-DD)

**Response fields:** `total_deliveries`, `accepted_deliveries`, `manual_review_deliveries`, `disputed_deliveries`, `average_evidence_score`, `dispute_rate`, `evidence_acceptance_rate`, `offline_capture_count`, `gps_failure_count`, `status_distribution`, `evidence_score_distribution`, `daily_delivery_counts`, `rider_performance`, `evidence_component_performance`, `dispute_analytics`

**Error responses:** `403` non-admin · `422` invalid date format or range

---

### Admin Experiments

| Method | Path | Purpose | Auth | Roles |
|---|---|---|---|---|
| `GET` | `/api/v1/admin/experiments` | List all experiment runs | Bearer JWT | admin |
| `GET` | `/api/v1/admin/experiments/{run_id}` | Fetch detailed results for one run | Bearer JWT | admin |
| `POST` | `/api/v1/admin/experiments/run` | Trigger a new 50-scenario benchmark run | Bearer JWT | admin |

**Run response fields:** `id`, `name`, `dataset_size`, `baseline_description`, `proposed_system_description`, `created_at`, `completed_at`, plus nested `results` array.

**Detail response:** Includes per-scenario breakdown (`evidence_complete`, `evidence_valid`, `false_positive`, `false_negative`, `final_classification`) and aggregate metrics (`improvement_percentage`, `false_positive_rate`, `false_negative_rate`).

**Error responses:** `403` non-admin

---

### Stakeholder Validation

| Method | Path | Purpose | Auth | Roles |
|---|---|---|---|---|
| `POST` | `/api/v1/validation/sessions` | Create a new validation session | Public | — |
| `POST` | `/api/v1/validation/responses` | Submit a Likert rating response | Public | — |
| `GET` | `/api/v1/validation/admin/summary` | Aggregated validation statistics | Bearer JWT | admin |
| `GET` | `/api/v1/validation/admin/responses` | All raw validation responses | Bearer JWT | admin |

**Session body:** `{ "participant_code": "P001", "stakeholder_role": "rider", "validation_scenario": "..." }`

**Response body:** `{ "session_id": "uuid", "question_id": "Q1", "rating": 4, "comment": "..." }`

Valid `stakeholder_role` values: `rider`, `dispatcher`, `restaurant`, `customer`

Valid `question_id` values: `Q1` – `Q10`

Valid `rating` values: integer 1–5 (Likert scale)

**Error responses:** `422` invalid role / question_id / rating out of range · `403` non-admin for summary endpoints

---

### Utility Endpoints

| Method | Path | Purpose | Auth |
|---|---|---|---|
| `GET` | `/` | System status and version | Public |
| `GET` | `/health` | Health check | Public |
| `GET` | `/static/uploads/{filename}` | Serve uploaded evidence photos and signatures | Public (URL-gated) |

---

## 9. Database Schema

The system uses **SQLite** in development/testing and **PostgreSQL** in
production.  The ORM layer (SQLAlchemy) is identical for both.

### Relationship Overview

```
users
 ├── deliveries (as restaurant, rider, or customer)
 │    ├── evidence (1:1)
 │    ├── disputes (1:many)
 │    └── dispatcher_overrides (1:many)
 ├── audit_logs (actor)
 └── (Rider profile linked via riders table)

restaurants ──► orders ──► deliveries
customers   ──► orders

experiment_runs ──► experiment_results ──► experiment_cases

stakeholder_validation_sessions ──► stakeholder_validation_responses
```

---

### `users`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | Integer | PK, indexed | Auto-increment user ID |
| `email` | String | UNIQUE, NOT NULL, indexed | Login email |
| `hashed_password` | String | NOT NULL | bcrypt hash |
| `full_name` | String | NOT NULL | Display name |
| `role` | Enum | NOT NULL | `restaurant`, `rider`, `customer`, `dispatcher`, `admin` |
| `is_active` | Boolean | default=True | Soft-disable account |
| `created_at` | DateTime | default=utcnow | Account creation time |

---

### `deliveries`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String | PK, indexed | Human-readable ID e.g. `DEL-1001` |
| `order_id` | String | FK → orders.id, nullable | Associated order (optional) |
| `restaurant_id` | Integer | FK → users.id, NOT NULL | Restaurant that created delivery |
| `rider_id` | Integer | FK → users.id, nullable | Assigned rider |
| `customer_id` | Integer | FK → users.id, nullable | Recipient customer |
| `rider_profile_id` | Integer | FK → riders.id, nullable | Link to riders profile table |
| `customer_name` | String | NOT NULL | Recipient name |
| `customer_phone` | String | NOT NULL | Recipient contact number |
| `delivery_address` | String | NOT NULL | Human-readable drop-off address |
| `target_latitude` | Float | NOT NULL | Drop-off GPS latitude |
| `target_longitude` | Float | NOT NULL | Drop-off GPS longitude |
| `otp_code` | String(6) | NOT NULL | 4-digit verification OTP |
| `status` | Enum | NOT NULL, default=pending | `pending`, `assigned`, `in_transit`, `delivered`, `needs_review`, `disputed` |
| `created_at` | DateTime | default=utcnow | |
| `updated_at` | DateTime | default=utcnow, onupdate | |

---

### `evidence`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String | PK, indexed | UUID |
| `delivery_id` | String | FK → deliveries.id, UNIQUE, NOT NULL | One evidence record per delivery |
| `rider_id` | Integer | FK → users.id, NOT NULL | Rider who submitted |
| `photo_url` | String | NOT NULL | Path/URL to stored photo file |
| `signature_url` | String | nullable | Path/URL to signature image |
| `captured_latitude` | Float | nullable | GPS latitude at capture |
| `captured_longitude` | Float | nullable | GPS longitude at capture |
| `captured_timestamp` | DateTime | NOT NULL | ISO-8601 timestamp from client |
| `is_offline_capture` | Boolean | default=False | True when GPS was null at capture |
| `otp_entered` | String(6) | nullable | OTP submitted by rider |
| `otp_valid` | Boolean | default=False | Whether OTP matched delivery record |
| `distance_m` | Float | nullable | Haversine distance to destination (metres) |
| `gps_valid` | Boolean | default=False | True if distance_m ≤ 150 m |
| `timestamp_valid` | Boolean | default=False | True if timestamp was present |
| `blur_score` | Float | nullable | Laplacian variance (higher = sharper) |
| `brightness_score` | Float | nullable | Mean pixel intensity [0–255] |
| `photo_score` | Float | default=0.0 | EQE score component (max 25) |
| `gps_score` | Float | default=0.0 | EQE score component (max 25) |
| `timestamp_score` | Float | default=0.0 | EQE score component (max 20) |
| `signature_score` | Float | default=0.0 | EQE score component (max 20) |
| `otp_score` | Float | default=0.0 | EQE score component (max 10) |
| `total_quality_score` | Float | default=0.0 | Sum of all components (0–100) |
| `classification` | Enum | NOT NULL | `ACCEPTED`, `NEEDS_MANUAL_REVIEW`, `DISPUTE` |
| `idempotency_key` | String | UNIQUE, indexed, NOT NULL | Client-generated UUID for dedup |
| `created_at` | DateTime | default=utcnow | |

---

### `dispatcher_overrides`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String | PK, indexed | UUID |
| `delivery_id` | String | FK → deliveries.id, NOT NULL | Target delivery |
| `dispatcher_id` | Integer | FK → users.id, NOT NULL | Dispatcher/admin who acted |
| `previous_status` | String | NOT NULL | Status before override |
| `new_status` | String | NOT NULL | Status after override |
| `reason_code` | String | NOT NULL | Machine-readable reason e.g. `BLURRY_PHOTO_VALIDATED` |
| `reason_text` | String | NOT NULL | Human-readable justification |
| `created_at` | DateTime | default=utcnow | |

---

### `audit_logs` (append-only)

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String | PK, indexed | UUID |
| `actor_id` | Integer | FK → users.id, nullable | User who triggered the event |
| `entity_type` | String | NOT NULL | Entity class: `DELIVERY`, `DISPUTE`, etc. |
| `entity_id` | String | NOT NULL | PK of the changed record |
| `action` | String | NOT NULL | Event code e.g. `CREATE_DELIVERY`, `dispatcher_override` |
| `previous_state` | Text | nullable | JSON snapshot before change |
| `new_state` | Text | nullable | JSON snapshot after change |
| `reason` | Text | nullable | Justification text |
| `created_at` | DateTime | default=utcnow | |

> **Append-only:** UPDATE and DELETE are blocked by SQLAlchemy event listeners
> (all environments) and a PostgreSQL trigger (production).

---

### `disputes`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String | PK, indexed | UUID |
| `delivery_id` | String | FK → deliveries.id, NOT NULL | Disputed delivery |
| `raised_by_user_id` | Integer | FK → users.id, NOT NULL | User who raised dispute |
| `reason` | String | NOT NULL | Dispute description |
| `status` | String | NOT NULL, default=OPEN | `OPEN`, `IN_REVIEW`, `RESOLVED_REFUNDED`, `RESOLVED_REJECTED` |
| `resolution_notes` | String | nullable | Resolution outcome notes |
| `created_at` | DateTime | default=utcnow | |
| `resolved_at` | DateTime | nullable | When dispute was closed |

---

### `orders`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | String | PK, indexed | e.g. `ORD-1001` |
| `restaurant_id` | Integer | FK → restaurants.id, NOT NULL | Restaurant that placed order |
| `customer_id` | Integer | FK → customers.id, NOT NULL | Customer who ordered |
| `items_summary` | String | NOT NULL | Free text order summary |
| `total_amount` | Float | NOT NULL | Order value |
| `target_address` | String | NOT NULL | Delivery address |
| `target_latitude` | Float | NOT NULL | GPS latitude |
| `target_longitude` | Float | NOT NULL | GPS longitude |
| `otp_code` | String(6) | NOT NULL | Verification OTP |
| `status` | String | NOT NULL, default=PENDING | `PENDING`, `ASSIGNED`, `COMPLETED`, `DISPUTED` |
| `created_at` | DateTime | default=utcnow | |

---

### `restaurants`, `riders`, `customers`

Profile tables that extend `users` with domain-specific fields.  Each links
back to `users.id` via a one-to-one foreign key.  See [`backend/app/models/`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/app/models/) for full column listings.

---

### Experiment Tables

| Table | Purpose |
|---|---|
| `experiment_runs` | One row per A/B evaluation run |
| `experiment_cases` | 50 pre-defined test scenarios (photo quality, GPS, OTP, etc.) |
| `experiment_results` | Per-scenario outcome for both BASELINE and PROPOSED systems |

---

### Stakeholder Validation Tables

| Table | Purpose |
|---|---|
| `stakeholder_validation_sessions` | One row per usability test participant session |
| `stakeholder_validation_responses` | One row per question (Q1–Q10) per session (Likert 1–5) |

---

## 10. Additional Documentation

| Document | Path | Contents |
|---|---|---|
| Testing Guide | [`docs/TESTING.md`](file:///c:/Users/logesh/Documents/CAT_PROJECT/docs/TESTING.md) | Per-suite test documentation, coverage matrix, skip rationale |
| Error Handling | [`docs/ERROR_HANDLING.md`](file:///c:/Users/logesh/Documents/CAT_PROJECT/docs/ERROR_HANDLING.md) | Error Boundary, frontend patterns, backend error codes |
| Decisions & Changelog | [`docs/DECISIONS_AND_CHANGELOG.md`](file:///c:/Users/logesh/Documents/CAT_PROJECT/docs/DECISIONS_AND_CHANGELOG.md) | Architectural Decision Records |
