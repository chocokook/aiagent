"use client";

import { useRef, useState } from "react";
import { Mail } from "lucide-react";

interface Props {
  prompt: string;
  onSubmit: (value: string) => void;
}

/**
 * Modal that pops up when the agent triggers a HITL interrupt
 * (e.g. asking for the customer's email address).
 */
export default function InterruptModal({ prompt, onSubmit }: Props) {
  const [value, setValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!value.trim()) return;
    onSubmit(value.trim());
    setValue("");
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 space-y-4">
        {/* Icon */}
        <div className="flex items-center justify-center w-12 h-12 rounded-full bg-brand-50 mx-auto">
          <Mail className="w-6 h-6 text-brand-600" />
        </div>

        {/* Title */}
        <div className="text-center">
          <h2 className="text-lg font-semibold text-gray-900">Verification Required</h2>
          <p className="text-sm text-gray-500 mt-1">{prompt}</p>
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            ref={inputRef}
            autoFocus
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="e.g. jane@example.com"
            className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
          <button
            type="submit"
            disabled={!value.trim()}
            className="w-full py-2.5 bg-brand-600 hover:bg-brand-700 disabled:opacity-40 text-white text-sm font-medium rounded-xl transition-colors"
          >
            Continue
          </button>
        </form>
      </div>
    </div>
  );
}
