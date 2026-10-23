import React, { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../api/client";
import { extractErrorMessage } from "./ui";

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi! Ask me about occupancy, pending rent, your room, or your payments." },
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setSending(true);

    try {
      const res = await sendChatMessage(text);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.data.reply,
          toolCalls: res.data.tool_calls_made,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${extractErrorMessage(err)}` },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {open && (
        <div className="w-80 sm:w-96 h-[28rem] bg-white rounded-lg shadow-xl border border-slate-200 flex flex-col mb-3 overflow-hidden">
          <div className="bg-brand-600 text-white px-4 py-3 flex items-center justify-between">
            <span className="font-medium text-sm">AI Assistant</span>
            <button onClick={() => setOpen(false)} className="text-white/80 hover:text-white">
              ✕
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    m.role === "user" ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-800"
                  }`}
                >
                  <p>{m.content}</p>
                  {/* {m.toolCalls && m.toolCalls.length > 0 && 
                  (
                    <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-400">
                      tools used: {m.toolCalls.join(", ")}
                    </p>
                  )
                  } */}
                </div>
              </div>
            ))}
            {sending && <p className="text-xs text-slate-400">Thinking...</p>}
            <div ref={bottomRef} />
          </div>

          <div className="border-t border-slate-200 p-2 flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask something..."
              className="flex-1 border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              disabled={sending}
            />
            <button
              onClick={send}
              disabled={sending}
              className="bg-brand-600 hover:bg-brand-700 text-white rounded-md px-3 py-2 text-sm disabled:opacity-50"
            >
              Send
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        className="bg-brand-600 hover:bg-brand-700 text-white rounded-full w-14 h-14 shadow-lg flex items-center justify-center text-2xl"
        aria-label="Toggle chat"
      >
        {open ? "✕" : "💬"}
      </button>
    </div>
  );
}
