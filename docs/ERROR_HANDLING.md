# Error Handling Documentation — Standardised POD System

> This document describes the complete error-handling architecture as it
> exists in the codebase, covering both the frontend React application and the
> FastAPI backend.

---

## 1. Frontend Error Boundary

### Architecture

The application now uses a **React Error Boundary** (`ErrorBoundary.tsx`) at
the root render level in `main.tsx`.  React Error Boundaries are class
components that implement the `getDerivedStateFromError` / `componentDidCatch`
lifecycle pair.  These are the only React mechanisms that can catch errors
thrown during the render, constructor, or lifecycle methods of child
components.

```
main.tsx
└── <ErrorBoundary>          ← top-level catch-all
    └── <StrictMode>
        └── <App />          ← entire application
```

**File:** [`frontend/src/components/ErrorBoundary.tsx`](file:///c:/Users/logesh/Documents/CAT_PROJECT/frontend/src/components/ErrorBoundary.tsx)

### How It Works

| Lifecycle Method | When Called | What It Does |
|---|---|---|
| `getDerivedStateFromError(error)` | During the render phase, after a child throws | Sets `hasError: true`, triggers re-render with fallback UI |
| `componentDidCatch(error, errorInfo)` | During the commit phase | Logs error + React component stack to console; hook point for future monitoring service |

### Fallback UI

When a render error is caught, the user sees a styled recovery screen:

- **"Something went wrong"** heading with a warning icon
- A plain-English message reassuring the user their offline evidence queue is safe
- In **development mode only**: the raw error message is displayed in a code block for rapid diagnosis
- **"Try again"** button — calls `setState({ hasError: false })` to unmount and re-mount the child tree without a page reload
- **"Reload page"** button — calls `window.location.reload()` as the ultimate fallback

### What Error Boundaries Do NOT Catch

Per React's design, Error Boundaries do **not** catch:

- Errors in **event handlers** (these are handled by `try/catch` in App.tsx)
- Errors in **asynchronous code** (fetch, setTimeout) — handled by promise `.catch()` / `try/catch` in async functions
- Errors in **the Error Boundary component itself**
- Server-side rendering errors

---

## 2. Frontend API / Network Error Handling

All API calls in `App.tsx` and `DispatcherWorkspace.tsx` use `axios` wrapped
in `try/catch` blocks.  The error-handling patterns are:

### 2.1 Login Failures

**Function:** `handleRoleLogin` (App.tsx)

| Error | Handling |
|---|---|
| HTTP 401 | `loginError` state set to "Incorrect email or password." displayed in the UI |
| HTTP 4xx with detail | `loginError` set to `err.response.data.detail` |
| Network / unknown | `loginError` set to "Authentication failed. Please check your credentials and server connection." |

### 2.2 Delivery List (Offline Fallback)

**Function:** `fetchDeliveries` (App.tsx)

| Error | Handling |
|---|---|
| Network down / `isOfflineSimulated=true` | Falls back to `getCachedDeliveries()` from IndexedDB immediately, no error displayed |
| API error | `catch` falls back to IndexedDB cached deliveries silently |

The rider always sees delivery data, even with no network.

### 2.3 Evidence Submission

**Function:** `handleEvidenceSubmit` (App.tsx)

This is the most critical error path because it must not silently lose captured evidence.

| Error | Handling |
|---|---|
| OTP not entered | `alert()` + `otpError` state set; form submission blocked |
| OTP wrong length (≠ 4 digits) | `alert()` + `otpError` state set; blocked |
| OTP mismatch (client-side pre-check) | `alert('Invalid OTP')` + `otpError` state set; blocked |
| Photo not provided | `alert('Please capture or upload a delivery photo!')` |
| Offline (`isOfflineSimulated` or `!navigator.onLine`) | Evidence saved directly to IndexedDB via `savePendingEvidence()`; alert confirms offline queue |
| Network error during online submission | `catch` block: saved to IndexedDB via `savePendingEvidence()`; alert: "Network request failed. Saved to offline IndexedDB queue!" |
| HTTP 4xx from server | Same `catch` → IndexedDB fallback (server rejected for business rules) |

**The IndexedDB fallback** ensures no evidence is lost regardless of network
state.  The `SyncManager` will retry uploads automatically when connectivity
returns.

### 2.4 GPS / Geolocation

The application does not use the browser Geolocation API (`navigator.geolocation`).
GPS coordinates are entered manually by the rider via form inputs pre-populated
with the delivery target coordinates, or via the Leaflet map picker component.

A **"Simulate Zero GPS (Offline Capture)"** checkbox sets coordinates to null,
which the backend recognises as an offline capture.  The UI shows a warning
banner when GPS is disabled.

### 2.5 Camera / Photo Permission

Photo capture uses an `<input type="file" accept="image/*" capture="environment">`
element, which delegates permission handling to the browser/OS.  If the user
denies camera permission the file input simply receives no file; the form
validation (`!photoBlob`) triggers an alert before submission.

A **"Use Sample Photo"** button generates a synthetic canvas image, allowing
the Rider flow to be demonstrated without a physical camera.

### 2.6 Evidence Submission Failure (Server-Side)

| HTTP Status | Frontend Behaviour |
|---|---|
| 201 Created | Evidence displayed, delivery status updated in UI |
| 409 Conflict (idempotency_key already exists) | Server returns existing record; treated as success |
| 404 Delivery not found | Falls into `catch` → IndexedDB queue |
| 422 Validation error | Falls into `catch` → IndexedDB queue |
| 500 Internal server error | Falls into `catch` → IndexedDB queue |

### 2.7 Admin Analytics

**Function:** `fetchAnalytics` (App.tsx)

| Error | Handling |
|---|---|
| HTTP 403 | `analyticsError` state set, displayed in UI panel |
| HTTP 422 (invalid date) | Error displayed in analytics panel |
| Network error | `analyticsError` set to error message |

### 2.8 Dispatcher Override Failures (DispatcherWorkspace.tsx)

| Error | Handling |
|---|---|
| Network failure | `catch` sets component error state, displays error in UI |
| HTTP 422 (missing reason) | Error message shown inline |
| HTTP 403 (wrong role) | Error message shown inline |

### 2.9 localStorage Access

`localStorage` reads and writes are wrapped in `try/catch` blocks throughout
`App.tsx`.  Failures (e.g. private browsing in Safari, storage quota exceeded)
are silently ignored so the application continues to function.

---

## 3. Offline Synchronisation Error Handling

**Service:** [`frontend/src/services/syncManager.ts`](file:///c:/Users/logesh/Documents/CAT_PROJECT/frontend/src/services/syncManager.ts)

| Scenario | Handling |
|---|---|
| Sync already in progress | Early return (no-op); `isSyncing` guard prevents race condition |
| Device offline during `flushQueue()` | Early return; item remains in IndexedDB queue |
| Individual item upload fails | `console.error` logged; `failedCount` incremented; other items continue |
| All items successfully uploaded | Items removed from IndexedDB via `removePendingEvidence()` |
| Network event fires while token missing | Sync skipped (requires valid JWT) |

The `isSyncing` lock is released in a `finally` block ensuring it is cleared
even if an unexpected exception propagates out of the loop.

---

## 4. Backend / API Error Handling

The FastAPI backend uses `HTTPException` for all structured error responses.
FastAPI's built-in exception handlers ensure consistent JSON error bodies:

```json
{
  "detail": "Human-readable error description"
}
```

### 4.1 Authentication & RBAC

| Condition | HTTP Status | Detail |
|---|---|---|
| Incorrect credentials | 401 | "Incorrect email or password" |
| Inactive user | 400 | "Inactive user account" |
| Missing / invalid JWT | 401 | FastAPI default OAuth2 error |
| Role not permitted for endpoint | 403 | "Access denied. Required role(s): ..." |

### 4.2 Delivery Endpoints

| Condition | HTTP Status | Detail |
|---|---|---|
| Delivery ID already exists (POST) | 400 | "Delivery with ID {id} already exists" |
| Delivery not found (GET/PATCH/DELETE) | 404 | "Delivery not found" |
| Wrong restaurant deleting delivery | 403 | "Not authorized to delete this delivery" |
| Invalid status value (PATCH) | 422 | FastAPI validation error |

### 4.3 Evidence Submission

| Condition | HTTP Status | Detail |
|---|---|---|
| Delivery not found | 404 | "Delivery not found" |
| Duplicate idempotency_key | — | Returns existing evidence record (HTTP 201) |
| Invalid timestamp format | — | Falls back to `datetime.utcnow()`, no error raised |
| Corrupt/unreadable photo | — | OpenCV returns 0-score; EQE classifies as DISPUTE |

### 4.4 Dispatcher Endpoints

| Condition | HTTP Status | Detail |
|---|---|---|
| Delivery not found | 404 | "Delivery {id} not found" |
| Override from disallowed status | 400 | "Cannot override delivery in status '...'" |
| Missing reason_code | 422 | FastAPI validation error |
| Non-dispatcher role | 403 | Access denied |

### 4.5 OTP / SMS Endpoints

| Condition | HTTP Status | Detail |
|---|---|---|
| Delivery not found | 404 | "Delivery '{id}' not found" |
| Missing phone number | 400 | "Customer mobile number is required to send OTP" |
| Invalid phone (< 10 digits) | 400 | "Invalid customer mobile number. Minimum 10 digits required." |
| SMS service not configured | 503 | "SMS service not configured" |
| SMS provider delivery failure | 502 | "Failed to deliver SMS: ..." |
| Unexpected error | 500 | "Error processing OTP request: ..." |

### 4.6 Admin Analytics

| Condition | HTTP Status | Detail |
|---|---|---|
| Non-admin role | 403 | Access denied |
| Invalid date format | 422 | "from_date must be in YYYY-MM-DD format" |
| from_date after to_date | 422 | "from_date cannot be after to_date" |
| No data in range | 200 | Returns valid response with zeros |

### 4.7 Validation Endpoints

| Condition | HTTP Status | Detail |
|---|---|---|
| Invalid stakeholder_role | 422 | "Invalid stakeholder role '...'. Must be one of ..." |
| Session not found (submit response) | 422 | "Validation session '{id}' not found." |
| Rating out of range [1–5] | 422 | "Rating must be between 1 and 5." |
| Invalid question_id format | 422 | "Question ID must be in range Q1 to Q10." |
| Non-admin accessing summary | 403 | Access denied |

### 4.8 Audit Log Protection

| Condition | Handling |
|---|---|
| ORM-level UPDATE on audit_log row | SQLAlchemy `before_update` event raises `PermissionError`; transaction rolled back |
| ORM-level DELETE on audit_log row | SQLAlchemy `before_delete` event raises `PermissionError`; transaction rolled back |
| Direct SQL UPDATE/DELETE (PostgreSQL) | Database-level trigger prevents mutation (PostgreSQL only) |

---

## 5. User-Facing Fallback Behaviour Summary

| Failure | User Sees |
|---|---|
| Render crash (Error Boundary caught) | "Something went wrong" screen with "Try again" and "Reload page" buttons |
| Login failure | Inline error message below the login form |
| Evidence submission (online, server error) | Alert: "Network request failed. Saved to offline IndexedDB queue!" |
| Evidence submission (offline) | Alert: "[OFFLINE MODE] Evidence stored in local IndexedDB Queue!" |
| Analytics load failure | Error message inside the analytics panel |
| Delivery list load failure | Cached delivery list from IndexedDB (silently) |
| GPS disabled by user | Warning banner: "Zero GPS signal captured. Tagged as is_offline_capture = true." |
| OTP validation failure | Inline red error box below OTP input field |
| SMS OTP dispatch failure | HTTP error code returned; frontend displays the server error message |

---

## 6. Recovery / Retry Behaviour

| Scenario | Recovery |
|---|---|
| Offline evidence queue | Automatically flushed when `window.online` event fires or every 15 seconds by `SyncManager` |
| Error Boundary "Try again" | Clears error state; React re-mounts the child component tree |
| Error Boundary "Reload page" | Hard page reload; clears all in-memory state; re-reads JWT from localStorage |
| Failed sync item | Remains in IndexedDB queue; retried on next flush cycle |
| Delivery list stale | Polled every 4 seconds; also refreshed on tab focus and browser `storage` events |
