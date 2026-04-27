"use client";

import * as React from "react";

export interface UseSSEOptions {
  url: string | null;
  onMessage?: (data: unknown) => void;
  onError?: (err: Event) => void;
  enabled?: boolean;
}

/**
 * Server-Sent Events hook for progress updates.
 * Connects to url when enabled; parses JSON messages and calls onMessage.
 */
export function useSSE({
  url,
  onMessage,
  onError,
  enabled = true,
}: UseSSEOptions): { connected: boolean; error: Error | null } {
  const [connected, setConnected] = React.useState(false);
  const [error, setError] = React.useState<Error | null>(null);
  const onMessageRef = React.useRef(onMessage);
  const onErrorRef = React.useRef(onError);
  onMessageRef.current = onMessage;
  onErrorRef.current = onError;

  React.useEffect(() => {
    if (!url || !enabled) {
      setConnected(false);
      return;
    }

    const es = new EventSource(url);
    setError(null);

    es.onopen = () => setConnected(true);
    es.onerror = (e) => {
      setConnected(false);
      onErrorRef.current?.(e);
      setError(new Error("SSE connection error"));
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessageRef.current?.(data);
      } catch {
        onMessageRef.current?.(event.data);
      }
    };

    return () => {
      es.close();
      setConnected(false);
    };
  }, [url, enabled]);

  return { connected, error };
}
