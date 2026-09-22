import { openDB, type DBSchema, type IDBPDatabase } from 'idb';

export interface PendingEvidenceItem {
  idempotency_key: string;
  delivery_id: string;
  captured_latitude: number | null;
  captured_longitude: number | null;
  captured_timestamp: string;
  otp_entered?: string | null;
  signature_base64: string | null;
  photo_blob: Blob;
  status: 'PENDING' | 'SYNCING' | 'FAILED';
  error_message?: string;
  created_at: string;
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
    key: string; // idempotency_key
    value: PendingEvidenceItem;
    indexes: { 'by-delivery': string };
  };
  cached_deliveries: {
    key: string; // delivery_id
    value: CachedDelivery;
  };
}

const DB_NAME = 'pod_offline_db';
const DB_VERSION = 1;

let dbPromise: Promise<IDBPDatabase<PODDatabase>> | null = null;

export function getDB() {
  if (!dbPromise) {
    dbPromise = openDB<PODDatabase>(DB_NAME, DB_VERSION, {
      upgrade(db) {
        // Pending evidence store
        const evidenceStore = db.createObjectStore('pending_evidence', {
          keyPath: 'idempotency_key',
        });
        evidenceStore.createIndex('by-delivery', 'delivery_id');

        // Cached deliveries store
        db.createObjectStore('cached_deliveries', {
          keyPath: 'id',
        });
      },
    });
  }
  return dbPromise;
}

export async function savePendingEvidence(item: PendingEvidenceItem): Promise<void> {
  const db = await getDB();
  await db.put('pending_evidence', item);
}

export async function getPendingEvidenceItems(): Promise<PendingEvidenceItem[]> {
  const db = await getDB();
  return db.getAll('pending_evidence');
}

export async function removePendingEvidence(idempotencyKey: string): Promise<void> {
  const db = await getDB();
  await db.delete('pending_evidence', idempotencyKey);
}

export async function cacheDeliveries(deliveries: CachedDelivery[]): Promise<void> {
  const db = await getDB();
  const tx = db.transaction('cached_deliveries', 'readwrite');
  await tx.objectStore('cached_deliveries').clear();
  for (const delivery of deliveries) {
    await tx.objectStore('cached_deliveries').put(delivery);
  }
  await tx.done;
}

export async function getCachedDeliveries(): Promise<CachedDelivery[]> {
  const db = await getDB();
  return db.getAll('cached_deliveries');
}
