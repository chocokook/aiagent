"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { streamChat, streamResume, submitFeedback } from "@/lib/api";

const INACTIVITY_MS = 5 * 60 * 1000; // 5 minutes

export type Role = "user" | "assistant";

export interface Message {
  id: string;
  role: Role;
  content: string;
  streaming?: boolean;
}

export interface InterruptState {
  prompt: string;
}

const STORAGE_SESSION_KEY = "techhub_session_id";
const STORAGE_MESSAGES_KEY = "techhub_messages";
const STORAGE_INTERRUPT_KEY = "techhub_interrupt";

/** Read a value from localStorage safely (SSR-safe). */
function readStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key: string, value: unknown): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage quota exceeded or private mode — silently ignore
  }
}

function removeStorage(key: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(key);
  } catch {}
}

export function useChat() {
  // Start with empty state (matches SSR) — load from localStorage after mount
  // to avoid React hydration mismatch (localStorage is unavailable during SSR).
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // After mount, restore persisted history from localStorage.
  useEffect(() => {
    const stored = readStorage<Message[]>(STORAGE_MESSAGES_KEY, []).filter((m) => !m.streaming);
    if (stored.length > 0) setMessages(stored);
    const storedSession = readStorage<string | null>(STORAGE_SESSION_KEY, null);
    if (storedSession) setSessionId(storedSession);
    const storedInterrupt = readStorage<InterruptState | null>(STORAGE_INTERRUPT_KEY, null);
    if (storedInterrupt) setInterrupt(storedInterrupt);
  }, []);

  const [loading, setLoading] = useState(false);
  const [interrupt, setInterrupt] = useState<InterruptState | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const inactivityRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  // Keep ref in sync so inactivity timer can read latest sessionId
  useEffect(() => {
    sessionIdRef.current = sessionId;
  }, [sessionId]);

  // Persist sessionId whenever it changes.
  useEffect(() => {
    if (sessionId) {
      writeStorage(STORAGE_SESSION_KEY, sessionId);
    }
  }, [sessionId]);

  // Persist interrupt state so it survives page refresh.
  useEffect(() => {
    if (interrupt) {
      writeStorage(STORAGE_INTERRUPT_KEY, interrupt);
    } else {
      removeStorage(STORAGE_INTERRUPT_KEY);
    }
  }, [interrupt]);

  // Persist completed messages whenever they change.
  useEffect(() => {
    const completed = messages.filter((m) => !m.streaming);
    writeStorage(STORAGE_MESSAGES_KEY, completed);
  }, [messages]);

  /** Reset the 5-minute inactivity timer. Called after every message exchange. */
  const resetInactivityTimer = useCallback(() => {
    if (inactivityRef.current) clearTimeout(inactivityRef.current);
    inactivityRef.current = setTimeout(() => {
      // Only show if there's an active session with messages
      if (sessionIdRef.current) setShowFeedback(true);
    }, INACTIVITY_MS);
  }, []);

  // Clear inactivity timer on unmount
  useEffect(() => {
    return () => {
      if (inactivityRef.current) clearTimeout(inactivityRef.current);
    };
  }, []);

  const appendToken = useCallback((id: string, token: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, content: m.content + token } : m))
    );
  }, []);

  const finaliseMessage = useCallback((id: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, streaming: false } : m))
    );
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (loading) return;

      const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: text };
      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setLoading(true);
      setInterrupt(null);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      await streamChat(text, sessionId, (event) => {
        if (event.type === "session") setSessionId(event.sessionId);
        else if (event.type === "token") appendToken(assistantId, event.content);
        else if (event.type === "interrupt") {
          finaliseMessage(assistantId);
          setInterrupt({ prompt: event.prompt });
          setLoading(false);
        } else if (event.type === "done") {
          finaliseMessage(assistantId);
          setLoading(false);
          resetInactivityTimer();
        } else if (event.type === "error") {
          appendToken(assistantId, `\n\n⚠️ ${event.message}`);
          finaliseMessage(assistantId);
          setLoading(false);
        }
      }, ctrl.signal);
    },
    [loading, sessionId, appendToken, finaliseMessage, resetInactivityTimer]
  );

  const resumeWithInput = useCallback(
    async (userInput: string) => {
      if (!sessionId || loading) return;

      const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: userInput };
      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setInterrupt(null);
      setLoading(true);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      await streamResume(sessionId, userInput, (event) => {
        if (event.type === "token") appendToken(assistantId, event.content);
        else if (event.type === "interrupt") {
          finaliseMessage(assistantId);
          setInterrupt({ prompt: event.prompt });
          setLoading(false);
        } else if (event.type === "done") {
          finaliseMessage(assistantId);
          setLoading(false);
          resetInactivityTimer();
        } else if (event.type === "error") {
          appendToken(assistantId, `\n\n⚠️ ${event.message}`);
          finaliseMessage(assistantId);
          setLoading(false);
        }
      }, ctrl.signal);
    },
    [sessionId, loading, appendToken, finaliseMessage, resetInactivityTimer]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  /** User clicks "结束对话" — show feedback immediately. */
  const endConversation = useCallback(() => {
    if (inactivityRef.current) clearTimeout(inactivityRef.current);
    setShowFeedback(true);
  }, []);

  /** Called when user submits feedback. */
  const handleFeedbackSubmit = useCallback(
    async (resolved: boolean, score: number) => {
      if (sessionId) {
        await submitFeedback(sessionId, resolved, score);
      }
      setShowFeedback(false);
      // Clear history to start fresh
      abortRef.current?.abort();
      removeStorage(STORAGE_SESSION_KEY);
      removeStorage(STORAGE_MESSAGES_KEY);
      setMessages([]);
      setSessionId(null);
      setLoading(false);
      setInterrupt(null);
    },
    [sessionId]
  );

  /** Called when user skips feedback. */
  const handleFeedbackSkip = useCallback(() => {
    setShowFeedback(false);
    abortRef.current?.abort();
    removeStorage(STORAGE_SESSION_KEY);
    removeStorage(STORAGE_MESSAGES_KEY);
    setMessages([]);
    setSessionId(null);
    setLoading(false);
    setInterrupt(null);
  }, []);

  /** Start a brand-new conversation, wiping localStorage history. */
  const clearHistory = useCallback(() => {
    abortRef.current?.abort();
    if (inactivityRef.current) clearTimeout(inactivityRef.current);
    removeStorage(STORAGE_SESSION_KEY);
    removeStorage(STORAGE_MESSAGES_KEY);
    setMessages([]);
    setSessionId(null);
    setLoading(false);
    setInterrupt(null);
    setShowFeedback(false);
  }, []);

  return {
    messages,
    sessionId,
    loading,
    interrupt,
    showFeedback,
    sendMessage,
    resumeWithInput,
    stop,
    endConversation,
    handleFeedbackSubmit,
    handleFeedbackSkip,
    clearHistory,
  };
}
