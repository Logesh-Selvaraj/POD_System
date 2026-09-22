# Standardised Proof-of-Delivery System with Evidence-Quality Checks
## Food-Delivery Service Coordinating Restaurants, Riders & Customers
### Academic Project Report — Review 1: Planning & Architecture

---

**Candidate Name:** LOGESH S  
**Degree / Program:** Bachelor of Engineering / Technology  
**Department:** Department of Computer Science & Engineering  
**Academic Milestone:** Review 1: Planning, Requirements Engineering, System Design & Core Verification  
**Date of Submission:** September 2026  

---

## Table of Contents
1. [Abstract](#1-abstract)
2. [Introduction](#2-introduction)
   - 2.1 Background
   - 2.2 Project Scope
   - 2.3 Stakeholders
3. [Problem Statement](#3-problem-statement)
4. [Objectives](#4-objectives)
5. [Existing System](#5-existing-system)
   - 5.1 Workflow of Current Platforms
   - 5.2 Limitations of the Existing System
6. [Proposed System](#6-proposed-system)
   - 6.1 System Overview & Core Paradigm
   - 6.2 Key Advantages
7. [Literature Survey](#7-literature-survey)
   - 7.1 Summary Table of Research Areas
   - 7.2 Detailed Analysis of Research Domains
8. [Research Gap](#8-research-gap)
9. [Requirements](#9-requirements)
   - 9.1 Functional Requirements (FR-01 to FR-26)
   - 9.2 Non-Functional Requirements (NFR-01 to NFR-10)
   - 9.3 Business Rules (BR-01 to BR-09)
10. [System Architecture](#10-system-architecture)
    - 10.1 Layered Architecture Overview
    - 10.2 System Architecture Diagram
    - 10.3 Layer Decomposition
11. [Modules](#11-modules)
    - 11.1 Role-Based User Modules
    - 11.2 Evidence Quality Engine (EQE)
    - 11.3 Dispatcher Override Module
    - 11.4 Audit & History Module
    - 11.5 Offline Synchronization Manager
12. [Database / ER Diagram](#12-database--er-diagram)
    - 12.1 Entity Relationship Diagram
    - 12.2 Database Schema & Data Dictionary
    - 12.3 Indexing & Integrity Strategy
13. [UI Design](#13-ui-design)
    - 13.1 User Interface Wireframes
    - 13.2 Interface Walkthrough by Role
14. [System Workflow](#14-system-workflow)
    - 14.1 End-to-End Delivery Workflow
    - 14.2 Dispatcher Review and Override Workflow
    - 14.3 Level-1 Data Flow Decomposition
    - 14.4 Handling of Critical Edge Cases
15. [Implementation Status](#15-implementation-status)
    - 15.1 Architectural Components Implemented
    - 15.2 Backend Service & API Implementation
    - 15.3 Frontend & Offline PWA Implementation
    - 15.4 Automated Test Suite Verification
16. [Expected Outcomes](#16-expected-outcomes)
17. [Conclusion](#17-conclusion)
18. [References](#18-references)

---

## 1. Abstract

Online food delivery platforms coordinate three independent actors—restaurants, riders, and customers—under tight time constraints for every order. The critical final step of this operational chain is delivery confirmation: the moment a platform determines whether an order was legitimately delivered to the intended recipient. In current industry practice, delivery confirmation is treated as a single, unverified action, typically consisting of a rider tapping a "Delivered" button and optionally uploading an arbitrary photo. Because these submissions lack real-time validation, blurred, pitch-black, misframed, or fraudulent photos are accepted as valid proof. Furthermore, GPS coordinates are rarely cross-checked against delivery geofences at confirmation, customer verification (OTP or digital signature) is frequently skipped under time pressure, and intermittent mobile connectivity in indoor or underground environments causes capture workflows to fail outright. The resulting ambiguity forces customer support teams to resolve high volumes of delivery disputes manually, leading to subjective decisions, financial losses, and eroded stakeholder trust.

To overcome these deficiencies, this project designs and implements a **Standardised Proof-of-Delivery (POD) System with Evidence-Quality Checks**. The system transitions delivery confirmation from an unverified status update to an explainable, multi-factor decision pipeline. The platform captures five structured evidence types for every delivery: delivery photo, device GPS coordinates, capture timestamp, one-time password (OTP), and an on-screen customer signature. At the core of the platform is an automated **Evidence Quality Engine (EQE)** that evaluates captured evidence against an explicit, weighted scoring rubric (0–100 points): Photo Quality (25), GPS Geofence Match (25), Timestamp Validity (20), Signature Presence (20), and OTP Verification (10). Deliveries are automatically triaged into three outcome bands: **Accepted** (score ≥ 90), **Needs Manual Review** (score 70–89), or **Dispute** (score < 70).

To ensure complete operational reliability in real-world delivery environments, the system features an **offline-first Progressive Web App (PWA)** client architecture. Captured evidence is persisted locally in an IndexedDB queue, allowing riders to mark deliveries complete without network connectivity; a background Synchronization Manager opportunistically transmits queued evidence to the backend once connectivity is restored. In degraded conditions (e.g., indoor delivery with zero GPS fix), the scoring engine withholds GPS marks, capping the maximum score at 75 and routing the delivery to a dedicated **Dispatcher Review Queue**. Human dispatchers can resolve edge cases using a controlled override workflow that enforces mandatory reason codes and justification logging. All state changes, evidence submissions, score evaluations, and dispatcher overrides are committed to an **append-only, immutable audit trail**, ensuring complete end-to-end traceability and non-repudiation.

For Review 1, the foundational engineering milestones have been achieved: complete Software Requirements Specification (SRS) following IEEE standards, layered client-server system architecture, third normal form (3NF) relational database schema, user interface wireframes, and a fully functional core backend and frontend prototype. Automated unit and integration testing confirms that the core scoring algorithms, OpenCV image validation, Haversine geofencing, and role-based workflows operate with high fidelity, passing 50 automated test cases across 8 test suites.

---

## 2. Introduction

### 2.1 Background
The rapid expansion of on-demand food delivery has established it as one of the largest last-mile logistics operations globally. Modern delivery platforms coordinate three distinct parties for every order:
1. **Restaurants**, who prepare meals and require timely pickup and guaranteed payment;
2. **Riders**, who navigate urban transit networks to fulfill deliveries under tight schedules; and
3. **Customers**, who expect prompt, accurate, and intact delivery at their doorstep.

While order dispatch, menu discovery, and routing have seen extensive automation, the final fulfillment step—**delivery confirmation**—remains the most vulnerable link in the fulfillment lifecycle. Confirming whether an order was actually delivered carries immediate operational and financial consequences. An erroneous or disputed delivery triggers customer refund requests, dispute claims by restaurants regarding meal costs, and payment penalties or deactivation for riders. In major urban centers where platforms handle tens of thousands of orders daily, even a 1% to 2% dispute rate generates thousands of contentious claims that must be investigated by human support agents.

Existing commercial platforms rely on coarse, single-factor mechanisms such as a simple rider status toggle, occasionally accompanied by a single unexamined photo. These practices fail to provide definitive, verifiable proof of fulfillment. When disputes arise, support teams are forced to make subjective determinations based on incomplete, unvalidated evidence. This project addresses this vulnerability by developing an automated, multi-factor proof-of-delivery framework that enforces evidence quality at the point of capture, transparently scores fulfillment signals, supports uninterrupted offline operations, and maintains an immutable audit log.

### 2.2 Project Scope
The scope of this project encompasses the design, implementation, and academic evaluation of a comprehensive Proof-of-Delivery system structured across five user roles: Restaurant, Rider, Customer, Dispatcher, and Platform Administrator.

#### In-Scope Capabilities:
- **Five-Factor Evidence Ingestion:** Capturing delivery photograph, GPS coordinates with accuracy radius, timestamp, customer OTP, and digital signature.
- **Evidence Quality Engine (EQE):** Real-time automated scoring (0–100) utilizing classical computer vision (OpenCV Laplacian variance for blur and pixel intensity for exposure) and geospatial analysis (Haversine distance calculation against a 150-meter delivery geofence).
- **Automated Triaged Classification:** Rule-based routing into Accepted, Needs Manual Review, and Dispute categories.
- **Offline-First PWA Architecture:** On-device persistent queueing using IndexedDB, allowing riders to capture evidence and complete routes in network-deprived environments (basements, elevators, high-rises), with automatic background sync.
- **Dispatcher Review & Override Workflow:** Dedicated operations console providing split-pane evidence inspection, geospatial discrepancy visualization, and mandatory reason-coded override actions.
- **Immutable Audit Trail:** Append-only logging of all order lifecycles, evidence payloads, scoring outputs, and dispatcher actions.
- **Role-Based Web Applications:** Responsive single-page applications for Restaurant, Rider, Customer, Dispatcher, and Admin roles.
- **Operational Analytics Dashboard:** Administrative visibility into delivery volumes, average evidence quality scores, dispute frequencies, and regional performance.

#### Explicitly Out-of-Scope (Review 1 & Academic Prototype Boundaries):
In accordance with Section 1.4 of the project SRS, the following areas are deliberately excluded from this academic prototype:
- Production payment gateway integration, card settlement, and merchant escrow accounts.
- Live native mobile store distributions (iOS App Store / Google Play Store); responsive Progressive Web Apps (PWA) with service workers serve as the standard multi-platform client.
- Dynamic large-scale multi-city vehicle routing optimization and batch dispatching.
- Third-party commercial SMS telecom aggregator integration (a sandbox/mock OTP service is utilized).

### 2.3 Stakeholders
The system serves six distinct stakeholder groups, each with specific operational roles and requirements:

| Stakeholder | Role in System | Key Needs & System Benefits |
| :--- | :--- | :--- |
| **Restaurant Partner** | Creates orders, tracks order preparation, and monitors fulfillment status. | Protection against false non-delivery claims; transparent visibility into handoff and delivery status; reduction in unfair food-loss liabilities. |
| **Rider / Delivery Executive** | Accepts assignments, travels to customer location, captures evidence, and marks delivery complete. | Fair, objective evidence standards; immunity from false customer accusations; seamless offline capture capability in elevators and network dead zones. |
| **Customer** | Places orders, receives secure OTP, provides signature, and inspects fulfillment. | Assurance of tamper-free delivery; protection against misdelivery; transparent, fast dispute raising mechanism with documented evidence review. |
| **Dispatcher / Operations Team** | Monitors real-time exception queue; reviews flagged deliveries; executes overrides. | Prioritized, pre-scored queue; granular insight into specific failed evidence factors; standardized override reason codes with auditable justifications. |
| **Platform Administrator** | Oversees platform health, configures thresholds, manages user accounts and access roles. | Centralized analytics dashboard tracking delivery volumes, average evidence scores, dispute rates, and regional compliance trends. |
| **Project Guide / Evaluators** | Academic review, evaluation of system engineering, adherence to specifications. | Assessment of technical rigor, adherence to IEEE SRS guidelines, mathematical correctness of scoring rubric, and experimental verification. |

---

## 3. Problem Statement

Delivery evidence collected by contemporary on-demand food delivery workflows is fundamentally inconsistent, unverified at the point of capture, and highly vulnerable to operational failure. Specifically, existing implementations suffer from the following core failure modes:

1. **Unverified and Poor-Quality Photographic Proof:** Platforms accept delivery photos as arbitrary binary attachments without performing real-time quality validation. Photos that are blurred, completely black, over-exposed, pointed at a floor or vehicle handle, or taken at an arbitrary location are routinely accepted as valid proof of fulfillment.
2. **Unvalidated GPS Telemetry:** GPS coordinates captured at the moment of delivery are rarely cross-referenced against the registered customer delivery address. In dense urban canyons or indoor settings, GPS drift, multipath reflection, or deliberate coordinate spoofing can lead to false confirmations hundreds of meters away from the true destination without triggering an alert.
3. **Skipped or Inconsistent Customer Verification:** Customer verification mechanisms such as OTPs or digital signatures are applied inconsistently. Delivery executives facing severe delivery time pressure frequently bypass customer interaction, while customers may be unavailable, resulting in deliveries left unattended with zero customer-side acknowledgement.
4. **Fragility in Network Dead Zones:** The final hundred meters of food delivery routinely occur in high-rise corridors, basements, elevators, or densely built residential complexes where cellular data connectivity drops. Traditional mobile applications block delivery completion or silently fail to transmit evidence photos, resulting in lost records, untracked orders, and stranded riders.
5. **Costly, Subjective, and Reactive Dispute Resolution:** Because proof of delivery is not evaluated when captured, disputes are handled purely reactively after an aggrieved customer files a support ticket. Support agents are forced to inspect whatever unvalidated artifact exists and make subjective judgements without standard guidelines. This process is labor-intensive, slow, highly inconsistent across agents, and scales poorly as order volumes expand.

---

## 4. Objectives

To resolve the stated problems, the project establishes the following seven technical and operational objectives:

1. **Standardised Multi-Factor Evidence Capture:** Design and prototype a structured Proof-of-Delivery pipeline that captures five distinct evidence signals—photo, GPS coordinates with accuracy metrics, server/device timestamp, OTP verification, and digital signature—in a consistent, schema-validated format.
2. **Automated Quality Scoring & Triaged Classification:** Develop and integrate an explainable Evidence Quality Engine (EQE) that computes a normalized 0–100 quality score based on explicit, weighted criteria and automatically classifies each delivery into **Accepted (≥90)**, **Needs Manual Review (70–89)**, or **Dispute (<70)** before customer complaints arise.
3. **Resilient Offline-First Architecture:** Ensure that the evidence capture workflow functions reliably without active network connectivity or GPS availability by utilizing client-side persistent storage (IndexedDB), enabling offline route completion and automatic background queue synchronization with exponential backoff and idempotency protection upon reconnect.
4. **Accountable Dispatcher Override Capability:** Provide an operational workspace allowing human dispatchers to inspect flagged edge cases and execute status overrides governed by mandatory reason codes and justification logging, ensuring flexibility without bypassing accountability.
5. **Immutable Audit History & Traceability:** Implement an append-only audit trail that permanently logs every lifecycle event—order creation, evidence ingestion, automated scoring, offline sync events, and dispatcher interventions—to provide complete non-repudiation.
6. **Empirical Baseline Benchmarking:** Establish an experimental validation methodology comparing the multi-factor Evidence Quality Engine against a conventional photo-only manual baseline on a labelled dataset spanning normal and edge-case scenarios, measuring classification agreement, false acceptances, and resolution efficiency.
7. **Comprehensive Academic Documentation & Working Prototype:** Deliver industry-standard engineering documentation (IEEE-compliant SRS, layered system architecture, normalized ER model, UI wireframes) alongside a fully functional, tested prototype across all five role modules.

---

## 5. Existing System

### 5.1 Workflow of Current Platforms
In mainstream commercial food delivery systems, the delivery confirmation lifecycle operates as follows:
1. **Pickup and Transit:** The rider collects the prepared food package from the restaurant and navigates toward the customer address.
2. **Arrival:** The rider arrives in the vicinity of the delivery location.
3. **Status Toggle:** The rider taps a button labeled "Arrived" or "Delivered" on their mobile interface.
4. **Optional Photo Capture:** Depending on platform settings, the rider may be prompted to snap a single photograph of the package at the doorstep. The mobile app uploads this image directly to object storage without local validation.
5. **Order Finalization:** The order status transitions immediately to "Completed" on the server. The customer receives a notification that their meal has arrived.
6. **Reactive Dispute Escalation:** If the customer cannot locate the package, received an incomplete order, or claims non-delivery, they must open a customer support ticket. A support agent manually retrieves the uploaded photo, inspects it subjectively, checks coarse rider GPS tracking logs, and decides whether to grant a refund or reject the claim.

### 5.2 Limitations of the Existing System
The existing approach presents major structural, technical, and operational deficiencies:

- **Absence of Image Validation:** No automated computer vision checks are performed at the point of capture. Blurred, unreadable, dark, or irrelevant images are accepted into platform records without warning.
- **Unverified Spatial Accuracy:** GPS coordinates are recorded passively for route tracing but are not mathematically validated against the registered delivery geofence during confirmation. Deliveries dropped at the wrong building or street corner go undetected.
- **Lack of Standardised Scoring:** Evidence is treated as a binary attachment (present or absent). There is no composite scoring metric that balances visual, spatial, temporal, and customer authorization factors.
- **Failure in Low/Zero Connectivity:** Standard delivery apps require active server connectivity to confirm an order. In elevators or basements, riders cannot mark orders complete, causing app freezing, lost photographic data, or repeated failed submissions.
- **Disconnected Audit Trail:** Order status updates and customer dispute logs are frequently stored across decoupled tables without cryptographic or foreign-key linkages to the exact evidence signals that justified the completion.
- **Subjective, Inconsistent Decisions:** Dispute outcomes depend entirely on individual support agent discretion, creating friction with customers, unfair penalties for riders, and unpredictable liabilities for restaurants.

---

## 6. Proposed System

### 6.1 System Overview & Core Paradigm
The proposed **Standardised Proof-of-Delivery System** transforms delivery confirmation from an unexamined status toggle into a structured, evidence-scored, automated decision pipeline. Instead of accepting a single photo as unverified proof, the system treats proof of delivery as a multi-dimensional evidentiary record evaluated instantly at capture time.

The system workflow progresses through four coordinated stages:
1. **Capture:** The rider app captures five structured evidence signals—high-resolution photograph, device GPS coordinates with accuracy radius, capture timestamp, 4-digit customer OTP, and on-screen touch signature. The capture interface runs within an offline-first container, writing records directly to local device storage before attempting network transmission.
2. **Score:** The Evidence Quality Engine (EQE) executes an explainable scoring rubric (0–100 points) evaluating image sharpness (Laplacian variance), brightness distribution, spatial geofence alignment (Haversine distance ≤ 150 meters), timestamp validity, signature stroke complexity, and cryptographic OTP match.
3. **Classify:** The calculated score maps deterministically into three operational outcome bands:
   - **Accepted (Score ≥ 90):** The delivery satisfies all evidentiary thresholds; fulfillment is auto-confirmed, rider payouts are cleared, and no human intervention is needed.
   - **Needs Manual Review (Score 70–89):** Minor discrepancies detected (e.g., missing GPS due to indoor delivery, or customer signature substituted for an unavailable OTP). The order is routed to the Dispatcher Review Queue with specific flagged gaps.
   - **Dispute (Score < 70):** Critical evidentiary failure (e.g., severe image blur, extreme GPS location mismatch > 150m, or failed OTP). The system proactively flags the order as a potential dispute, notifying dispatchers and customers before formal escalation.
4. **Resolve:** Dispatchers inspect flagged deliveries in a specialized workspace displaying side-by-side evidence and geospatial maps, executing documented overrides with mandatory reason codes that are permanently committed to the immutable audit log.

### 6.2 Key Advantages
- **Objective and Explainable:** Every delivery decision is governed by explicit mathematical formulas and weighted rules, eliminating subjective human bias.
- **Proactive Risk Mitigation:** Low-quality or suspicious evidence is flagged immediately, enabling operational intervention before customer dissatisfaction escalates.
- **Uncompromised Offline Reliability:** Delivery executives can complete deliveries anywhere, anytime, with zero dependency on immediate network access.
- **Accelerated Dispatcher Resolution:** Flagged orders arrive pre-analyzed with specific failing criteria highlighted, reducing dispatcher investigation time from minutes to seconds.
- **Complete End-to-End Auditability:** The append-only audit trail guarantees that every status change, score calculation, and override decision can be historically reconstructed and defended.
- **Extensible Architecture:** The modular scoring engine easily accommodates future evidence modalities (such as biometric verification or video evidence) without structural redesign.

---

## 7. Literature Survey

### 7.1 Summary Table of Research Areas
The design of this Proof-of-Delivery system is informed by research in last-mile logistics, computer vision, geospatial positioning, distributed systems, and audit architectures. The table below summarizes the eight foundational areas reviewed from project literature:

| No | Research Area | Key Idea in Literature | Identified Limitation | Literature / Industry Gap | Proposed Project Improvement |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **Proof of Delivery (POD)** | Replacing paper manifests with digital delivery acknowledgements. | Binary validation; platforms check only file presence rather than quality. | Lack of composite, explainable evidence quality scoring. | Multi-signal 0–100 Evidence Quality Engine evaluating 5 distinct proof factors. |
| **2** | **Last-Mile Logistics** | Coordinating delivery workflows between merchant, courier, and end-consumer. | High dispute frequency at the point of handoff resulting in costly manual reviews. | Absence of standardized fulfillment verification standards. | Standardized POD schema with automated triage into Accepted, Review, and Dispute. |
| **3** | **GPS Tracking & Geofencing** | Validating proximity to destination using mobile location services. | Satellite attenuation, urban canyon multipath errors, indoor signal loss. | Inability to handle zero-GPS edge cases gracefully without app failure. | Haversine geofencing (150m tolerance) with degraded-mode scoring fallback for zero-GPS. |
| **4** | **Offline Mobile Systems** | Local caching of data for intermittently connected mobile environments. | Generic local storage implementations without domain-specific sync logic. | Lack of reliable offline evidence queuing tailored for logistics proof. | Offline-first PWA using IndexedDB, service workers, and idempotent background sync. |
| **5** | **Image Quality Assessment** | Classical computer vision algorithms for evaluating blur and exposure. | Standalone image processing without integration into operational workflows. | Real-time edge quality feedback absent at the moment of photo capture. | OpenCV Laplacian variance blur detection and mean intensity checks with retake prompts. |
| **6** | **Audit Logging & Security** | Maintaining tamper-evident system logs for forensic traceability. | Generic logging of database writes without business-context metadata or override links. | Lack of structured human override logging linked to automated scores. | Append-only, immutable audit table recording actor, action, payload snapshots, and reason codes. |
| **7** | **Customer Verification** | Using one-time passwords (OTP) or digital signatures for identity assurance. | Single-factor reliance; OTP fails on dead phones, signature is easily forged. | Lack of dual-factor fallback mechanisms for diverse handoff contexts. | Multi-factor verification combining OTP with on-screen signature fallback. |
| **8** | **Dispute Resolution Systems** | Case management software for resolving post-delivery customer complaints. | Slow, reactive manual investigation relying on incomplete, unvalidated evidence. | Disconnect between raw delivery evidence and dispute triage queues. | Dispatcher operations workspace pre-populated with automated scores and evidence gaps. |

### 7.2 Detailed Analysis of Research Domains
The project synthesizes five distinct technical foundations:

1. **Blur and Exposure Detection via Computer Vision:** Image blur is quantitatively evaluated using the variance of the Laplacian operator applied to greyscale image matrices ($Var(\nabla^2 I)$). Sharp images with defined edges exhibit high spatial variance, whereas blurred images produce low variance. Combined with mean pixel brightness calculations, this provides an explainable, computationally lightweight validation mechanism suitable for mobile and edge execution without requiring opaque deep-learning models.
2. **Geospatial Distance Calculation via Haversine Formulation:** To verify delivery location, spherical trigonometry using the Haversine formula calculates the great-circle distance between the rider's recorded latitude/longitude and the customer's registered delivery address:
   $$d = 2R \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)} \right)$$
   A threshold of 150 meters accommodates urban positioning drift while preventing false delivery claims.
3. **Offline-First Application Architecture:** Implementing Service Workers and IndexedDB client storage ensures the application functions as a local-first system. Evidence records are committed to durable browser storage first, decoupling the user experience from transient network connectivity.
4. **Multi-Factor Verification in Last-Mile Logistics:** Combining knowledge/possession factors (OTP sent to customer) with behavioral/physical factors (touch signature and photographic proof) significantly elevates non-repudiation compared to single-factor confirmations.
5. **Append-Only Immutability for Operational Traceability:** Adhering to event-sourcing principles ensures audit records cannot be modified or deleted, preserving forensic truth during downstream merchant and customer arbitrations.

---

## 8. Research Gap

While existing literature and commercial applications address isolated aspects of logistics tracking and mobile data capture, a critical research and architectural gap remains:

> **Core Research Gap:**  
> Existing logistics and delivery confirmation systems rarely combine photo quality validation, GPS accuracy geofencing, OTP verification, digital signatures, capture timestamps, offline-first execution, dispatcher override workflows, and immutable audit history in one unified, explainable proof-of-delivery framework.

Specifically, current platforms exhibit five distinct gaps:
1. **The Multi-Signal Integration Gap:** Delivery systems evaluate evidence in siloes (e.g., GPS tracking in one system, photo upload in another, OTP in a third). No unified mathematical model aggregates these signals into an explainable composite quality index.
2. **The Point-of-Capture Validation Gap:** Image validation, when performed at all, is executed post-hoc on centralized servers. There is no real-time validation at the edge that prompts the rider to retake a blurred photo before leaving the delivery location.
3. **The Offline-Degraded Scoring Gap:** Systems either assume constant high-speed connectivity or fail completely when offline. No existing framework mathematically models degraded evidence modes (e.g., capping scores when GPS is unavailable indoors) while preserving the ability to finalize delivery.
4. **The Operational Override Accountability Gap:** In current support software, operational managers can manually alter delivery statuses without structured reason codes or mandatory justification, weakening auditability and employee accountability.
5. **The Proactive Dispute Triage Gap:** Current industry architectures are 100% reactive, waiting for customer complaints before inspecting evidence. There is a lack of automated triage that proactively routes low-quality deliveries into manual review queues prior to customer escalation.

---

## 9. Requirements

### 9.1 Functional Requirements
The system functional requirements define the precise behaviors, capabilities, and constraints across all application modules, uniquely indexed from FR-01 to FR-26:

| ID | Module / Area | Functional Requirement Description |
| :--- | :--- | :--- |
| **FR-01** | Restaurant Module | The system shall allow restaurant operators to create orders with itemized details, customer delivery address, and estimated preparation time. |
| **FR-02** | Restaurant Module | The system shall allow restaurant operators or dispatchers to assign available delivery riders to confirmed orders. |
| **FR-03** | Restaurant Module | The system shall provide real-time tracking of order fulfillment status (Created, Assigned, Picked Up, In Transit, Delivered, Disputed). |
| **FR-04** | Rider Module | The system shall allow delivery riders to accept or reject assigned deliveries within a configurable operational time window. |
| **FR-05** | Rider Module | The system shall enable riders to capture a photographic image of the delivered food package at the point of delivery using device camera hardware. |
| **FR-06** | Rider Module | The system shall capture device GPS coordinates and location accuracy radius at the exact instant of evidence capture. |
| **FR-07** | Rider Module | The system shall provide an input interface for riders to enter a 4-digit customer-provided OTP for delivery authentication. |
| **FR-08** | Rider Module | The system shall provide an on-screen signature canvas allowing riders to capture customer digital signatures when OTP is unavailable. |
| **FR-09** | Rider Module | The system shall permit marking a delivery as Complete only after minimum required evidence is captured or a documented degraded path is invoked. |
| **FR-10** | Customer Module | The system shall generate and display a unique, time-limited one-time password (OTP) to the customer upon order dispatch. |
| **FR-11** | Customer Module | The system shall allow customers to confirm receipt of their order and view the photographic proof captured by the delivery executive. |
| **FR-12** | Customer Module | The system shall allow customers to initiate a formal delivery dispute by selecting predefined reason categories and attaching notes. |
| **FR-13** | Evidence Engine | The system shall compute an Evidence Quality Score (0–100) for every delivery by executing the weighted multi-factor scoring rubric. |
| **FR-14** | Evidence Engine | The system shall classify delivery outcomes into Accepted (≥90), Needs Manual Review (70–89), or Dispute (<70) based on the computed score. |
| **FR-15** | Evidence Engine | The system shall validate delivery photos for blur (Laplacian variance) and exposure, prompting the rider for an immediate retake if thresholds fail. |
| **FR-16** | Offline Handling | The system shall persist captured evidence records to an on-device IndexedDB queue whenever network connectivity is unavailable. |
| **FR-17** | Offline Handling | The system shall automatically synchronize locally queued offline evidence to the backend once connectivity is restored without manual user trigger. |
| **FR-18** | Offline Handling | The system shall tag evidence captured without GPS as Offline/Reduced-Accuracy, withholding GPS marks and capping total score at ≤75. |
| **FR-19** | Dispatcher Module | The system shall present dispatchers with a prioritized queue of deliveries flagged for Manual Review or Dispute, sorted by score and age. |
| **FR-20** | Dispatcher Module | The system shall require dispatchers to select a standardized reason code and provide justification text when executing a status override. |
| **FR-21** | Dispatcher Module | The system shall notify affected riders and customers whenever a dispatcher override modifies an order or delivery outcome. |
| **FR-22** | Audit & History | The system shall record an immutable, timestamped audit log entry for every state transition, evidence submission, score calculation, and override. |
| **FR-23** | Audit & History | The system shall allow authorized dispatchers and administrators to inspect the full historical timeline and raw evidence of any delivery. |
| **FR-24** | Admin Module | The system shall provide an administrative analytics dashboard summarizing delivery volume, average evidence quality, dispute rates, and regional metrics. |
| **FR-25** | Admin Module | The system shall provide account management and role-based access control (RBAC) administration across all five system roles. |
| **FR-26** | Reporting | The system shall enable authorized administrators to export delivery, evidence, and dispute records for specified date ranges. |

### 9.2 Non-Functional Requirements
The non-functional requirements define the architectural quality attributes, performance targets, and security baselines for the system:

| ID | Category | Requirement Specification |
| :--- | :--- | :--- |
| **NFR-01** | **Performance** | The Evidence Quality Engine shall compute quality scores and classification within 2.0 seconds of receiving evidence under normal load (≤100 concurrent requests). |
| **NFR-02** | **Availability** | The offline evidence capture path on the rider client shall operate with zero network dependency, targeting 99.5% capture success regardless of connectivity. |
| **NFR-03** | **Reliability** | Locally queued offline evidence stored in IndexedDB shall withstand browser refreshes, application restarts, and device reboots without data corruption. |
| **NFR-04** | **Scalability** | The backend REST API architecture shall horizontally scale to support a minimum throughput of 10,000 simulated deliveries per day. |
| **NFR-05** | **Usability** | A delivery rider shall be capable of completing the standard multi-factor evidence capture workflow in under 60 seconds under typical operating conditions. |
| **NFR-06** | **Security** | All client-server communication shall be secured via TLS 1.2+ encryption; user passwords shall be hashed using salted bcrypt algorithms. |
| **NFR-07** | **Data Integrity** | Audit trail records shall be strictly append-only; application APIs and database privileges shall prohibit update (UPDATE) or deletion (DELETE) operations. |
| **NFR-08** | **Maintainability** | Backend services shall follow a modular monolith pattern with decoupled domain services, enabling independent updates to the scoring engine. |
| **NFR-09** | **Portability** | The web application shall be fully responsive and installable as a Progressive Web App (PWA) across modern Android and iOS mobile web browsers. |
| **NFR-10** | **Compliance** | Personally identifiable information (PII) including customer phone numbers and addresses shall be protected by RBAC and masked in analytics views. |

### 9.3 Business Rules
The operational logic of the platform is governed by nine fundamental business rules:
- **BR-01 (Minimum Evidence Threshold):** A delivery cannot be marked Complete without at least a photographic image and either an OTP or digital signature, unless captured under a recognized offline degraded-evidence workflow.
- **BR-02 (Auto-Acceptance Threshold):** An Evidence Quality Score of ≥90 triggers immediate automatic acceptance. Dispatcher intervention is not permitted to reverse auto-acceptance without opening a formal customer-initiated dispute.
- **BR-03 (Manual Review SLA):** Deliveries with an Evidence Quality Score between 70 and 89 must be routed to the Dispatcher Review Queue and resolved within a 24-hour Service Level Agreement (SLA).
- **BR-04 (Automated Dispute Flagging):** An Evidence Quality Score below 70 automatically generates a Dispute record, notifying both customer and dispatcher.
- **BR-05 (Mandatory Override Justification):** Every dispatcher override must include a recognized reason code and an accompanying justification of at least 10 characters.
- **BR-06 (OTP Lifecycle):** One-time passwords are single-use, strictly valid for 15 minutes from issuance, and expire immediately upon successful verification.
- **BR-07 (Queue Throttling):** A rider may not be assigned a new order while an existing completed delivery has un-synced offline evidence pending beyond a maximum retry threshold.
- **BR-08 (Geofence Threshold):** GPS coordinates captured more than 150 meters from the registered customer delivery address are classified as a location mismatch, resulting in 0 points for the GPS criterion.
- **BR-09 (Audit Immutability):** Historical audit records cannot be altered or purged; corrections must be executed as new compensating audit log entries.

---

## 10. System Architecture

### 10.1 Layered Architecture Overview
The system employs a **Layered Client-Server Architecture** featuring an explicit **offline-sync boundary** at the client edge. This architectural pattern isolates presentation, network routing, business logic, computer vision scoring, and data persistence into cohesive, loosely coupled tiers.

### 10.2 System Architecture Diagram
The physical and logical layout of the system architecture is illustrated below:

![System Architecture Diagram](System_Architecture_Diagram.png)

### 10.3 Layer Decomposition

#### 1. Presentation & Client Layer
The presentation tier comprises five role-specific Single Page Applications (SPAs) built with **React 18** and **TypeScript**, bundled using **Vite**, and styled with **Tailwind CSS**:
- **Rider App:** Engineered as an offline-first Progressive Web App (PWA) incorporating Service Workers for static asset caching and **IndexedDB** for local evidence queuing. Features custom HTML5 Canvas components for on-screen customer signature capture and direct device camera API integration.
- **Dispatcher Console:** Specialized workspace for real-time triage, featuring split-pane evidence comparison, OpenCV quality metric badges, and interactive **Leaflet.js / OpenStreetMap** geofence overlays.
- **Admin Dashboard:** Executive analytics portal displaying operational KPI cards, score distribution charts, and regional dispute breakdowns.
- **Restaurant & Customer Portals:** Order placement, live status tracking, OTP verification, and dispute submission interfaces.

#### 2. Gateway & Ingress Layer
Incoming HTTP/WebSocket traffic terminates at a reverse proxy and API Gateway (**NGINX**) providing:
- TLS 1.2+ termination for end-to-end data encryption in transit.
- Cross-Origin Resource Sharing (CORS) enforcement.
- Rate limiting to protect authentication and evidence endpoints from brute-force and denial-of-service vectors.

#### 3. Application Service Layer (Modular Monolith)
The core backend is implemented in **Python 3.13** using the high-performance **FastAPI** framework. Built as a modular monolith, it enforces clean domain boundaries across internal services:
- **Authentication Service:** Issues and validates JSON Web Tokens (JWT) using HMAC-SHA256, enforcing Role-Based Access Control (RBAC) across all endpoints.
- **Order & Delivery Service:** Manages the lifecycle of orders, rider dispatch, assignment acceptance, and state transitions.
- **POD Evidence Ingestion Service:** Ingests multipart form submissions containing photo binaries, GPS coordinates, timestamps, OTP strings, and signature vectors.
- **Evidence Quality Engine (EQE):** Orchestrates image blur/brightness analysis, Haversine geofence calculations, and weighted scoring rubric aggregation.
- **Offline Sync Manager:** Ingests batched offline evidence submissions from client IndexedDB queues, resolving duplicate submissions via idempotency keys.
- **Dispatcher & Dispute Service:** Manages the review queue, evaluates SLAs, and processes manual overrides.
- **Audit & History Service:** Asynchronously logs immutable event payloads to the relational database.
- **Notification Service:** Dispatches simulated SMS OTPs and in-app status updates to customers and riders.

#### 4. Data & Storage Layer
Persistence is divided across three dedicated storage systems:
- **Relational Store (PostgreSQL 15):** Houses normalized transactional entities (users, restaurants, riders, customers, orders, deliveries, evidence metadata, disputes, overrides) and append-only audit records.
- **In-Memory Cache (Redis):** Manages active session tokens, real-time dispatcher queue caches, and offline sync lock queues.
- **Binary Object Storage:** High-durability file storage (local file system in development, MinIO/S3-compatible in production) storing raw delivery photos and digital signature image blobs.

---

## 11. Modules

### 11.1 Role-Based User Modules
The system is partitioned into five distinct role-based modules, each tailored to a specific operational participant:

1. **Restaurant Module:** Provides restaurant staff with an interface to create new food orders, specify line items and customer delivery addresses, view nearby available delivery riders, assign orders, and monitor pickup-to-delivery fulfillment progress in real time.
2. **Rider Module:** Mobile-optimized interface allowing riders to view active assignments, accept or reject delivery requests, view drop-off navigation targets, and execute multi-factor evidence capture (camera, GPS, OTP, signature) with full offline queuing support.
3. **Customer Module:** Customer-facing web view enabling patrons to view real-time delivery progress, retrieve their secret 4-digit OTP, inspect proof-of-delivery photos upon completion, and initiate structured delivery disputes if discrepancies occur.
4. **Dispatcher Module:** Operations console displaying an active triage queue of deliveries categorized as Needs Manual Review or Dispute, providing deep-dive evidence inspection tools and override actions.
5. **Admin Module:** Executive management console enabling user account administration, RBAC role assignment, system threshold configuration, and aggregate operational analytics reporting.

### 11.2 Evidence Quality Engine (EQE)
The Evidence Quality Engine represents the primary algorithmic contribution of the platform. Instead of accepting unvalidated binary uploads, it evaluates every delivery submission against a 100-point transparent scoring rubric.

#### Scoring Rubric Breakdown:

| Evaluation Criterion | Maximum Points | Algorithmic Validation Logic & Thresholds |
| :--- | :---: | :--- |
| **1. Delivery Photo Quality** | **25 pts** | Evaluates presence of image binary, minimum resolution, image sharpness via OpenCV Laplacian variance ($Var(\nabla^2 I) \ge 100.0$), and mean pixel brightness ($40.0 \le \mu \le 220.0$). Photos failing checks score 0 points. |
| **2. GPS Geofence Match** | **25 pts** | Compares captured device coordinates against registered delivery address using the Haversine formula. Scores **25 pts** if distance $\le 150\text{ m}$. Scores **0 pts** if distance $> 150\text{ m}$ (mismatch) or if GPS is unavailable (offline/indoor). |
| **3. Timestamp Validity** | **20 pts** | Validates presence of capture timestamp, verifies timestamp occurs within the active delivery window, and checks that client-server clock drift does not exceed acceptable thresholds. Scores **20 pts** if valid, **0 pts** if missing or skew detected. |
| **4. Digital Signature** | **20 pts** | Evaluates customer signature captured via canvas. Validates presence of vector/image stroke data and minimum stroke density (rejects blank or trivial single-point taps). Scores **20 pts** if present and valid, **0 pts** if absent. |
| **5. OTP Verification** | **10 pts** | Validates customer-entered 4-digit one-time password against the cryptographically generated hash stored in the delivery record. Scores **10 pts** on exact match, **0 pts** on failure or absence. |
| **TOTAL SCORE** | **100 pts** | **Normalized composite quality score.** |

#### Outcome Classification Thresholds:
- **Accepted (Score ≥ 90):** Delivery is automatically confirmed as successfully fulfilled. Order status transitions to `DELIVERED`, rider payment is authorized, and customer is notified.
- **Needs Manual Review (Score 70–89):** Minor non-critical evidentiary discrepancy detected (e.g., valid photo, OTP, and timestamp, but missing GPS due to indoor delivery, yielding a score of 75). Routed to the Dispatcher Queue with an SLA of 24 hours.
- **Dispute (Score < 70):** Severe evidentiary failure (e.g., blurred photo, GPS mismatch > 150m, and missing OTP). System automatically flags the delivery as a Dispute, alerting dispatchers and customers immediately.

#### Degraded-Mode (Zero-GPS) Handling:
When a delivery occurs in an indoor mall, basement, or urban high-rise where GPS fix cannot be established, the system records `captured_latitude = null` and `is_offline_capture = true`. The EQE awards 0 points for the GPS criterion. Even with perfect photo (25), timestamp (20), signature (20), and OTP (10), the maximum possible score is capped at **75 points**. This mathematically guarantees that zero-GPS deliveries can never be silently auto-accepted, correctly routing them to the manual review queue while still allowing riders to complete their routes.

### 11.3 Dispatcher Override Module
To handle complex real-world edge cases where automated scoring flags an order (e.g., customer refuses to sign, or building delivery entrance differs from street address), the system provides an authorized Dispatcher Override mechanism.

#### Standard Reason Codes:
Dispatchers must select an explicit reason code from a controlled enumeration or supply custom text meeting strict length validation:

| Reason Code | Operational Scenario | Linked Edge Case |
| :--- | :--- | :--- |
| `CUST_REFUSED_SIG` | Customer declined on-screen signature; identity verified via OTP or direct verbal handoff. | Edge Case 4 |
| `GPS_ADDR_MISMATCH` | GPS coordinates exceeded 150m threshold, but manual map inspection confirms valid delivery gate/building entrance. | Edge Case 5 |
| `PHOTO_RETAKE_FAILED` | Rider attempted photo retakes, but environmental lighting or physical obstruction prevented clear capture. | Edge Case 3 |
| `NETWORK_DELAYED_SYNC` | Evidence was delayed due to prolonged connectivity outage; verified authentic upon post-shift sync. | Edge Case 2 |
| `CUSTOMER_UNREACHABLE` | Customer failed to respond to door arrival; package deposited in secure building reception per instructions. | General Edge Case |
| `OTHER` | Specific exception not covered above; requires mandatory free-text justification of at least 10 characters. | Operational Fallback |

### 11.4 Audit & History Module
The Audit & History Module provides tamper-proof non-repudiation across the application lifecycle. Every state-modifying action triggers an asynchronous audit event committed to the `audit_logs` table. Audit records capture:
- Unique log identifier and millisecond-accurate timestamp.
- Target entity type (`order`, `delivery`, `evidence`, `dispute`, `dispatcher_override`) and entity primary key.
- Action name (`ORDER_CREATED`, `RIDER_ASSIGNED`, `EVIDENCE_CAPTURED`, `EVIDENCE_SYNCED`, `SCORE_EVALUATED`, `OVERRIDE_APPLIED`).
- Authenticated actor ID and user role.
- Complete JSON snapshot payload of the entity state before and after modification.

Database user privileges for the application role enforce `INSERT` permissions while strictly revoking `UPDATE` and `DELETE` privileges, ensuring immutability.

### 11.5 Offline Synchronization Manager
The Offline Synchronization Manager operates on the rider's client device to ensure resilient evidence capture in disconnected environments:
- **Local Enqueuing:** Evidence payloads (Base64/blob photo, GPS coordinates, timestamp, OTP, signature strokes) are written immediately to IndexedDB store `pending_evidence`.
- **Status Decoupling:** The rider app marks the delivery locally as `PENDING_SYNC` and allows the rider to continue to their next delivery route without UI blocking.
- **Connection Listening:** A background service listens for browser `online` network events and conducts periodic health probes.
- **Opportunistic Synchronization:** Upon reconnect, the sync manager drains the local queue against the `/api/v1/evidence/submit` endpoint using exponential backoff with randomized jitter.
- **Idempotency Protection:** Each evidence payload includes a client-generated UUID idempotency key, ensuring duplicate network transmissions do not generate duplicate database records.

---

## 12. Database / ER Diagram

### 12.1 Entity Relationship Diagram
The conceptual and logical data model is designed in Third Normal Form (3NF) for transactional stability, while maintaining an append-only structure for audit logs. The complete Entity Relationship diagram is shown below:

![Entity Relationship Diagram](ER_Diagram.png)

### 12.2 Database Schema & Data Dictionary
The relational schema comprises ten primary entities:

#### 1. `users` Table
Stores authentication credentials and role assignments.
- `user_id` (Integer, PK, Auto-increment)
- `name` (VARCHAR(100), NOT NULL)
- `email` (VARCHAR(255), UNIQUE, NOT NULL)
- `phone` (VARCHAR(20), NOT NULL)
- `password_hash` (VARCHAR(255), NOT NULL)
- `role` (ENUM: `restaurant`, `rider`, `customer`, `dispatcher`, `admin`, NOT NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())

#### 2. `restaurants` Table
Stores restaurant partner metadata and geocoordinates.
- `restaurant_id` (Integer, PK, Auto-increment)
- `owner_user_id` (Integer, FK → `users.user_id`, NOT NULL)
- `name` (VARCHAR(150), NOT NULL)
- `address` (TEXT, NOT NULL)
- `latitude` (DOUBLE PRECISION, NOT NULL)
- `longitude` (DOUBLE PRECISION, NOT NULL)

#### 3. `riders` Table
Tracks delivery executive profiles and vehicle details.
- `rider_id` (Integer, PK, Auto-increment)
- `user_id` (Integer, FK → `users.user_id`, UNIQUE, NOT NULL)
- `vehicle_no` (VARCHAR(50), NOT NULL)
- `status` (ENUM: `AVAILABLE`, `BUSY`, `OFFLINE`, DEFAULT `AVAILABLE`)
- `current_lat` (DOUBLE PRECISION, NULLABLE)
- `current_lng` (DOUBLE PRECISION, NULLABLE)

#### 4. `customers` Table
Maintains customer delivery profiles and addresses.
- `customer_id` (Integer, PK, Auto-increment)
- `user_id` (Integer, FK → `users.user_id`, UNIQUE, NOT NULL)
- `delivery_address` (TEXT, NOT NULL)
- `default_lat` (DOUBLE PRECISION, NOT NULL)
- `default_lng` (DOUBLE PRECISION, NOT NULL)

#### 5. `orders` Table
Captures food order transactions and assignments.
- `order_id` (Integer, PK, Auto-increment)
- `restaurant_id` (Integer, FK → `restaurants.restaurant_id`, NOT NULL)
- `customer_id` (Integer, FK → `customers.customer_id`, NOT NULL)
- `rider_id` (Integer, FK → `riders.rider_id`, NULLABLE)
- `status` (ENUM: `CREATED`, `ASSIGNED`, `PICKED_UP`, `IN_TRANSIT`, `DELIVERED`, `DISPUTED`, NOT NULL)
- `total_amount` (NUMERIC(10, 2), NOT NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())
- `assigned_at` (TIMESTAMP WITH TIME ZONE, NULLABLE)

#### 6. `deliveries` Table
Represents the physical fulfillment lifecycle of an order.
- `delivery_id` (UUID / VARCHAR(36), PK)
- `order_id` (Integer, FK → `orders.order_id`, UNIQUE, NOT NULL)
- `target_latitude` (DOUBLE PRECISION, NOT NULL)
- `target_longitude` (DOUBLE PRECISION, NOT NULL)
- `otp_code` (VARCHAR(10), NOT NULL)
- `status` (ENUM: `PENDING`, `IN_TRANSIT`, `DELIVERED`, `NEEDS_MANUAL_REVIEW`, `DISPUTE`, NOT NULL)
- `started_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())
- `completed_at` (TIMESTAMP WITH TIME ZONE, NULLABLE)
- `is_offline_capture` (BOOLEAN, DEFAULT FALSE)
- `synced_at` (TIMESTAMP WITH TIME ZONE, NULLABLE)

#### 7. `evidence` Table
Stores multi-factor evidence signals and automated quality scores.
- `evidence_id` (Integer, PK, Auto-increment)
- `delivery_id` (UUID / VARCHAR(36), FK → `deliveries.delivery_id`, UNIQUE, NOT NULL)
- `photo_url` (TEXT, NOT NULL)
- `signature_url` (TEXT, NULLABLE)
- `captured_latitude` (DOUBLE PRECISION, NULLABLE)
- `captured_longitude` (DOUBLE PRECISION, NULLABLE)
- `captured_timestamp` (TIMESTAMP WITH TIME ZONE, NOT NULL)
- `blur_score` (DOUBLE PRECISION, NULLABLE)
- `brightness_score` (DOUBLE PRECISION, NULLABLE)
- `distance_m` (DOUBLE PRECISION, NULLABLE)
- `photo_score` (DOUBLE PRECISION, NOT NULL)
- `gps_score` (DOUBLE PRECISION, NOT NULL)
- `timestamp_score` (DOUBLE PRECISION, NOT NULL)
- `signature_score` (DOUBLE PRECISION, NOT NULL)
- `otp_score` (DOUBLE PRECISION, NOT NULL)
- `total_quality_score` (DOUBLE PRECISION, NOT NULL)
- `classification` (ENUM: `ACCEPTED`, `NEEDS_MANUAL_REVIEW`, `DISPUTE`, NOT NULL)

#### 8. `disputes` Table
Manages customer-initiated or auto-generated delivery disputes.
- `dispute_id` (Integer, PK, Auto-increment)
- `delivery_id` (UUID / VARCHAR(36), FK → `deliveries.delivery_id`, NOT NULL)
- `raised_by_user_id` (Integer, FK → `users.user_id`, NOT NULL)
- `reason` (VARCHAR(100), NOT NULL)
- `notes` (TEXT, NULLABLE)
- `status` (ENUM: `OPEN`, `UNDER_REVIEW`, `RESOLVED_REFUND`, `RESOLVED_REJECTED`, NOT NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())
- `resolved_at` (TIMESTAMP WITH TIME ZONE, NULLABLE)

#### 9. `dispatcher_overrides` Table
Maintains accountable records of human dispatcher intervention.
- `override_id` (Integer, PK, Auto-increment)
- `delivery_id` (UUID / VARCHAR(36), FK → `deliveries.delivery_id`, NOT NULL)
- `dispatcher_user_id` (Integer, FK → `users.user_id`, NOT NULL)
- `previous_status` (VARCHAR(50), NOT NULL)
- `new_status` (VARCHAR(50), NOT NULL)
- `reason_code` (VARCHAR(50), NOT NULL)
- `justification_text` (TEXT, NOT NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())

#### 10. `audit_logs` Table
Append-only tamper-resistant system log.
- `log_id` (Integer, PK, Auto-increment)
- `entity_type` (VARCHAR(50), NOT NULL)
- `entity_id` (VARCHAR(50), NOT NULL)
- `action` (VARCHAR(50), NOT NULL)
- `actor_user_id` (Integer, FK → `users.user_id`, NOT NULL)
- `payload_json` (JSONB / TEXT, NOT NULL)
- `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT NOW())

### 12.3 Indexing & Integrity Strategy
To ensure sub-second response times and preserve data integrity, the following database constraints and indexes are established:
- **Foreign Key Constraints:** Enforced with `ON DELETE RESTRICT` on evidence and delivery tables to prevent accidental cascading deletions of historical audit trails.
- **Queue Indexing:** Composite B-tree index on `deliveries(status, completed_at)` to accelerate dispatcher queue retrieval.
- **Score Indexing:** Index on `evidence(total_quality_score)` to facilitate analytics aggregations and range queries.
- **Audit Lookup Index:** Composite index on `audit_logs(entity_type, entity_id)` enabling rapid timeline reconstruction for specific orders.
- **Geospatial Indexing:** Coordinate indexing on `evidence(captured_latitude, captured_longitude)` supporting distance queries and geofence evaluations.

---

## 13. UI Design

### 13.1 User Interface Wireframes
The user experience and screen layouts for all primary system roles were designed to ensure high clarity, intuitive touch interactions, and rapid operational workflows. The composite UI wireframes are presented below:

![UI Wireframes](UI_Wireframes.png)

### 13.2 Interface Walkthrough by Role

#### 1. Rider Evidence Capture Interface
- **Active Order Header:** Displays customer name, destination address, and order reference.
- **Camera Viewfinder:** Direct camera preview with real-time blur feedback prompts. If an image is blurry or dark, a warning banner alerts the rider immediately.
- **Live GPS Badge:** Displays device geolocation coordinates and estimated horizontal accuracy radius (in meters). In offline mode, displays a clear warning: *"GPS Offline — Location will be flagged for review."*
- **Verification Inputs:** Numeric keypad for 4-digit customer OTP entry alongside an expandable HTML5 canvas pad for digital signature capture.
- **Offline Sync Status Banner:** Floating indicator showing pending offline queue items and sync status (*"2 deliveries queued locally — will sync automatically when online"*).
- **Completion Action:** High-contrast, full-width button to submit evidence and finalize delivery.

#### 2. Dispatcher Review Workspace
- **Prioritized Queue List:** Left sidebar presenting flagged orders sorted by severity (Disputes first, followed by Manual Review) and wait time.
- **Side-by-Side Evidence Inspection:** Main pane displaying high-resolution delivery photo with OpenCV quality indicators (blur variance score and brightness index).
- **Geospatial Discrepancy Map:** Integrated Leaflet map showing the customer's registered delivery address, the rider's recorded capture coordinates, and a visual 150-meter geofence circle.
- **Score Breakdown Card:** Transparent progress bars displaying component scores across all five criteria.
- **Override Action Modal:** Controlled action drawer prompting the dispatcher to select an outcome (Accept, Reject, Request Re-delivery), choose a mandatory reason code, and enter justification notes.

#### 3. Admin Operations & Analytics Dashboard
- **Top-Line KPI Metrics:** High-level summary cards showing Total Deliveries, Average Evidence Quality Score, Auto-Acceptance Rate (%), and Dispute Rate (%).
- **Score Distribution Histogram:** Graphical breakdown of deliveries across the 0–100 score spectrum, highlighting volumes in Accepted, Review, and Dispute tiers.
- **Dispute Breakdown by Reason:** Categorical bar charts illustrating dispute drivers (e.g., photo quality vs. GPS mismatch).
- **User & Role Management Table:** Administrative grid allowing role assignments and account status updates.

#### 4. Restaurant & Customer Views
- **Restaurant View:** Order creation form with live status badges tracking preparation, rider pickup, and delivery completion.
- **Customer View:** Secure order tracker displaying current rider transit location, customer verification OTP, and post-delivery confirmation photo.

---

## 14. System Workflow

### 14.1 End-to-End Delivery Workflow
The standard lifecycle of a delivery fulfillment follows a coordinated multi-step workflow (mapped to use case **UC-05**):

```
+------------------+       +------------------+       +----------------------+
| Restaurant Order | ----> | Rider Assignment | ----> | Food Transit         |
| Creation (FR-01) |       | & Pickup (FR-04) |       | to Customer Location |
+------------------+       +------------------+       +----------------------+
                                                                 |
                                                                 v
+----------------------------------------------------------------------------+
| Rider Multi-Factor Evidence Capture at Doorstep (FR-05 - FR-09)            |
| - Capture Delivery Photo (OpenCV Laplacian blur check)                     |
| - Acquire GPS Coordinates & Accuracy Radius (Haversine geofence check)     |
| - Collect Customer OTP or Customer Digital Signature                       |
| - Generate Capture Timestamp                                               |
+----------------------------------------------------------------------------+
                                 |
                                 v
                     [ Network Available? ]
                     /                    \
              (YES) /                      \ (NO - Offline Path)
                   v                        v
+-----------------------+        +-------------------------------------------+
| Direct REST Upload    |        | Local Storage in IndexedDB Queue (FR-16)  |
| to Backend API        |        | Route marked complete locally;            |
+-----------------------+        | Opportunistic auto-sync on reconnect (17) |
           |                     +-------------------------------------------+
           |                                          |
           +------------------------------------------+
                                 |
                                 v
+----------------------------------------------------------------------------+
| Evidence Quality Engine (EQE) Scoring (FR-13)                              |
| Composite Score = Photo(25) + GPS(25) + Time(20) + Sig(20) + OTP(10)       |
+----------------------------------------------------------------------------+
                                 |
        +------------------------+------------------------+
        |                                                 |
        v (Score >= 90)                                   v (Score 70 - 89)
+-----------------------+                       +----------------------------+
| AUTOMATIC ACCEPTANCE  |                       | MANUAL REVIEW QUEUE        |
| Delivery Confirmed;   |                       | Flagged to Dispatcher;     |
| Payout Authorized     |                       | 24-Hour SLA (BR-03)        |
+-----------------------+                       +----------------------------+
                                                              |
                                                              v
                                                +----------------------------+
                                                | Dispatcher Override (FR-20)|
                                                | Mandatory Reason Code &    |
                                                | Immutable Audit Log Entry  |
                                                +----------------------------+
```

### 14.2 Dispatcher Review and Override Workflow
When a delivery produces an Evidence Quality Score below 90, it enters the Dispatcher Override Workflow (mapped to use case **UC-11**):
1. **Queue Ingestion:** The delivery is inserted into the Dispatcher Queue prioritized by lowest score and longest wait time.
2. **Evidence Inspection:** The dispatcher opens the order workspace, reviewing raw photos, OpenCV sharpness indicators, GPS distance metrics, and OTP/signature status.
3. **Decision Evaluation:**
   - If evidence demonstrates authentic delivery despite an automated flag (e.g., GPS drift verified against apartment entrance), the dispatcher selects **Accept Delivery**.
   - If evidence demonstrates non-fulfillment or fraudulent capture, the dispatcher selects **Reject / Confirm Dispute**.
   - If evidence is inconclusive, the dispatcher selects **Request Re-delivery**.
4. **Mandatory Justification:** The dispatcher selects an applicable reason code (`CUST_REFUSED_SIG`, `GPS_ADDR_MISMATCH`, etc.) and inputs mandatory justification text.
5. **Audit Commitment:** The override is written to `dispatcher_overrides`, order status is updated, an immutable entry is appended to `audit_logs`, and notifications are dispatched to rider and customer.

### 14.3 Level-1 Data Flow Decomposition
The Level-1 Data Flow Diagram (DFD) decomposes the system into five core functional processes:
1. **Process 1.0 (Capture Evidence):** Receives sensory inputs (camera stream, GPS receiver, touch canvas, keypad) from the Rider client and outputs validated evidence structures.
2. **Process 2.0 (Validate Quality & Score):** Ingests raw evidence, queries delivery address coordinates, executes OpenCV filters and Haversine algorithms, and outputs quality scores and classification enums.
3. **Process 3.0 (Sync & Store):** Mediates between client IndexedDB queues and server PostgreSQL/Object Storage, ensuring idempotency and transactional integrity.
4. **Process 4.0 (Dispatcher Review & Override):** Serves review queues, ingests human override decisions, and commits state updates.
5. **Process 5.0 (Generate Reports & Audit):** Aggregates transactional tables into executive KPI analytics and provides immutable audit trail queries.

### 14.4 Handling of Critical Edge Cases
The system explicitly accommodates five critical real-world edge cases defined in project specifications:

| Edge Case Scenario | System Behavior & Fallback Mechanism | Resulting Quality Score & Classification |
| :--- | :--- | :--- |
| **Case 1: GPS Unavailable (Indoor / Basement)** | Mobile device cannot acquire a satellite GPS fix. System flags `is_offline_capture = true`, assigns 0 points to the GPS criterion, and completes capture using photo, timestamp, and OTP/signature. | Score is capped at **≤ 75 points**. Delivery is routed to **Needs Manual Review**, preventing improper auto-acceptance while keeping the rider moving. |
| **Case 2: Network Unavailable (Dead Zone)** | Device loses cellular connectivity during capture. App commits full evidence payload to on-device IndexedDB queue, marks delivery locally as `PENDING_SYNC`, and prompts rider to proceed. | Evidence synchronizes automatically upon network reconnection; scored instantly upon receipt by the backend. |
| **Case 3: Blurred Delivery Photo** | Rider snaps a blurred photo due to motion or low light. The client/server OpenCV analyzer detects Laplacian variance below threshold. | If online, system rejects the photo and displays an immediate retake prompt with visual guidance. If offline, scored 0 pts for photo. |
| **Case 4: Customer Signature Refusal** | Customer declines on-screen signature for privacy/hygiene reasons. Rider falls back to 4-digit OTP verification. | Signature scores 0 pts, OTP scores 10 pts. Total score reaches 80 pts (Manual Review), where dispatcher verifies OTP match and resolves with code `CUST_REFUSED_SIG`. |
| **Case 5: GPS Location Mismatch (>150m)** | Rider confirms delivery, but device coordinates are 300m away from the customer address. Haversine check detects geofence violation. | GPS criterion awarded 0 pts and flagged `LOCATION_MISMATCH`. Routed to Dispute or Review for dispatcher evaluation against street entrance mapping. |

---

## 15. Implementation Status

### 15.1 Architectural Components Implemented
In accordance with the Review 1 milestone schedule, the foundational architecture, domain models, validation services, and user interfaces have been fully established:

```
CAT_PROJECT/
├── backend/
│   ├── app/
│   │   ├── core/           # Security (JWT, bcrypt) & Configuration settings
│   │   ├── models/         # SQLAlchemy ORM Entities (10 models matching ER design)
│   │   ├── routers/        # FastAPI REST Routers (Auth, Deliveries, Evidence, Dispatcher, Admin, etc.)
│   │   ├── schemas/        # Pydantic v2 Request/Response Validation Schemas
│   │   ├── services/       # Quality Engine, OpenCV Validator, Haversine, Storage
│   │   ├── database.py     # Database engine & session dependency management
│   │   └── main.py         # Application factory, middleware & route mounting
│   └── tests/              # Pytest test suite covering all services and endpoints
└── frontend/
    └── src/
        ├── components/     # SignatureCanvas, LeafletMap, DispatcherWorkspace
        ├── db/             # IndexedDB local storage wrapper (idb library)
        ├── services/       # SyncManager background synchronization service
        └── App.tsx         # Role-based multi-dashboard application shell
```

### 15.2 Backend Service & API Implementation
The backend modular monolith is implemented using Python 3.13 and FastAPI:
- **Core Domain Models (`backend/app/models/`):** Complete ORM representations implemented for `User`, `Restaurant`, `Rider`, `Customer`, `Order`, `Delivery`, `Evidence`, `Dispute`, `DispatcherOverride`, `AuditLog`, and `SyncQueue`.
- **Quality Engine Service (`quality_engine.py`):** Fully operational scoring service implementing the exact 100-point rubric:
  - Photo quality evaluation via `opencv_validator.py` using `cv2.Laplacian` variance for blur detection and mean pixel intensity for brightness.
  - Geofence calculation via `haversine.py` using spherical distance equations against `GPS_MISMATCH_THRESHOLD_METERS = 150.0`.
  - Timestamp, signature, and OTP score aggregation.
  - Deterministic classification into `ACCEPTED`, `NEEDS_MANUAL_REVIEW`, and `DISPUTE`.
- **RESTful Endpoints (`backend/app/routers/`):**
  - `/auth`: Registration, JWT login, current user profile retrieval.
  - `/deliveries`: Order creation, assignment, status querying, and status patching.
  - `/evidence`: Multipart evidence submission, on-the-fly quality evaluation, delivery evidence fetching.
  - `/dispatcher`: Priority review queue retrieval, override submission with reason code validation, full delivery audit history.
  - `/admin`: Operational analytics endpoint aggregating delivery counts, scores, and dispute metrics.
  - `/admin/experiments`: Benchmark and scenario test runners for baseline evaluation.
  - `/validation`: Stakeholder evaluation session recording and Likert scoring endpoints.

### 15.3 Frontend & Offline PWA Implementation
The frontend is constructed using React 19, TypeScript, Vite, and Tailwind CSS:
- **Multi-Role Application Shell (`App.tsx`):** Unified role-switched workspace covering Restaurant, Rider, Customer, Dispatcher, and Admin perspectives.
- **Digital Signature Component (`SignatureCanvas.tsx`):** HTML5 canvas component capturing touch and mouse stroke coordinates, exporting smoothed PNG binaries.
- **Geospatial Map Component (`LeafletMap.tsx`):** Interactive map rendering customer destination coordinates, rider capture point, and a dynamic 150-meter geofence polygon.
- **Dispatcher Workspace Component (`DispatcherWorkspace.tsx`):** Side-by-side review panel displaying image sharpness metrics, delivery details, and override modals.
- **Client-Side Storage (`db/indexedDb.ts`):** Persistent IndexedDB wrapper using the `idb` library managing local stores `pending_evidence` and `cached_deliveries`.
- **Background Sync Engine (`services/syncManager.ts`):** Automatic synchronization manager monitoring window online/offline states and executing queue drain cycles.

### 15.4 Automated Test Suite Verification
The backend implementation was validated through an automated test suite executed using `pytest`. The test execution confirmed **50 passing tests (1 skipped)** across all eight domain suites:

```
============================= test session starts =============================
platform win32 -- Python 3.13.3, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\logesh\Documents\CAT_PROJECT\backend
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.14.1, asyncio-1.4.0
collected 51 items

tests\test_admin.py ......                                               [ 11%]
tests\test_auth.py ...                                                   [ 17%]
tests\test_deliveries.py ..                                              [ 21%]
tests\test_dispatcher.py ..........                                      [ 41%]
tests\test_experiments.py ..............                                 [ 68%]
tests\test_quality_engine.py ...                                         [ 74%]
tests\test_relationships.py ..s                                          [ 80%]
tests\test_validation.py ........                                        [100%]

========== 50 passed, 1 skipped, 1166 warnings in 142.07s (0:02:22) ===========
```

#### Key Validated Behaviors:
- Perfect score calculation (100.0) resulting in `ACCEPTED` classification.
- Missing GPS offline mode resulting in score capped at 75.0 and `NEEDS_MANUAL_REVIEW` classification.
- GPS mismatch (>150m) resulting in score deduction and `DISPUTE` routing.
- Dispatcher override execution requiring mandatory reason codes and generating corresponding entries in both `dispatcher_overrides` and `audit_logs`.
- Immutability of previous and updated delivery statuses across multiple sequential overrides.
- Role-based security validation rejecting unauthorized role access.

---

## 16. Expected Outcomes

Upon full completion and deployment across subsequent project phases (Reviews 2 and 3), the project anticipates the following concrete technical and operational outcomes:

1. **Standardisation of Proof-of-Delivery:** Transformation of fragmented, subjective delivery confirmations into a standardized schema capturing five synchronized evidence signals for every delivery.
2. **Measurable Reduction in Dispute Volume:** Proactive identification and flagging of poor-quality or mismatched evidence before order completion, significantly reducing the volume of customer-initiated complaints.
3. **Elimination of Subjectivity in Dispute Resolution:** Replacement of discretionary support agent decisions with a transparent, explainable 0–100 scoring index backed by mathematical formulas.
4. **Complete Offline Reliability:** 0% evidence capture failure in network-deprived environments (elevators, basements) via durable IndexedDB queuing and automatic background synchronization.
5. **Operational Accountability & Non-Repudiation:** 100% auditable dispatcher intervention history with mandatory reason codes, protecting platforms, riders, and customers in payment and fulfillment disputes.
6. **Quantifiable Benchmark Superiority:** Rigorous experimental validation demonstrating that multi-factor evidence scoring significantly outperforms conventional single-photo confirmation across all critical operational edge cases.

---

## 17. Conclusion

Review 1 successfully establishes the conceptual, architectural, and engineering foundation for the **Standardised Proof-of-Delivery System with Evidence-Quality Checks**. By addressing the systemic vulnerabilities of current delivery confirmation practices—unverified photos, ignored GPS telemetry, skipped customer verification, and network fragility—the project introduces a robust, multi-factor validation framework.

The project deliverables for Review 1 have been fully accomplished:
- A formal, IEEE-compliant Software Requirements Specification defining 26 functional requirements, 10 non-functional requirements, and 9 business rules.
- A layered client-server system architecture featuring an explicit offline-sync boundary.
- A normalized Third Normal Form (3NF) relational database schema coupled with an immutable append-only audit trail.
- Intuitive, role-tailored user interface wireframes for all five stakeholder groups.
- A working backend and frontend prototype whose core Evidence Quality Engine, OpenCV blur validator, Haversine distance calculator, and dispatcher override workflows have been experimentally verified through 50 passing automated tests.

This foundation positions the project effectively for upcoming milestones in Review 2 (full pipeline live demonstration, end-to-end integration) and Review 3 (comprehensive experimental benchmark evaluation, performance stress testing, and final defense).

---

## 18. References

1. **IEEE Std 830-1998**, *"IEEE Recommended Practice for Software Requirements Specifications,"* IEEE Computer Society, 1998.
2. **ISO/IEC/IEEE 29148:2018**, *"Systems and software engineering — Life cycle processes — Requirements engineering,"* International Organization for Standardization, 2018.
3. **R. Szeliski**, *Computer Vision: Algorithms and Applications*, 2nd ed., Springer, 2022.
4. **OpenCV Development Team**, *"OpenCV Documentation — Image Filtering and Laplacian Operator,"* Available: https://docs.opencv.org, accessed 2026.
5. **FastAPI Documentation**, *"FastAPI: Modern, High-Performance Web Framework for Python,"* Available: https://fastapi.tiangolo.com, accessed 2026.
6. **PostgreSQL Global Development Group**, *"PostgreSQL 15 Documentation: The World's Most Advanced Open Source Relational Database,"* Available: https://www.postgresql.org/docs/15/, accessed 2026.
7. **OpenStreetMap Foundation & Leaflet.js**, *"Leaflet — An Open-Source JavaScript Library for Mobile-Friendly Interactive Maps,"* Available: https://leafletjs.com, accessed 2026.
8. **M. Fowler**, *Patterns of Enterprise Application Architecture*, Addison-Wesley Professional, 2002.
9. **N. Offer and D. Winer**, *"Offline-First Web Application Design Patterns,"* W3C Community Group Report, 2021.
10. **Google Developers**, *"Workbox and Progressive Web App Offline Caching Strategies,"* Available: https://developer.chrome.com/docs/workbox, accessed 2026.
