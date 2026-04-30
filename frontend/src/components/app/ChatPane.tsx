"use client";

import { FormEvent, useEffect, useMemo, useRef, useCallback, useState } from "react";
import { useNanoAssist, stepLabel } from "@/state/useNanoAssist";

const QUICK_REPLIES = [
  { label: "1 — Buscar receita", value: "1" },
  { label: "2 — Orçamento", value: "2" },
  { label: "SIM", value: "SIM" },
  { label: "NÃO", value: "NAO" },
  { label: "PIX", value: "1" },
  { label: "Link", value: "2" },
  { label: "CONFIRMAR", value: "CONFIRMAR" },
  { label: "ALTERAR", value: "ALTERAR" },
];

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function renderText(text: string) {
  return text.split(/(\*[^*]+\*)/g).map((part, i) =>
    part.startsWith("*") && part.endsWith("*") && part.length > 2
      ? <strong key={i}>{part.slice(1, -1)}</strong>
      : <span key={i}>{part}</span>
  );
}

export function ChatPane() {
  const { currentPhone, messagesByPhone, currentStep, isSending, error, sendMessage, clearError, createSession } =
    useNanoAssist();
  const messages = useMemo(() => messagesByPhone[currentPhone] ?? [], [messagesByPhone, currentPhone]);
  const [draft, setDraft] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const submit = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) return;
      setDraft("");
      await sendMessage(trimmed);
      inputRef.current?.focus();
    },
    [isSending, sendMessage],
  );

  const handleFormSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      submit(draft);
    },
    [draft, submit],
  );

  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-[#090e1a]">
      {/* Decorative overlays */}
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_15%,rgba(32,51,109,0.22),transparent_60%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_80%_0%,rgba(16,134,173,0.1),transparent_55%)]" />

      {/* WhatsApp chat area */}
      <div className="relative flex flex-1 items-center justify-center overflow-hidden p-4 sm:p-6 lg:p-10">
        <div
          className="flex w-full max-w-lg flex-col overflow-hidden rounded-2xl shadow-2xl"
          style={{ height: "calc(100vh - 120px)", maxHeight: "780px" }}
        >
          {/* WhatsApp top bar */}
          <div className="flex items-center gap-3 bg-[#075e54] px-4 py-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#128c7e] text-lg font-bold text-white">
              N
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-semibold text-white">Nanofarmacos</p>
              <p className="text-xs text-[#a7d7c5]">Atendimento automático · /webhook/test</p>
            </div>
            {currentStep ? (
              <span className="shrink-0 max-w-[130px] truncate rounded-full bg-[#128c7e] px-2 py-0.5 text-[10px] text-white">
                {stepLabel(currentStep)}
              </span>
            ) : null}
          </div>

          {/* Messages */}
          <div
            className="flex-1 overflow-y-auto px-3 py-4 space-y-1"
            style={{ backgroundColor: "#efeae2" }}
          >
            {messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
                <span className="text-4xl">💊</span>
                <p className="text-sm text-gray-500">Envie uma mensagem para iniciar o fluxo.</p>
                <p className="text-xs text-gray-400">Use os atalhos abaixo ou digite livremente.</p>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`relative max-w-[80%] rounded-lg px-3 py-2 shadow-sm ${
                      msg.role === "user" ? "bg-[#d9fdd3]" : "bg-white"
                    }`}
                  >
                    <p className="whitespace-pre-wrap text-sm text-gray-800">{renderText(msg.text)}</p>
                    <span className="float-right ml-4 mt-0.5 text-[10px] text-gray-400">
                      {formatTime(msg.timestamp)}
                      {msg.role === "user" && " ✓✓"}
                    </span>
                  </div>
                </div>
              ))
            )}
            {isSending && (
              <div className="flex justify-start">
                <div className="rounded-lg bg-white px-4 py-2 shadow-sm">
                  <div className="flex h-4 items-center gap-1">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: "0ms" }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: "150ms" }} />
                    <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Error bar */}
          {error && (
            <div className="flex items-center justify-between bg-red-50 px-4 py-2 text-xs text-red-600">
              <span>{error}</span>
              <button type="button" onClick={clearError} className="ml-2 font-bold">
                ×
              </button>
            </div>
          )}

          {/* Quick replies */}
          <div className="flex flex-wrap gap-1.5 bg-[#f0f2f5] px-3 pb-1 pt-2">
            {QUICK_REPLIES.map((qr) => (
              <button
                key={qr.label}
                type="button"
                onClick={() => submit(qr.value)}
                disabled={isSending}
                className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-medium text-[#075e54] transition hover:bg-[#075e54] hover:text-white disabled:opacity-40"
              >
                {qr.label}
              </button>
            ))}
          </div>

          {/* Input bar */}
          <form
            onSubmit={handleFormSubmit}
            className="flex items-center gap-2 bg-[#f0f2f5] px-3 pb-3 pt-1"
          >
            <input
              ref={inputRef}
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Digite uma mensagem"
              disabled={isSending}
              className="flex-1 rounded-full border border-gray-200 bg-white px-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition focus:border-[#075e54] disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={isSending || !draft.trim()}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#075e54] text-white transition hover:bg-[#128c7e] disabled:opacity-40"
            >
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </form>
        </div>
      </div>

      {/* Bottom info */}
      <div className="absolute bottom-2 right-4 text-[10px] uppercase tracking-[0.35em] text-[#3a3f55]">
        <button
          type="button"
          onClick={createSession}
          className="rounded-full border border-white/10 px-3 py-1 text-[#5c6383] transition hover:border-[#05adca]/40 hover:text-[#05adca]"
        >
          Nova sessão
        </button>
      </div>
    </div>
  );
}
