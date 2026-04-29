"use client";

import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

export interface NanoMessage {
  id: string;
  role: "user" | "bot";
  text: string;
  timestamp: number;
}

export interface NanoSession {
  phone: string;
  title: string;
  createdAt: number;
  step: string;
}

interface NanoAssistState {
  sessions: NanoSession[];
  currentPhone: string;
  messagesByPhone: Record<string, NanoMessage[]>;
  currentStep: string;
  isSending: boolean;
  error: string | null;
  createSession: () => void;
  selectSession: (phone: string) => void;
  sendMessage: (text: string) => Promise<void>;
  clearError: () => void;
}

const STEP_LABELS: Record<string, string> = {
  "ConversationStep.INITIAL": "Início",
  "ConversationStep.MENU": "Menu",
  "ConversationStep.F1_AGUARDANDO_ID": "Aguardando ID",
  "ConversationStep.F1_CONFIRMANDO_RECEITA": "Confirmando Receita",
  "ConversationStep.F1_AGUARDANDO_PAGAMENTO": "Aguardando Pagamento",
  "ConversationStep.F1_AGUARDANDO_COMPROVANTE": "Aguardando Comprovante",
  "ConversationStep.F1_CONFIRMACAO_FINAL": "Confirmação Final",
  "ConversationStep.F2_COLETANDO_DADOS": "Coletando Dados",
  "ConversationStep.F2_VALIDANDO_DADOS": "Validando Dados",
  "ConversationStep.AGUARDANDO_HUMANO": "Transferido para Humano",
};

export function stepLabel(raw: string): string {
  return STEP_LABELS[raw] ?? raw;
}

function makePhone(): string {
  return "5511" + Math.floor(900_000_000 + Math.random() * 100_000_000);
}

const NanoAssistContext = createContext<NanoAssistState | null>(null);

export function NanoAssistProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<NanoSession[]>(() => {
    const phone = makePhone();
    return [{ phone, title: "Sessão inicial", createdAt: Date.now(), step: "" }];
  });
  const [currentPhone, setCurrentPhone] = useState<string>(() => sessions[0]?.phone ?? "");
  const [messagesByPhone, setMessagesByPhone] = useState<Record<string, NanoMessage[]>>({});
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const stepRef = useRef<Record<string, string>>({});

  const createSession = useCallback(() => {
    const phone = makePhone();
    const session: NanoSession = { phone, title: `Sessão ${phone.slice(-4)}`, createdAt: Date.now(), step: "" };
    setSessions((prev) => [session, ...prev]);
    setCurrentPhone(phone);
    setError(null);
  }, []);

  const selectSession = useCallback((phone: string) => {
    setCurrentPhone(phone);
    setError(null);
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;

    setError(null);
    setIsSending(true);

    const phone = currentPhone;
    const userMsg: NanoMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: trimmed,
      timestamp: Date.now(),
    };
    setMessagesByPhone((prev) => ({ ...prev, [phone]: [...(prev[phone] ?? []), userMsg] }));

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ number: phone, body: trimmed }),
      });
      const data = await res.json();

      if (data.error) {
        setError(data.error);
        return;
      }

      const step: string = data.step ?? "";
      stepRef.current[phone] = step;

      setSessions((prev) =>
        prev.map((s) =>
          s.phone === phone
            ? { ...s, title: s.title, step }
            : s,
        ),
      );

      const botMsg: NanoMessage = {
        id: crypto.randomUUID(),
        role: "bot",
        text: data.response || "(sem resposta)",
        timestamp: Date.now(),
      };
      setMessagesByPhone((prev) => ({ ...prev, [phone]: [...(prev[phone] ?? []), botMsg] }));
    } catch {
      setError("Backend indisponível. O servidor está rodando em localhost:8000?");
    } finally {
      setIsSending(false);
    }
  }, [currentPhone, isSending]);

  const clearError = useCallback(() => setError(null), []);

  const value = useMemo<NanoAssistState>(
    () => ({
      sessions,
      currentPhone,
      messagesByPhone,
      currentStep: stepRef.current[currentPhone] ?? "",
      isSending,
      error,
      createSession,
      selectSession,
      sendMessage,
      clearError,
    }),
    [sessions, currentPhone, messagesByPhone, isSending, error, createSession, selectSession, sendMessage, clearError],
  );

  return <NanoAssistContext.Provider value={value}>{children}</NanoAssistContext.Provider>;
}

export function useNanoAssist() {
  const ctx = useContext(NanoAssistContext);
  if (!ctx) throw new Error("useNanoAssist deve estar dentro de NanoAssistProvider");
  return ctx;
}
