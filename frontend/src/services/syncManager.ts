import axios from 'axios';
import { getPendingEvidenceItems, removePendingEvidence } from '../db/indexedDb';

export class SyncManager {
  private static isSyncing = false;
  private static listeners: Array<(count: number) => void> = [];

  public static subscribe(listener: (count: number) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private static async notifyListeners() {
    const items = await getPendingEvidenceItems();
    this.listeners.forEach((l) => l(items.length));
  }

  public static async flushQueue(authToken?: string): Promise<{ success: number; failed: number }> {
    if (this.isSyncing) return { success: 0, failed: 0 };
    if (!navigator.onLine) return { success: 0, failed: 0 };

    this.isSyncing = true;
    let successCount = 0;
    let failedCount = 0;

    try {
      const items = await getPendingEvidenceItems();
      for (const item of items) {
        try {
          const formData = new FormData();
          formData.append('delivery_id', item.delivery_id);
          formData.append('idempotency_key', item.idempotency_key);
          if (item.captured_latitude !== null) formData.append('captured_latitude', item.captured_latitude.toString());
          if (item.captured_longitude !== null) formData.append('captured_longitude', item.captured_longitude.toString());
          formData.append('captured_timestamp', item.captured_timestamp);
          if (item.otp_entered) formData.append('otp_entered', item.otp_entered);
          if (item.signature_base64) formData.append('signature_base64', item.signature_base64);
          formData.append('photo', item.photo_blob, `evidence_${item.delivery_id}.jpg`);

          const headers: Record<string, string> = {
            'Content-Type': 'multipart/form-data',
          };
          if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
          }

          await axios.post('/api/v1/evidence/submit', formData, { headers });

          // Successfully uploaded -> purge from IndexedDB queue
          await removePendingEvidence(item.idempotency_key);
          successCount++;
        } catch (error) {
          console.error(`Sync error for key ${item.idempotency_key}:`, error);
          failedCount++;
        }
      }
    } finally {
      this.isSyncing = false;
      await this.notifyListeners();
    }

    return { success: successCount, failed: failedCount };
  }

  public static initAutoSync(getAuthToken: () => string | null) {
    // Listen for online network events
    window.addEventListener('online', () => {
      console.log('Network status: ONLINE. Flushing evidence queue...');
      const token = getAuthToken();
      if (token) {
        this.flushQueue(token);
      }
    });

    // Periodic sync check every 15 seconds
    setInterval(() => {
      if (navigator.onLine) {
        const token = getAuthToken();
        if (token) {
          this.flushQueue(token);
        }
      }
    }, 15000);
  }
}
