import React, { useState, useEffect, useCallback } from 'react';
import ReactDOM from 'react-dom';
import axios from 'axios';
import {
  ShieldCheck,
  Wifi,
  WifiOff,
  Camera,
  MapPin,
  FileSignature,
  KeyRound,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  PlusCircle,
  Eye,
  LogOut,
  Bike,
  ClipboardList,
  BarChart3,
  Store,
  ShoppingBag,
  ArrowRight,
  Trash2
} from 'lucide-react';

import { SignatureCanvas } from './components/SignatureCanvas';
import { LeafletMap } from './components/LeafletMap';
import { DispatcherWorkspace } from './components/DispatcherWorkspace';
import {
  savePendingEvidence,
  getPendingEvidenceItems,
  cacheDeliveries,
  getCachedDeliveries,
  type PendingEvidenceItem
} from './db/indexedDb';
import { SyncManager } from './services/syncManager';

interface Delivery {
  id: string;
  restaurant_id: number;
  rider_id?: number;
  customer_name: string;
  customer_phone: string;
  delivery_address: string;
  target_latitude: number;
  target_longitude: number;
  otp_code: string;
  status: string;
  created_at: string;
}

interface Evidence {
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
}

const getEvidenceUrl = (url?: string) => {
  if (!url) return '';
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) {
    return url;
  }
  const backendBase = import.meta.env.DEV ? 'http://localhost:8000' : window.location.origin;
  return `${backendBase}${url}`;
};

const VALID_ROLES = ['rider', 'dispatcher', 'admin', 'restaurant', 'customer'];

const getDashboardTabForRole = (role: string): 'deliveries' | 'dispatcher' | 'admin_analytics' | 'create_delivery' | 'experiments' | 'validation' | 'evidence_capture' => {
  if (role === 'dispatcher') return 'dispatcher';
  if (role === 'admin') return 'admin_analytics';
  if (role === 'restaurant') return 'create_delivery';
  return 'deliveries';
};

const getRoleFromLocation = (currentPathName: string): string | null => {
  const path = currentPathName.replace(/^\/|\/$/g, '').toLowerCase();
  if (VALID_ROLES.includes(path)) {
    return path;
  }
  const hash = window.location.hash.replace(/^#\/?|\/$/g, '').toLowerCase();
  if (VALID_ROLES.includes(hash)) {
    return hash;
  }
  return null;
};

const isUnknownRoute = (currentPathName: string): boolean => {
  const path = currentPathName.replace(/^\/|\/$/g, '').toLowerCase();
  const hash = window.location.hash.replace(/^#\/?|\/$/g, '').toLowerCase();
  
  const hasPath = path !== '' && path !== 'login' && path !== 'index.html';
  const hasHash = hash !== '' && hash !== 'login';
  
  if (hasPath && !VALID_ROLES.includes(path)) {
    return true;
  }
  if (hasHash && !VALID_ROLES.includes(hash)) {
    return true;
  }
  return false;
};

export default function App() {
  // Router path state
  const [currentPath, setCurrentPath] = useState<string>(window.location.pathname);
  const [isInitializing, setIsInitializing] = useState<boolean>(true);

  const navigate = (path: string) => {
    window.history.pushState(null, '', path);
    setCurrentPath(path);
  };

  // Auth state
  const [token, setToken] = useState<string | null>(localStorage.getItem('pod_token'));
  const [userRole, setUserRole] = useState<string>(localStorage.getItem('pod_role') || getRoleFromLocation(window.location.pathname) || 'rider');
  const [userEmail, setUserEmail] = useState<string>(localStorage.getItem('pod_email') || 'rider@pod.com');
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null);

  // Network & Queue state
  const [isOfflineSimulated, setIsOfflineSimulated] = useState<boolean>(false);
  const [pendingQueueCount, setPendingQueueCount] = useState<number>(0);

  // Deliveries state
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [selectedDelivery, setSelectedDelivery] = useState<Delivery | null>(null);
  const [activeTab, setActiveTab] = useState<'deliveries' | 'evidence_capture' | 'create_delivery' | 'dispatcher' | 'admin_analytics' | 'experiments' | 'validation'>(() => 
    getDashboardTabForRole(localStorage.getItem('pod_role') || getRoleFromLocation(window.location.pathname) || 'rider')
  );

  // Evidence Capture form state
  const [photoBlob, setPhotoBlob] = useState<Blob | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [signatureBase64, setSignatureBase64] = useState<string | null>(null);
  const [capturedLat, setCapturedLat] = useState<number | null>(12.971598);
  const [capturedLng, setCapturedLng] = useState<number | null>(77.594566);
  const [disableGPS, setDisableGPS] = useState<boolean>(false);
  const [otpEntered, setOtpEntered] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Evidence Review state (for Dispatcher/Admin)
  const [reviewedEvidence, setReviewedEvidence] = useState<Evidence | null>(null);
  const [showEvidenceModal, setShowEvidenceModal] = useState<boolean>(false);
  const [deliveryToDelete, setDeliveryToDelete] = useState<string | null>(null);

  // Create Delivery Form state
  const [newDeliveryId, setNewDeliveryId] = useState(`DEL-${Math.floor(1000 + Math.random() * 9000)}`);
  const [newCustomerName, setNewCustomerName] = useState('Sarah Connor');
  const [newCustomerPhone, setNewCustomerPhone] = useState('+19876543219');
  const [newAddress, setNewAddress] = useState('789 Cyberdyne Way, Block C');
  const [newLat, setNewLat] = useState(12.971598);
  const [newLng, setNewLng] = useState(77.594566);
  const [newOtp, setNewOtp] = useState('9876');

  // Admin Analytics state
  const [fromDate, setFromDate] = useState<string>('');
  const [toDate, setToDate] = useState<string>('');
  const [analytics, setAnalytics] = useState<any>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState<boolean>(false);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

  // Experiment state
  const [runs, setRuns] = useState<any[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [runDetail, setRunDetail] = useState<any>(null);
  const [runDetailLoading, setRunDetailLoading] = useState<boolean>(false);
  const [isEvaluationRunning, setIsEvaluationRunning] = useState<boolean>(false);

  // Stakeholder Validation state
  const [validationSummary, setValidationSummary] = useState<any>(null);
  const [validationSummaryLoading, setValidationSummaryLoading] = useState<boolean>(false);

  const [valParticipantCode, setValParticipantCode] = useState<string>('');
  const [valStakeholderRole, setValStakeholderRole] = useState<string>('rider');
  const [valScenario, setValScenario] = useState<string>('Accept an assigned delivery and capture POD evidence.');
  const [valRatings, setValRatings] = useState<Record<string, number>>({});
  const [valComments, setValComments] = useState<Record<string, string>>({});
  const [valSessionId, setValSessionId] = useState<string>('');
  const [valSessionCreated, setValSessionCreated] = useState<boolean>(false);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState<boolean>(false);

  // Login preset accounts
  const loginPresets = [
    {
      label: 'Rider (John)',
      email: 'rider@pod.com',
      pass: 'rider123',
      role: 'rider',
      desc: 'Field courier application. Capture camera snapshots, validation coordinates, recipient signatures, and offline synch.',
      icon: Bike
    },
    {
      label: 'Dispatcher (General)',
      email: 'dispatcher@pod.com',
      pass: 'dispatcher123',
      role: 'dispatcher',
      desc: 'Operations queue dashboard. Investigate alerts, verify Haversine proximity, and perform overrides with audit reasons.',
      icon: ClipboardList
    },
    {
      label: 'Admin (System)',
      email: 'admin@pod.com',
      pass: 'admin123',
      role: 'admin',
      desc: 'Enterprise console. Monitor system-wide KPIs, examine usability surveys, and simulate baseline experiment runs.',
      icon: BarChart3
    },
    {
      label: 'Restaurant (Tasty Bytes)',
      email: 'restaurant@pod.com',
      pass: 'restaurant123',
      role: 'restaurant',
      desc: 'Merchant platform. Dispatch new delivery requests with OTP verification codes and track active completions.',
      icon: Store
    },
    {
      label: 'Customer (Alice)',
      email: 'customer@pod.com',
      pass: 'customer123',
      role: 'customer',
      desc: 'Recipient validation page. Track order status, verify safe receipt using OTP codes, or raise security disputes.',
      icon: ShoppingBag
    }
  ];

  const fetchValidationSummary = async () => {
    if (!token || userRole !== 'admin') return;
    setValidationSummaryLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const resp = await axios.get('/api/v1/validation/admin/summary', { headers });
      setValidationSummary(resp.data);
    } catch (err: any) {
      console.error(err);
    } finally {
      setValidationSummaryLoading(false);
    }
  };

  const handleStartValidationSession = async () => {
    try {
      const resp = await axios.post('/api/v1/validation/sessions', {
        participant_code: valParticipantCode || undefined,
        stakeholder_role: valStakeholderRole,
        validation_scenario: valScenario
      });
      setValSessionId(resp.data.id);
      setValSessionCreated(true);
      setValRatings({});
      setValComments({});
    } catch (err: any) {
      alert('Failed to start session: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleSubmitValidationFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!valSessionId) return;

    // Verify all 10 questions have rating
    const unanswered = [];
    for (let i = 1; i <= 10; i++) {
      if (!valRatings[`Q${i}`]) {
        unanswered.push(`Q${i}`);
      }
    }

    if (unanswered.length > 0) {
      alert(`Please answer all 10 questions before submitting! Unanswered: ${unanswered.join(', ')}`);
      return;
    }

    setIsSubmittingFeedback(true);
    try {
      for (let i = 1; i <= 10; i++) {
        const qId = `Q${i}`;
        await axios.post('/api/v1/validation/responses', {
          session_id: valSessionId,
          question_id: qId,
          rating: valRatings[qId],
          comment: valComments[qId] || undefined
        });
      }
      alert('Validation response submitted successfully! Thank you for participating.');
      setValSessionCreated(false);
      setValSessionId('');
      setValParticipantCode('');
    } catch (err: any) {
      alert('Error submitting feedback: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  useEffect(() => {
    // Subscribe to SyncManager queue count
    const unsubscribe = SyncManager.subscribe((count) => setPendingQueueCount(count));
    SyncManager.initAutoSync(() => token);

    // Initial queue count check
    getPendingEvidenceItems().then((items) => setPendingQueueCount(items.length));

    return () => unsubscribe();
  }, [token]);

  const fetchDeliveries = useCallback(async (authToken?: string) => {
    if (isOfflineSimulated || !navigator.onLine) {
      const cached = await getCachedDeliveries();
      setDeliveries(cached);
      return cached;
    }

    const effectiveToken = authToken || token || localStorage.getItem('pod_token');
    try {
      const headers: Record<string, string> = {};
      if (effectiveToken) {
        headers['Authorization'] = `Bearer ${effectiveToken}`;
      }
      const resp = await axios.get('/api/v1/deliveries/', { headers });
      setDeliveries(resp.data);
      // Cache to IndexedDB
      await cacheDeliveries(resp.data);
      return resp.data;
    } catch (err) {
      const cached = await getCachedDeliveries();
      setDeliveries(cached);
      return cached;
    }
  }, [token, isOfflineSimulated]);

  useEffect(() => {
    fetchDeliveries();

    // Poll for delivery list updates automatically every 4 seconds
    const intervalId = setInterval(() => {
      fetchDeliveries();
    }, 4000);

    // Cross-tab and visibility auto-refresh synchronization
    let bc: BroadcastChannel | null = null;
    try {
      if (typeof BroadcastChannel !== 'undefined') {
        bc = new BroadcastChannel('pod_deliveries_channel');
        bc.onmessage = (event) => {
          if (event.data?.type === 'DELIVERY_CREATED') {
            fetchDeliveries();
          } else if (event.data?.type === 'DELIVERY_DELETED') {
            const delId = event.data.deliveryId;
            setDeliveries((prev) => prev.filter((d) => d.id !== delId));
            fetchDeliveries();
          }
        };
      }
    } catch {
      // ignore
    }

    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'pod_delivery_sync' || e.key === 'pod_token' || e.key === 'pod_role') {
        fetchDeliveries();
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchDeliveries();
      }
    };

    const handleFocus = () => {
      fetchDeliveries();
    };

    window.addEventListener('storage', handleStorageChange);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);

    return () => {
      clearInterval(intervalId);
      if (bc) bc.close();
      window.removeEventListener('storage', handleStorageChange);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
    };
  }, [fetchDeliveries]);

  useEffect(() => {
    if (activeTab === 'admin_analytics') {
      fetchAnalytics();
      fetchValidationSummary();
    }
  }, [activeTab, token, userRole]);

  useEffect(() => {
    if (activeTab === 'experiments') {
      fetchExperimentRuns();
    }
  }, [activeTab, token, userRole]);

  useEffect(() => {
    if (selectedRunId) {
      fetchExperimentDetail(selectedRunId);
    }
  }, [selectedRunId]);

  const fetchExperimentRuns = async () => {
    if (!token || userRole !== 'admin') return;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const resp = await axios.get('/api/v1/admin/experiments', { headers });
      setRuns(resp.data);
      if (resp.data.length > 0 && !selectedRunId) {
        setSelectedRunId(resp.data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchExperimentDetail = async (runId: string) => {
    if (!token || !runId) return;
    setRunDetailLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const resp = await axios.get(`/api/v1/admin/experiments/${runId}`, { headers });
      setRunDetail(resp.data);
    } catch (err) {
      console.error(err);
    } finally {
      setRunDetailLoading(false);
    }
  };

  const triggerExperiment = async () => {
    if (!token || userRole !== 'admin') return;
    setIsEvaluationRunning(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const resp = await axios.post('/api/v1/admin/experiments/run', {}, { headers });
      alert(`Experiment run ${resp.data.id} executed successfully!`);
      await fetchExperimentRuns();
      setSelectedRunId(resp.data.id);
    } catch (err: any) {
      alert('Failed to trigger experiment run: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsEvaluationRunning(false);
    }
  };

  const fetchAnalytics = async () => {
    if (!token || userRole !== 'admin') return;
    setAnalyticsLoading(true);
    setAnalyticsError(null);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const params: any = {};
      if (fromDate) params.from_date = fromDate;
      if (toDate) params.to_date = toDate;

      const resp = await axios.get('/api/v1/admin/analytics', { headers, params });
      setAnalytics(resp.data);
    } catch (err: any) {
      setAnalyticsError(err.response?.data?.detail || err.message || 'Failed to load analytics');
      setAnalytics(null);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const handleLogin = async (email: string, pass: string) => {
    const preset = loginPresets.find(p => p.email === email);
    const expectedRole = preset ? preset.role : 'rider';

    try {
      const resp = await axios.post('/api/v1/auth/login', { email, password: pass });
      const { access_token, user } = resp.data;
      setToken(access_token);
      setUserRole(user.role);
      setUserEmail(user.email);
      localStorage.setItem('pod_token', access_token);
      localStorage.setItem('pod_role', user.role);
      localStorage.setItem('pod_email', user.email);
      const targetTab = getDashboardTabForRole(user.role);
      setActiveTab(targetTab);
      await fetchDeliveries(access_token);
      navigate(`/${user.role}`);
    } catch (err) {
      alert('Login failed! Using offline demo session.');
      setToken('demo_token');
      setUserRole(expectedRole);
      setUserEmail(email);
      localStorage.setItem('pod_token', 'demo_token');
      localStorage.setItem('pod_role', expectedRole);
      localStorage.setItem('pod_email', email);
      const targetTab = getDashboardTabForRole(expectedRole);
      setActiveTab(targetTab);
      await fetchDeliveries('demo_token');
      navigate(`/${expectedRole}`);
    }
  };

  const handleLogout = () => {
    setToken(null);
    setUserRole('rider');
    localStorage.removeItem('pod_token');
    localStorage.removeItem('pod_role');
    localStorage.removeItem('pod_email');
    navigate('/');
  };

  useEffect(() => {
    const handleUrlRouting = async () => {
      setIsInitializing(true);
      if (isUnknownRoute(currentPath)) {
        alert("Unknown or invalid role. Redirecting to login preset page.");
        handleLogout();
        setIsInitializing(false);
        return;
      }

      const roleFromUrl = getRoleFromLocation(currentPath);
      if (roleFromUrl) {
        const preset = loginPresets.find(p => p.role === roleFromUrl);
        if (preset) {
          const storedToken = localStorage.getItem('pod_token');
          const storedRole = localStorage.getItem('pod_role');
          
          if (!storedToken || storedRole !== roleFromUrl) {
            try {
              const resp = await axios.post('/api/v1/auth/login', { email: preset.email, password: preset.pass });
              const { access_token, user } = resp.data;
              setToken(access_token);
              setUserRole(user.role);
              setUserEmail(user.email);
              localStorage.setItem('pod_token', access_token);
              localStorage.setItem('pod_role', user.role);
              localStorage.setItem('pod_email', user.email);
              setActiveTab(getDashboardTabForRole(user.role));
              await fetchDeliveries(access_token);
            } catch (err) {
              setToken('demo_token');
              setUserRole(roleFromUrl);
              setUserEmail(preset.email);
              localStorage.setItem('pod_token', 'demo_token');
              localStorage.setItem('pod_role', roleFromUrl);
              localStorage.setItem('pod_email', preset.email);
              setActiveTab(getDashboardTabForRole(roleFromUrl));
              await fetchDeliveries('demo_token');
            }
          } else {
            setToken(storedToken);
            setUserRole(storedRole);
            setUserEmail(localStorage.getItem('pod_email') || preset.email);
            const tab = getDashboardTabForRole(storedRole);
            setActiveTab(prev => {
              if (storedRole === 'admin') return prev;
              if (storedRole === 'dispatcher' && (prev === 'deliveries' || prev === 'validation' || prev === 'dispatcher')) return prev;
              if (storedRole === 'restaurant' && (prev === 'deliveries' || prev === 'validation' || prev === 'create_delivery')) return prev;
              if (storedRole === 'customer') return 'deliveries';
              if (storedRole === 'rider' && (prev === 'deliveries' || prev === 'validation' || prev === 'evidence_capture')) return prev;
              return tab;
            });
            await fetchDeliveries(storedToken);
          }
        }
      } else {
        // Clear auth state to show login presets page when path is root
        setToken(null);
        setUserRole('rider');
        localStorage.removeItem('pod_token');
        localStorage.removeItem('pod_role');
        localStorage.removeItem('pod_email');
      }
      setIsInitializing(false);
    };

    handleUrlRouting();
  }, [currentPath, fetchDeliveries]);

  useEffect(() => {
    const handleUrlChange = () => {
      const hashRole = getRoleFromLocation(window.location.hash);
      const pathRole = getRoleFromLocation(window.location.pathname);
      if (pathRole) {
        setCurrentPath(`/${pathRole}`);
      } else if (hashRole) {
        setCurrentPath(`/${hashRole}`);
      } else {
        setCurrentPath(window.location.pathname);
      }
    };
    window.addEventListener('popstate', handleUrlChange);
    window.addEventListener('hashchange', handleUrlChange);
    return () => {
      window.removeEventListener('popstate', handleUrlChange);
      window.removeEventListener('hashchange', handleUrlChange);
    };
  }, []);

  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setPhotoBlob(file);
      setPhotoPreview(URL.createObjectURL(file));
    }
  };

  const handleEvidenceSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDelivery) return;
    if (!photoBlob) {
      alert('Please capture or upload a delivery photo!');
      return;
    }

    setIsSubmitting(true);
    const idempotencyKey = `POD-SYNC-${selectedDelivery.id}-${Date.now()}`;
    const timestampStr = new Date().toISOString();

    const pendingItem: PendingEvidenceItem = {
      idempotency_key: idempotencyKey,
      delivery_id: selectedDelivery.id,
      captured_latitude: disableGPS ? null : capturedLat,
      captured_longitude: disableGPS ? null : capturedLng,
      captured_timestamp: timestampStr,
      otp_entered: otpEntered,
      signature_base64: signatureBase64,
      photo_blob: photoBlob,
      status: 'PENDING',
      created_at: timestampStr
    };

    if (isOfflineSimulated || !navigator.onLine) {
      // Offline mode: Store directly to IndexedDB local queue
      await savePendingEvidence(pendingItem);
      const items = await getPendingEvidenceItems();
      setPendingQueueCount(items.length);
      alert(`[OFFLINE MODE] Evidence stored in local IndexedDB Queue! (Idempotency Key: ${idempotencyKey.slice(0, 16)}...)`);
      resetCaptureForm();
      setIsSubmitting(false);
      return;
    }

    // Online mode: Push directly to backend API
    try {
      const formData = new FormData();
      formData.append('delivery_id', selectedDelivery.id);
      formData.append('idempotency_key', idempotencyKey);
      if (!disableGPS && capturedLat !== null) formData.append('captured_latitude', capturedLat.toString());
      if (!disableGPS && capturedLng !== null) formData.append('captured_longitude', capturedLng.toString());
      formData.append('captured_timestamp', timestampStr);
      if (otpEntered) formData.append('otp_entered', otpEntered);
      if (signatureBase64) formData.append('signature_base64', signatureBase64);
      formData.append('photo', photoBlob, `evidence_${selectedDelivery.id}.jpg`);

      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const resp = await axios.post('/api/v1/evidence/submit', formData, { headers });

      alert(`Evidence submitted & verified! Total Score: ${resp.data.total_quality_score}/100 [${resp.data.classification}]`);
      resetCaptureForm();
      fetchDeliveries();
    } catch (err: any) {
      // Fallback to IndexedDB queue if server request fails
      await savePendingEvidence(pendingItem);
      const items = await getPendingEvidenceItems();
      setPendingQueueCount(items.length);
      alert('Network request failed. Saved to offline IndexedDB queue!');
      resetCaptureForm();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCreateDeliverySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.post('/api/v1/deliveries/', {
        id: newDeliveryId,
        customer_name: newCustomerName,
        customer_phone: newCustomerPhone,
        delivery_address: newAddress,
        target_latitude: newLat,
        target_longitude: newLng,
        otp_code: newOtp,
        rider_id: 4, // Assigned to Rider John
        customer_id: 5 // Assigned to Customer Alice (Alice Smith)
      }, { headers });

      alert(`Delivery ${newDeliveryId} created successfully!`);
      setNewDeliveryId(`DEL-${Math.floor(1000 + Math.random() * 9000)}`);
      fetchDeliveries();

      // Trigger cross-tab synchronization for open Customer dashboards
      try {
        localStorage.setItem('pod_delivery_sync', `${newDeliveryId}-${Date.now()}`);
        if (typeof BroadcastChannel !== 'undefined') {
          const bc = new BroadcastChannel('pod_deliveries_channel');
          bc.postMessage({ type: 'DELIVERY_CREATED', deliveryId: newDeliveryId });
          bc.close();
        }
      } catch {
        // ignore storage/broadcast errors
      }

      setActiveTab('deliveries');
    } catch (err: any) {
      alert('Error creating delivery: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDeleteDelivery = (deliveryId: string) => {
    setDeliveryToDelete(deliveryId);
  };

  const executeDeleteDelivery = async (deliveryId: string) => {
    setDeliveryToDelete(null);
    try {
      const activeToken = token || localStorage.getItem('pod_token');
      const headers = activeToken ? { Authorization: `Bearer ${activeToken}` } : {};
      await axios.delete(`/api/v1/deliveries/${deliveryId}`, { headers });

      // Immediately remove from shared state
      setDeliveries((prev) => prev.filter((d) => d.id !== deliveryId));

      // Remove from IndexedDB cache
      try {
        const cached = await getCachedDeliveries();
        await cacheDeliveries(cached.filter((d) => d.id !== deliveryId));
      } catch (cacheErr) {
        console.error('Error updating cache on delete:', cacheErr);
      }

      // Trigger cross-tab synchronization for all open dashboards
      try {
        localStorage.setItem('pod_delivery_sync', `DELETE-${deliveryId}-${Date.now()}`);
        if (typeof BroadcastChannel !== 'undefined') {
          const bc = new BroadcastChannel('pod_deliveries_channel');
          bc.postMessage({ type: 'DELIVERY_DELETED', deliveryId });
          bc.close();
        }
      } catch {
        // ignore storage/broadcast errors
      }

      // Refresh to ensure absolute alignment with backend
      await fetchDeliveries();
    } catch (err: any) {
      alert('Error deleting delivery: ' + (err.response?.data?.detail || err.message));
    }
  };

  const viewEvidenceDetails = async (deliveryId: string) => {
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const resp = await axios.get(`/api/v1/evidence/${deliveryId}`, { headers });
      setReviewedEvidence(resp.data);
      setShowEvidenceModal(true);
    } catch (err) {
      alert('No evidence record found for this delivery yet.');
    }
  };

  const updateDeliveryStatus = async (deliveryId: string, newStatus: string) => {
    try {
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      await axios.patch(`/api/v1/deliveries/${deliveryId}/status`, { status: newStatus }, { headers });
      alert(`Delivery status updated to ${newStatus}`);
      setShowEvidenceModal(false);
      fetchDeliveries();
    } catch (err) {
      alert('Failed to update status.');
    }
  };

  const resetCaptureForm = () => {
    setPhotoBlob(null);
    setPhotoPreview(null);
    setSignatureBase64(null);
    setOtpEntered('');
    setSelectedDelivery(null);
    setActiveTab('deliveries');
  };

  // Live Score Calculator Preview
  const calculateLiveScores = () => {
    const photoScore = photoBlob ? 25 : 0;
    const gpsScore = disableGPS ? 0 : 25;
    const timestampScore = 20;
    const sigScore = signatureBase64 ? 20 : 0;
    const otpScore = (selectedDelivery && otpEntered === selectedDelivery.otp_code) ? 10 : 0;
    const total = photoScore + gpsScore + timestampScore + sigScore + otpScore;
    
    let classification = 'ACCEPTED';
    if (total < 70) classification = 'DISPUTE';
    else if (total < 90) classification = 'NEEDS_MANUAL_REVIEW';

    return { photoScore, gpsScore, timestampScore, sigScore, otpScore, total, classification };
  };

  const liveScores = calculateLiveScores();

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-6">
        <div className="flex items-center space-x-3 justify-center">
          <RefreshCw className="w-12 h-12 text-emerald-500 animate-spin" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Loading...</h1>
            <p className="text-slate-400 text-xs">Initializing session and routing...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-6 sm:p-12 animate-fade-in-up">
        <div className="max-w-6xl w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 md:p-12 shadow-sm space-y-8">
          <div className="flex flex-col items-center text-center space-y-3">
            <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-2xl shadow-sm w-fit mx-auto">
              <ShieldCheck className="w-10 h-10 text-emerald-500" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-slate-100 text-center">Standardised POD Engine</h1>
              <p className="text-slate-400 text-sm mt-2 max-w-md mx-auto text-center">
                Proof-of-Delivery verification platform with telemetry grading and offline synchronization.
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-xs uppercase tracking-wider font-bold text-slate-400 text-center">
              Select your workspace role to sign in
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {loginPresets.map((preset) => {
                const IconComponent = preset.icon;
                const isSelected = selectedEmail === preset.email;
                return (
                  <button
                    key={preset.email}
                    onClick={() => {
                      setSelectedEmail(preset.email);
                      setTimeout(() => {
                        handleLogin(preset.email, preset.pass);
                      }, 200);
                    }}
                    className={`group text-left bg-slate-900 border rounded-3xl p-6 hover-elevation flex flex-col justify-between h-72 text-sm focus:outline-none focus:ring-2 focus:ring-slate-100 focus:ring-offset-2 btn-press-feedback transition-all duration-200 ${
                      isSelected
                        ? 'border-slate-100 ring-2 ring-slate-100 bg-slate-950'
                        : 'border-slate-800'
                    }`}
                  >
                    <div className="space-y-4">
                      <div className={`p-3 rounded-2xl border transition w-fit ${
                        isSelected
                          ? 'bg-slate-900 border-slate-100 text-slate-100'
                          : 'bg-slate-950 border-slate-800 group-hover:border-slate-400'
                      }`}>
                        <IconComponent className={`w-6 h-6 transition ${
                          isSelected
                            ? 'text-emerald-500'
                            : 'text-slate-100 group-hover:text-emerald-500'
                        }`} />
                      </div>
                      <div>
                        <div className="font-extrabold text-base text-slate-100">{preset.label}</div>
                        <div className="text-xs text-slate-400 font-mono mt-0.5">{preset.email}</div>
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">{preset.desc}</p>
                    </div>
                    
                    <div className={`flex items-center justify-between pt-4 border-t transition mt-auto w-full ${
                      isSelected ? 'border-slate-100' : 'border-slate-800 group-hover:border-slate-400'
                    }`}>
                      <span className="text-xs font-semibold text-slate-400 group-hover:text-slate-100">Access Portal</span>
                      <ArrowRight className={`w-4 h-4 transition ${
                        isSelected ? 'text-emerald-500 translate-x-1' : 'text-slate-400 group-hover:text-emerald-500 group-hover:translate-x-1'
                      }`} />
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Header */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex flex-wrap justify-between items-center gap-4 sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <ShieldCheck className="w-8 h-8 text-slate-100" />
          <div>
            <h1 className="text-lg font-bold text-slate-100">Standardised POD Engine</h1>
            <span className="text-[10px] px-2.5 py-1 rounded-full bg-slate-950 border border-slate-800 text-slate-400 capitalize font-mono font-semibold">
              Role: {userRole} ({userEmail})
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {/* Offline Mode Toggle Simulator */}
          <button
            onClick={() => setIsOfflineSimulated(!isOfflineSimulated)}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-full text-xs font-semibold border transition btn-press-feedback ${
              isOfflineSimulated
                ? 'bg-amber-50 text-amber-700 border-amber-200'
                : 'bg-emerald-50 text-emerald-700 border-emerald-200'
            }`}
          >
            {isOfflineSimulated ? <WifiOff className="w-4 h-4" /> : <Wifi className="w-4 h-4" />}
            <span>{isOfflineSimulated ? 'Offline Mode (Simulated)' : 'Online Mode'}</span>
          </button>

          {/* Sync Queue Badge */}
          <button
            onClick={() => SyncManager.flushQueue(token)}
            className="flex items-center space-x-2 px-3.5 py-1.5 rounded-xl bg-slate-950 border border-slate-800 hover:bg-slate-800 text-xs text-slate-400 transition btn-press-feedback"
            title="Flush IndexedDB Queue"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
            <span>Sync Queue:</span>
            <span className="font-bold text-slate-100">{pendingQueueCount}</span>
          </button>

          <button
            onClick={handleLogout}
            className="p-2 text-slate-400 hover:text-slate-100 rounded-xl hover:bg-slate-800 transition btn-press-feedback"
            title="Sign out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6 space-y-6">
        {/* Navigation Tabs */}
        <div className="flex space-x-2 border-b border-slate-800 pb-2 overflow-x-auto">
          <button
            onClick={() => {
              setActiveTab('deliveries');
              fetchDeliveries();
            }}
            className={`px-4 py-2 text-sm font-semibold rounded-xl transition btn-press-feedback ${
              activeTab === 'deliveries' ? 'bg-slate-100 text-slate-900 shadow-sm' : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            Deliveries List ({deliveries.length})
          </button>

          <button
            onClick={() => setActiveTab('validation')}
            className={`px-4 py-2 text-sm font-semibold rounded-xl flex items-center space-x-1.5 transition btn-press-feedback ${
              activeTab === 'validation' ? 'bg-slate-100 text-slate-900 shadow-sm' : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            <ShieldCheck className={`w-4 h-4 ${activeTab === 'validation' ? 'text-slate-900' : 'text-slate-400'}`} />
            <span>Stakeholder Validation</span>
          </button>

          {(userRole === 'dispatcher' || userRole === 'admin') && (
            <button
              onClick={() => setActiveTab('dispatcher')}
              className={`px-4 py-2 text-sm font-semibold rounded-xl flex items-center space-x-1.5 transition btn-press-feedback ${
                activeTab === 'dispatcher' ? 'bg-slate-100 text-slate-900 shadow-sm' : 'text-slate-400 hover:bg-slate-800'
              }`}
            >
              <ShieldCheck className={`w-4 h-4 ${activeTab === 'dispatcher' ? 'text-slate-900' : 'text-slate-400'}`} />
              <span>Dispatcher Console</span>
            </button>
          )}

          {userRole === 'admin' && (
            <>
              <button
                onClick={() => setActiveTab('admin_analytics')}
                className={`px-4 py-2 text-sm font-semibold rounded-xl flex items-center space-x-1.5 transition btn-press-feedback ${
                  activeTab === 'admin_analytics' ? 'bg-slate-100 text-slate-900 shadow-sm' : 'text-slate-400 hover:bg-slate-800'
                }`}
              >
                <ShieldCheck className={`w-4 h-4 ${activeTab === 'admin_analytics' ? 'text-slate-900' : 'text-slate-400'}`} />
                <span>Admin Analytics</span>
              </button>

              <button
                onClick={() => setActiveTab('experiments')}
                className={`px-4 py-2 text-sm font-semibold rounded-xl flex items-center space-x-1.5 transition btn-press-feedback ${
                  activeTab === 'experiments' ? 'bg-slate-100 text-slate-900 shadow-sm' : 'text-slate-400 hover:bg-slate-800'
                }`}
              >
                <RefreshCw className={`w-4 h-4 ${activeTab === 'experiments' ? 'text-slate-900' : 'text-slate-400'}`} />
                <span>Experiment & Evaluation</span>
              </button>
            </>
          )}

          {userRole === 'restaurant' && (
            <button
              onClick={() => setActiveTab('create_delivery')}
              className={`px-4 py-2 text-sm font-semibold rounded-xl flex items-center space-x-1.5 transition btn-press-feedback ${
                activeTab === 'create_delivery' ? 'bg-slate-100 text-slate-900 shadow-sm' : 'text-slate-400 hover:bg-slate-800'
              }`}
            >
              <PlusCircle className={`w-4 h-4 ${activeTab === 'create_delivery' ? 'text-slate-900' : 'text-slate-400'}`} />
              <span>Create Delivery</span>
            </button>
          )}
        </div>

        {/* TAB: Stakeholder Validation (Participant Form) */}
        {activeTab === 'validation' && (
          <div className="space-y-6 animate-fade-in-up">
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-sm space-y-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
                  <ShieldCheck className="w-6 h-6 text-slate-100" />
                  <span>Stakeholder Validation Workspace</span>
                </h2>
                <p className="text-xs text-slate-400 mt-1">Help the project team evaluate system usability by completing assigned tasks and sharing your experience.</p>
              </div>

              {!valSessionCreated ? (
                <div className="bg-slate-950 p-6 rounded-2xl border border-slate-800 space-y-4 max-w-xl">
                  <h3 className="text-sm font-bold text-slate-300">Start a Validation Session</h3>
                  
                  <div className="space-y-3 text-xs">
                    <div className="space-y-1">
                      <label className="text-slate-400 font-semibold block">Select Your Role</label>
                      <select
                        value={valStakeholderRole}
                        onChange={(e) => {
                          const role = e.target.value;
                          setValStakeholderRole(role);
                          if (role === 'rider') setValScenario('Accept delivery, capture multi-factor evidence, complete offline, sync');
                          if (role === 'dispatcher') setValScenario('Inspect disputed delivery, verify telemetry, perform override');
                          if (role === 'customer') setValScenario('Track order, verify using OTP, raise delivery dispute');
                          if (role === 'restaurant') setValScenario('Create order, assign rider, view final completion state');
                        }}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none"
                      >
                        <option value="rider">Rider (Courier)</option>
                        <option value="dispatcher">Dispatcher (Reviewer)</option>
                        <option value="restaurant">Restaurant Staff</option>
                        <option value="customer">Customer (Recipient)</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-slate-400 font-semibold block">Participant Code (Optional)</label>
                      <input
                        type="text"
                        placeholder="e.g. PART-01"
                        value={valParticipantCode}
                        onChange={(e) => setValParticipantCode(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none font-mono"
                      />
                    </div>

                    <div className="space-y-1">
                      <label className="text-slate-400 font-semibold block">Scenario Description</label>
                      <textarea
                        readOnly
                        value={valScenario}
                        rows={2}
                        className="w-full bg-slate-900/50 border border-slate-800 rounded-xl px-3 py-2 text-slate-400 focus:outline-none resize-none"
                      />
                    </div>
                  </div>

                  {/* Scenarios Reference */}
                  <div className="p-3.5 bg-slate-900/50 rounded-xl border border-slate-800 text-xs space-y-2">
                    <span className="font-bold text-slate-300 block">Your Assigned Tasks:</span>
                    {valStakeholderRole === 'rider' && (
                      <ol className="list-decimal pl-4 text-slate-400 space-y-1">
                        <li>Accept an assigned delivery.</li>
                        <li>Capture photo, GPS, timestamp, OTP and signature.</li>
                        <li>Complete delivery while offline.</li>
                        <li>Reconnect and verify synchronization.</li>
                      </ol>
                    )}
                    {valStakeholderRole === 'dispatcher' && (
                      <ol className="list-decimal pl-4 text-slate-400 space-y-1">
                        <li>Open a disputed delivery.</li>
                        <li>Inspect evidence score and GPS.</li>
                        <li>Review the evidence.</li>
                        <li>Perform an override with a reason.</li>
                      </ol>
                    )}
                    {valStakeholderRole === 'customer' && (
                      <ol className="list-decimal pl-4 text-slate-400 space-y-1">
                        <li>View delivery status.</li>
                        <li>Verify delivery using OTP.</li>
                        <li>Raise a dispute.</li>
                      </ol>
                    )}
                    {valStakeholderRole === 'restaurant' && (
                      <ol className="list-decimal pl-4 text-slate-400 space-y-1">
                        <li>Create an order.</li>
                        <li>Assign/track delivery.</li>
                        <li>View delivery completion status.</li>
                      </ol>
                    )}
                  </div>

                  <button
                    onClick={handleStartValidationSession}
                    className="w-full btn-primary font-bold text-xs py-2.5 rounded-xl transition btn-press-feedback"
                  >
                    Start Validation Session
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmitValidationFeedback} className="space-y-6 max-w-2xl bg-slate-950 p-6 rounded-2xl border border-slate-800">
                  <div className="flex justify-between items-center border-b border-slate-800 pb-3">
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase font-mono font-bold block">Active Session</span>
                      <span className="text-xs font-mono text-slate-400">{valSessionId}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setValSessionCreated(false)}
                      className="text-xs text-slate-400 hover:text-slate-100 hover:underline"
                    >
                      Cancel Session
                    </button>
                  </div>

                  <h3 className="text-sm font-bold text-slate-300">Usability Questionnaire</h3>
                  <p className="text-xs text-slate-400">Please rate the system usability based on your validation experience. (1 = Strongly Disagree, 5 = Strongly Agree)</p>

                  <div className="space-y-5">
                    {[
                      { id: 'Q1', text: 'The delivery workflow was easy to understand.' },
                      { id: 'Q2', text: 'Capturing delivery evidence was easy.' },
                      { id: 'Q3', text: 'The evidence quality score was easy to understand.' },
                      { id: 'Q4', text: 'The system clearly explained missing or invalid evidence.' },
                      { id: 'Q5', text: 'Offline capture and synchronization were understandable.' },
                      { id: 'Q6', text: 'The dispatcher review and override process was clear.' },
                      { id: 'Q7', text: 'The system provided enough information to resolve a delivery dispute.' },
                      { id: 'Q8', text: 'The dashboard information was easy to understand.' },
                      { id: 'Q9', text: 'The system increased confidence in delivery verification.' },
                      { id: 'Q10', text: 'Overall, I would be comfortable using this system.' }
                    ].map((q) => (
                      <div key={q.id} className="p-4 bg-slate-900/40 border border-slate-800/80 rounded-xl space-y-3.5">
                        <div className="flex justify-between items-start gap-2">
                          <span className="text-xs font-bold text-slate-400 font-mono w-6">{q.id}.</span>
                          <span className="text-xs text-slate-200 flex-1">{q.text}</span>
                        </div>

                        <div className="flex justify-between items-center gap-2 max-w-sm ml-6">
                          {[1, 2, 3, 4, 5].map((score) => (
                            <button
                              key={score}
                              type="button"
                              onClick={() => setValRatings({ ...valRatings, [q.id]: score })}
                              className={`w-9 h-9 rounded-full font-mono text-xs font-bold border transition btn-press-feedback ${
                                valRatings[q.id] === score
                                  ? 'bg-slate-100 border-slate-100 text-slate-900 shadow-sm'
                                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-300'
                              }`}
                            >
                              {score}
                            </button>
                          ))}
                        </div>

                        <div className="ml-6">
                          <input
                            type="text"
                            placeholder="Optional comment/observation for this question..."
                            value={valComments[q.id] || ''}
                            onChange={(e) => setValComments({ ...valComments, [q.id]: e.target.value })}
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-slate-700"
                          />
                        </div>
                      </div>
                    ))}
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmittingFeedback}
                    className="w-full btn-primary disabled:opacity-50 font-bold text-xs py-2.5 rounded-xl transition btn-press-feedback"
                  >
                    {isSubmittingFeedback ? 'Submitting Responses...' : 'Submit Feedback Responses'}
                  </button>
                </form>
              )}
            </div>
          </div>
        )}

        {/* TAB: Dispatcher Console */}
        {activeTab === 'dispatcher' && (
          <DispatcherWorkspace token={token} onRefreshDeliveries={fetchDeliveries} />
        )}

        {/* TAB: Experiment & Evaluation */}
        {activeTab === 'experiments' && (
          <div className="space-y-6">
            {/* Header & Controls */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-wrap justify-between items-center gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
                  <RefreshCw className="w-6 h-6 text-amber-500" />
                  <span>Baseline Comparison & Measurable Evaluation</span>
                </h2>
                <p className="text-xs text-slate-400 mt-1">Compare proposed multi-factor engine against traditional baseline using 50+ delivery scenarios</p>
              </div>

              <div className="flex items-center gap-3">
                {runs.length > 0 && (
                  <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase font-semibold">Select Run</span>
                    <select
                      value={selectedRunId}
                      onChange={(e) => setSelectedRunId(e.target.value)}
                      className="bg-transparent border-0 text-xs text-slate-200 focus:ring-0 font-mono outline-none cursor-pointer"
                    >
                      {runs.map((r: any) => (
                        <option key={r.id} value={r.id} className="bg-slate-900">
                          {r.name} ({r.id})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
                <button
                  onClick={triggerExperiment}
                  disabled={isEvaluationRunning}
                  className="btn-primary disabled:opacity-50 text-xs font-bold px-4 py-2 rounded-xl transition flex items-center space-x-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isEvaluationRunning ? 'animate-spin' : ''}`} />
                  <span>{isEvaluationRunning ? 'Evaluating...' : 'Run New Experiment'}</span>
                </button>
              </div>
            </div>

            {/* Run Detail Loading */}
            {runDetailLoading && (
              <div className="text-center py-12 bg-slate-900/40 border border-slate-800/60 rounded-3xl">
                <RefreshCw className="w-8 h-8 text-amber-500 animate-spin mx-auto mb-2" />
                <span className="text-sm text-slate-400">Loading experiment detail...</span>
              </div>
            )}

            {/* Run Content */}
            {!runDetailLoading && runDetail && (
              <div className="space-y-6">
                {/* A. Experiment Summary Card */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold uppercase text-slate-400">Run Configuration & Metadata</h3>
                    <div className="space-y-2 text-xs">
                      <div>
                        <span className="text-slate-500 block">Experiment Name</span>
                        <span className="font-semibold text-slate-200">{runDetail.run.name}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Dataset Size</span>
                        <span className="font-mono text-amber-400 font-semibold">{runDetail.run.dataset_size} Realistic Scenarios</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <span className="text-slate-500 block">Run ID</span>
                          <span className="font-mono text-slate-300">{runDetail.run.id}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Executed At</span>
                          <span className="text-slate-300">{new Date(runDetail.run.created_at).toLocaleString()}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3 border-t md:border-t-0 md:border-l border-slate-800/80 md:pl-6">
                    <h3 className="text-xs font-bold uppercase text-slate-400">Comparison Models</h3>
                    <div className="space-y-2 text-xs">
                      <div>
                        <span className="text-rose-400 font-semibold block">Baseline (Traditional System)</span>
                        <span className="text-slate-400">{runDetail.run.baseline_description}</span>
                      </div>
                      <div>
                        <span className="text-emerald-400 font-semibold block">Proposed System (Standardised POD Engine)</span>
                        <span className="text-slate-400">{runDetail.run.proposed_system_description}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* B. KPI Comparison Side-by-Side Cards */}
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  {[
                    { label: 'Accuracy', base: runDetail.baseline_metrics.accuracy, prop: runDetail.proposed_metrics.accuracy, isPct: true },
                    { label: 'Dispute Rate', base: runDetail.baseline_metrics.dispute_rate, prop: runDetail.proposed_metrics.dispute_rate, isPct: true },
                    { label: 'Disputes Resolved', base: runDetail.baseline_metrics.disputes_resolved, prop: runDetail.proposed_metrics.disputes_resolved, isPct: false },
                    { label: 'Dispute Res. Rate', base: runDetail.baseline_metrics.dispute_resolution_rate, prop: runDetail.proposed_metrics.dispute_resolution_rate, isPct: true },
                    { label: 'Evidence Validity', base: runDetail.baseline_metrics.evidence_validity_rate, prop: runDetail.proposed_metrics.evidence_validity_rate, isPct: true }
                  ].map((card, idx) => {
                    const diff = card.prop - card.base;
                    const changeSymbol = diff >= 0 ? '+' : '';
                    const baseDisp = card.isPct ? `${(card.base * 100).toFixed(0)}%` : card.base;
                    const propDisp = card.isPct ? `${(card.prop * 100).toFixed(0)}%` : card.prop;
                    const diffDisp = card.isPct ? `${changeSymbol}${(diff * 100).toFixed(0)}%` : `${changeSymbol}${diff.toFixed(1)}`;
                    
                    return (
                      <div key={idx} className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2 shadow-lg">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold">{card.label}</span>
                        <div className="flex justify-between items-baseline">
                          <div>
                            <span className="text-[10px] text-rose-400 font-mono block">Base: {baseDisp}</span>
                            <span className="text-xl font-bold font-mono text-slate-100">Prop: {propDisp}</span>
                          </div>
                          <span className={`text-xs font-bold font-mono px-2 py-0.5 rounded-full ${
                            diff > 0 ? 'bg-emerald-500/10 text-emerald-400' : diff < 0 ? 'bg-rose-500/10 text-rose-400' : 'bg-slate-800 text-slate-400'
                          }`}>
                            {diffDisp}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* C. Metrics and Incident Detection Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* side-by-side metrics */}
                  <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl">
                    <h3 className="text-xs font-bold uppercase text-slate-400">Key Performance Indicators</h3>
                    <div className="space-y-4">
                      {[
                        { label: 'Overall System Accuracy', base: runDetail.baseline_metrics.accuracy, prop: runDetail.proposed_metrics.accuracy },
                        { label: 'Dispute Resolution Efficiency', base: runDetail.baseline_metrics.dispute_resolution_rate, prop: runDetail.proposed_metrics.dispute_resolution_rate },
                        { label: 'Evidence Validity Rate', base: runDetail.baseline_metrics.evidence_validity_rate, prop: runDetail.proposed_metrics.evidence_validity_rate },
                        { label: 'Offline Success Rate', base: runDetail.baseline_metrics.offline_success_rate, prop: runDetail.proposed_metrics.offline_success_rate }
                      ].map((item, idx) => (
                        <div key={idx} className="space-y-1 text-xs">
                          <span className="text-slate-300 font-medium">{item.label}</span>
                          <div className="flex items-center space-x-2">
                            <span className="w-8 text-[10px] text-rose-400 font-mono">BASE</span>
                            <div className="flex-1 bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                              <div style={{ width: `${item.base * 100}%` }} className="h-full bg-rose-600 transition-all duration-500 ease-out" />
                            </div>
                            <span className="w-8 text-right font-mono text-rose-400">{(item.base * 100).toFixed(0)}%</span>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="w-8 text-[10px] text-emerald-400 font-mono">PROP</span>
                            <div className="flex-1 bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                              <div style={{ width: `${item.prop * 100}%` }} className="h-full bg-emerald-600 transition-all duration-500 ease-out" />
                            </div>
                            <span className="w-8 text-right font-mono text-emerald-400">{(item.prop * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Incident Detection Performance */}
                  <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl">
                    <h3 className="text-xs font-bold uppercase text-slate-400">Anomalous Telemetry Detection Rate</h3>
                    <div className="space-y-3.5">
                      {[
                        { label: 'Blurry Photo Detection', val: runDetail.proposed_metrics.blur_detection_rate, color: 'bg-emerald-500' },
                        { label: 'GPS Absent Flagging', val: runDetail.proposed_metrics.gps_failure_detection_rate, color: 'bg-slate-100' },
                        { label: 'GPS Mismatch (>150m) Isolation', val: runDetail.proposed_metrics.gps_mismatch_detection_rate, color: 'bg-slate-100' },
                        { label: 'Missing Signature Capture', val: runDetail.proposed_metrics.missing_signature_detection_rate, color: 'bg-slate-300' },
                        { label: 'Invalid OTP Verification', val: runDetail.proposed_metrics.invalid_otp_detection_rate, color: 'bg-slate-300' }
                      ].map((item, idx) => (
                        <div key={idx} className="space-y-1 text-xs">
                          <div className="flex justify-between font-medium">
                            <span className="text-slate-300">{item.label}</span>
                            <span className="font-mono text-slate-400">{(item.val * 100).toFixed(0)}% Detected</span>
                          </div>
                          <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-800">
                            <div style={{ width: `${item.val * 100}%` }} className={`h-full ${item.color} rounded-full transition-all duration-500 ease-out`} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* D. Target vs Measured Goals */}
                <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
                  <h3 className="text-sm font-bold uppercase text-slate-300">Target Objectives vs Stored Measurements</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 space-y-2">
                      <span className="font-bold text-slate-400 block">Baseline Accuracy</span>
                      <div className="text-2xl font-mono font-bold text-rose-400">{(runDetail.baseline_metrics.accuracy * 100).toFixed(0)}%</div>
                      <span className="text-slate-500 text-[10px]">Historic benchmark accuracy under traditional protocols.</span>
                    </div>
                    <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 border-l-slate-100 space-y-2">
                      <span className="font-bold text-slate-100 block">Target KPI Objective</span>
                      <div className="text-2xl font-mono font-bold text-slate-100">95%</div>
                      <span className="text-slate-500 text-[10px]">Strategic benchmark goal set for accuracy in evidence classification.</span>
                    </div>
                    <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 border-l-emerald-500/30 space-y-2">
                      <span className="font-bold text-emerald-400 block">Measured Result</span>
                      <div className="text-2xl font-mono font-bold text-emerald-400">{(runDetail.proposed_metrics.accuracy * 100).toFixed(0)}%</div>
                      <span className="text-slate-500 text-[10px]">Actual verified performance calculated from this experiment run.</span>
                    </div>
                  </div>
                </div>

                {/* E. Error Analysis Ledger */}
                <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
                  <h3 className="text-sm font-bold uppercase text-slate-300">Automated Error Analysis Ledger</h3>
                  {runDetail.error_analysis_table.length === 0 ? (
                    <div className="p-4 bg-slate-950 rounded-2xl text-center text-xs text-emerald-400 border border-emerald-500/10">
                      Zero classification errors recorded! Nominal accuracy matches expected ground-truth outcomes.
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400">
                            <th className="py-3 px-4">Case ID</th>
                            <th className="py-3 px-4">Scenario Category</th>
                            <th className="py-3 px-4">Expected (Ground Truth)</th>
                            <th className="py-3 px-4">Baseline Output</th>
                            <th className="py-3 px-4">Proposed Output</th>
                            <th className="py-3 px-4">Error Type</th>
                            <th className="py-3 px-4">Technical Explanation</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                          {runDetail.error_analysis_table.map((row: any, idx: number) => (
                            <tr key={idx} className="hover:bg-slate-800/20 text-slate-300 transition">
                              <td className="py-3.5 px-4 font-mono font-bold text-amber-500">{row.case_id}</td>
                              <td className="py-3.5 px-4">{row.scenario_type}</td>
                              <td className="py-3.5 px-4 uppercase font-semibold text-slate-200">{row.expected_outcome}</td>
                              <td className="py-3.5 px-4 uppercase text-slate-500">{row.baseline_outcome}</td>
                              <td className="py-3.5 px-4 uppercase text-slate-300">{row.proposed_outcome}</td>
                              <td className="py-3.5 px-4">
                                <span className="px-2 py-0.5 rounded-full font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 text-[10px]">
                                  {row.error_type}
                                </span>
                              </td>
                              <td className="py-3.5 px-4 text-slate-400 italic">{row.explanation}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* F. Metric Comparison Table */}
                <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
                  <h3 className="text-sm font-bold uppercase text-slate-300">Metric Comparison Matrix</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="py-3 px-4">Metric Dimension</th>
                          <th className="py-3 px-4">Baseline Performance</th>
                          <th className="py-3 px-4">Proposed System</th>
                          <th className="py-3 px-4">Absolute Gain</th>
                          <th className="py-3 px-4">Improvement Rate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50">
                        {runDetail.comparison_table.map((row: any, idx: number) => {
                          const isCount = row.metric_name.includes("Count") || row.metric_name.includes("Resolved");
                          const baseStr = isCount ? row.baseline_value.toFixed(0) : `${(row.baseline_value * 100).toFixed(0)}%`;
                          const propStr = isCount ? row.proposed_value.toFixed(0) : `${(row.proposed_value * 100).toFixed(0)}%`;
                          const diffStr = isCount ? `${row.absolute_difference >= 0 ? '+' : ''}${row.absolute_difference.toFixed(0)}` : `${row.absolute_difference >= 0 ? '+' : ''}${(row.absolute_difference * 100).toFixed(0)}%`;
                          const gainColor = row.absolute_difference > 0 ? 'text-emerald-400' : row.absolute_difference < 0 ? 'text-rose-400' : 'text-slate-400';

                          return (
                            <tr key={idx} className="hover:bg-slate-800/20 text-slate-300 transition">
                              <td className="py-3.5 px-4 font-semibold text-slate-200">{row.metric_name}</td>
                              <td className="py-3.5 px-4 font-mono">{baseStr}</td>
                              <td className="py-3.5 px-4 font-mono font-bold text-slate-100">{propStr}</td>
                              <td className={`py-3.5 px-4 font-mono font-bold ${gainColor}`}>{diffStr}</td>
                              <td className="py-3.5 px-4 font-mono">
                                {row.percentage_improvement !== null ? (
                                  <span className={`font-semibold ${row.percentage_improvement >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                    {row.percentage_improvement >= 0 ? '+' : ''}{row.percentage_improvement.toFixed(1)}%
                                  </span>
                                ) : (
                                  <span className="text-slate-500">N/A</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* G. Reproducibility Footer */}
                <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl flex flex-wrap justify-between items-center gap-2 text-[10px] text-slate-500 font-mono">
                  <span>Rules Version: v1.1.0-engine</span>
                  <span>Dataset Seed: #POD-EXP-SEED-50S</span>
                  <span>Evaluator Hash: MD5-DeterministicBSSLN</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB: Admin Analytics */}
        {activeTab === 'admin_analytics' && (
          <div className="space-y-6">
            {/* Header & Date Filters */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-wrap justify-between items-center gap-4">
              <div>
                <h2 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
                  <ShieldCheck className="w-6 h-6 text-purple-400" />
                  <span>Admin Control & Analytics Dashboard</span>
                </h2>
                <p className="text-xs text-slate-400 mt-1">Real-time performance indicators and evidence verification metrics</p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">From</span>
                  <input
                    type="date"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                    className="bg-transparent border-0 text-xs text-slate-200 focus:ring-0 font-mono outline-none"
                  />
                </div>
                <div className="flex items-center space-x-2 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 uppercase font-semibold">To</span>
                  <input
                    type="date"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                    className="bg-transparent border-0 text-xs text-slate-200 focus:ring-0 font-mono outline-none"
                  />
                </div>
                <button
                  onClick={fetchAnalytics}
                  className="btn-primary text-xs font-bold px-4 py-2 rounded-xl transition"
                >
                  Apply Filter
                </button>
                <button
                  onClick={() => {
                    setFromDate('');
                    setToDate('');
                    setTimeout(() => fetchAnalytics(), 0);
                  }}
                  className="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold px-3 py-2 rounded-xl transition"
                >
                  Reset
                </button>
              </div>
            </div>

            {/* Error or Loading States */}
            {analyticsLoading && (
              <div className="text-center py-12 bg-slate-900/40 border border-slate-800/60 rounded-3xl">
                <RefreshCw className="w-8 h-8 text-slate-100 animate-spin mx-auto mb-2" />
                <span className="text-sm text-slate-400">Aggregating system statistics from database...</span>
              </div>
            )}

            {analyticsError && (
              <div className="bg-rose-500/10 border border-rose-500/20 text-rose-400 px-4 py-3 rounded-2xl text-xs flex items-center space-x-2">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{analyticsError}</span>
              </div>
            )}

            {/* Empty State */}
            {!analyticsLoading && !analyticsError && (!analytics || analytics.total_deliveries === 0) && (
              <div className="text-center py-16 bg-slate-900 border border-slate-800 rounded-3xl space-y-4">
                <AlertTriangle className="w-12 h-12 text-slate-600 mx-auto" />
                <h3 className="text-lg font-bold text-slate-300">No Data Available</h3>
                <p className="text-xs text-slate-500 max-w-sm mx-auto">No delivery data available for the selected period.</p>
              </div>
            )}

            {/* Dashboard Content */}
            {!analyticsLoading && !analyticsError && analytics && analytics.total_deliveries > 0 && (
              <div className="space-y-6">
                {/* 1. KPI Cards Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1 shadow-lg">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Total Deliveries</span>
                    <div className="text-2xl font-bold font-mono text-slate-100">{analytics.total_deliveries}</div>
                    <div className="text-[10px] text-slate-500">Scheduled / Dispatched</div>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1 shadow-lg border-l-emerald-500/40">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Accepted</span>
                    <div className="text-2xl font-bold font-mono text-emerald-400">{analytics.accepted_deliveries}</div>
                    <div className="text-[10px] text-emerald-500 font-mono">{(analytics.evidence_acceptance_rate * 100).toFixed(1)}% Rate</div>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1 shadow-lg border-l-amber-500/40">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Manual Review</span>
                    <div className="text-2xl font-bold font-mono text-amber-400">{analytics.manual_review_deliveries}</div>
                    <div className="text-[10px] text-slate-500">Awaiting override</div>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1 shadow-lg border-l-rose-500/40">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Disputed</span>
                    <div className="text-2xl font-bold font-mono text-rose-400">{analytics.disputed_deliveries}</div>
                    <div className="text-[10px] text-slate-500">Contested by customer</div>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1 shadow-lg">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Avg Quality Score</span>
                    <div className="text-2xl font-bold font-mono text-slate-100">
                      {analytics.average_evidence_score ? `${analytics.average_evidence_score}/100` : 'N/A'}
                    </div>
                    <div className="text-[10px] text-slate-500">Overall engine mean</div>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-1 shadow-lg">
                    <span className="text-[10px] text-slate-400 uppercase font-semibold">Dispute Rate</span>
                    <div className="text-2xl font-bold font-mono text-slate-100">
                      {(analytics.dispute_rate * 100).toFixed(1)}%
                    </div>
                    <div className="text-[10px] text-slate-500">Disputes / Total Ratio</div>
                  </div>
                </div>

                {/* 2. Visualizations Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Left Column: Delivery Status & Score Ranges */}
                  <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-6 shadow-xl">
                    {/* Status Distribution Visual */}
                    <div className="space-y-3">
                      <h3 className="text-xs font-bold uppercase text-slate-400">Delivery Status Breakdown</h3>
                      <div className="h-6 w-full bg-slate-950 rounded-full overflow-hidden flex border border-slate-800">
                        {analytics.status_distribution.map((item: any, idx: number) => {
                          const pct = (item.count / analytics.total_deliveries) * 100;
                          if (pct === 0) return null;
                          const color = item.status === 'delivered' ? 'bg-emerald-500' :
                                        item.status === 'needs_review' ? 'bg-amber-500' :
                                        item.status === 'disputed' ? 'bg-rose-500' : 'bg-slate-500';
                          return (
                            <div
                              key={idx}
                              style={{ width: `${pct}%` }}
                              className={`${color} h-full transition-all duration-500`}
                              title={`${item.status}: ${item.count} (${pct.toFixed(1)}%)`}
                            />
                          );
                        })}
                      </div>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
                        {analytics.status_distribution.map((item: any, idx: number) => {
                          const color = item.status === 'delivered' ? 'bg-emerald-500' :
                                        item.status === 'needs_review' ? 'bg-amber-500' :
                                        item.status === 'disputed' ? 'bg-rose-500' : 'bg-slate-500';
                          return (
                            <div key={idx} className="flex items-center space-x-1.5">
                              <span className={`w-2.5 h-2.5 rounded-full ${color}`} />
                              <span className="capitalize text-slate-300">{item.status} ({item.count})</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Score Distribution Ranges */}
                    <div className="space-y-3 pt-4 border-t border-slate-800/60">
                      <h3 className="text-xs font-bold uppercase text-slate-400">Evidence Quality distribution</h3>
                      <div className="space-y-3">
                        {analytics.evidence_score_distribution.map((item: any, idx: number) => {
                          const totalScores = analytics.evidence_score_distribution.reduce((acc: number, curr: any) => acc + curr.count, 0);
                          const pct = totalScores > 0 ? (item.count / totalScores) * 100 : 0;
                          const color = item.range === '90–100' ? 'bg-emerald-600' :
                                        item.range === '70–89' ? 'bg-amber-600' : 'bg-rose-600';
                          return (
                            <div key={idx} className="space-y-1">
                              <div className="flex justify-between text-xs font-medium">
                                <span className="text-slate-300">Range: {item.range}</span>
                                <span className="text-slate-400 font-mono">{item.count} items ({pct.toFixed(0)}%)</span>
                              </div>
                              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                                <div style={{ width: `${pct}%` }} className={`h-full ${color} rounded-full transition-all duration-500 ease-out`} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {/* Middle Column: Component Performance & Flags */}
                  <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-6 shadow-xl">
                    <div className="space-y-3">
                      <h3 className="text-xs font-bold uppercase text-slate-400">Evidence Component Ratings</h3>
                      <div className="space-y-3.5">
                        {[
                          { label: 'Photo Verification', val: analytics.evidence_component_performance.photo, max: 25, color: 'bg-emerald-500' },
                          { label: 'GPS Geolocation Match', val: analytics.evidence_component_performance.gps, max: 25, color: 'bg-slate-100' },
                          { label: 'Timestamp Sanity Check', val: analytics.evidence_component_performance.timestamp, max: 20, color: 'bg-slate-100' },
                          { label: 'Recipient Signature', val: analytics.evidence_component_performance.signature, max: 20, color: 'bg-slate-300' },
                          { label: 'OTP Code Validation', val: analytics.evidence_component_performance.otp, max: 10, color: 'bg-slate-300' }
                        ].map((comp, idx) => {
                          const pct = (comp.val / comp.max) * 100;
                          return (
                            <div key={idx} className="space-y-1">
                              <div className="flex justify-between text-xs font-medium">
                                <span className="text-slate-300">{comp.label}</span>
                                <span className="font-mono text-slate-400">{comp.val} / {comp.max} ({pct.toFixed(0)}%)</span>
                              </div>
                              <div className="w-full bg-slate-950 h-2.5 rounded-full overflow-hidden border border-slate-800">
                                <div style={{ width: `${pct}%` }} className={`h-full ${comp.color} rounded-full transition-all duration-500 ease-out`} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Flags / Anomalies */}
                    <div className="space-y-2 pt-4 border-t border-slate-800/60 text-xs">
                      <h3 className="text-xs font-bold uppercase text-slate-400 mb-1">Incident Rates</h3>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                          <span className="text-slate-500 block">Missing GPS</span>
                          <span className="font-mono font-bold text-slate-200">{analytics.evidence_component_flags.missing_gps_percentage}%</span>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                          <span className="text-slate-500 block">GPS Mismatch</span>
                          <span className="font-mono font-bold text-slate-200">{analytics.evidence_component_flags.gps_mismatch_percentage}%</span>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                          <span className="text-slate-500 block">Offline Capture</span>
                          <span className="font-mono font-bold text-slate-200">{analytics.evidence_component_flags.offline_capture_percentage}%</span>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                          <span className="text-slate-500 block">Low-Quality Photo</span>
                          <span className="font-mono font-bold text-slate-200">{analytics.evidence_component_flags.low_quality_photo_percentage}%</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Right Column: Dispute Analytics & Trends */}
                  <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-6 shadow-xl">
                    <div className="space-y-3">
                      <h3 className="text-xs font-bold uppercase text-slate-400">Dispute Resolution Performance</h3>
                      <div className="grid grid-cols-3 gap-2 text-center text-xs">
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
                          <span className="text-[10px] text-slate-500 block">Total Raised</span>
                          <span className="font-mono font-bold text-slate-200 text-sm">{analytics.dispute_analytics.total_disputes}</span>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 border-t-amber-500/40">
                          <span className="text-[10px] text-slate-500 block">Open / Review</span>
                          <span className="font-mono font-bold text-slate-200 text-sm">
                            {analytics.dispute_analytics.open_disputes + analytics.dispute_analytics.in_review_disputes}
                          </span>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800 border-t-emerald-500/40">
                          <span className="text-[10px] text-slate-500 block">Resolved</span>
                          <span className="font-mono font-bold text-slate-200 text-sm">
                            {analytics.dispute_analytics.resolved_disputes + analytics.dispute_analytics.rejected_disputes}
                          </span>
                        </div>
                      </div>
                      <div className="space-y-1.5 text-xs text-slate-300">
                        <div className="flex justify-between">
                          <span>Resolution Rate:</span>
                          <span className="font-bold font-mono text-emerald-400">{(analytics.dispute_analytics.resolution_rate * 100).toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Avg Resolution Time:</span>
                          <span className="font-bold font-mono text-slate-200">
                            {analytics.dispute_analytics.average_resolution_time_seconds
                              ? `${(analytics.dispute_analytics.average_resolution_time_seconds / 60).toFixed(1)} min`
                              : 'No resolved data'}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Timeline Trends lists */}
                    <div className="space-y-3 pt-4 border-t border-slate-800/60 text-xs">
                      <h3 className="text-xs font-bold uppercase text-slate-400">Recent Daily Trends</h3>
                      {analytics.daily_delivery_counts.length === 0 ? (
                        <span className="text-slate-500">No trend entries</span>
                      ) : (
                        <div className="max-h-36 overflow-y-auto space-y-2 pr-1 font-mono">
                          {analytics.daily_delivery_counts.map((item: any, idx: number) => {
                            const dispItem = analytics.daily_dispute_counts.find((d: any) => d.day === item.day);
                            return (
                              <div key={idx} className="flex justify-between items-center bg-slate-950 p-2 rounded-xl border border-slate-800/50">
                                <span className="text-slate-400">{item.day}</span>
                                <div className="space-x-3 text-[11px]">
                                  <span className="text-slate-200">Dels: <strong>{item.count}</strong></span>
                                  <span className="text-rose-400">Disps: <strong>{dispItem ? dispItem.count : 0}</strong></span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* 3. Rider Performance Table */}
                <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
                  <h3 className="text-sm font-bold uppercase text-slate-300">Rider Performance Ledger</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="py-3 px-4">Rider</th>
                          <th className="py-3 px-4">Deliveries</th>
                          <th className="py-3 px-4">Accepted</th>
                          <th className="py-3 px-4">Review</th>
                          <th className="py-3 px-4">Disputed</th>
                          <th className="py-3 px-4">Avg Score</th>
                          <th className="py-3 px-4">Offline Captures</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50">
                        {analytics.rider_performance.map((item: any) => (
                          <tr key={item.rider_id} className="hover:bg-slate-800/20 text-slate-300 transition">
                            <td className="py-3.5 px-4 font-semibold text-slate-200">{item.rider_name}</td>
                            <td className="py-3.5 px-4 font-mono">{item.total_deliveries}</td>
                            <td className="py-3.5 px-4 text-emerald-400 font-mono">{item.accepted_deliveries}</td>
                            <td className="py-3.5 px-4 text-amber-400 font-mono">{item.review_deliveries}</td>
                            <td className="py-3.5 px-4 text-rose-400 font-mono">{item.disputed_deliveries}</td>
                            <td className="py-3.5 px-4 font-mono font-bold text-slate-100">
                              {item.average_evidence_score !== null ? `${item.average_evidence_score.toFixed(1)}/100` : 'N/A'}
                            </td>
                            <td className="py-3.5 px-4 font-mono text-amber-500">{item.offline_captures}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 4. Operational Alerts */}
                <div className="space-y-3">
                  <h3 className="text-sm font-bold uppercase text-slate-300">Operational Alerts & Anomalies</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Dispute rate threshold alert */}
                    {analytics.dispute_rate > 0.15 && (
                      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 flex items-start space-x-3 text-rose-700 animate-fade-in-up">
                        <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-600" />
                        <div>
                          <span className="font-bold text-sm block">High Dispute Rate Detected</span>
                          <span className="text-xs text-slate-500 mt-1 block">
                            The dispute rate stands at <strong>{(analytics.dispute_rate * 100).toFixed(1)}%</strong>, which exceeds the acceptable operating threshold of 15.0%. Investigate driver behavior or evidence validity.
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Low evidence score alert */}
                    {analytics.average_evidence_score && analytics.average_evidence_score < 75.0 && (
                      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-start space-x-3 text-amber-700 animate-fade-in-up">
                        <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-600" />
                        <div>
                          <span className="font-bold text-sm block">Sub-optimal Evidence Scores</span>
                          <span className="text-xs text-slate-500 mt-1 block">
                            The overall quality score average is <strong>{analytics.average_evidence_score}/100</strong>. This indicates frequent blur, low lighting, or OTP mismatches. Recommend retraining drivers on photo acquisition.
                          </span>
                        </div>
                      </div>
                    )}

                    {/* GPS failures alert */}
                    {analytics.gps_failure_count / analytics.total_deliveries > 0.25 && (
                      <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 flex items-start space-x-3 text-rose-700 animate-fade-in-up">
                        <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-rose-600" />
                        <div>
                          <span className="font-bold text-sm block">Frequent GPS Failures</span>
                          <span className="text-xs text-slate-500 mt-1 block">
                            Over <strong>{((analytics.gps_failure_count / analytics.total_deliveries) * 100).toFixed(0)}%</strong> of deliveries record GPS failures or out-of-bounds coordinates. Verify rider device compatibility.
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Offline capture alert */}
                    {analytics.offline_capture_count / analytics.total_deliveries > 0.35 && (
                      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-start space-x-3 text-amber-700 animate-fade-in-up">
                        <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5 text-amber-600" />
                        <div>
                          <span className="font-bold text-sm block">Elevated Offline Deliveries</span>
                          <span className="text-xs text-slate-500 mt-1 block">
                            Offline captures represent <strong>{((analytics.offline_capture_count / analytics.total_deliveries) * 100).toFixed(0)}%</strong> of total volume. Indicates network connection drops or riders executing delivery offline.
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Healthy operations state */}
                    {analytics.dispute_rate <= 0.15 &&
                     (!analytics.average_evidence_score || analytics.average_evidence_score >= 75.0) &&
                     (analytics.gps_failure_count / analytics.total_deliveries <= 0.25) &&
                     (analytics.offline_capture_count / analytics.total_deliveries <= 0.35) && (
                      <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 flex items-start space-x-3 text-emerald-700 col-span-2 animate-fade-in-up">
                        <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-600" />
                        <div>
                          <span className="font-bold text-sm block">Operational Efficiency Nominal</span>
                          <span className="text-xs text-slate-500 mt-1 block">
                            All key quality indices fall within nominal limits. Dispute rates, GPS validation bounds, photo quality, and network synchronisation are in healthy thresholds.
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* 5. Stakeholder Validation Summary */}
                <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-6">
                  <div>
                    <h3 className="text-sm font-bold uppercase text-slate-300 flex items-center space-x-2">
                      <ShieldCheck className="w-5 h-5 text-slate-100" />
                      <span>Stakeholder Usability & Validation Summary</span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">Aggregated results from user tests and questionnaire submissions.</p>
                  </div>

                  {validationSummaryLoading && (
                    <div className="text-center py-6 text-xs text-slate-400">
                      Loading validation results...
                    </div>
                  )}

                  {!validationSummaryLoading && (!validationSummary || validationSummary.total_participants === 0) && (
                    <div className="p-4 bg-slate-950 rounded-2xl text-center text-xs text-amber-500 border border-amber-500/10">
                      No stakeholder validation responses available.
                    </div>
                  )}

                  {!validationSummaryLoading && validationSummary && validationSummary.total_participants > 0 && (
                    <div className="space-y-6">
                      {/* KPI Grid */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                        <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                          <span className="text-slate-500 block">Total Participants</span>
                          <span className="text-xl font-bold font-mono text-slate-100">{validationSummary.total_participants}</span>
                        </div>
                        <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                          <span className="text-slate-500 block">Completed Sessions</span>
                          <span className="text-xl font-bold font-mono text-slate-100">{validationSummary.completed_sessions}</span>
                        </div>
                        <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                          <span className="text-slate-500 block">Completion Rate</span>
                          <span className="text-xl font-bold font-mono text-slate-100">{(validationSummary.completion_rate * 100).toFixed(0)}%</span>
                        </div>
                        <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                          <span className="text-slate-500 block">Avg Overall Usability</span>
                          <span className="text-xl font-bold font-mono text-slate-100">{validationSummary.average_overall_rating.toFixed(2)} / 5.0</span>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Question-wise Scores */}
                        <div className="space-y-3.5">
                          <h4 className="text-xs font-bold uppercase text-slate-400">Usability Ratings per Dimension</h4>
                          <div className="space-y-3">
                            {validationSummary.average_rating_per_question.map((item: any, idx: number) => {
                              const pct = (item.average_rating / 5.0) * 100;
                              return (
                                <div key={idx} className="space-y-1 text-xs">
                                  <div className="flex justify-between font-medium">
                                    <span className="text-slate-300">Question {item.question_id}</span>
                                    <span className="font-mono text-slate-400">{item.average_rating.toFixed(1)} / 5.0</span>
                                  </div>
                                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                                    <div style={{ width: `${pct}%` }} className="h-full bg-slate-100 rounded-full transition-all duration-500 ease-out" />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        {/* Role-wise Ratings */}
                        <div className="space-y-3.5">
                          <h4 className="text-xs font-bold uppercase text-slate-400">Usability Ratings by Role</h4>
                          <div className="space-y-3">
                            {validationSummary.average_rating_by_role.map((item: any, idx: number) => {
                              const pct = (item.average_rating / 5.0) * 100;
                              return (
                                <div key={idx} className="space-y-1 text-xs">
                                  <div className="flex justify-between font-medium capitalize">
                                    <span className="text-slate-300">{item.role}</span>
                                    <span className="font-mono text-slate-400">{item.average_rating.toFixed(1)} / 5.0</span>
                                  </div>
                                  <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                                    <div style={{ width: `${pct}%` }} className="h-full bg-slate-100 rounded-full transition-all duration-500 ease-out" />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>

                      {/* Comments Ledger */}
                      {validationSummary.comments.length > 0 && (
                        <div className="space-y-3 pt-4 border-t border-slate-800/60">
                          <h4 className="text-xs font-bold uppercase text-slate-400">Verbatim Feedback & Difficulty Areas</h4>
                          <div className="max-h-40 overflow-y-auto space-y-2 pr-1 text-xs">
                            {validationSummary.comments.map((item: any, idx: number) => (
                              <div key={idx} className="bg-slate-950 p-3 rounded-xl border border-slate-800/50 space-y-1">
                                <div className="flex justify-between items-center text-[10px] text-slate-500">
                                  <span className="font-bold capitalize text-pink-400">{item.role}</span>
                                  <span className="font-mono">{item.question_id}</span>
                                </div>
                                <p className="text-slate-300 italic">"{item.comment}"</p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 1: Deliveries List */}
        {activeTab === 'deliveries' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {deliveries.map((del) => (
              <div
                key={del.id}
                className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-4 hover-elevation transition"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-xs font-mono bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
                      {del.id}
                    </span>
                    <h3 className="font-bold text-lg text-slate-100 mt-1">{del.customer_name}</h3>
                    <p className="text-slate-400 text-xs">{del.customer_phone}</p>
                  </div>
                  <span
                    className={`text-xs font-semibold px-2.5 py-1 rounded-full uppercase border ${
                      del.status === 'delivered' || del.status === 'accepted'
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : del.status === 'needs_review'
                        ? 'bg-amber-50 text-amber-700 border-amber-200'
                        : del.status === 'disputed'
                        ? 'bg-rose-50 text-rose-700 border-rose-200'
                        : del.status === 'in_transit'
                        ? 'bg-slate-100 text-slate-700 border-slate-200'
                        : 'bg-slate-50 text-slate-500 border-slate-200'
                    }`}
                  >
                    {del.status}
                  </span>
                </div>

                <div className="text-xs text-slate-300 space-y-1">
                  <div className="flex items-center space-x-1.5 text-slate-400">
                    <MapPin className="w-3.5 h-3.5 flex-shrink-0 text-slate-50" />
                    <span>{del.delivery_address}</span>
                  </div>
                  <div className="flex items-center space-x-1.5 text-slate-400">
                    <KeyRound className="w-3.5 h-3.5 text-slate-50" />
                    <span>Required OTP Code: <strong className="text-slate-200 font-mono">{del.otp_code}</strong></span>
                  </div>
                </div>

                {/* Leaflet Map Preview */}
                <LeafletMap targetLat={del.target_latitude} targetLng={del.target_longitude} />

                <div className="flex space-x-2 pt-2">
                  {(userRole === 'rider' || userRole === 'admin') && del.status !== 'delivered' && (
                    <button
                      onClick={() => {
                        setSelectedDelivery(del);
                        setActiveTab('evidence_capture');
                      }}
                      className="flex-1 btn-primary py-2.5 rounded-xl font-semibold text-xs transition flex items-center justify-center space-x-1.5 btn-press-feedback"
                    >
                      <Camera className="w-4 h-4" />
                      <span>Capture POD Evidence</span>
                    </button>
                  )}

                  <button
                    onClick={() => viewEvidenceDetails(del.id)}
                    className="px-3.5 py-2.5 btn-secondary rounded-xl font-semibold text-xs transition flex items-center space-x-1 btn-press-feedback"
                  >
                    <Eye className="w-4 h-4" />
                    <span>View Evidence</span>
                  </button>

                  {userRole === 'restaurant' && (
                    <button
                      onClick={() => handleDeleteDelivery(del.id)}
                      className="px-3.5 py-2.5 bg-rose-950/40 hover:bg-rose-900/60 text-rose-400 border border-rose-800/60 rounded-xl font-semibold text-xs transition flex items-center space-x-1 btn-press-feedback"
                      title="Delete Delivery"
                    >
                      <Trash2 className="w-4 h-4" />
                      <span>Delete</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* TAB 2: Rider Evidence Capture */}
        {activeTab === 'evidence_capture' && selectedDelivery && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Form Column */}
            <form onSubmit={handleEvidenceSubmit} className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl">
              <div className="border-b border-slate-800 pb-4 flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-bold">Capture Evidence for {selectedDelivery.id}</h2>
                  <p className="text-xs text-slate-400">{selectedDelivery.customer_name} • {selectedDelivery.delivery_address}</p>
                </div>
                <button
                  type="button"
                  onClick={resetCaptureForm}
                  className="text-xs text-slate-400 hover:text-slate-200 bg-slate-800 px-3 py-1.5 rounded-lg"
                >
                  Cancel
                </button>
              </div>

              {/* 1. Photo Capture */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center space-x-1">
                  <Camera className="w-4 h-4 text-slate-400" />
                  <span>1. Delivery Photo Capture (Laplacian Blur & Brightness Check)</span>
                </label>
                <div className="flex items-center space-x-4">
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    onChange={handlePhotoSelect}
                    className="text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border file:border-slate-800 file:text-xs file:font-semibold file:bg-slate-950 file:text-slate-100 hover:file:bg-slate-800 cursor-pointer transition"
                  />
                </div>
                {photoPreview && (
                  <div className="mt-2 relative w-full h-48 bg-slate-950 rounded-xl overflow-hidden border border-slate-800">
                    <img src={photoPreview} alt="Preview" className="w-full h-full object-cover" />
                  </div>
                )}
              </div>

              {/* 2. Signature Pad */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center space-x-1">
                  <FileSignature className="w-4 h-4 text-slate-400" />
                  <span>2. Recipient Signature</span>
                </label>
                <SignatureCanvas onSave={(sig) => setSignatureBase64(sig)} />
              </div>

              {/* 3. GPS Coordinates & Offline Simulation */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-semibold text-slate-300 flex items-center space-x-1">
                    <MapPin className="w-4 h-4 text-slate-400" />
                    <span>3. GPS Geolocation Validation</span>
                  </label>
                  <label className="flex items-center space-x-2 text-xs text-slate-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={disableGPS}
                      onChange={(e) => setDisableGPS(e.target.checked)}
                      className="rounded bg-slate-950 border-slate-800 text-emerald-500 focus:ring-0"
                    />
                    <span>Simulate Zero GPS (Offline Capture)</span>
                  </label>
                </div>

                {!disableGPS ? (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-[10px] text-slate-400">Captured Latitude</span>
                      <input
                        type="number"
                        step="any"
                        value={capturedLat || ''}
                        onChange={(e) => setCapturedLat(parseFloat(e.target.value))}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono"
                      />
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400">Captured Longitude</span>
                      <input
                        type="number"
                        step="any"
                        value={capturedLng || ''}
                        onChange={(e) => setCapturedLng(parseFloat(e.target.value))}
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="p-3 bg-amber-50 text-amber-700 border-amber-200 rounded-xl text-xs flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0 text-amber-600" />
                    <span>Zero GPS signal captured. Tagged as <strong>is_offline_capture = true</strong>. Score = 0/25 for GPS criterion.</span>
                  </div>
                )}
              </div>

              {/* 4. OTP Code Entry */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center space-x-1">
                  <KeyRound className="w-4 h-4 text-slate-400" />
                  <span>4. Recipient OTP Code Verification (10 Pts)</span>
                </label>
                <input
                  type="text"
                  maxLength={6}
                  placeholder="Enter 4-digit OTP"
                  value={otpEntered}
                  onChange={(e) => setOtpEntered(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-200 font-mono tracking-widest"
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full btn-success font-bold py-3.5 rounded-xl shadow-sm transition flex items-center justify-center space-x-2 disabled:opacity-50 btn-press-feedback"
              >
                <CheckCircle2 className="w-5 h-5" />
                <span>{isSubmitting ? 'Processing Engine...' : 'Submit Proof of Delivery'}</span>
              </button>
            </form>

            {/* Quality Score Realtime Feedback Sidebar */}
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl h-fit sticky top-24">
              <h3 className="text-lg font-bold text-slate-100 flex items-center space-x-2">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
                <span>Live Quality Engine Meter</span>
              </h3>

              <div className="text-center py-4 bg-slate-950 border border-slate-800 rounded-2xl space-y-1">
                <div className="text-4xl font-extrabold font-mono text-emerald-400">{liveScores.total}/100</div>
                <div className="text-xs font-semibold tracking-wider uppercase text-slate-400">Projected Score</div>
                <div className={`inline-block text-[11px] font-bold px-3 py-0.5 rounded-full uppercase mt-2 border ${
                  liveScores.classification === 'ACCEPTED'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : liveScores.classification === 'NEEDS_MANUAL_REVIEW'
                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                    : 'bg-rose-50 text-rose-700 border-rose-200'
                }`}>
                  {liveScores.classification}
                </div>
              </div>

              <div className="space-y-3 text-xs">
                <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Photo Quality (OpenCV)</span>
                  <span className="font-mono font-bold text-slate-200">{liveScores.photoScore}/25</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
                  <span className="text-slate-400">GPS Proximity (Haversine)</span>
                  <span className="font-mono font-bold text-slate-200">{liveScores.gpsScore}/25</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Timestamp Validity</span>
                  <span className="font-mono font-bold text-slate-200">{liveScores.timestampScore}/20</span>
                </div>
                <div className="flex justify-between items-center pb-2 border-b border-slate-800/60">
                  <span className="text-slate-400">Recipient Signature</span>
                  <span className="font-mono font-bold text-slate-200">{liveScores.sigScore}/20</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">OTP Matching</span>
                  <span className="font-mono font-bold text-slate-200">{liveScores.otpScore}/10</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: Create Delivery (Restaurant Only) */}
        {activeTab === 'create_delivery' && (
          <form onSubmit={handleCreateDeliverySubmit} className="max-w-xl mx-auto bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <h2 className="text-xl font-bold text-slate-100">Create New Order Delivery</h2>

            <div>
              <label className="text-xs text-slate-400">Delivery ID</label>
              <input
                type="text"
                value={newDeliveryId}
                onChange={(e) => setNewDeliveryId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-400">Customer Name</label>
                <input
                  type="text"
                  value={newCustomerName}
                  onChange={(e) => setNewCustomerName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400">Customer Phone</label>
                <input
                  type="text"
                  value={newCustomerPhone}
                  onChange={(e) => setNewCustomerPhone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
                />
              </div>
            </div>

            <div>
              <label className="text-xs text-slate-400">Delivery Address</label>
              <input
                type="text"
                value={newAddress}
                onChange={(e) => setNewAddress(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-slate-400">Target Lat</label>
                <input
                  type="number"
                  step="any"
                  value={newLat}
                  onChange={(e) => setNewLat(parseFloat(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400">Target Lng</label>
                <input
                  type="number"
                  step="any"
                  value={newLng}
                  onChange={(e) => setNewLng(parseFloat(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400">OTP Code</label>
                <input
                  type="text"
                  maxLength={6}
                  value={newOtp}
                  onChange={(e) => setNewOtp(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-slate-200"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full btn-primary font-bold py-3 rounded-xl transition btn-press-feedback"
            >
              Publish Delivery
            </button>
          </form>
        )}

        {/* Evidence Review Modal — rendered via portal at document.body to escape all parent stacking contexts */}
        {showEvidenceModal && reviewedEvidence && ReactDOM.createPortal(
          <div
            className="fixed inset-0 flex items-center justify-center p-4 animate-modal-backdrop"
            style={{ zIndex: 9999, backgroundColor: 'rgba(15,23,42,0.4)', backdropFilter: 'blur(2px)' }}
            onClick={(e) => { if (e.target === e.currentTarget) setShowEvidenceModal(false); }}
          >
            <div
              className="bg-slate-900 border border-slate-800 max-w-2xl w-full rounded-3xl p-6 space-y-6 shadow-2xl max-h-[90vh] overflow-y-auto animate-modal-content"
              style={{ position: 'relative', zIndex: 10000 }}
            >
              <div className="flex justify-between items-start border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-xl font-bold">Evidence Breakdown: {reviewedEvidence.delivery_id}</h3>
                  <span className="text-xs text-slate-400">Captured at {new Date(reviewedEvidence.captured_timestamp).toLocaleString()}</span>
                </div>
                <button
                  onClick={() => setShowEvidenceModal(false)}
                  className="text-slate-400 hover:text-slate-200 text-lg font-bold"
                >
                  ✕
                </button>
              </div>

              {/* Total Score Header */}
              <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 flex justify-between items-center">
                <div>
                  <div className="text-xs text-slate-400">Quality Score Engine Rating</div>
                  <div className="text-3xl font-extrabold font-mono text-emerald-400">{reviewedEvidence.total_quality_score}/100</div>
                </div>
                <span className={`px-3 py-1 text-xs font-bold rounded-full border uppercase ${
                  reviewedEvidence.classification === 'ACCEPTED'
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : reviewedEvidence.classification === 'NEEDS_MANUAL_REVIEW'
                    ? 'bg-amber-50 text-amber-700 border-amber-200'
                    : 'bg-rose-50 text-rose-700 border-rose-200'
                }`}>
                  {reviewedEvidence.classification}
                </span>
              </div>

              {/* Photos & Signatures */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-xs text-slate-400 block mb-1">Captured Photo</span>
                  <div className="w-full h-40 bg-slate-950 rounded-xl overflow-hidden border border-slate-800">
                    <img src={getEvidenceUrl(reviewedEvidence.photo_url)} alt="Photo Proof" className="w-full h-full object-cover" />
                  </div>
                </div>
                <div>
                  <span className="text-xs text-slate-400 block mb-1">Captured Signature</span>
                  <div className="w-full h-40 bg-slate-950 rounded-xl overflow-hidden border border-slate-800 flex items-center justify-center">
                    {reviewedEvidence.signature_url ? (
                      <img src={getEvidenceUrl(reviewedEvidence.signature_url)} alt="Signature Proof" className="max-h-full" />
                    ) : (
                      <span className="text-xs text-slate-600">No Signature Provided</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Granular OpenCV & GPS Metrics */}
              <div className="grid grid-cols-2 gap-4 text-xs bg-slate-950 p-4 rounded-2xl border border-slate-800">
                <div>
                  <span className="text-slate-500 block">OpenCV Blur Score (Laplacian)</span>
                  <span className="font-mono text-slate-200 font-bold">{reviewedEvidence.blur_score ?? 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">OpenCV Brightness Mean</span>
                  <span className="font-mono text-slate-200 font-bold">{reviewedEvidence.brightness_score ?? 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Haversine Distance (Meters)</span>
                  <span className="font-mono text-slate-200 font-bold">{reviewedEvidence.distance_m ? `${reviewedEvidence.distance_m}m` : 'Missing (Offline)'}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Offline Capture Tag</span>
                  <span className="font-mono text-amber-400 font-bold">{reviewedEvidence.is_offline_capture ? 'true' : 'false'}</span>
                </div>
              </div>

              {/* Dispatcher Actions */}
              {(userRole === 'dispatcher' || userRole === 'admin') && (
                <div className="flex space-x-3 pt-2 border-t border-slate-800">
                  <button
                    onClick={() => updateDeliveryStatus(reviewedEvidence.delivery_id, 'delivered')}
                    className="flex-1 btn-primary py-2.5 rounded-xl text-xs transition btn-press-feedback"
                  >
                    Override: Mark as DELIVERED (Accepted)
                  </button>
                  <button
                    onClick={() => updateDeliveryStatus(reviewedEvidence.delivery_id, 'disputed')}
                    className="flex-1 bg-rose-600 hover:bg-rose-500 text-white font-bold py-2.5 rounded-xl text-xs transition btn-press-feedback"
                  >
                    Mark as DISPUTED
                  </button>
                </div>
              )}
            </div>
          </div>,
          document.body
        )}

        {/* Delete Confirmation Modal */}
        {deliveryToDelete && ReactDOM.createPortal(
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-md w-full p-6 space-y-4 shadow-2xl animate-in fade-in">
              <div className="flex items-center space-x-3 text-rose-400">
                <div className="p-3 bg-rose-950/60 rounded-2xl border border-rose-800/40">
                  <Trash2 className="w-6 h-6 text-rose-400" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-100">Delete Delivery Order</h3>
                  <span className="text-xs text-slate-400 font-mono">{deliveryToDelete}</span>
                </div>
              </div>
              <p className="text-sm text-slate-300">
                Are you sure you want to delete delivery order <strong className="font-mono text-slate-100">{deliveryToDelete}</strong>? This action will permanently remove it across Restaurant, Customer, Rider, Dispatcher, and Admin dashboards.
              </p>
              <div className="flex justify-end space-x-3 pt-3 border-t border-slate-800/60">
                <button
                  id="cancel-delete-btn"
                  onClick={() => setDeliveryToDelete(null)}
                  className="px-4 py-2.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition btn-press-feedback"
                >
                  Cancel
                </button>
                <button
                  id="confirm-delete-btn"
                  onClick={() => executeDeleteDelivery(deliveryToDelete)}
                  className="px-4 py-2.5 text-xs font-bold rounded-xl bg-rose-600 hover:bg-rose-500 text-white transition flex items-center space-x-1.5 btn-press-feedback shadow-lg shadow-rose-900/30"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Yes, Delete Delivery</span>
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
      </main>
    </div>
  );
}
