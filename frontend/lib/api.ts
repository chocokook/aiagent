/**
 * TechHub Support API client
 *
 * Handles chat (streaming SSE) and HITL resume calls.
 */

const API_BASE = "/api/v1";

export type StreamEvent =
  | { type: "session"; sessionId: string }
  | { type: "token"; content: string }
  | { type: "interrupt"; prompt: string }
  | { type: "done" }
  | { type: "error"; message: string };

/**
 * Stream a chat message. Yields StreamEvents via the callback.
 */
export async function streamChat(
  message: string,
  sessionId: string | null,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, stream: true }),
    signal,
  });

  if (!res.ok) {
    onEvent({ type: "error", message: `Server error ${res.status}` });
    return;
  }

  await parseSSE(res, onEvent);
}

/**
 * Resume a HITL-interrupted conversation (e.g. after user provides email).
 */
export async function streamResume(
  sessionId: string,
  userInput: string,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, user_input: userInput, stream: true }),
    signal,
  });

  if (!res.ok) {
    onEvent({ type: "error", message: `Server error ${res.status}` });
    return;
  }

  await parseSSE(res, onEvent);
}

/** Parse an SSE stream and dispatch StreamEvents. */
async function parseSSE(
  res: Response,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const data = line.slice(6).trim();

      if (data === "[DONE]") {
        onEvent({ type: "done" });
      } else if (data.startsWith("[SESSION] ")) {
        onEvent({ type: "session", sessionId: data.slice(10) });
      } else if (data.startsWith("[INTERRUPT] ")) {
        onEvent({ type: "interrupt", prompt: data.slice(12) });
      } else if (data) {
        onEvent({ type: "token", content: data });
      }
    }
  }
}
