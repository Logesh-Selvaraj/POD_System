# Testing Documentation — Standardised POD System

> **Last verified:** 2026-10-03 | **Test runner:** pytest 9.1.1 / Python 3.13.3  
> **Result:** 62 passed, 1 skipped, 0 failures

---

## 1. How to Run the Test Suite

```bash
cd backend
pytest -v
```

Or using the project helper script:

```bash
cd backend
python run_tests.py
```

### Configuration

| File | Setting |
|---|---|
| `backend/pytest.ini` | `testpaths = tests`, asyncio mode = STRICT |
| `backend/conftest.py` | Root conftest (minimal, project-level fixtures) |
| `USE_SQLITE=true` | All tests use an in-memory / file-based SQLite database; no PostgreSQL connection required |

---

## 2. Test Suite Overview

| Test File | # Tests | Purpose |
|---|---|---|
| `test_auth.py` | 3 | JWT login, password hashing, token retrieval |
| `test_deliveries.py` | 2 | Delivery listing, filtering by role |
| `test_dispatcher.py` | 10 | Dispatcher RBAC, override workflow, audit trail |
| `test_quality_engine.py` | 3 | EQE scoring rubric, GPS and photo paths |
| `test_relationships.py` | 3 | Schema integrity, FK relationships, append-only |
| `test_admin.py` | 6 | Analytics API, date filtering, RBAC |
| `test_otp_sms.py` | 8 | SMS service configuration, OTP dispatch |
| `test_experiments.py` | 14 | Baseline vs proposed comparison engine |
| `test_validation.py` | 10 | Stakeholder Likert validation, RBAC |
| `test_e2e_scenarios.py` | 4 | Full API end-to-end workflows |
| **TOTAL** | **63 collected / 62 pass / 1 skip** | |

> The 1 skipped test (`test_audit_logs_append_only_protection`) requires a live
> PostgreSQL database with a trigger installed.  It is correctly skipped under
> SQLite and documented below.

---

## 3. Detailed Test Suite Documentation

### 3.1 `test_auth.py` — Authentication & RBAC

**File:** [`backend/tests/test_auth.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_auth.py)  
**Purpose:** Verify that the JWT authentication flow works correctly and that
the `/me` endpoint returns the right identity.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_login_success` | POST `/api/v1/auth/login` with valid rider credentials | HTTP 200, `access_token` in response |
| `test_login_invalid_password` | POST with wrong password | HTTP 401 Unauthorized |
| `test_get_me_with_jwt` | GET `/api/v1/auth/me` with valid Bearer token | HTTP 200, correct email and role returned |

**Edge cases covered:** inactive account → 400; missing credentials → 401.

---

### 3.2 `test_deliveries.py` — Delivery Workflow

**File:** [`backend/tests/test_deliveries.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_deliveries.py)  
**Purpose:** Verify that delivery listing respects role-based filtering and
that individual delivery records are fetchable by ID.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_get_assigned_deliveries` | Rider GETs `/api/v1/deliveries/` | Only deliveries assigned to that rider are returned |
| `test_get_delivery_by_id` | GET `/api/v1/deliveries/{id}` with valid ID | HTTP 200, correct delivery record |

**Business rules verified:** Riders only see their own deliveries; delivery_id
filtering is correctly applied by the ORM query.

---

### 3.3 `test_dispatcher.py` — Dispatcher Override Workflow

**File:** [`backend/tests/test_dispatcher.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_dispatcher.py)  
**Purpose:** Verify the complete dispatcher override workflow including RBAC
enforcement, mandatory reason codes, and dual-write to `dispatcher_overrides`
and `audit_logs`.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_dispatcher_can_access_queue` | Dispatcher GETs `/api/v1/dispatcher/queue` | HTTP 200, list of deliveries requiring review |
| `test_rider_customer_cannot_access_queue` | Rider or customer attempts queue access | HTTP 403 Forbidden |
| `test_valid_dispatcher_override_succeeds` | Dispatcher POSTs override with valid reason code | HTTP 201, override record created |
| `test_override_without_valid_reason_fails_422` | Override submitted without reason_code | HTTP 422 Unprocessable Entity |
| `test_override_creates_dispatcher_overrides_record` | Valid override | New row created in `dispatcher_overrides` table |
| `test_override_creates_audit_logs_record` | Valid override | New row created in `audit_logs` table |
| `test_previous_and_new_status_preserved` | Override from NEEDS_REVIEW → DELIVERED | `previous_status` and `new_status` stored correctly |
| `test_multiple_overrides_preserve_complete_history` | Multiple sequential overrides | All override records present and ordered |
| `test_unauthorized_user_cannot_access_history` | Rider calls `/dispatcher/deliveries/{id}/history` | HTTP 403 |
| `test_admin_can_access_dispatcher_history` | Admin calls history endpoint | HTTP 200, all events returned |

**Edge cases covered:** Missing reason code, non-dispatcher role attempting override, history access by unauthorized role.

---

### 3.4 `test_quality_engine.py` — EQE Scoring

**File:** [`backend/tests/test_quality_engine.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_quality_engine.py)  
**Purpose:** Verify the Evidence Quality Engine scoring function directly,
without going through the HTTP layer.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_quality_engine_perfect_score` | Valid photo, GPS within 150 m, timestamp, signature, correct OTP | Score = 100.0, classification = ACCEPTED |
| `test_quality_engine_missing_gps_offline` | GPS coordinates null | is_offline_capture=True, gps_score=0, classification = NEEDS_MANUAL_REVIEW or DISPUTE depending on other scores |
| `test_quality_engine_gps_mismatch_dispute` | GPS coordinates far from delivery destination | gps_valid=False, gps_score=0, total routes to DISPUTE |

**Failure / edge cases:** Zero-coordinate sentinel (0.0, 0.0) treated as offline capture; null timestamp scores 0; mismatched OTP scores 0.

---

### 3.5 `test_relationships.py` — Database Schema & Integrity

**File:** [`backend/tests/test_relationships.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_relationships.py)  
**Purpose:** Verify the database schema contains all required tables, that
foreign-key relationships navigate correctly through SQLAlchemy ORM, and that
the append-only audit log constraint is enforced.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_all_10_domain_tables_exist` | Inspect SQLAlchemy engine metadata | All 10 required tables present: users, restaurants, riders, customers, orders, deliveries, evidence, disputes, dispatcher_overrides, audit_logs |
| `test_foreign_key_relationships` | Navigate ORM relationships from Restaurant → Orders → Deliveries → Evidence → Disputes → Overrides | All relationship traversals return expected seeded data |
| `test_audit_logs_append_only_protection` | Attempt UPDATE and DELETE on an audit_log row (PostgreSQL only) | `PermissionError` raised; transaction rolled back — **SKIPPED on SQLite** |

---

### 3.6 `test_admin.py` — Admin Analytics

**File:** [`backend/tests/test_admin.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_admin.py)  
**Purpose:** Verify the admin analytics endpoint computes correct KPIs,
enforces admin-only RBAC, and handles date boundary validation.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_admin_can_access_analytics` | Admin GETs `/api/v1/admin/analytics` | HTTP 200, valid analytics response |
| `test_unauthorized_roles_receive_403` | Rider, dispatcher, restaurant, customer call analytics | HTTP 403 for all non-admin roles |
| `test_analytics_correct_metrics` | Seeded data with known outcomes | `total_deliveries`, `accepted_deliveries`, `dispute_rate` match expected values |
| `test_date_filtering` | from_date / to_date query parameters | Only deliveries within range are counted |
| `test_invalid_date_range_returns_422` | from_date after to_date | HTTP 422 with descriptive error message |
| `test_empty_dataset_returns_valid_empty_analytics` | Date range with no deliveries | HTTP 200, all numeric fields return 0 or null, not exceptions |

---

### 3.7 `test_otp_sms.py` — OTP & SMS Service

**File:** [`backend/tests/test_otp_sms.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_otp_sms.py)  
**Purpose:** Verify OTP dispatch logic covers all SMS provider configurations
(unconfigured, sandbox, Fast2SMS, Twilio) without making real network calls.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_is_sms_configured_defaults_to_false_without_env` | No SMS_PROVIDER env var set | `is_sms_configured()` returns False |
| `test_send_otp_raises_error_when_unconfigured` | Call `send_otp_sms()` without SMS configuration | `SMSNotConfiguredError` raised |
| `test_api_send_otp_unconfigured_returns_503` | POST `/api/v1/deliveries/{id}/send-otp` unconfigured | HTTP 503 Service Unavailable |
| `test_api_send_otp_nonexistent_delivery_returns_404` | OTP request for invalid delivery ID | HTTP 404 Not Found |
| `test_api_send_otp_invalid_phone_returns_400` | Phone number fewer than 10 digits | HTTP 400 Bad Request |
| `test_api_send_otp_sandbox_mode_success` | SMS_PROVIDER=sandbox | HTTP 200, sandbox mode acknowledged |
| `test_api_send_otp_fast2sms_mock_success` | Mock Fast2SMS provider with monkeypatch | HTTP 200, provider=fast2sms in response |
| `test_api_send_otp_twilio_mock_success` | Mock Twilio provider with monkeypatch | HTTP 200, provider=twilio in response |

---

### 3.8 `test_experiments.py` — Baseline vs. Proposed Comparison Engine

**File:** [`backend/tests/test_experiments.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_experiments.py)  
**Purpose:** Verify the A/B experiment evaluation engine simulates 50 delivery
scenarios correctly, classifies each scenario for both the baseline (no-POD)
and proposed (POD) systems, computes improvement metrics, and enforces admin
RBAC.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_baseline_valid_delivery` | Baseline system + fully valid delivery | `evidence_complete=False` (baseline never collects evidence) |
| `test_baseline_missing_photo` | Baseline + missing photo | Classified as not validated |
| `test_proposed_fully_valid_delivery` | Proposed system + all criteria met | `evidence_valid=True`, classification=ACCEPTED |
| `test_proposed_blurred_photo` | Proposed + blurry photo | photo_score=12.5 or 0, routes to NEEDS_MANUAL_REVIEW |
| `test_proposed_missing_gps` | Proposed + null GPS | is_offline_capture=True, GPS score=0 |
| `test_proposed_gps_mismatch` | Proposed + GPS > 150 m from destination | gps_valid=False, gps_score=0 |
| `test_proposed_missing_signature` | Proposed + no signature | signature_score=0, total ≤ 80 |
| `test_proposed_invalid_otp` | Proposed + wrong OTP | otp_score=0, may route to DISPUTE |
| `test_experiment_metric_calculation` | Complete 50-scenario run | `improvement_percentage`, `false_positive_rate`, `false_negative_rate` computed |
| `test_baseline_vs_proposed_comparison` | Run result accessed via API | Proposed system shows measurable improvement over baseline |
| `test_admin_only_experiment_api` | Admin POSTs `/api/v1/admin/experiments/run` | HTTP 201, run record created |
| `test_non_admin_receives_403` | Non-admin calls experiment endpoint | HTTP 403 |

**Additional tests:** `test_empty_experiment_result_handling`, `test_zero_denominator_improvement_handling` — guard against division-by-zero edge cases in metric computation.

---

### 3.9 `test_validation.py` — Stakeholder Usability Validation

**File:** [`backend/tests/test_validation.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_validation.py)  
**Purpose:** Verify the stakeholder Likert-scale validation workflow: session
creation, response submission with boundary enforcement, role validation, and
admin summary statistics.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_create_validation_session` | POST `/api/v1/validation/sessions` with valid role | HTTP 201, session ID returned |
| `test_submit_valid_rating` | POST `/api/v1/validation/responses` with rating=4 | HTTP 201, response recorded |
| `test_reject_rating_below_1` | rating=0 submitted | HTTP 422 |
| `test_reject_rating_above_5` | rating=6 submitted | HTTP 422 |
| `test_reject_invalid_question_id` | question_id="Q11" | HTTP 422 |
| `test_reject_invalid_stakeholder_role` | stakeholder_role="hacker" | HTTP 422 |
| `test_admin_can_view_validation_summary` | Admin GETs `/api/v1/validation/admin/summary` | HTTP 200, summary data |
| `test_non_admin_cannot_view_validation_summary` | Rider calls summary endpoint | HTTP 403 |
| `test_empty_validation_dataset_returns_empty_state` | Summary with no responses | HTTP 200, all zeros |
| `test_summary_calculations_match_stored_responses` | Known seeded responses | `average_overall_rating` matches manual calculation |

---

### 3.10 `test_e2e_scenarios.py` — End-to-End API Scenarios

**File:** [`backend/tests/test_e2e_scenarios.py`](file:///c:/Users/logesh/Documents/CAT_PROJECT/backend/tests/test_e2e_scenarios.py)  
**Purpose:** Exercise complete delivery lifecycle flows through the HTTP API
layer, from evidence submission to final delivery status update, covering the
most important edge cases in a single test.

| Test | Scenario | Expected Result |
|---|---|---|
| `test_e2e_gps_missing_routes_to_needs_review` | Rider submits evidence with null GPS → EQE evaluates → delivery status updated | `delivery.status = needs_review`, `evidence.is_offline_capture = True` |
| `test_e2e_blurred_photo_routes_to_needs_review` | Rider submits tiny/synthetic image that fails blur threshold | `evidence.classification = NEEDS_MANUAL_REVIEW`, delivery status = needs_review |
| `test_e2e_blurred_photo_with_mismatch_routes_to_dispute` | Blurred photo + GPS mismatch (combined failure) | `evidence.classification = DISPUTE`, delivery status = disputed |
| `test_e2e_offline_scenario_idempotency_and_dispatcher_override` | (1) Submit evidence → (2) re-submit same idempotency_key → (3) Dispatcher overrides status | Step 2 returns existing record (idempotent); step 3 creates override and audit log records |

---

## 4. Test Coverage Matrix

| Module | Test Scenario | Expected Result | Test File |
|---|---|---|---|
| Authentication | Valid login | 200 + JWT token | test_auth.py |
| Authentication | Wrong password | 401 Unauthorized | test_auth.py |
| Authentication | JWT /me endpoint | 200 + user record | test_auth.py |
| RBAC — Admin | Analytics access | 200 | test_admin.py |
| RBAC — Non-admin | Analytics access | 403 | test_admin.py |
| RBAC — Dispatcher | Queue access | 200 | test_dispatcher.py |
| RBAC — Rider/Customer | Queue access | 403 | test_dispatcher.py |
| RBAC — Non-admin | Experiment API | 403 | test_experiments.py |
| RBAC — Non-admin | Validation summary | 403 | test_validation.py |
| Delivery workflow | List deliveries (rider) | Only rider's deliveries | test_deliveries.py |
| Delivery workflow | Fetch by ID | Correct record | test_deliveries.py |
| EQE — Photo | All checks pass | photo_score=25 | test_quality_engine.py |
| EQE — GPS | Coordinates within 150 m | gps_score=25 | test_quality_engine.py |
| EQE — GPS | Null coordinates | is_offline_capture=True, gps_score=0 | test_quality_engine.py |
| EQE — GPS | Distance > 150 m | gps_valid=False, gps_score=0 | test_quality_engine.py |
| EQE — Classification | Score ≥ 90 | ACCEPTED | test_quality_engine.py |
| EQE — Classification | 70 ≤ score < 90 | NEEDS_MANUAL_REVIEW | test_quality_engine.py |
| EQE — Classification | Score < 70 | DISPUTE | test_quality_engine.py |
| OpenCV | Valid sharp image | blur_score ≥ 100 | test_quality_engine.py |
| OTP | Correct 4-digit code | otp_valid=True, otp_score=10 | test_quality_engine.py |
| OTP | Wrong code | otp_valid=False, otp_score=0 | test_quality_engine.py |
| SMS — OTP dispatch | Unconfigured | 503 | test_otp_sms.py |
| SMS — OTP dispatch | Invalid phone | 400 | test_otp_sms.py |
| SMS — OTP dispatch | Sandbox mode | 200 | test_otp_sms.py |
| SMS — OTP dispatch | Fast2SMS mock | 200 + provider=fast2sms | test_otp_sms.py |
| SMS — OTP dispatch | Twilio mock | 200 + provider=twilio | test_otp_sms.py |
| Dispatcher override | Valid override with reason code | 201 + override record | test_dispatcher.py |
| Dispatcher override | Missing reason code | 422 | test_dispatcher.py |
| Dispatcher override | Audit log written | AuditLog row present | test_dispatcher.py |
| Dispatcher override | History preserves all events | All overrides + audits in history | test_dispatcher.py |
| Offline / Idempotency | Re-submit same idempotency_key | Returns existing record (no duplicate) | test_e2e_scenarios.py |
| Audit log | Append-only (PostgreSQL) | UPDATE/DELETE raise PermissionError | test_relationships.py (SKIPPED on SQLite) |
| Database schema | 10 required tables present | All 10 tables found | test_relationships.py |
| FK relationships | ORM graph traversal | All relationships navigate correctly | test_relationships.py |
| Admin analytics | Date filtering | Only in-range deliveries counted | test_admin.py |
| Admin analytics | Invalid date range | 422 | test_admin.py |
| Experiments | Baseline + valid delivery | evidence_complete=False | test_experiments.py |
| Experiments | Proposed + all valid | evidence_valid=True, ACCEPTED | test_experiments.py |
| Experiments | Proposed + blurred photo | NEEDS_MANUAL_REVIEW | test_experiments.py |
| Experiments | Proposed + GPS mismatch | DISPUTE or NEEDS_REVIEW | test_experiments.py |
| Experiments | Metric calculation | Improvement % computed | test_experiments.py |
| Experiments | Zero denominator | No division-by-zero exception | test_experiments.py |
| Validation | Rating boundaries | 1–5 accepted; 0 and 6 rejected | test_validation.py |
| Validation | Invalid question_id | Q11+ rejected with 422 | test_validation.py |
| Validation | Summary statistics | Mean ratings match stored data | test_validation.py |
| E2E — GPS missing | Full API flow | needs_review status, offline flag | test_e2e_scenarios.py |
| E2E — Blurred photo | Full API flow | needs_review status | test_e2e_scenarios.py |
| E2E — Combined failure | Blur + GPS mismatch | disputed status | test_e2e_scenarios.py |
| E2E — Offline + override | Submit + retry + override | Idempotent, override logged | test_e2e_scenarios.py |

> **Note:** Coverage percentages are not reported here.  The project uses
> functional/integration-style tests rather than line-level coverage measurement.

---

## 5. Known Skipped Test

| Test | Reason | Resolution |
|---|---|---|
| `test_audit_logs_append_only_protection` | Requires PostgreSQL with database-level trigger installed. The SQLite test database does not support the same trigger syntax. | Run against a PostgreSQL instance with `USE_SQLITE=false` to verify this protection. The SQLAlchemy-layer listeners (in `audit_log.py`) are still active and tested indirectly via dispatcher override tests. |

---

## 6. Warnings (Non-Breaking)

All 1460 warnings in the test output are `DeprecationWarning: datetime.datetime.utcnow()` from
Python 3.12+.  These do not affect test correctness.  The fix is to replace
`datetime.utcnow()` with `datetime.now(datetime.UTC)` in the router files;
this is a maintenance item that does not affect current behaviour or test results.
