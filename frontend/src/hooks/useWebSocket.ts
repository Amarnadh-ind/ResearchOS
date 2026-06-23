"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { WSMessage } from "@/lib/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 16000];
const MAX_RECONNECT_ATTEMPTS = 5;
const HEARTBEAT_INTERVAL = 30000; // 30 seconds

export function useWebSocket(sessionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectedSessionId, setConnectedSessionId] = useState<string | null>(null);
  const [reconnecting, setReconnecting] = useState(false);
  const [messageState, setMessageState] = useState<{
    sessionId: string | null;
    messages: WSMessage[];
    lastMessage: WSMessage | null;
  }>({
    sessionId: null,
    messages: [],
    lastMessage: null,
  });

  const connectRef = useRef<(() => void) | null>(null);

  const cleanup = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (heartbeatTimerRef.current) {
      clearTimeout(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
    if (wsRef.current) {
      const ws = wsRef.current;
      wsRef.current = null;
      ws.close();
    }
  }, []);

  const connect = useCallback(() => {
    if (!sessionId) return;
    cleanup();

    const ws = new WebSocket(`${WS_URL}/ws/research/${sessionId}`);

    ws.onopen = () => {
      setIsConnected(true);
      setConnectedSessionId(sessionId);
      setReconnecting(false);
      reconnectAttemptRef.current = 0;
      // Start heartbeat
      heartbeatTimerRef.current = setTimeout(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, HEARTBEAT_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        
        // Handle pong response
        if (msg.type === "pong") {
          return;
        }
        
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

    ws.onclose = (event) => {
      if (wsRef.current === ws) {
        setIsConnected(false);
        setConnectedSessionId(null);
        
        // Clear heartbeat on close
        if (heartbeatTimerRef.current) {
          clearTimeout(heartbeatTimerRef.current);
          heartbeatTimerRef.current = null;
        }

        if (event.code !== 1000 && reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = RECONNECT_DELAYS[reconnectAttemptRef.current] || RECONNECT_DELAYS[RECONNECT_DELAYS.length - 1];
          reconnectAttemptRef.current += 1;
          setReconnecting(true);
          reconnectTimerRef.current = setTimeout(() => {
            if (wsRef.current === null && connectRef.current) {
              connectRef.current();
            }
          }, delay);
        }
      }
    };

    ws.onerror = () => {
      if (wsRef.current === ws) {
        setIsConnected(false);
        setConnectedSessionId(null);
      }
    };

    wsRef.current = ws;
  }, [sessionId, cleanup]);

  const disconnect = useCallback(() => {
    reconnectAttemptRef.current = MAX_RECONNECT_ATTEMPTS; // Prevent reconnect
    cleanup();
  }, [cleanup]);

  const manualReconnect = useCallback(() => {
    reconnectAttemptRef.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  // Reset reconnect counter when session changes
  useEffect(() => {
    reconnectAttemptRef.current = 0;
  }, [sessionId]);

  const isActiveSession = messageState.sessionId === sessionId;

  return {
    isConnected: isConnected && connectedSessionId === sessionId,
    reconnecting,
    messages: isActiveSession ? messageState.messages : [],
    lastMessage: isActiveSession ? messageState.lastMessage : null,
    manualReconnect,
  };
}
