"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { streamChat, streamResume } from "@/lib/api";

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
  }, []);

  const [loading, setLoading] = useState(false);
  const [interrupt, setInterrupt] = useState<InterruptState | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Persist sessionId whenever it changes.
  useEffect(() => {
    if (sessionId) {
      writeStorage(STORAGE_SESSION_KEY, sessionId);
    }
  }, [sessionId]);

  // Persist completed messages whenever they change.
  // Only store non-streaming messages to avoid saving incomplete bubbles.
  useEffect(() => {
    const completed = messages.filter((m) => !m.streaming);
    writeStorage(STORAGE_MESSAGES_KEY, completed);
  }, [messages]);

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
        } else if (event.type === "error") {
          appendToken(assistantId, `\n\n⚠️ ${event.message}`);
          finaliseMessage(assistantId);
          setLoading(false);
        }
      }, ctrl.signal);
    },
    [loading, sessionId, appendToken, finaliseMessage]
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
        } else if (event.type === "error") {
          appendToken(assistantId, `\n\n⚠️ ${event.message}`);
          finaliseMessage(assistantId);
          setLoading(false);
        }
      }, ctrl.signal);
    },
    [sessionId, loading, appendToken, finaliseMessage]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setLoading(false);
  }, []);

  /** Start a brand-new conversation, wiping localStorage history. */
  const clearHistory = useCallback(() => {
    abortRef.current?.abort();
    removeStorage(STORAGE_SESSION_KEY);
    removeStorage(STORAGE_MESSAGES_KEY);
    setMessages([]);
    setSessionId(null);
    setLoading(false);
    setInterrupt(null);
  }, []);

  return { messages, sessionId, loading, interrupt, sendMessage, resumeWithInput, stop, clearHistory };
}
