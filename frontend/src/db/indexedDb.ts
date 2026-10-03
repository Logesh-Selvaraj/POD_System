import { openDB, type DBSchema, type IDBPDatabase } from 'idb';

/**
 * IndexedDB schema for the POD offline-first PWA.
 *
 * WHY IndexedDB INSTEAD OF localStorage:
 *   localStorage is synchronous, has a strict ~5 MB cap, and cannot store
 *   binary data (Blob / File) without base64 encoding that inflates photo
 *   sizes by ~33 %.  IndexedDB is asynchronous, supports transactions, and
 *   can store raw Blob objects, making it suitable for buffering multi-
 *   megabyte delivery photos while the rider is offline.
 *
 * TWO OBJECT STORES:
 *
 *   pending_evidence  — Holds evidence submissions that could not be sent to
 *                       the backend because the device was offline.  Each
 *                       entry is keyed by idempotency_key (a UUID generated
 *                       at capture time) to guarantee that the SyncManager
 *                       can safely retry uploads without creating duplicate
 *                       evidence records on the server.
 *
 *   cached_deliveries — A local read-through cache of the rider's current
 *                       delivery list.  Populated on every successful API
 *                       response and served immediately when the device is
 *                       offline, so the rider can still navigate to the
 *                       correct address and reference the OTP code without
 *                       network access.
 */

export interface PendingEvidenceItem {
  idempotency_key: string;    // UUID; server-side deduplication key
  delivery_id: string;
  captured_latitude: number | null;
  captured_longitude: number | null;
  captured_timestamp: string;  // ISO-8601 string
  otp_entered?: string | null;
  signature_base64: string | null;
  photo_blob: Blob;            // Raw image stored as Blob to avoid base64 overhead
  status: 'PENDING' | 'SYNCING' | 'FAILED';
  error_message?: string;
  created_at: string;          // ISO-8601 string, for age-based cleanup (future)
}

export interface CachedDelivery {
  id: string;
  restaurant_id: number;
  customer_name: string;
  customer_phone: string;
  delivery_address: string;
  target_latitude: number;
  target_longitude: number;
  otp_code: string;
  status: string;
  created_at: string;
}

interface PODDatabase extends DBSchema {
  pending_evidence: {
    key: string;  // idempotency_key
    value: PendingEvidenceItem;
    indexes: { 'by-delivery': string };
  };
  cached_deliveries: {
    key: string;  // delivery_id
    value: CachedDelivery;
  };
}

const DB_NAME = 'pod_offline_db';
const DB_VERSION = 1;

/** Singleton promise so we open the database connection only once per page load. */
let dbPromise: Promise<IDBPDatabase<PODDatabase>> | null = null;

export function getDB() {
  if (!dbPromise) {
    dbPromise = openDB<PODDatabase>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        // pending_evidence: keyed by idempotency_key so that put() is
        // idempotent — re-adding the same key after a failed sync attempt
        // overwrites the existing record instead of creating a duplicate.
        const evidenceStore = db.createObjectStore('pending_evidence', {
          keyPath: 'idempotency_key',
        });
        // Secondary index allows querying by delivery_id, which is useful
        // if the UI needs to display "evidence pending for delivery X".
        evidenceStore.createIndex('by-delivery', 'delivery_id');

        // cached_deliveries: keyed by delivery id for O(1) lookup.
        db.createObjectStore('cached_deliveries', {
          keyPath: 'id',
        });
      },
    });
  }
  return dbPromise;
}

/** Upsert a pending evidence item (safe to call on retry — idempotency_key deduplicates). */
export async function savePendingEvidence(item: PendingEvidenceItem): Promise<void> {
  const db = await getDB();
  await db.put('pending_evidence', item);
}

/** Return all items still waiting for upload. */
export async function getPendingEvidenceItems(): Promise<PendingEvidenceItem[]> {
  const db = await getDB();
  return db.getAll('pending_evidence');
}

/** Remove a successfully uploaded item to keep the queue clean. */
export async function removePendingEvidence(idempotencyKey: string): Promise<void> {
  const db = await getDB();
  await db.delete('pending_evidence', idempotencyKey);
}

/**
 * Replace the entire cached_deliveries store with a fresh server snapshot.
 *
 * WHY REPLACE RATHER THAN MERGE:
 *   The server is the source of truth.  A full replace avoids stale entries
 *   (e.g. deleted deliveries) surviving in the local cache indefinitely.
 *   The transaction is atomic: if any put fails the entire operation rolls
 *   back, preventing a partial/corrupt cache state.
 */
export async function cacheDeliveries(deliveries: CachedDelivery[]): Promise<void> {
  const db = await getDB();
  const tx = db.transaction('cached_deliveries', 'readwrite');
  await tx.objectStore('cached_deliveries').clear();
  for (const delivery of deliveries) {
    await tx.objectStore('cached_deliveries').put(delivery);
  }
  await tx.done;
}

/** Return the last-known delivery list for offline display. */
export async function getCachedDeliveries(): Promise<CachedDelivery[]> {
  const db = await getDB();
  return db.getAll('cached_deliveries');
}
