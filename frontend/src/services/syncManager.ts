import axios from 'axios';
import { getPendingEvidenceItems, removePendingEvidence } from '../db/indexedDb';

/**
 * SyncManager — Background service that drains the IndexedDB pending-evidence
 * queue by uploading each item to the backend when network connectivity is
 * restored.
 *
 * IDEMPOTENCY GUARANTEE:
 *   Every evidence submission includes an idempotency_key (generated at
 *   capture time, format: "POD-SYNC-{delivery_id}-{timestamp}").  The
 *   backend's /api/v1/evidence/submit endpoint checks for an existing
 *   Evidence record with that key before processing.  If a match is found the
 *   server returns the existing record immediately (HTTP 201 with existing
 *   data) and the client removes the item from the queue.  This guarantees
 *   that network retries — including duplicate submissions caused by poor
 *   connectivity during the upload — never create duplicate evidence records.
 *
 * CONCURRENCY GUARD (isSyncing flag):
 *   The isSyncing flag prevents multiple concurrent flush operations from
 *   being triggered simultaneously (e.g. the 'online' event and the 15-second
 *   interval firing at the same time).  Without this guard the same pending
 *   item could be uploaded twice in parallel before either call has a chance
 *   to remove it from the queue, resulting in duplicate network requests
 *   (though the server-side idempotency key would still prevent duplicate DB
 *   records).
 *
 * AUTO-SYNC TRIGGERS:
 *   1. window 'online' event — fired by the browser when the device reconnects.
 *      This provides near-instant sync after a connectivity gap.
 *   2. 15-second polling interval — provides a safety net for environments
 *      where the 'online' event fires unreliably (some Android WebViews,
 *      corporate proxies that intercept network change events).
 */
export class SyncManager {
  /** Prevents concurrent flush invocations from racing against each other. */
  private static isSyncing = false;
  /** Registered UI listeners that receive the current pending queue count. */
  private static listeners: Array<(count: number) => void> = [];

  public static subscribe(listener: (count: number) => void) {
    this.listeners.push(listener);
    // Return an unsubscribe function so React components can clean up in
    // useEffect's return callback, preventing memory leaks after unmount.
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private static async notifyListeners() {
    const items = await getPendingEvidenceItems();
    this.listeners.forEach((l) => l(items.length));
  }

  /**
   * Upload all pending items in the IndexedDB queue to the backend.
   *
   * Each item is processed sequentially rather than in parallel to avoid
   * overwhelming the server or the mobile device's upload bandwidth.  A
   * failed upload for one item (e.g. server 500) is logged and counted but
   * does NOT abort the remaining items — all other pending uploads continue.
   *
   * Returns a summary of successful and failed upload counts for the caller
   * (used by the UI to display sync results).
   */
  public static async flushQueue(authToken?: string): Promise<{ success: number; failed: number }> {
    // Bail out immediately if a sync is already in progress or the device is
    // still offline — avoids queuing redundant work.
    if (this.isSyncing) return { success: 0, failed: 0 };
    if (!navigator.onLine) return { success: 0, failed: 0 };

    this.isSyncing = true;
    let successCount = 0;
    let failedCount = 0;

    try {
      const items = await getPendingEvidenceItems();
      for (const item of items) {
        try {
          // Reconstruct the exact multipart/form-data payload that would have
          // been sent online, including the original idempotency_key so the
          // server can deduplicate on retry.
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

          // Successfully uploaded → purge from IndexedDB queue.
          // Removing after a confirmed 2xx response (not before) ensures the
          // item remains in the queue if the upload fails mid-transfer.
          await removePendingEvidence(item.idempotency_key);
          successCount++;
        } catch (error) {
          // Log for developer diagnostics but continue processing other items.
          console.error(`Sync error for key ${item.idempotency_key}:`, error);
          failedCount++;
        }
      }
    } finally {
      // Always clear the lock in the finally block so that a thrown exception
      // does not permanently block future sync attempts.
      this.isSyncing = false;
      await this.notifyListeners();
    }

    return { success: successCount, failed: failedCount };
  }

  /**
   * Register window-level event listeners that trigger automatic queue flush.
   *
   * Called once at application startup (App.tsx useEffect).  The method is
   * idempotent in the sense that duplicate calls attach duplicate listeners,
   * so callers must ensure it is invoked only once per page lifecycle.
   */
  public static initAutoSync(getAuthToken: () => string | null) {
    // Trigger immediate flush when the browser declares the device is online.
    window.addEventListener('online', () => {
      console.log('Network status: ONLINE. Flushing evidence queue...');
      const token = getAuthToken();
      if (token) {
        this.flushQueue(token);
      }
    });

    // Periodic safety-net flush every 15 seconds for unreliable environments.
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
