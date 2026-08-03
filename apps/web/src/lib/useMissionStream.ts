/**
 * SSE hook — subscribe to live mission events from the agent runtime.
 */
"use client";

import { useEffect, useRef, useCallback } from "react";
import type { SSEEvent } from "@/types";

const API = "/api/backend";

export function useMissionStream(
  missionId: string | null,
  onEvent: (event: SSEEvent) => void
): () => void {
  const esRef = useRef<EventSource | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  useEffect(() => {
    if (!missionId) return;

    const es = new EventSource(`${API}/api/v1/stream/${missionId}`);
    esRef.current = es;

    es.onmessage = (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data as string) as SSEEvent;
        onEventRef.current(payload);
      } catch {
        // malformed event — ignore
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [missionId]);

  const close = useCallback(() => {
    esRef.current?.close();
  }, []);

  return close;
}
