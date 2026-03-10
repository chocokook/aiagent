"use client";

import { useCallback, useRef, useState } from "react";
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

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [interrupt, setInterrupt] = useState<InterruptState | null>(null);
  const abortRef = useRef<AbortController | null>(null);

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

      // Add user bubble immediately
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

  return { messages, sessionId, loading, interrupt, sendMessage, resumeWithInput, stop };
}
