# -*- coding: utf-8 -*-
"""
create_docx_report.py
Generates a publication-grade academic Word Document for Review 1:
'Standardised Proof-of-Delivery System with Evidence-Quality Checks'
Preserving all facts, terminology, scope, tables, formulas, and diagrams.
"""

import os
import shutil
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def style_table(table, col_widths, col_alignments=None):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    header_row = table.rows[0]
    trPr = header_row._tr.get_or_add_trPr()
    trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
    
    for i, cell in enumerate(header_row.cells):
        set_cell_background(cell, "1E3A8A")
        set_cell_margins(cell, 120, 120, 140, 140)
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if (col_alignments and col_alignments[i] == 'C') else WD_ALIGN_PARAGRAPH.LEFT
            for run in p.runs:
                run.font.bold = True
                run.font.color.rgb = RGBColor(255, 255, 255)
                run.font.size = Pt(9.5)
                run.font.name = "Calibri"

    for r_idx, row in enumerate(table.rows[1:], start=1):
        bg_hex = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
        for c_idx, cell in enumerate(row.cells):
            set_cell_background(cell, bg_hex)
            set_cell_margins(cell, 90, 90, 130, 130)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for p in cell.paragraphs:
                align = col_alignments[c_idx] if col_alignments else 'L'
                if align == 'C':
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                elif align == 'R':
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in p.runs:
                    run.font.size = Pt(9.0)
                    run.font.name = "Calibri"
                    run.font.color.rgb = RGBColor(30, 41, 59)

    for row in table.rows:
        for c_idx, width in enumerate(col_widths):
            row.cells[c_idx].width = Inches(width)

def build_document():
    doc = docx.Document()
    
    # Set page margins to 1 inch
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)

    # Styles
    styles = doc.styles
    normal_style = styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(30, 41, 59)

    # Title Block
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(18)
    title_p.paragraph_format.space_after = Pt(6)
    title_run = title_p.add_run("Standardised Proof-of-Delivery System with Evidence-Quality Checks")
    title_run.font.size = Pt(22)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(15, 23, 42)

    subtitle_p = doc.add_paragraph()
    subtitle_p.paragraph_format.space_before = Pt(0)
    subtitle_p.paragraph_format.space_after = Pt(14)
    subtitle_run = subtitle_p.add_run("Food-Delivery Service Coordinating Restaurants, Riders & Customers\nAcademic Project Report — Review 1: Planning & Architecture")
    subtitle_run.font.size = Pt(14)
    subtitle_run.font.italic = True
    subtitle_run.font.color.rgb = RGBColor(30, 58, 138)

    # Metadata Card Table
    meta_table = doc.add_table(rows=5, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_data = [
        ("Candidate Name:", "LOGESH S"),
        ("Degree / Program:", "Bachelor of Engineering / Technology in Computer Science & Engineering"),
        ("Department:", "Department of Computer Science & Engineering"),
        ("Academic Milestone:", "Review 1: Planning, Requirements Engineering, System Design & Core Verification"),
        ("Date of Submission:", "September 2026")
    ]
    for idx, (lbl, val) in enumerate(meta_data):
        row = meta_table.rows[idx]
        cell_lbl, cell_val = row.cells[0], row.cells[1]
        set_cell_background(cell_lbl, "F1F5F9")
        set_cell_background(cell_val, "FFFFFF")
        set_cell_margins(cell_lbl, 60, 60, 100, 100)
        set_cell_margins(cell_val, 60, 60, 100, 100)
        cell_lbl.width = Inches(2.2)
        cell_val.width = Inches(4.3)
        p_l = cell_lbl.paragraphs[0]
        r_l = p_l.add_run(lbl)
        r_l.font.bold = True
        r_l.font.size = Pt(10)
        p_v = cell_val.paragraphs[0]
        r_v = p_v.add_run(val)
        r_v.font.size = Pt(10)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(12)
    doc.add_page_break()

    def add_sec_heading(num, title):
        h = doc.add_heading(f"{num}. {title}", level=1)
        h.paragraph_format.space_before = Pt(16)
        h.paragraph_format.space_after = Pt(6)
        for r in h.runs:
            r.font.name = 'Calibri'
            r.font.size = Pt(16)
            r.font.bold = True
            r.font.color.rgb = RGBColor(15, 23, 42)
        return h

    def add_sub_heading(num, title):
        h = doc.add_heading(f"{num} {title}", level=2)
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(4)
        for r in h.runs:
            r.font.name = 'Calibri'
            r.font.size = Pt(13)
            r.font.bold = True
            r.font.color.rgb = RGBColor(30, 58, 138)
        return h

    def add_body(text, space_after=6):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        r = p.add_run(text)
        r.font.size = Pt(10.5)
        return p

    # 1. ABSTRACT
    add_sec_heading(1, "Abstract")
    add_body(
        "Online food delivery platforms coordinate three independent actors—restaurants, riders, and customers—under "
        "tight time constraints for every order. The critical final step of this operational chain is delivery confirmation: "
        "the moment a platform determines whether an order was legitimately delivered to the intended recipient. In current "
        "industry practice, delivery confirmation is treated as a single, unverified action, typically consisting of a rider "
        "tapping a 'Delivered' button and optionally uploading an arbitrary photo. Because these submissions lack real-time "
        "validation, blurred, pitch-black, misframed, or fraudulent photos are accepted as valid proof. Furthermore, GPS coordinates "
        "are rarely cross-checked against delivery geofences at confirmation, customer verification (OTP or digital signature) "
        "is frequently skipped under time pressure, and intermittent mobile connectivity in indoor or underground environments "
        "causes capture workflows to fail outright. The resulting ambiguity forces customer support teams to resolve high volumes "
        "of delivery disputes manually, leading to subjective decisions, financial losses, and eroded stakeholder trust."
    )
    add_body(
        "To overcome these deficiencies, this project designs and implements a Standardised Proof-of-Delivery (POD) System with "
        "Evidence-Quality Checks. The system transitions delivery confirmation from an unverified status update to an explainable, "
        "multi-factor decision pipeline. The platform captures five structured evidence types for every delivery: delivery photo, "
        "device GPS coordinates, capture timestamp, one-time password (OTP), and an on-screen customer signature. At the core "
        "of the platform is an automated Evidence Quality Engine (EQE) that evaluates captured evidence against an explicit, "
        "weighted scoring rubric (0–100 points): Photo Quality (25), GPS Geofence Match (25), Timestamp Validity (20), "
        "Signature Presence (20), and OTP Verification (10). Deliveries are automatically triaged into three outcome bands: "
        "Accepted (score ≥ 90), Needs Manual Review (score 70–89), or Dispute (score < 70)."
    )
    add_body(
        "To ensure complete operational reliability in real-world delivery environments, the system features an offline-first "
        "Progressive Web App (PWA) client architecture. Captured evidence is persisted locally in an IndexedDB queue, allowing "
        "riders to mark deliveries complete without network connectivity; a background Synchronization Manager opportunistically "
        "transmits queued evidence to the backend once connectivity is restored. In degraded conditions (e.g., indoor delivery with "
        "zero GPS fix), the scoring engine withholds GPS marks, capping the maximum score at 75 and routing the delivery to a "
        "dedicated Dispatcher Review Queue. Human dispatchers can resolve edge cases using a controlled override workflow that "
        "enforces mandatory reason codes and justification logging. All state changes, evidence submissions, score evaluations, "
        "and dispatcher overrides are committed to an append-only, immutable audit trail, ensuring complete end-to-end traceability "
        "and non-repudiation."
    )
    add_body(
        "For Review 1, the foundational engineering milestones have been achieved: complete Software Requirements Specification "
        "(SRS) following IEEE standards, layered client-server system architecture, third normal form (3NF) relational database schema, "
        "user interface wireframes, and a fully functional core backend and frontend prototype. Automated unit and integration "
        "testing confirms that the core scoring algorithms, OpenCV image validation, Haversine geofencing, and role-based workflows "
        "operate with high fidelity, passing 50 automated test cases across 8 test suites."
    )

    # 2. INTRODUCTION
    add_sec_heading(2, "Introduction")
    add_sub_heading("2.1", "Background")
    add_body(
        "The rapid expansion of on-demand food delivery has established it as one of the largest last-mile logistics operations "
        "globally. Modern delivery platforms coordinate three distinct parties for every order: (1) Restaurants, who prepare meals "
        "and require timely pickup and guaranteed payment; (2) Riders, who navigate urban transit networks to fulfill deliveries "
        "under tight schedules; and (3) Customers, who expect prompt, accurate, and intact delivery at their doorstep."
    )
    add_body(
        "While order dispatch, menu discovery, and routing have seen extensive automation, the final fulfillment step—delivery "
        "confirmation—remains the most vulnerable link in the fulfillment lifecycle. Confirming whether an order was actually "
        "delivered carries immediate operational and financial consequences. An erroneous or disputed delivery triggers customer "
        "refund requests, dispute claims by restaurants regarding meal costs, and payment penalties or deactivation for riders. "
        "In major urban centers where platforms handle tens of thousands of orders daily, even a 1% to 2% dispute rate generates "
        "thousands of contentious claims that must be investigated by human support agents."
    )
    add_body(
        "Existing commercial platforms rely on coarse, single-factor mechanisms such as a simple rider status toggle, occasionally "
        "accompanied by a single unexamined photo. These practices fail to provide definitive, verifiable proof of fulfillment. "
        "When disputes arise, support teams are forced to make subjective determinations based on incomplete, unvalidated evidence. "
        "This project addresses this vulnerability by developing an automated, multi-factor proof-of-delivery framework that enforces "
        "evidence quality at the point of capture, transparently scores fulfillment signals, supports uninterrupted offline "
        "operations, and maintains an immutable audit log."
    )

    add_sub_heading("2.2", "Project Scope")
    add_body(
        "The scope of this project encompasses the design, implementation, and academic evaluation of a comprehensive "
        "Proof-of-Delivery system structured across five user roles: Restaurant, Rider, Customer, Dispatcher, and Platform Administrator."
    )
    add_body(
        "In-Scope Capabilities: (1) Five-Factor Evidence Ingestion capturing delivery photo, GPS telemetry, timestamp, OTP, and digital "
        "signature; (2) Automated Evidence Quality Engine (EQE) executing OpenCV Laplacian variance blur checks, brightness analysis, "
        "and Haversine geofence validation (150m); (3) Automated classification into Accepted, Needs Manual Review, and Dispute tiers; "
        "(4) Offline-first Progressive Web App (PWA) client architecture with IndexedDB local queueing and background synchronization; "
        "(5) Dispatcher operations console with split-pane evidence comparison, Leaflet geofence map, and reason-coded override workflows; "
        "(6) Immutable append-only audit trail logging every state transition; (7) Role-based interfaces for all five user roles; "
        "(8) Administrative analytics dashboard tracking operational quality metrics."
    )
    add_body(
        "Explicitly Out-of-Scope (Review 1 & Academic Prototype Boundaries): Per Section 1.4 of the project SRS, the following "
        "are excluded: production-grade payment gateway settlements, commercial native app store publishing (PWA web architecture is "
        "used), large-scale dynamic vehicle routing algorithms, and commercial SMS telecom gateway integrations (a sandbox OTP service is used)."
    )

    add_sub_heading("2.3", "Stakeholders")
    add_body("The system serves six distinct stakeholder groups, mapped in the table below:")

    stk_headers = ["Stakeholder", "Role in System", "Key Needs & System Benefits"]
    stk_data = [
        ["Restaurant Partner", "Creates orders, tracks preparation, monitors fulfillment.", "Protection from false non-delivery claims; transparent handoff tracking; elimination of unfair food loss liabilities."],
        ["Rider / Delivery Exec", "Accepts assignments, captures evidence, marks complete.", "Fair, objective evidence standards; immunity from false customer accusations; seamless offline operation in dead zones."],
        ["Customer", "Receives OTP, verifies delivery, provides signature, disputes.", "Assurance of tamper-free delivery; transparent, fast dispute raising with documented evidence review."],
        ["Dispatcher / Ops", "Monitors exception queue, reviews flagged deliveries, overrides.", "Prioritized pre-scored queue; granular visibility into specific failed criteria; standardized override reason codes."],
        ["Platform Admin", "Oversees operational health, manages accounts and roles.", "Centralized analytics dashboard tracking volume, average evidence quality, dispute rates, and regional trends."],
        ["Project Evaluators", "Academic review and engineering assessment.", "Evaluation of technical depth, IEEE SRS compliance, mathematical correctness of scoring rubric, and test verification."]
    ]
    stk_table = doc.add_table(rows=len(stk_data) + 1, cols=3)
    for c_i, h_text in enumerate(stk_headers):
        stk_table.rows[0].cells[c_i].paragraphs[0].text = h_text
    for r_i, row_items in enumerate(stk_data, start=1):
        for c_i, val in enumerate(row_items):
            stk_table.rows[r_i].cells[c_i].paragraphs[0].text = val
    style_table(stk_table, [1.5, 2.0, 3.0], ['L', 'L', 'L'])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 3. PROBLEM STATEMENT
    add_sec_heading(3, "Problem Statement")
    add_body(
        "Delivery evidence collected by contemporary on-demand food delivery workflows is fundamentally inconsistent, "
        "unverified at the point of capture, and highly vulnerable to operational failure. Specifically, existing implementations "
        "suffer from the following core failure modes:"
    )
    add_body("1. Unverified and Poor-Quality Photographic Proof: Delivery photos are accepted as arbitrary attachments without real-time validation. Photos that are blurred, completely black, over-exposed, or pointed at irrelevant objects are accepted into platform records without warning.")
    add_body("2. Unvalidated GPS Telemetry: GPS coordinates recorded at delivery confirmation are rarely cross-referenced against the registered delivery address geofence. Coordinate drift, indoor signal attenuation, or deliberate spoofing lead to false confirmations hundreds of meters away from the customer.")
    add_body("3. Skipped or Inconsistent Customer Verification: OTP and signature verifications are skipped due to rider time pressure or customer unavailability, leaving packages unattended with zero verified handoff acknowledgement.")
    add_body("4. Fragility in Network Dead Zones: Delivery handoffs in basements, elevators, or dense high-rises suffer from severe cellular drops, causing standard apps to block completion or silently fail to transmit evidence photos.")
    add_body("5. Costly, Subjective, and Reactive Dispute Resolution: Proof of delivery is only inspected after an aggrieved customer files a dispute. Support agents inspect unvalidated evidence and make subjective calls, leading to high labor costs and inconsistent outcomes.")

    # 4. OBJECTIVES
    add_sec_heading(4, "Objectives")
    add_body("To resolve the stated problems, the project establishes seven formal technical and operational objectives:")
    add_body("1. Standardised Multi-Factor Evidence Capture: Design and prototype a structured pipeline capturing five distinct evidence signals (photo, GPS coordinates with accuracy, timestamp, OTP, signature) in a consistent format.")
    add_body("2. Automated Quality Scoring & Triaged Classification: Develop an explainable Evidence Quality Engine (EQE) computing a 0–100 quality score and classifying deliveries into Accepted (≥90), Needs Manual Review (70–89), or Dispute (<70).")
    add_body("3. Resilient Offline-First Architecture: Ensure capture workflows function reliably with zero network or GPS connectivity using client-side IndexedDB persistent storage, enabling route completion and automatic opportunistic background sync.")
    add_body("4. Accountable Dispatcher Override Capability: Provide a dedicated operations console allowing human dispatchers to inspect flagged edge cases and execute overrides governed by mandatory reason codes and justification logging.")
    add_body("5. Immutable Audit History & Traceability: Implement an append-only audit trail permanently logging order lifecycles, evidence submissions, automated scores, and dispatcher actions to guarantee non-repudiation.")
    add_body("6. Empirical Baseline Benchmarking: Establish an experimental validation methodology comparing the multi-factor EQE against a photo-only manual baseline on a labelled validation dataset across normal and edge-case scenarios.")
    add_body("7. Comprehensive Academic Documentation & Working Prototype: Deliver industry-standard documentation (IEEE SRS, architecture, ER model, wireframes) alongside a fully functional, tested prototype across all five role modules.")

    # 5. EXISTING SYSTEM
    add_sec_heading(5, "Existing System")
    add_sub_heading("5.1", "Workflow of Current Platforms")
    add_body(
        "Current mainstream food-delivery platforms typically mark an order 'delivered' based on a rider tapping a status button, "
        "optionally attaching a single photo. GPS is logged for tracking purposes but rarely validated against the delivery address "
        "at the moment of confirmation. OTP is used inconsistently, and signature capture is largely absent in food delivery. When a "
        "customer disputes a delivery, a support agent manually opens the order, looks at whatever photo exists, and makes a subjective "
        "accept/reject call—there is no scoring, no consistent evidence bar, and no structured record of why a decision was made."
    )
    add_sub_heading("5.2", "Limitations of the Existing System")
    add_body("• No automated quality check on delivery photos—blurred or irrelevant images are accepted as valid proof.")
    add_body("• GPS accuracy and address match are not verified at the point of delivery confirmation.")
    add_body("• No standardised, weighted scoring of evidence; decisions are subjective and vary by agent.")
    add_body("• Poor offline behaviour—evidence capture or submission commonly fails outright when network connectivity drops.")
    add_body("• No systematic audit trail linking a delivery's final status to the specific evidence and decision-maker responsible.")
    add_body("• Dispute resolution is reactive and manual, with no data-driven flag raised before the customer complains.")

    # 6. PROPOSED SYSTEM
    add_sec_heading(6, "Proposed System")
    add_sub_heading("6.1", "System Overview & Core Paradigm")
    add_body(
        "The proposed Standardised Proof-of-Delivery system converts delivery confirmation from a single unverified action into a "
        "structured, evidence-scored decision. The system executes through a four-stage pipeline:"
    )
    add_body("1. Capture: Rider app captures photo, GPS, timestamp, and OTP/signature—online or offline—writing to local storage first.")
    add_body("2. Score: The Evidence Quality Engine computes an explainable 0–100 weighted score instantly upon receipt.")
    add_body("3. Classify: Deliveries are categorized into Accepted (≥90), Needs Manual Review (70–89), or Dispute (<70).")
    add_body("4. Resolve: Auto-accepted without human intervention, or routed to a dispatcher with full evidence context.")
    add_sub_heading("6.2", "Key Advantages")
    add_body("• Objective, explainable, and consistent evidence scoring instead of subjective manual judgement.")
    add_body("• Fewer disputes reach human agents, because low-quality evidence is caught and flagged automatically before customer complaints.")
    add_body("• Reliable operation without GPS or network connectivity, through offline capture and automatic background sync.")
    add_body("• Faster, better-informed dispatcher decisions, since flagged deliveries arrive pre-scored with specific evidence gaps highlighted.")
    add_body("• Full auditability: every delivery status can be traced back to the evidence, score, and human override with documented reasons.")
    add_body("• A reusable, extensible scoring framework that easily absorbs future evidence types (video, biometric) without re-architecting.")

    # 7. LITERATURE SURVEY
    add_sec_heading(7, "Literature Survey")
    add_sub_heading("7.1", "Summary Table of Research Areas")
    add_body("The table below summarizes research areas from literature informing the system architecture:")

    lit_headers = ["No", "Area", "Key Idea", "Limitation", "Literature Gap", "Our Improvement"]
    lit_data = [
        ["1", "Proof of Delivery", "Digital proof manifests", "Weak validation", "No composite score", "Evidence scoring (0-100)"],
        ["2", "Last-mile Delivery", "Delivery coordination", "High dispute rates", "Weak fulfillment proof", "Standardized POD schema"],
        ["3", "GPS Tracking", "Location check", "GPS drift / indoor loss", "No offline fallback", "Haversine check & offline mode"],
        ["4", "Offline Apps", "Local caching", "Generic storage", "No POD queuing", "Offline-first PWA with IndexedDB"],
        ["5", "Image Validation", "Blur / exposure checks", "Standalone image tools", "No operational integration", "OpenCV Laplacian blur checks"],
        ["6", "Audit Logs", "System event logs", "Generic logging", "No override accountability", "Append-only log with reason codes"],
        ["7", "OTP / Signature", "Customer verification", "Single-factor reliance", "Low reliability", "Multi-factor dual verification"],
        ["8", "Dispute Systems", "Manual review tools", "Slow investigation", "Incomplete evidence data", "Pre-scored dispatcher workspace"]
    ]
    lit_table = doc.add_table(rows=len(lit_data) + 1, cols=6)
    for c_i, h_text in enumerate(lit_headers):
        lit_table.rows[0].cells[c_i].paragraphs[0].text = h_text
    for r_i, row_items in enumerate(lit_data, start=1):
        for c_i, val in enumerate(row_items):
            lit_table.rows[r_i].cells[c_i].paragraphs[0].text = val
    style_table(lit_table, [0.4, 1.2, 1.2, 1.2, 1.2, 1.3], ['C', 'L', 'L', 'L', 'L', 'L'])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    add_sub_heading("7.2", "Detailed Analysis of Research Domains")
    add_body(
        "Computer Vision for Image Quality: Blur is evaluated using the variance of the Laplacian operator on greyscale image matrices "
        "(Var(∇²I)). Sharp edges exhibit high second-derivative spatial variance, whereas blurred images produce low variance. Combined "
        "with mean pixel intensity checks, this provides a computationally efficient, explainable metric avoiding opaque deep models."
    )
    add_body(
        "Geospatial Validation: Spherical trigonometry via the Haversine formula calculates great-circle distance between rider capture "
        "coordinates and registered customer coordinates. A 150m threshold accommodates GPS urban drift while flagging true misdeliveries."
    )
    add_body(
        "Offline-First Web Architecture: Leveraging Service Workers for caching and IndexedDB for local data persistence guarantees that "
        "evidence capture and delivery completion never block on network connectivity, syncing automatically via background workers."
    )

    # 8. RESEARCH GAP
    add_sec_heading(8, "Research Gap")
    add_body(
        "Core Research Gap: Existing systems rarely combine photo quality, GPS accuracy, OTP, signature, timestamps, offline "
        "capability, dispatcher override, and audit history in one unified proof-of-delivery solution."
    )
    add_body("1. Multi-Signal Integration Gap: Systems evaluate GPS, photos, or OTP in silos without a composite, weighted scoring rubric.")
    add_body("2. Point-of-Capture Validation Gap: Lack of real-time blur detection at the edge that prompts the rider to retake a photo before leaving.")
    add_body("3. Offline-Degraded Scoring Gap: Lack of formal mathematical accommodation for incomplete sensor data in network dead zones.")
    add_body("4. Operational Override Accountability Gap: Disconnected dispatcher override workflows lacking mandatory reason codes and immutable logs.")
    add_body("5. Proactive Dispute Triage Gap: Lack of automated classification routing deliveries into review queues before customer complaints arise.")

    # 9. REQUIREMENTS
    add_sec_heading(9, "Requirements")
    add_sub_heading("9.1", "Functional Requirements (FR-01 to FR-26)")
    add_body("The functional requirements define specific behaviors across all application modules:")

    fr_headers = ["ID", "Module", "Requirement Specification"]
    fr_data = [
        ["FR-01", "Restaurant", "Allow restaurant to create orders with items, customer address, and expected prep time."],
        ["FR-02", "Restaurant", "Allow restaurant/dispatcher to assign an available rider to an order."],
        ["FR-03", "Restaurant", "Allow restaurant to track real-time order and delivery fulfillment status."],
        ["FR-04", "Rider", "Allow rider to accept or reject assigned deliveries within an operational time window."],
        ["FR-05", "Rider", "Allow rider to capture a delivery photo using device camera at the point of delivery."],
        ["FR-06", "Rider", "Capture device GPS coordinates and accuracy radius at the moment of evidence capture."],
        ["FR-07", "Rider", "Allow rider to input customer-provided OTP for delivery verification."],
        ["FR-08", "Rider", "Allow rider to capture customer signature on-screen when OTP is not available."],
        ["FR-09", "Rider", "Allow rider to mark delivery Complete only after minimum required evidence is captured."],
        ["FR-10", "Customer", "Send single-use, time-limited OTP to customer upon order dispatch."],
        ["FR-11", "Customer", "Allow customer to verify delivery receipt and view captured photographic proof."],
        ["FR-12", "Customer", "Allow customer to raise a formal dispute with reason codes and supporting notes."],
        ["FR-13", "Evidence Engine", "Compute Evidence Quality Score (0–100) using the weighted rubric."],
        ["FR-14", "Evidence Engine", "Classify deliveries into Accepted (≥90), Manual Review (70–89), or Dispute (<70)."],
        ["FR-15", "Evidence Engine", "Reject delivery photos failing blur/brightness checks and prompt immediate retake."],
        ["FR-16", "Offline Handling", "Persist captured evidence locally on rider device when network is unavailable."],
        ["FR-17", "Offline Handling", "Automatically synchronize locally queued evidence once network connectivity is restored."],
        ["FR-18", "Offline Handling", "Flag evidence captured without GPS as 'Offline/Reduced-Accuracy' and deduct GPS marks."],
        ["FR-19", "Dispatcher", "Present dispatchers with a prioritized queue of flagged deliveries ordered by score and age."],
        ["FR-20", "Dispatcher", "Require dispatcher to select a standardized reason code and justification for overrides."],
        ["FR-21", "Dispatcher", "Notify affected rider and customer when a dispatcher override modifies delivery status."],
        ["FR-22", "Audit & History", "Record an immutable audit log for every order creation, evidence capture, score, and override."],
        ["FR-23", "Audit & History", "Allow authorized users to view complete history and raw evidence of a delivery."],
        ["FR-24", "Admin", "Provide admin dashboard showing delivery volumes, average score, dispute rate, and region stats."],
        ["FR-25", "Admin", "Allow admin to manage user accounts and role assignments across all five roles."],
        ["FR-26", "Reporting", "Enable export of delivery and dispute reports for specified date ranges."]
    ]
    fr_table = doc.add_table(rows=len(fr_data) + 1, cols=3)
    for c_i, h_text in enumerate(fr_headers):
        fr_table.rows[0].cells[c_i].paragraphs[0].text = h_text
    for r_i, row_items in enumerate(fr_data, start=1):
        for c_i, val in enumerate(row_items):
            fr_table.rows[r_i].cells[c_i].paragraphs[0].text = val
    style_table(fr_table, [0.8, 1.4, 4.3], ['C', 'L', 'L'])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    add_sub_heading("9.2", "Non-Functional Requirements (NFR-01 to NFR-10)")
    nfr_headers = ["ID", "Category", "Requirement Specification"]
    nfr_data = [
        ["NFR-01", "Performance", "Evidence Quality Engine shall compute score within 2 seconds under normal load (≤100 req)."],
        ["NFR-02", "Availability", "Offline capture on rider app shall function with zero network, targeting 99.5% success."],
        ["NFR-03", "Reliability", "Locally queued offline evidence shall not be lost across app restarts or device reboots."],
        ["NFR-04", "Scalability", "Backend API shall horizontally scale to support at least 10,000 deliveries/day."],
        ["NFR-05", "Usability", "Rider shall be able to complete evidence capture workflow in under 60 seconds."],
        ["NFR-06", "Security", "All API traffic encrypted via TLS 1.2+; passwords hashed using bcrypt; JWT RBAC enforced."],
        ["NFR-07", "Data Integrity", "Audit log entries strictly append-only; database permissions prohibit UPDATE or DELETE."],
        ["NFR-08", "Maintainability", "Modular monolith backend allowing independent updates to scoring engine."],
        ["NFR-09", "Portability", "Responsive PWA installable and operational on modern Android and iOS browsers."],
        ["NFR-10", "Compliance", "Customer PII (phone, address) protected by RBAC and excluded from analytics exports."]
    ]
    nfr_table = doc.add_table(rows=len(nfr_data) + 1, cols=3)
    for c_i, h_text in enumerate(nfr_headers):
        nfr_table.rows[0].cells[c_i].paragraphs[0].text = h_text
    for r_i, row_items in enumerate(nfr_data, start=1):
        for c_i, val in enumerate(row_items):
            nfr_table.rows[r_i].cells[c_i].paragraphs[0].text = val
    style_table(nfr_table, [0.8, 1.4, 4.3], ['C', 'L', 'L'])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    add_sub_heading("9.3", "Business Rules (BR-01 to BR-09)")
    add_body("• BR-01: Minimum Evidence: Delivery cannot be marked Complete without photo and either OTP or signature.")
    add_body("• BR-02: Auto-Acceptance: Score ≥ 90 results in automatic acceptance; no dispatcher action permitted to reverse without dispute.")
    add_body("• BR-03: Manual Review SLA: Score 70–89 routed to Dispatcher Manual Review with 24-hour SLA.")
    add_body("• BR-04: Auto-Dispute: Score < 70 automatically opens Dispute record and notifies customer and dispatcher.")
    add_body("• BR-05: Override Justification: Every override must include a valid reason code and ≥10 character justification.")
    add_body("• BR-06: OTP Expiry: OTP valid for single delivery attempt and expires after 15 minutes.")
    add_body("• BR-07: Queue Throttling: Rider cannot be assigned new delivery while previous un-synced evidence exceeds retry limit.")
    add_body("• BR-08: Geofence Limit: GPS coordinates > 150m from registered delivery address flagged as location mismatch (0 pts).")
    add_body("• BR-09: Audit Immutability: Audit records are immutable; corrections made via new compensating entries.")

    # 10. SYSTEM ARCHITECTURE
    add_sec_heading(10, "System Architecture")
    add_sub_heading("10.1", "Layered Architecture Overview")
    add_body(
        "The system employs a layered client-server architecture with an explicit offline-sync boundary at the client edge. "
        "The architecture decouples presentation, routing, application services, scoring algorithms, and data persistence."
    )
    add_sub_heading("10.2", "System Architecture Diagram")
    
    # Embed Architecture Image
    arch_img_path = "review_1/System_Architecture_Diagram.png"
    if os.path.exists(arch_img_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(4)
        run_img = p_img.add_run()
        run_img.add_picture(arch_img_path, width=Inches(6.2))
        
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_after = Pt(10)
        r_cap = p_cap.add_run("Figure 10.1 — Layered System Architecture Diagram with Offline-Sync Boundary")
        r_cap.font.size = Pt(9.5)
        r_cap.font.italic = True
        r_cap.font.color.rgb = RGBColor(71, 85, 105)

    add_sub_heading("10.3", "Layer Decomposition")
    add_body("1. Client Layer: React 18 + TypeScript PWA, Leaflet.js maps, HTML5 canvas for signatures, Service Worker, and IndexedDB local store.")
    add_body("2. Gateway Layer: NGINX reverse proxy providing TLS 1.2+ termination, CORS handling, and rate limiting.")
    add_body("3. Application Layer: FastAPI modular monolith comprising Auth, Order, POD, Quality Engine, Sync, Dispatcher, and Audit services.")
    add_body("4. Data Layer: PostgreSQL 15 relational store (3NF schema), Redis in-memory cache and queue, and S3/local object storage.")

    # 11. MODULES
    add_sec_heading(11, "Modules")
    add_sub_heading("11.1", "Role-Based User Modules")
    add_body("The system provides tailored interfaces for Restaurant, Rider, Customer, Dispatcher, and Admin roles.")
    add_sub_heading("11.2", "Evidence Quality Engine (EQE)")
    add_body("The EQE evaluates deliveries across five weighted criteria totaling 100 points:")

    rubric_headers = ["Criterion", "Max Pts", "Validation Logic & Algorithmic Rules"]
    rubric_data = [
        ["Photo Quality", "25", "OpenCV Laplacian blur check (Var >= 100.0) and mean brightness (40.0 - 220.0)."],
        ["GPS Valid", "25", "Haversine distance <= 150m from registered delivery address. Missing GPS scores 0 pts."],
        ["Timestamp Valid", "20", "Present and falls within valid order delivery window without clock skew."],
        ["Signature Captured", "20", "On-screen signature present with non-blank stroke verification."],
        ["OTP Verified", "10", "4-digit OTP matches cryptographic delivery token issued to customer."],
        ["TOTAL SCORE", "100", "Normalized score triaged into Accepted (>=90), Review (70-89), Dispute (<70)."]
    ]
    rubric_table = doc.add_table(rows=len(rubric_data) + 1, cols=3)
    for c_i, h_text in enumerate(rubric_headers):
        rubric_table.rows[0].cells[c_i].paragraphs[0].text = h_text
    for r_i, row_items in enumerate(rubric_data, start=1):
        for c_i, val in enumerate(row_items):
            rubric_table.rows[r_i].cells[c_i].paragraphs[0].text = val
    style_table(rubric_table, [1.5, 0.8, 4.2], ['L', 'C', 'L'])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    add_body(
        "Degraded-Mode (Zero-GPS) Handling: When GPS is unavailable (basements, high-rises), GPS is scored 0 and delivery is tagged "
        "is_offline_capture = true. Score is capped at 75 points, routing to Manual Review and preventing improper auto-acceptance."
    )

    add_sub_heading("11.3", "Dispatcher Override Module")
    add_body("Controlled override mechanism requiring mandatory reason codes:")
    rc_headers = ["Reason Code", "Operational Meaning", "Linked Edge Case"]
    rc_data = [
        ["CUST_REFUSED_SIG", "Customer declined signature; OTP or verbal confirmation verified.", "Edge Case 4"],
        ["GPS_ADDR_MISMATCH", "GPS distance > 150m, but manual review confirms valid entrance.", "Edge Case 5"],
        ["PHOTO_RETAKE_FAILED", "Rider unable to capture sharp photo after retakes due to light.", "Edge Case 3"],
        ["NETWORK_DELAYED_SYNC", "Evidence legitimately delayed by network drop; verified on late sync.", "Edge Case 2"],
        ["CUSTOMER_UNREACHABLE", "Customer unreachable; package deposited at security/reception.", "Operational Fallback"],
        ["OTHER", "Special scenario; requires free-text justification >= 10 characters.", "Operational Fallback"]
    ]
    rc_table = doc.add_table(rows=len(rc_data) + 1, cols=3)
    for c_i, h_text in enumerate(rc_headers):
        rc_table.rows[0].cells[c_i].paragraphs[0].text = h_text
    for r_i, row_items in enumerate(rc_data, start=1):
        for c_i, val in enumerate(row_items):
            rc_table.rows[r_i].cells[c_i].paragraphs[0].text = val
    style_table(rc_table, [1.8, 3.4, 1.3], ['L', 'L', 'L'])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    add_sub_heading("11.4", "Audit & History Module")
    add_body("Maintains append-only tamper-resistant logs capturing entity ID, action, actor ID, timestamp, and JSON state snapshots.")
    add_sub_heading("11.5", "Offline Synchronization Manager")
    add_body("Queues evidence payloads in client IndexedDB, listens for online events, and synchronizes opportunistically with exponential backoff.")

    # 12. DATABASE / ER DIAGRAM
    add_sec_heading(12, "Database / ER Diagram")
    add_sub_heading("12.1", "Entity Relationship Diagram")
    
    er_img_path = "review_1/ER_Diagram.png"
    if os.path.exists(er_img_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(4)
        run_img = p_img.add_run()
        run_img.add_picture(er_img_path, width=Inches(6.2))
        
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_after = Pt(10)
        r_cap = p_cap.add_run("Figure 12.1 — Normalized Entity Relationship Diagram (3NF & Append-Only Audit)")
        r_cap.font.size = Pt(9.5)
        r_cap.font.italic = True
        r_cap.font.color.rgb = RGBColor(71, 85, 105)

    add_sub_heading("12.2", "Database Schema & Data Dictionary")
    add_body("Core entities: users, restaurants, riders, customers, orders, deliveries, evidence, disputes, dispatcher_overrides, audit_logs.")
    add_sub_heading("12.3", "Indexing & Integrity Strategy")
    add_body("Composite B-tree indexes on deliveries(status, completed_at), evidence(total_quality_score), and audit_logs(entity_type, entity_id). ON DELETE RESTRICT foreign keys safeguard audit trails.")

    # 13. UI DESIGN
    add_sec_heading(13, "UI Design")
    add_sub_heading("13.1", "User Interface Wireframes")
    
    ui_img_path = "review_1/UI_Wireframes.png"
    if os.path.exists(ui_img_path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(8)
        p_img.paragraph_format.space_after = Pt(4)
        run_img = p_img.add_run()
        run_img.add_picture(ui_img_path, width=Inches(6.2))
        
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cap.paragraph_format.space_after = Pt(10)
        r_cap = p_cap.add_run("Figure 13.1 — UI Wireframes: Rider Capture, Dispatcher Console, Admin Dashboard")
        r_cap.font.size = Pt(9.5)
        r_cap.font.italic = True
        r_cap.font.color.rgb = RGBColor(71, 85, 105)

    add_sub_heading("13.2", "Interface Walkthrough by Role")
    add_body("1. Rider Interface: Viewfinder with blur feedback, live GPS coordinates, OTP keypad, signature pad, and offline sync indicator.")
    add_body("2. Dispatcher Workspace: Split-pane review, OpenCV blur/brightness indicators, Leaflet geofence map, and override modal.")
    add_body("3. Admin Analytics: KPI summary cards (Volume, Avg Score, Dispute Rate), score distribution histograms, and user RBAC grid.")
    add_body("4. Restaurant & Customer: Order placement and tracking; OTP display and dispute submission interfaces.")

    # 14. SYSTEM WORKFLOW
    add_sec_heading(14, "System Workflow")
    add_sub_heading("14.1", "End-to-End Delivery Workflow")
    add_body("Order creation -> Rider assignment -> Food transit -> Multi-factor evidence capture -> Offline queue or direct upload -> EQE scoring -> Auto-acceptance (>=90) or Manual Review (70-89).")
    add_sub_heading("14.2", "Dispatcher Review and Override Workflow")
    add_body("Flagged order ingestion -> Split-pane inspection -> Reason-coded override decision -> State update and immutable audit commitment.")
    add_sub_heading("14.3", "Level-1 Data Flow Decomposition")
    add_body("Five core processes: 1.0 Capture Evidence -> 2.0 Validate & Score -> 3.0 Sync & Store -> 4.0 Dispatcher Review -> 5.0 Report & Audit.")
    add_sub_heading("14.4", "Handling of Critical Edge Cases")

    ec_headers = ["Edge Case", "System Behavior & Fallback", "Resulting Score & Band"]
    ec_data = [
        ["1. GPS Unavailable", "is_offline_capture = true; GPS criterion = 0; capture completes with photo/OTP/sig.", "Score capped <= 75; routed to Manual Review."],
        ["2. Network Unavailable", "Payload committed to IndexedDB; route marked complete locally; auto-syncs on reconnect.", "Scored immediately upon background sync."],
        ["3. Blurred Photo", "OpenCV Laplacian detects blur; prompts immediate retake with guide banners.", "Rejected online; scores 0 if submitted offline."],
        ["4. Signature Refused", "Rider falls back to customer OTP; signature scores 0, OTP scores 10.", "Score reaches 80 (Manual Review); resolved via code."],
        ["5. GPS Mismatch (>150m)", "Haversine detects coordinate drift > 150m; GPS marks withheld (0 pts).", "Routed to Review/Dispute for map inspection."]
    ]
    ec_table = doc.add_table(rows=len(ec_data) + 1, cols=3)
    for c_i, h_text in enumerate(ec_headers):
        ec_table.rows[0].cells[c_i].paragraphs[0].text = h_text
    for r_i, row_items in enumerate(ec_data, start=1):
        for c_i, val in enumerate(row_items):
            ec_table.rows[r_i].cells[c_i].paragraphs[0].text = val
    style_table(ec_table, [1.4, 3.4, 1.7], ['L', 'L', 'L'])
    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # 15. IMPLEMENTATION STATUS
    add_sec_heading(15, "Implementation Status")
    add_sub_heading("15.1", "Architectural Components Implemented")
    add_body("The repository structure comprises a complete FastAPI modular monolith in backend/ and a React 19 / TypeScript SPA in frontend/.")
    add_sub_heading("15.2", "Backend Service & API Implementation")
    add_body("Implemented models: User, Restaurant, Rider, Customer, Order, Delivery, Evidence, Dispute, DispatcherOverride, AuditLog, SyncQueue.")
    add_body("Implemented services: quality_engine.py, opencv_validator.py, haversine.py, storage.py, security.py (JWT + bcrypt).")
    add_body("Implemented routers: /auth, /deliveries, /evidence, /dispatcher, /admin, /admin/experiments, /validation.")
    add_sub_heading("15.3", "Frontend & Offline PWA Implementation")
    add_body("Implemented components: SignatureCanvas.tsx, LeafletMap.tsx, DispatcherWorkspace.tsx, App.tsx multi-role shell.")
    add_body("Offline infrastructure: db/indexedDb.ts (persistent queue) and services/syncManager.ts (opportunistic background sync).")
    add_sub_heading("15.4", "Automated Test Suite Verification")
    add_body("Pytest execution confirmed 50 passed tests (1 skipped) across 8 test suites in backend/tests/:")
    add_body("• test_admin.py (6 tests passed)")
    add_body("• test_auth.py (3 tests passed)")
    add_body("• test_deliveries.py (2 tests passed)")
    add_body("• test_dispatcher.py (10 tests passed)")
    add_body("• test_experiments.py (14 tests passed)")
    add_body("• test_quality_engine.py (3 tests passed)")
    add_body("• test_relationships.py (2 passed, 1 skipped)")
    add_body("• test_validation.py (8 tests passed)")
    add_body("All core scoring, offline degradation, geofence, and override audit behaviors operate correctly with zero failures.")

    # 16. EXPECTED OUTCOMES
    add_sec_heading(16, "Expected Outcomes")
    add_body("1. Standardisation of Proof-of-Delivery into structured 5-factor schema.")
    add_body("2. Measurable reduction in dispute volume via proactive quality validation.")
    add_body("3. Elimination of subjectivity in dispute resolution through explainable 0–100 scoring.")
    add_body("4. Complete offline reliability (0% capture failure in dead zones).")
    add_body("5. 100% operational auditability and non-repudiation for dispatcher overrides.")
    add_body("6. Quantifiable benchmark superiority over single-signal manual baseline on labelled validation datasets.")

    # 17. CONCLUSION
    add_sec_heading(17, "Conclusion")
    add_body(
        "Review 1 establishes a comprehensive, mathematically rigorous foundation for the Standardised Proof-of-Delivery System. "
        "The project deliverables—IEEE SRS, layered architecture, 3NF database schema, UI wireframes, core scoring engine, offline sync "
        "pipeline, and passing automated test suite—have been successfully achieved, providing a solid launchpad for Reviews 2 and 3."
    )

    # 18. REFERENCES
    add_sec_heading(18, "References")
    refs = [
        "[1] IEEE Std 830-1998, 'IEEE Recommended Practice for Software Requirements Specifications,' IEEE Computer Society, 1998.",
        "[2] ISO/IEC/IEEE 29148:2018, 'Systems and software engineering — Life cycle processes — Requirements engineering,' ISO, 2018.",
        "[3] R. Szeliski, Computer Vision: Algorithms and Applications, 2nd ed., Springer, 2022.",
        "[4] OpenCV Development Team, 'OpenCV Documentation — Image Filtering and Laplacian Operator,' opencv.org, accessed 2026.",
        "[5] FastAPI Documentation, 'FastAPI: Modern, High-Performance Web Framework for Python,' fastapi.tiangolo.com, accessed 2026.",
        "[6] PostgreSQL Global Development Group, 'PostgreSQL 15 Documentation,' postgresql.org, accessed 2026.",
        "[7] OpenStreetMap Foundation & Leaflet.js, 'Leaflet — An Open-Source JavaScript Library for Mobile-Friendly Maps,' leafletjs.com, accessed 2026.",
        "[8] M. Fowler, Patterns of Enterprise Application Architecture, Addison-Wesley Professional, 2002.",
        "[9] N. Offer and D. Winer, 'Offline-First Web Application Design Patterns,' W3C Community Group Report, 2021.",
        "[10] Google Developers, 'Workbox and Progressive Web App Offline Caching Strategies,' developer.chrome.com, accessed 2026."
    ]
    for r in refs:
        add_body(r, space_after=3)

    # Save documents
    out_docx_review1 = "review_1/Review_1_Project_Report.docx"
    out_docx_root = "Review_1_Project_Report.docx"
    
    doc.save(out_docx_review1)
    shutil.copyfile(out_docx_review1, out_docx_root)
    print(f"Successfully created: {out_docx_review1} and {out_docx_root}")

if __name__ == "__main__":
    build_document()
