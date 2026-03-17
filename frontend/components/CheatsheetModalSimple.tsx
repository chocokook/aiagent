"use client";

import { useEffect, useState } from "react";

export default function CheatsheetModalSimple() {
  const [open, setOpen] = useState(false);
  const [showHint, setShowHint] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem("cheatsheet_hint_seen")) return;
    const show = setTimeout(() => setShowHint(true), 800);
    const hide = setTimeout(() => {
      setShowHint(false);
      localStorage.setItem("cheatsheet_hint_seen", "1");
    }, 4500);
    return () => { clearTimeout(show); clearTimeout(hide); };
  }, []);

  const handleOpen = () => {
    setShowHint(false);
    localStorage.setItem("cheatsheet_hint_seen", "1");
    setOpen(true);
  };

  const examples = [
    "What is your return policy?",
    "How long does standard shipping take?",
    "What does the warranty cover?",
  ];

  return (
    <>
      {/* First-visit tooltip */}
      {showHint && (
        <div className="fixed bottom-[4.5rem] right-6 z-40 flex items-center gap-2 bg-gray-900 text-white text-xs rounded-xl px-3 py-2 shadow-lg animate-fade-in whitespace-nowrap">
          <span>👋 新来的？点击查看使用指南</span>
          <span className="absolute -bottom-1.5 right-4 w-3 h-3 bg-gray-900 rotate-45" />
        </div>
      )}

      {/* Floating help button */}
      <button
        onClick={handleOpen}
        className="fixed bottom-6 right-6 w-10 h-10 rounded-full bg-brand-600 text-white shadow-lg hover:bg-brand-700 transition-colors flex items-center justify-center text-lg font-bold z-40"
        title="Quick Start Guide"
        aria-label="Open quick start guide"
      >
        ?
      </button>

      {/* Backdrop */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">Quick Start Guide</h2>
              <button
                onClick={() => setOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors text-xl leading-none"
              >
                ×
              </button>
            </div>

            {/* Content */}
            <div className="px-5 py-4">
              <div className="flex items-center gap-2 mb-1.5">
                <span>📋</span>
                <span className="text-sm font-semibold text-gray-800">Policies &amp; Warranties</span>
              </div>
              <p className="text-xs text-gray-500 mb-3">
                Get details on return, shipping, and warranty policies.
              </p>
              <ul className="space-y-1.5">
                {examples.map((ex) => (
                  <li key={ex}>
                    <CopyableBubble text={ex} />
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function CopyableBubble({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <button
      onClick={handleCopy}
      className="w-full text-left flex items-center justify-between gap-2 rounded-lg bg-gray-50 hover:bg-gray-100 px-3 py-2 transition-colors group"
      title="Click to copy"
    >
      <span className="text-xs text-gray-700">{text}</span>
      <span className="text-xs text-gray-400 group-hover:text-gray-600 shrink-0">
        {copied ? "✓" : "copy"}
      </span>
    </button>
  );
}
