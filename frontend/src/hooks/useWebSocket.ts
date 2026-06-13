"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSMessage } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";

export function useWebSocket(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectedSessionId, setConnectedSessionId] = useState<string | null>(null);
  const [messageState, setMessageState] = useState<{
    sessionId: string | null;
    messages: WSMessage[];
    lastMessage: WSMessage | null;
  }>({
    sessionId: null,
    messages: [],
    lastMessage: null,
  });

  const connect = useCallback(() => {
    if (!sessionId) return;

    if (wsRef.current) {
      const previous = wsRef.current;
      wsRef.current = null;
      previous.close();
    }

    const ws = new WebSocket(`${WS_URL}/ws/research/${sessionId}`);

    ws.onopen = () => {
      setIsConnected(true);
      setConnectedSessionId(sessionId);
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        setMessageState((prev) => {
          const messages = prev.sessionId === sessionId ? prev.messages : [];
          return {
            sessionId,
            messages: [...messages, msg],
            lastMessage: msg,
          };
        });
      } catch {
        // Ignore invalid messages
      }
    };

    ws.onclose = () => {
      if (wsRef.current === ws) {
        setIsConnected(false);
        setConnectedSessionId(null);
      }
    };

    ws.onerror = () => {
      if (wsRef.current === ws) {
        setIsConnected(false);
        setConnectedSessionId(null);
      }
    };

    wsRef.current = ws;
  }, [sessionId]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  const isActiveSession = messageState.sessionId === sessionId;

  return {
    isConnected: isConnected && connectedSessionId === sessionId,
    messages: isActiveSession ? messageState.messages : [],
    lastMessage: isActiveSession ? messageState.lastMessage : null,
  };
}
