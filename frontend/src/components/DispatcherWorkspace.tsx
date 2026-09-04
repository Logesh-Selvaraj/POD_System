import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  AlertTriangle,
  CheckCircle2,
  MapPin,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  History,
  CheckSquare
} from 'lucide-react';
import { LeafletMap } from './LeafletMap';

interface DispatcherQueueItem {
  delivery: {
    id: string;
    order_id?: string;
    rider_id?: number;
    restaurant_id: number;
    customer_id?: number;
    customer_name: string;
    customer_phone: string;
    delivery_address: string;
    target_latitude: number;
    target_longitude: number;
    otp_code: string;
    status: string;
    created_at: string;
    updated_at: string;
  };
  evidence?: {
    id: string;
    delivery_id: string;
    photo_url: string;
    signature_url?: string;
    captured_latitude?: number;
    captured_longitude?: number;
    captured_timestamp: string;
    is_offline_capture: boolean;
    otp_valid: boolean;
    distance_m?: number;
    gps_valid: boolean;
    blur_score?: number;
    brightness_score?: number;
    photo_score: number;
    gps_score: number;
    timestamp_score: number;
    signature_score: number;
    otp_score: number;
    total_quality_score: number;
    classification: 'ACCEPTED' | 'NEEDS_MANUAL_REVIEW' | 'DISPUTE';
  };
  disputes: Array<{
    id: string;
    delivery_id: string;
    raised_by_user_id: number;
    reason: string;
    status: string;
    resolution_notes?: string;
    created_at: string;
  }>;
  rider_name?: string;
  restaurant_name?: string;
}

interface HistoryEvent {
  id: string;
  event_type: 'OVERRIDE' | 'AUDIT' | 'DISPUTE';
  timestamp: string;
  actor_id?: number;
  actor_name?: string;
  action_or_reason_code?: string;
  previous_status?: string;
  new_status?: string;
  reason_text?: string;
  details?: any;
}

interface Props {
  token: string | null;
  onRefreshDeliveries: () => void;
}

export function DispatcherWorkspace({ token, onRefreshDeliveries }: Props) {
  const [queue, setQueue] = useState<DispatcherQueueItem[]>([]);
  const [selectedItem, setSelectedItem] = useState<DispatcherQueueItem | null>(null);
  const [historyEvents, setHistoryEvents] = useState<HistoryEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  // Override Form State
  const [newStatus, setNewStatus] = useState<string>('delivered');
  const [reasonCode, setReasonCode] = useState<string>('CUSTOMER_CONFIRMED_RECEIPT');
  const [reasonText, setReasonText] = useState<string>('');
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const reasonCodes = [
    { code: 'CUSTOMER_CONFIRMED_RECEIPT', label: 'Customer Confirmed Order Receipt' },
    { code: 'GPS_UNAVAILABLE', label: 'GPS Tower Signal Unavailable / Subterranean' },
    { code: 'NETWORK_FAILURE', label: 'Cellular Network Failure / Offline Delay' },
    { code: 'SIGNATURE_UNAVAILABLE', label: 'Contactless Delivery / Signature Exempt' },
    { code: 'EVIDENCE_EXCEPTION', label: 'Manual Photo Quality Validation' },
    { code: 'OPERATIONAL_EXCEPTION', label: 'Operational Dispatch Exception' },
    { code: 'OTHER', label: 'Other Custom Reason (Requires min 10 chars)' }
  ];

  useEffect(() => {
    fetchQueue();

    let bc: BroadcastChannel | null = null;
    try {
      if (typeof BroadcastChannel !== 'undefined') {
        bc = new BroadcastChannel('pod_deliveries_channel');
        bc.onmessage = (event) => {
          if (event.data?.type === 'DELIVERY_CREATED' || event.data?.type === 'DELIVERY_DELETED') {
            fetchQueue();
          }
        };
      }
    } catch {
      // ignore
    }

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'pod_delivery_sync') {
        fetchQueue();
      }
    };
    window.addEventListener('storage', handleStorageChange);

    return () => {
      if (bc) bc.close();
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [token]);

  useEffect(() => {
    if (selectedItem) {
      fetchHistory(selectedItem.delivery.id);
    } else {
      setHistoryEvents([]);
    }
  }, [selectedItem]);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const resp = await axios.get('/api/v1/dispatcher/queue', { headers });
      setQueue(resp.data);
      if (resp.data.length > 0 && !selectedItem) {
        setSelectedItem(resp.data[0]);
      }
    } catch (err: any) {
      console.error('Failed to fetch dispatcher queue', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async (deliveryId: string) => {
    setHistoryLoading(true);
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const resp = await axios.get(`/api/v1/dispatcher/deliveries/${deliveryId}/history`, { headers });
      setHistoryEvents(resp.data);
    } catch (err) {
      console.error('Failed to fetch delivery history', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleOpenConfirmModal = (e: React.FormEvent) => {
    e.preventDefault();
    if (reasonCode === 'OTHER' && (!reasonText || reasonText.trim().length < 10)) {
      alert('Reason text must be at least 10 characters long when reason code is OTHER.');
      return;
    }
    setShowConfirmModal(true);
  };

  const handleExecuteOverride = async () => {
    if (!selectedItem) return;
    setIsSubmitting(true);
    setFeedbackMsg(null);

    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const payload = {
        delivery_id: selectedItem.delivery.id,
        new_status: newStatus,
        reason_code: reasonCode,
        reason_text: reasonText
      };

      await axios.post('/api/v1/dispatcher/overrides', payload, { headers });
      
      setFeedbackMsg(`Override successful! Delivery status updated to ${newStatus.toUpperCase()}`);
      setShowConfirmModal(false);
      
      // Reset text & refresh
      setReasonText('');
      onRefreshDeliveries();
      fetchQueue();
      fetchHistory(selectedItem.delivery.id);
    } catch (err: any) {
      alert('Override failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-100 flex items-center space-x-2">
            <ShieldAlert className="w-6 h-6 text-amber-400" />
            <span>Dispatcher Manual Review & Override Workspace</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Prioritised evidence queue ordered by lowest quality score and oldest timestamp.
          </p>
        </div>
        <button
          onClick={fetchQueue}
          disabled={loading}
          className="flex items-center space-x-2 btn-secondary px-4 py-2 rounded-xl text-xs font-semibold transition btn-press-feedback"
        >
          <RefreshCw className={`w-4 h-4 text-slate-400 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Queue ({queue.length})</span>
        </button>
      </div>

      {feedbackMsg && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl text-emerald-400 text-sm font-semibold flex items-center space-x-2">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
          <span>{feedbackMsg}</span>
        </div>
      )}

      {/* Main Grid: Queue on Left, Details & Override on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Manual Review Queue */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3 shadow-xl h-fit">
          <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center justify-between">
            <span>Manual Review Queue</span>
            <span className="bg-slate-800 text-slate-300 text-xs px-2.5 py-0.5 rounded-full font-mono font-bold">
              {queue.length}
            </span>
          </h3>

          {queue.length === 0 ? (
            <div className="p-8 text-center bg-slate-950/60 rounded-xl border border-slate-800/80 space-y-2">
              <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
              <p className="text-xs text-slate-400">No deliveries requiring manual override at this time!</p>
            </div>
          ) : (
            <div className="space-y-2.5 max-h-[700px] overflow-y-auto pr-1">
              {queue.map((item) => {
                const isSelected = selectedItem?.delivery.id === item.delivery.id;
                const score = item.evidence?.total_quality_score;
                return (
                  <div
                    key={item.delivery.id}
                    onClick={() => setSelectedItem(item)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition space-y-2 hover-elevation ${
                      isSelected
                        ? 'bg-slate-800/90 border-slate-100 shadow-sm ring-1 ring-slate-100'
                        : 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="font-mono text-[11px] bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
                          {item.delivery.id}
                        </span>
                        <h4 className="font-bold text-sm text-slate-200 mt-1">{item.delivery.customer_name}</h4>
                      </div>
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase border ${
                        item.delivery.status === 'delivered' || item.delivery.status === 'accepted'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : item.delivery.status === 'needs_review'
                          ? 'bg-amber-50 text-amber-700 border-amber-200'
                          : item.delivery.status === 'disputed'
                          ? 'bg-rose-50 text-rose-700 border-rose-200'
                          : item.delivery.status === 'in_transit'
                          ? 'bg-slate-100 text-slate-700 border-slate-200'
                          : 'bg-slate-50 text-slate-500 border-slate-200'
                      }`}>
                        {item.delivery.status}
                      </span>
                    </div>

                    <div className="flex justify-between items-center text-xs pt-1 border-t border-slate-800/60">
                      <span className="text-slate-400 text-[11px]">Quality Score:</span>
                      <span className={`font-mono font-extrabold text-xs ${
                        score !== undefined && score < 70 ? 'text-rose-400' : 'text-amber-400'
                      }`}>
                        {score !== undefined ? `${score}/100` : 'No Evidence'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Columns: Selected Delivery Details, Maps, Evidence, Override & Audit History */}
        {selectedItem ? (
          <div className="lg:col-span-2 space-y-6">
            {/* Delivery Overview Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
              <div className="flex flex-wrap justify-between items-start border-b border-slate-800 pb-4 gap-4">
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-mono text-sm bg-slate-800 text-emerald-400 px-3 py-1 rounded-lg font-bold">
                      {selectedItem.delivery.id}
                    </span>
                    <span className="text-xs text-slate-400">Order #{selectedItem.delivery.order_id || 'N/A'}</span>
                  </div>
                  <h3 className="text-xl font-bold text-slate-100 mt-2">{selectedItem.delivery.customer_name}</h3>
                  <p className="text-xs text-slate-400">{selectedItem.delivery.delivery_address}</p>
                </div>

                <div className="text-right">
                  <div className="text-xs text-slate-400">Current Status</div>
                  <span className={`inline-block text-xs font-bold px-3 py-1 rounded-full uppercase border mt-1 ${
                    selectedItem.delivery.status === 'delivered' || selectedItem.delivery.status === 'accepted'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : selectedItem.delivery.status === 'needs_review'
                      ? 'bg-amber-50 text-amber-700 border-amber-200'
                      : selectedItem.delivery.status === 'disputed'
                      ? 'bg-rose-50 text-rose-700 border-rose-200'
                      : selectedItem.delivery.status === 'in_transit'
                      ? 'bg-slate-100 text-slate-700 border-slate-200'
                      : 'bg-slate-50 text-slate-500 border-slate-200'
                  }`}>
                    {selectedItem.delivery.status}
                  </span>
                </div>
              </div>

              {/* Quality Score Meter & Granular Breakdown */}
              {selectedItem.evidence ? (
                <div className="space-y-4">
                  <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
                    <ShieldCheck className="w-4 h-4 text-slate-100" />
                    <span>Evidence Quality Score Engine Assessment</span>
                  </h4>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-center space-y-1">
                      <div className="text-xs text-slate-400">Total Quality Score</div>
                      <div className="text-3xl font-extrabold font-mono text-slate-100">
                        {selectedItem.evidence.total_quality_score}/100
                      </div>
                      <div className={`text-[10px] uppercase font-bold ${
                        selectedItem.evidence.classification === 'ACCEPTED'
                          ? 'text-emerald-600'
                          : selectedItem.evidence.classification === 'NEEDS_MANUAL_REVIEW'
                          ? 'text-amber-600'
                          : 'text-rose-600'
                      }`}>
                        [{selectedItem.evidence.classification}]
                      </div>
                    </div>

                    <div className="md:col-span-2 grid grid-cols-2 gap-2 text-xs bg-slate-950 p-4 rounded-xl border border-slate-800">
                      <div>
                        <span className="text-slate-400 block">Photo Score (OpenCV)</span>
                        <span className="font-mono font-bold text-slate-200">{selectedItem.evidence.photo_score}/25</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">GPS Score (Haversine)</span>
                        <span className="font-mono font-bold text-slate-200">{selectedItem.evidence.gps_score}/25</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">Timestamp Score</span>
                        <span className="font-mono font-bold text-slate-200">{selectedItem.evidence.timestamp_score}/20</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">Signature Score</span>
                        <span className="font-mono font-bold text-slate-200">{selectedItem.evidence.signature_score}/20</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">OTP Score</span>
                        <span className="font-mono font-bold text-slate-200">{selectedItem.evidence.otp_score}/10</span>
                      </div>
                      <div>
                        <span className="text-slate-400 block">GPS Distance</span>
                        <span className="font-mono font-bold text-emerald-400">
                          {selectedItem.evidence.distance_m !== undefined ? `${selectedItem.evidence.distance_m}m` : 'Missing'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Photo & Signature Preview */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-xs text-slate-400 block mb-1">Delivery Photo Proof</span>
                      <div className="h-44 bg-slate-950 rounded-xl overflow-hidden border border-slate-800">
                        <img
                          src={selectedItem.evidence.photo_url}
                          alt="Photo Evidence"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    </div>
                    <div>
                      <span className="text-xs text-slate-400 block mb-1">Recipient Signature</span>
                      <div className="h-44 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-center">
                        {selectedItem.evidence.signature_url ? (
                          <img
                            src={selectedItem.evidence.signature_url}
                            alt="Signature Evidence"
                            className="max-h-full"
                          />
                        ) : (
                          <span className="text-xs text-slate-500">No Signature Provided</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Leaflet Map for GPS Verification */}
                  <div className="space-y-2">
                    <span className="text-xs text-slate-400 flex items-center space-x-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      <span>GPS Verification Map (Target vs Captured Location)</span>
                    </span>
                    <LeafletMap
                      targetLat={selectedItem.delivery.target_latitude}
                      targetLng={selectedItem.delivery.target_longitude}
                      capturedLat={selectedItem.evidence.captured_latitude}
                      capturedLng={selectedItem.evidence.captured_longitude}
                      distanceM={selectedItem.evidence.distance_m}
                    />
                  </div>
                </div>
              ) : (
                <div className="p-6 bg-slate-950/80 rounded-xl border border-slate-800 text-center text-xs text-slate-400">
                  No proof of delivery evidence submitted for this delivery yet.
                </div>
              )}

              {/* Disputes Section if any */}
              {selectedItem.disputes.length > 0 && (
                <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl space-y-2">
                  <h4 className="text-xs font-bold text-rose-700 uppercase tracking-wider flex items-center space-x-1.5">
                    <AlertTriangle className="w-4 h-4 text-rose-600" />
                    <span>Customer Dispute Information</span>
                  </h4>
                  {selectedItem.disputes.map((disp) => (
                    <div key={disp.id} className="text-xs text-slate-700">
                      <p><strong>Reason:</strong> {disp.reason}</p>
                      <p className="text-[11px] text-slate-400">Raised at {new Date(disp.created_at).toLocaleString()}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Override Action Form */}
            <form onSubmit={handleOpenConfirmModal} className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-md font-bold text-slate-100 flex items-center space-x-2">
                <CheckSquare className="w-5 h-5 text-slate-100" />
                <span>Execute Dispatcher Override</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-400 block mb-1">New Target Status</label>
                  <select
                    value={newStatus}
                    onChange={(e) => setNewStatus(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-semibold"
                  >
                    <option value="delivered">DELIVERED (Accepted Override)</option>
                    <option value="needs_review">NEEDS_REVIEW (Re-open Review)</option>
                    <option value="disputed">DISPUTED (Flag as Dispute)</option>
                    <option value="in_transit">IN_TRANSIT (Re-assign to Rider)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1">Predefined Reason Code</label>
                  <select
                    value={reasonCode}
                    onChange={(e) => setReasonCode(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-semibold"
                  >
                    {reasonCodes.map((r) => (
                      <option key={r.code} value={r.code}>{r.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400 block mb-1">
                  Reason Explanation Text {reasonCode === 'OTHER' && <span className="text-rose-400">* (Min 10 characters)</span>}
                </label>
                <textarea
                  rows={2}
                  value={reasonText}
                  onChange={(e) => setReasonText(e.target.value)}
                  placeholder="Provide operational context for this status override..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200"
                />
              </div>

              <button
                type="submit"
                className="w-full btn-primary font-bold py-3 rounded-xl transition flex items-center justify-center space-x-2 btn-press-feedback"
              >
                <ShieldCheck className="w-5 h-5" />
                <span>Submit Dispatcher Status Override</span>
              </button>
            </form>

            {/* Complete Audit History Panel */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
              <h3 className="text-md font-bold text-slate-100 flex items-center space-x-2">
                <History className="w-5 h-5 text-slate-400" />
                <span>Complete Append-Only Audit History ({historyEvents.length})</span>
              </h3>

              {historyLoading ? (
                <div className="text-xs text-slate-400 p-4 text-center">Loading audit timeline...</div>
              ) : historyEvents.length === 0 ? (
                <div className="text-xs text-slate-500 p-4 text-center">No audit history records found yet.</div>
              ) : (
                <div className="space-y-3 relative before:absolute before:inset-0 before:left-3.5 before:w-0.5 before:bg-slate-800">
                  {historyEvents.map((ev) => (
                    <div key={ev.id} className="relative pl-8 space-y-1">
                      <div className="absolute left-1.5 top-1 w-4 h-4 rounded-full bg-slate-900 border-2 border-slate-100 flex items-center justify-center" />
                      <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs space-y-1">
                        <div className="flex justify-between items-center">
                          <span className="font-bold text-slate-200">
                            {ev.event_type} - {ev.action_or_reason_code || 'EVENT'}
                          </span>
                          <span className="text-[10px] text-slate-500">
                            {new Date(ev.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-slate-400 text-[11px]">
                          <strong>Actor:</strong> {ev.actor_name || `User #${ev.actor_id}`}
                        </p>
                        {ev.previous_status && ev.new_status && (
                          <div className="text-[11px] font-mono text-slate-100">
                            Transition: {ev.previous_status} → {ev.new_status}
                          </div>
                        )}
                        {ev.reason_text && (
                          <p className="text-[11px] text-slate-300 italic">"{ev.reason_text}"</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400 shadow-xl">
            Select a delivery from the manual review queue to inspect evidence and perform overrides.
          </div>
        )}
      </div>

      {/* Safety Confirmation Modal */}
      {showConfirmModal && selectedItem && (
        <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-[2px] z-50 flex items-center justify-center p-4 animate-modal-backdrop">
          <div className="bg-slate-900 border border-slate-800 max-w-md w-full rounded-3xl p-6 space-y-5 shadow-2xl animate-modal-content">
            <div className="flex items-center space-x-3 text-amber-400 border-b border-slate-800 pb-3">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-slate-100">Confirm Dispatcher Override</h3>
            </div>

            <div className="space-y-3 text-xs bg-slate-950 p-4 rounded-2xl border border-slate-800">
              <div>
                <span className="text-slate-400">Target Delivery ID:</span>
                <span className="font-mono text-emerald-400 font-bold ml-2">{selectedItem.delivery.id}</span>
              </div>
              <div>
                <span className="text-slate-400">Status Change:</span>
                <span className="font-mono font-bold text-slate-200 ml-2 uppercase">
                  {selectedItem.delivery.status} → {newStatus}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Reason Code:</span>
                <span className="font-mono font-bold text-slate-200 ml-2">{reasonCode}</span>
              </div>
              {reasonText && (
                <div>
                  <span className="text-slate-400 block mb-0.5">Reason Explanation:</span>
                  <p className="text-slate-300 italic pl-2 border-l-2 border-slate-700">{reasonText}</p>
                </div>
              )}
            </div>

            <div className="flex space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setShowConfirmModal(false)}
                className="flex-1 btn-secondary font-bold py-3 rounded-xl transition text-xs btn-press-feedback"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={handleExecuteOverride}
                className="flex-1 btn-success font-bold py-3 rounded-xl transition text-xs flex items-center justify-center space-x-1.5 disabled:opacity-50 btn-press-feedback"
              >
                <CheckCircle2 className="w-4 h-4" />
                <span>{isSubmitting ? 'Recording...' : 'Confirm & Commit Override'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
