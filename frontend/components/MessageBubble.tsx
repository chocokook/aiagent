"use client";

import React from "react";
import clsx from "clsx";
import type { Message } from "@/hooks/useChat";

/** Render inline markdown: **bold**, *italic*, `code` */
function renderInline(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const re = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+)`)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    if (m[2] !== undefined) parts.push(<strong key={key++} className="font-semibold">{m[2]}</strong>);
    else if (m[3] !== undefined) parts.push(<em key={key++}>{m[3]}</em>);
    else if (m[4] !== undefined) parts.push(<code key={key++} className="bg-gray-100 rounded px-1 font-mono text-xs">{m[4]}</code>);
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

/** Lightweight markdown renderer (no external packages) */
function Markdown({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let key = 0;
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Headings
    const h3 = line.match(/^###\s+(.*)/);
    const h2 = line.match(/^##\s+(.*)/);
    const h1 = line.match(/^#\s+(.*)/);
    if (h3) { elements.push(<h3 key={key++} className="font-semibold text-sm mt-3 mb-1 text-gray-900">{renderInline(h3[1])}</h3>); i++; continue; }
    if (h2) { elements.push(<h2 key={key++} className="font-bold text-sm mt-3 mb-1 text-gray-900">{renderInline(h2[1])}</h2>); i++; continue; }
    if (h1) { elements.push(<h1 key={key++} className="font-bold text-base mt-3 mb-1 text-gray-900">{renderInline(h1[1])}</h1>); i++; continue; }

    // Unordered list: collect consecutive items
    if (/^[-*]\s/.test(line)) {
      const items: React.ReactNode[] = [];
      while (i < lines.length && /^[-*]\s/.test(lines[i])) {
        const text = lines[i].replace(/^[-*]\s/, "");
        items.push(<li key={i} className="leading-relaxed">{renderInline(text)}</li>);
        i++;
      }
      elements.push(<ul key={key++} className="list-disc pl-4 my-1 space-y-0.5">{items}</ul>);
      continue;
    }

    // Ordered list
    if (/^\d+\.\s/.test(line)) {
      const items: React.ReactNode[] = [];
      while (i < lines.length && /^\d+\.\s/.test(lines[i])) {
        const text = lines[i].replace(/^\d+\.\s/, "");
        items.push(<li key={i} className="leading-relaxed">{renderInline(text)}</li>);
        i++;
      }
      elements.push(<ol key={key++} className="list-decimal pl-4 my-1 space-y-0.5">{items}</ol>);
      continue;
    }

    // Blank line
    if (line.trim() === "") { i++; continue; }

    // Paragraph
    elements.push(<p key={key++} className="mb-1 last:mb-0 leading-relaxed">{renderInline(line)}</p>);
    i++;
  }

  return <>{elements}</>;
}

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-bold mr-2 mt-0.5 shrink-0">
          T
        </div>
      )}

      <div
        className={clsx(
          "max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed break-words overflow-hidden",
          isUser
            ? "bg-brand-600 text-white rounded-br-sm"
            : "bg-white border border-gray-100 text-gray-800 rounded-bl-sm shadow-sm"
        )}
      >
        {isUser ? (
          <span className="whitespace-pre-wrap">{message.content || (message.streaming ? "" : "…")}</span>
        ) : message.content ? (
          <Markdown content={message.content} />
        ) : message.streaming ? null : "…"}

        {message.streaming && message.content && <span className="cursor-blink" />}
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
