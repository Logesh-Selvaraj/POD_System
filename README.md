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
- `tests/test_e2e_scenarios.py`: Explicit end-to-end API tests for missing GPS, blurred photos, and offline capture with dispatcher override.
