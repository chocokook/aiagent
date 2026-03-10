"use client";

import clsx from "clsx";
import type { Message } from "@/hooks/useChat";

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      {/* Avatar for assistant */}
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-bold mr-2 mt-0.5 shrink-0">
          T
        </div>
      )}

      <div
        className={clsx(
          "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap",
          isUser
            ? "bg-brand-600 text-white rounded-br-sm"
            : "bg-white border border-gray-100 text-gray-800 rounded-bl-sm shadow-sm"
        )}
      >
        {message.content || (message.streaming ? "" : "…")}
        {/* Blinking cursor while streaming */}
        {message.streaming && message.content && (
          <span className="cursor-blink" />
        )}
        {/* Pulse dots when streaming but no content yet */}
        {message.streaming && !message.content && (
          <span className="inline-flex gap-1 items-center h-4">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.3s]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.15s]" />
            <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" />
          </span>
        )}
      </div>
    </div>
  );
}
