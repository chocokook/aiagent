import ChatWindow from "@/components/ChatWindow";
import CheatsheetModal from "@/components/CheatsheetModal";

declare const process: { env: Record<string, string | undefined> };
const GRAFANA_URL = process.env.NEXT_PUBLIC_GRAFANA_URL ?? null;

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center p-4">
      {/* Header */}
      <div className="w-full max-w-2xl mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white font-bold text-lg">
            T
          </div>
          <div>
            <h1 className="text-xl font-semibold text-gray-900">TechHub Support</h1>
            <p className="text-sm text-gray-500">AI-powered customer assistant</p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            {GRAFANA_URL && (
              <a
                href={GRAFANA_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-xs text-violet-600 hover:text-violet-800 font-medium transition-colors border border-violet-200 hover:border-violet-400 rounded-lg px-2.5 py-1"
                title="Open live monitoring dashboard"
              >
                <span>📊</span>
                Live Monitoring
              </a>
            )}
            <span className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse" />
              Online
            </span>
          </div>
        </div>
      </div>

      {/* Chat */}
      <ChatWindow />

      {/* Floating cheatsheet */}
      <CheatsheetModal />
    </main>
  );
}
