"use client";

import { useRef, useState } from "react";
import { Send, Square } from "lucide-react";
import clsx from "clsx";

interface Props {
  loading: boolean;
  disabled?: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}

export default function ChatInput({ loading, disabled, onSend, onStop }: Props) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    onSend(trimmed);
    setText("");
    // Reset textarea height
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm"
    >
      <textarea
        ref={textareaRef}
        rows={1}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        placeholder="Ask about your orders, products, or policies…"
        className="flex-1 resize-none bg-transparent text-sm text-gray-800 placeholder-gray-400 focus:outline-none leading-relaxed"
        style={{ maxHeight: 160 }}
      />

      {loading ? (
        <button
          type="button"
          onClick={onStop}
          className="shrink-0 w-9 h-9 rounded-xl bg-red-100 hover:bg-red-200 flex items-center justify-center transition-colors"
        >
          <Square className="w-4 h-4 text-red-600 fill-red-600" />
        </button>
      ) : (
        <button
          type="submit"
          disabled={!text.trim() || disabled}
          className={clsx(
            "shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-colors",
            text.trim()
              ? "bg-brand-600 hover:bg-brand-700 text-white"
              : "bg-gray-100 text-gray-400 cursor-not-allowed"
          )}
        >
          <Send className="w-4 h-4" />
        </button>
      )}
    </form>
  );
}
