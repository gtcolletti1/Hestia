import { useEffect, useState } from "react";
import { isOnline, onOnlineStatusChange } from "@/utils/offline";

export default function OfflineBanner() {
  const [online, setOnline] = useState(isOnline());
  const [pendingCount, setPendingCount] = useState(0);
  const [visible, setVisible] = useState(!isOnline());

  useEffect(() => {
    const unsubscribe = onOnlineStatusChange((status) => {
      setOnline(status);
      setVisible(!status);
    });
    return unsubscribe;
  }, []);

  // Poll pending sync count from the offline queue when offline
  useEffect(() => {
    if (online) {
      setPendingCount(0);
      return;
    }

    async function checkPending() {
      try {
        const db = await openQueueDB();
        const tx = db.transaction("requests", "readonly");
        const store = tx.objectStore("requests");
        const countReq = store.count();
        countReq.onsuccess = () => setPendingCount(countReq.result);
      } catch {
        // IndexedDB unavailable — ignore
      }
    }

    checkPending();
    const interval = setInterval(checkPending, 5000);
    return () => clearInterval(interval);
  }, [online]);

  if (!visible) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9999,
        background: "#fbbf24",
        color: "#78350f",
        textAlign: "center",
        padding: "8px 16px",
        fontSize: "14px",
        fontWeight: 500,
        transition: "transform 0.3s ease-in-out",
        transform: visible ? "translateY(0)" : "translateY(-100%)",
      }}
    >
      📡 You&apos;re offline — changes will sync when reconnected
      {pendingCount > 0 && (
        <span style={{ marginLeft: 12, fontWeight: 700 }}>
          ({pendingCount} pending)
        </span>
      )}
    </div>
  );
}

function openQueueDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open("family-hub-offline-queue", 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore("requests", {
        keyPath: "id",
        autoIncrement: true,
      });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
