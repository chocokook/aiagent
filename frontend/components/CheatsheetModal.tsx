"use client";

import { useState } from "react";

type Tab = "features" | "accounts";

export default function CheatsheetModal() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("features");

  return (
    <>
      {/* Floating help button */}
      <button
        onClick={() => setOpen(true)}
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
          {/* Modal */}
          <div
            className="bg-white rounded-2xl shadow-2xl w-full max-w-md max-h-[80vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">Quick Start Guide</h2>
              <button
                onClick={() => setOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors text-xl leading-none"
                aria-label="Close"
              >
                ×
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-100">
              <button
                onClick={() => setTab("features")}
                className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                  tab === "features"
                    ? "text-brand-600 border-b-2 border-brand-600"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Features & Examples
              </button>
              <button
                onClick={() => setTab("accounts")}
                className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                  tab === "accounts"
                    ? "text-brand-600 border-b-2 border-brand-600"
                    : "text-gray-500 hover:text-gray-700"
                }`}
              >
                Test Accounts
              </button>
            </div>

            {/* Content */}
            <div className="overflow-y-auto flex-1 px-5 py-4">
              {tab === "features" ? <FeaturesTab /> : <AccountsTab />}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function FeaturesTab() {
  const sections = [
    {
      icon: "📦",
      title: "Order Management",
      desc: "Query order status, history, and details.",
      examples: [
        "What's the status of order ORD-2024-0042?",
        "Show me all my recent orders.",
        "When will my order be shipped?",
      ],
    },
    {
      icon: "🛍️",
      title: "Product Information",
      desc: "Explore product specs, pricing, and availability.",
      examples: [
        "What laptops do you have under $1000?",
        "Tell me about the UltraBook Pro 15 specs.",
        "Is the MechMaster Pro keyboard in stock?",
      ],
    },
    {
      icon: "📋",
      title: "Policies & Warranties",
      desc: "Get details on return, shipping, and warranty policies.",
      examples: [
        "What is your return policy?",
        "How long does standard shipping take?",
        "What does the warranty cover?",
      ],
    },
  ];

  return (
    <div className="space-y-5">
      <p className="text-sm text-gray-500">
        TechHub Support can help you with the following. Click any example to get started quickly.
      </p>
      <p className="text-xs text-brand-600 bg-brand-50 rounded-lg px-3 py-2">
        💬 支持中文提问 · English also supported
      </p>
      {sections.map((s) => (
        <div key={s.title}>
          <div className="flex items-center gap-2 mb-1.5">
            <span>{s.icon}</span>
            <span className="text-sm font-semibold text-gray-800">{s.title}</span>
          </div>
          <p className="text-xs text-gray-500 mb-2">{s.desc}</p>
          <ul className="space-y-1.5">
            {s.examples.map((ex) => (
              <li key={ex}>
                <CopyableBubble text={ex} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function AccountsTab() {
  const accounts = [
    {
      name: "Sarah Chen",
      email: "sarah.chen@gmail.com",
      id: "CUST-001",
      examples: [
        "What are my recent orders?",
        "Can you check the status of my latest order?",
        "What have I ordered this year?",
      ],
    },
    {
      name: "Marcus Johnson",
      email: "marcus.johnson@yahoo.com",
      id: "CUST-002",
      examples: [
        "Show me my order history.",
        "Is my order eligible for return?",
        "What's the total I've spent this month?",
      ],
    },
  ];

  return (
    <div className="space-y-5">
      <p className="text-sm text-gray-500">
        Use these demo accounts to test order queries. The agent will ask for your email to verify identity.
      </p>
      {accounts.map((a) => (
        <div key={a.id} className="rounded-xl border border-gray-200 p-3.5">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-7 h-7 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold">
              {a.name[0]}
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-800">{a.name}</p>
              <p className="text-xs text-gray-400">{a.id}</p>
            </div>
          </div>
          <CopyableBubble text={a.email} mono />
          <p className="text-xs text-gray-500 mt-3 mb-1.5">Example questions:</p>
          <ul className="space-y-1.5">
            {a.examples.map((ex) => (
              <li key={ex}>
                <CopyableBubble text={ex} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function CopyableBubble({ text, mono = false }: { text: string; mono?: boolean }) {
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
      <span className={`text-xs text-gray-700 ${mono ? "font-mono" : ""}`}>{text}</span>
      <span className="text-xs text-gray-400 group-hover:text-gray-600 shrink-0">
        {copied ? "✓" : "copy"}
      </span>
    </button>
  );
}
