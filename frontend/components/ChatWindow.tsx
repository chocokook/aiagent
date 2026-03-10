"use client";

import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import InterruptModal from "./InterruptModal";

const WELCOME: string =
  "Hi! I'm TechHub's AI support assistant. I can help you with:\n• Order status & history\n• Product information\n• Return & shipping policies\n\nHow can I help you today?";

export default function ChatWindow() {
  const { messages, loading, interrupt, sendMessage, resumeWithInput, stop } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <>
      {/* HITL modal — overlays chat when agent needs user input */}
      {interrupt && (
        <InterruptModal prompt={interrupt.prompt} onSubmit={resumeWithInput} />
      )}

      <div className="w-full max-w-2xl bg-white rounded-3xl shadow-lg border border-gray-100 flex flex-col overflow-hidden h-[72vh]">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Static welcome message */}
          <div className="flex justify-start">
            <div className="flex items-start gap-2">
              <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5">
                T
              </div>
              <div className="max-w-[75%] bg-white border border-gray-100 shadow-sm rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                {WELCOME}
              </div>
            </div>
          </div>

          {/* Conversation history */}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}

          <div ref={bottomRef} />
        </div>

        {/* Divider */}
        <div className="border-t border-gray-100" />

        {/* Input */}
        <div className="p-4">
          <ChatInput
            loading={loading}
            disabled={!!interrupt}
            onSend={sendMessage}
            onStop={stop}
          />
          <p className="text-center text-xs text-gray-400 mt-2">
            Powered by LangGraph · Press <kbd className="font-mono">Enter</kbd> to send
          </p>
        </div>
      </div>
    </>
  );
}
