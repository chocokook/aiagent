"use client";

import { useState } from "react";

interface Props {
  onSubmit: (resolved: boolean, score: number) => void;
  onSkip: () => void;
}

export default function FeedbackModal({ onSubmit, onSkip }: Props) {
  const [resolved, setResolved] = useState<boolean | null>(null);
  const [score, setScore] = useState<number>(0);
  const [hovered, setHovered] = useState<number>(0);

  const canSubmit = resolved !== null && score > 0;

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm mx-4 flex flex-col gap-5">
        <h2 className="text-base font-semibold text-gray-900 text-center">
          感谢您的使用！
        </h2>

        {/* Resolved */}
        <div className="flex flex-col gap-2">
          <p className="text-sm text-gray-600 font-medium">问题解决了吗？</p>
          <div className="flex gap-3">
            <button
              onClick={() => setResolved(true)}
              className={`flex-1 py-2 rounded-xl border text-sm font-medium transition-colors ${
                resolved === true
                  ? "bg-emerald-50 border-emerald-400 text-emerald-700"
                  : "border-gray-200 text-gray-600 hover:border-gray-300"
              }`}
            >
              ✓ 解决了
            </button>
            <button
              onClick={() => setResolved(false)}
              className={`flex-1 py-2 rounded-xl border text-sm font-medium transition-colors ${
                resolved === false
                  ? "bg-red-50 border-red-400 text-red-700"
                  : "border-gray-200 text-gray-600 hover:border-gray-300"
              }`}
            >
              ✗ 没解决
            </button>
          </div>
        </div>

        {/* Stars */}
        <div className="flex flex-col gap-2">
          <p className="text-sm text-gray-600 font-medium">本次服务满意度</p>
          <div className="flex gap-1 justify-center">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                onClick={() => setScore(star)}
                onMouseEnter={() => setHovered(star)}
                onMouseLeave={() => setHovered(0)}
                className="text-3xl transition-transform hover:scale-110"
              >
                <span className={(hovered || score) >= star ? "text-amber-400" : "text-gray-200"}>
                  ★
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-1">
          <button
            onClick={onSkip}
            className="flex-1 py-2 rounded-xl border border-gray-200 text-sm text-gray-400 hover:text-gray-600 transition-colors"
          >
            跳过
          </button>
          <button
            onClick={() => canSubmit && onSubmit(resolved!, score)}
            disabled={!canSubmit}
            className={`flex-1 py-2 rounded-xl text-sm font-medium transition-colors ${
              canSubmit
                ? "bg-brand-600 text-white hover:bg-brand-700"
                : "bg-gray-100 text-gray-300 cursor-not-allowed"
            }`}
          >
            提交
          </button>
        </div>
      </div>
    </div>
  );
}
