import React from 'react';
import {
  AlertTriangle,
  ExternalLink,
  Eye,
  RefreshCw,
  ArrowRight
} from 'lucide-react';

interface BenchmarkExperimentCardProps {
  runDetail: any;
  loading: boolean;
  onViewFullExperiment: () => void;
}

export const BenchmarkExperimentCard: React.FC<BenchmarkExperimentCardProps> = ({
  runDetail,
  loading,
  onViewFullExperiment
}) => {
  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl text-center py-10 space-y-2">
        <RefreshCw className="w-6 h-6 text-amber-500 animate-spin mx-auto" />
        <p className="text-xs text-slate-400">Loading stored benchmark evaluation...</p>
      </div>
    );
  }

  if (!runDetail) {
    return null;
  }

  const base = runDetail.baseline_metrics;
  const prop = runDetail.proposed_metrics;

  const metrics = [
    {
      label: 'Evidence Completeness',
      base: `${(base.evidence_completeness_rate * 100).toFixed(0)}%`,
      prop: `${(prop.evidence_completeness_rate * 100).toFixed(0)}%`,
      desc: 'All 5 modalities verified',
      highlight: true
    },
    {
      label: 'Disputes Resolved',
      base: `${base.disputes_resolved}`,
      prop: `${prop.disputes_resolved}`,
      desc: 'Dispatcher overrides with reason code',
      highlight: true
    },
    {
      label: 'System Accuracy',
      base: `${(base.accuracy * 100).toFixed(0)}%`,
      prop: `${(prop.accuracy * 100).toFixed(0)}%`,
      desc: 'Correct classification outcome'
    },
    {
      label: 'Dispute Rate',
      base: `${(base.dispute_rate * 100).toFixed(0)}%`,
      prop: `${(prop.dispute_rate * 100).toFixed(0)}%`,
      desc: 'Deliveries flagged for arbitration'
    }
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-5">
      <div className="flex flex-wrap justify-between items-start gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-md">
              STORED BENCHMARK
            </span>
            <span className="text-xs font-mono text-slate-400">{runDetail.run.id}</span>
          </div>
          <h3 className="text-base font-bold text-slate-100 mt-1 flex items-center space-x-2">
            <RefreshCw className="w-4 h-4 text-amber-500" />
            <span>Empirical Evaluation: Traditional Baseline vs Proposed System</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            50 realistic test scenarios evaluated under both single-photo baseline and multi-factor EQE engine.
          </p>
        </div>

        <button
          onClick={onViewFullExperiment}
          className="btn-primary text-xs font-semibold px-4 py-2 rounded-xl flex items-center space-x-1.5 transition btn-press-feedback"
        >
          <span>Inspect Full 50 Scenarios</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Side-by-side KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {metrics.map((m, idx) => (
          <div
            key={idx}
            className={`p-3.5 rounded-2xl border ${
              m.highlight
                ? 'bg-slate-950/80 border-slate-700/80'
                : 'bg-slate-950/50 border-slate-800/60'
            } space-y-2`}
          >
            <span className="text-xs font-semibold text-slate-300 block">{m.label}</span>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="bg-rose-950/20 border border-rose-900/30 rounded-lg p-1.5">
                <span className="text-[10px] text-rose-400 block uppercase">Baseline</span>
                <span className="text-sm font-bold text-slate-200">{m.base}</span>
              </div>
              <div className="bg-emerald-950/20 border border-emerald-900/30 rounded-lg p-1.5">
                <span className="text-[10px] text-emerald-400 block uppercase">Proposed</span>
                <span className="text-sm font-bold text-emerald-400">{m.prop}</span>
              </div>
            </div>
            <span className="text-[10px] text-slate-500 block leading-tight">{m.desc}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

interface LimitationsReportCardProps {
  compact?: boolean;
}

export const LimitationsReportCard: React.FC<LimitationsReportCardProps> = () => {
  const limitations = [
    {
      code: 'LIMIT-01',
      title: 'Vertical Elevation & Urban Canyon Geofencing',
      desc: 'Standard HTML5 Geolocation provides horizontal coordinates (latitude/longitude) with an accuracy radius, but cannot resolve vertical altitude (floor level) in multi-story high-rise apartments or dense urban canyons with GPS multipath interference.',
      mitigation: 'Tri-band routing caps score at 75 without GPS and safely routes to Dispatcher Manual Review rather than penalizing couriers.'
    },
    {
      code: 'LIMIT-02',
      title: 'Semantic Content vs Structural Blur Analysis',
      desc: 'OpenCV Laplacian variance verifies focus sharpness and pixel intensity verifies ambient lighting, but does not perform semantic visual object classification to verify whether the photograph contains the actual parcel or meal packaging.',
      mitigation: 'Coupled with 4-digit recipient OTP and digital signature to ensure physical presence even if camera scene is ambiguous.'
    },
    {
      code: 'LIMIT-03',
      title: 'Client Clock Skew & Replay Boundaries',
      desc: 'Client device timestamps are checked against server time using a 15-minute sanity window. In extended offline mode, device hardware clock tampering is theoretically possible without hardware security module (HSM) attestation.',
      mitigation: 'Append-only server receipt timestamps record actual network ingress time and compute differential flags.'
    },
    {
      code: 'LIMIT-04',
      title: 'Mobile Browser Sandbox Storage Quotas',
      desc: 'Offline IndexedDB storage on mobile devices is subject to browser-controlled storage quotas and aggressive storage eviction policies under low-disk conditions on budget courier smartphones.',
      mitigation: 'PWA service worker limits raw photo sizes to compressed JPEG blobs and auto-clears synced items after confirmation.'
    },
    {
      code: 'LIMIT-05',
      title: 'Dispatcher Review Queue Scalability',
      desc: 'Manual review queues require human intervention. During extreme weather conditions or platform-wide connectivity outages, review queue depth can spike and create customer confirmation latency.',
      mitigation: 'Dispatcher UI prioritizes orders by lowest quality score and supports standardized reason-coded overrides with full audit accountability.'
    }
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
      <div>
        <h3 className="text-sm font-bold uppercase text-slate-300 flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <span>System Limitations & Operational Constraints Report</span>
        </h3>
        <p className="text-xs text-slate-400 mt-1">
          Review-1 academic limitations analysis and engineering boundary conditions for real-world last-mile operations.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
        {limitations.map((item, idx) => (
          <div
            key={idx}
            className="p-4 bg-slate-950/70 border border-slate-800/80 rounded-2xl space-y-2 text-xs"
          >
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-200">{item.title}</span>
              <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded">
                {item.code}
              </span>
            </div>
            <p className="text-slate-400 leading-relaxed">{item.desc}</p>
            <div className="bg-slate-900/60 p-2 rounded-xl border border-slate-800/60 text-[11px] text-slate-300">
              <span className="text-emerald-400 font-semibold">Mitigation: </span>
              {item.mitigation}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export const DemoMediaHubCard: React.FC = () => {
  const deliverables = [
    {
      title: 'System Architecture Diagram',
      desc: '4-layer decomposition: PWA Client, FastAPI Service, Evidence Quality Engine (EQE), and Append-Only Data Store.',
      path: '/review_1/System_Architecture_Diagram.png',
      badge: 'Architecture',
      type: 'image'
    },
    {
      title: 'Entity Relationship Diagram (ERD)',
      desc: 'Complete Third Normal Form (3NF) relational schema covering 10 domain entities and append-only audit protection.',
      path: '/review_1/ER_Diagram.png',
      badge: 'Database (3NF)',
      type: 'image'
    },
    {
      title: 'UI Wireframes & Interface Flow',
      desc: 'Screen layouts for Courier Capture, Recipient Tracking, Dispatcher Review, and Admin Analytics consoles.',
      path: '/review_1/UI_Wireframes.png',
      badge: 'UI Wireframes',
      type: 'image'
    },
    {
      title: 'Review 1 Academic Project Report',
      desc: 'Comprehensive 800+ line project report detailing requirements engineering, literature survey, and evaluation.',
      path: '/review_1/Review_1_Project_Report.docx',
      badge: 'Document',
      type: 'doc'
    },
    {
      title: 'Review 1 Presentation Slide Deck',
      desc: 'Academic presentation covering project background, problem formulation, system design, and prototype demonstration.',
      path: '/review_1/Proof_of_Delivery_Review1.pptx',
      badge: 'Slides',
      type: 'presentation'
    },
    {
      title: 'Demonstration Video & Walkthrough',
      desc: 'Recorded end-to-end walkthrough demonstrating Courier Offline PWA capture, sync, and Dispatcher override workflow.',
      path: '#demo-video',
      badge: 'Video Walkthrough',
      type: 'video'
    }
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
      <div>
        <h3 className="text-sm font-bold uppercase text-slate-300 flex items-center space-x-2">
          <Eye className="w-5 h-5 text-slate-100" />
          <span>Demo Media, Diagrams & Academic Deliverables Hub</span>
        </h3>
        <p className="text-xs text-slate-400 mt-1">
          Quick-access links and artifacts for Review 1 project presentation, wireframes, diagrams, and video walkthrough.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {deliverables.map((item, idx) => (
          <div
            key={idx}
            className="bg-slate-950 p-4 rounded-2xl border border-slate-800/80 space-y-2 flex flex-col justify-between text-xs hover:border-slate-700 transition"
          >
            <div className="space-y-1.5">
              <div className="flex justify-between items-start gap-2">
                <span className="font-bold text-slate-200">{item.title}</span>
                <span className="px-1.5 py-0.5 text-[9px] font-mono font-bold bg-slate-800 text-slate-300 rounded shrink-0">
                  {item.badge}
                </span>
              </div>
              <p className="text-slate-400 text-[11px] leading-relaxed">{item.desc}</p>
            </div>

            <div className="pt-2 border-t border-slate-800/60 flex justify-between items-center text-[11px]">
              <span className="text-slate-500 font-mono truncate max-w-[170px]">{item.path}</span>
              <a
                href={item.path}
                target="_blank"
                rel="noreferrer"
                className="text-slate-300 hover:text-white flex items-center space-x-1 font-semibold hover:underline"
              >
                <span>View</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
