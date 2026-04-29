"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useNanoAssist, stepLabel } from "@/state/useNanoAssist";

export function HistoryList() {
  const router = useRouter();
  const { sessions, messagesByPhone, selectSession } = useNanoAssist();

  return (
    <div className="flex min-h-screen flex-1 flex-col bg-gradient-to-br from-[#05080f] via-[#0b1428] to-[#080d18] px-4 py-8 text-[#dfdecf] sm:px-6 lg:px-10 lg:py-12">
      <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between lg:mb-10">
        <div>
          <div className="text-[11px] uppercase tracking-[0.4em] text-[#05adca]/70">Sessões de Teste</div>
          <h1
            className="text-3xl font-bold uppercase text-white"
            style={{ fontFamily: "var(--font-condensed)" }}
          >
            Histórico de Sessões
          </h1>
          <p className="mt-2 max-w-xl text-sm text-[#7f8baf]">
            Todas as sessões da sessão atual. Clique para retomar uma conversa.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center justify-center self-start rounded-full border border-[#1086ad]/60 bg-[#1086ad]/10 px-5 py-2.5 text-[11px] uppercase tracking-[0.4em] text-white transition hover:bg-[#1086ad]/20 sm:self-auto"
        >
          Voltar ao Simulador
        </Link>
      </header>

      {sessions.length === 0 ? (
        <div className="mt-12 flex flex-col items-center gap-6 rounded-3xl border border-dashed border-white/12 bg-white/5 px-8 py-16 text-center">
          <p className="text-sm text-[#7f8baf]">Nenhuma sessão iniciada ainda.</p>
          <Link
            href="/"
            className="rounded-full border border-[#1086ad]/60 bg-[#1086ad]/10 px-6 py-2.5 text-[11px] uppercase tracking-[0.4em] text-white transition hover:bg-[#1086ad]/20"
          >
            Iniciar simulação
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {sessions.map((session) => {
            const msgs = messagesByPhone[session.phone] ?? [];
            const firstUser = msgs.find((m) => m.role === "user")?.text ?? "";
            return (
              <button
                key={session.phone}
                type="button"
                className="group flex flex-col gap-3 rounded-3xl border border-white/15 bg-[rgba(9,14,26,0.9)] px-5 py-5 text-left transition-all hover:border-[#1086ad]/50 hover:bg-[#1086ad]/5 hover:shadow-[0_35px_80px_rgba(0,0,0,0.55)]"
                onClick={() => {
                  selectSession(session.phone);
                  router.push("/");
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <span
                    className="text-base font-semibold uppercase text-white"
                    style={{ fontFamily: "var(--font-condensed)" }}
                  >
                    {session.phone.slice(-4)}
                  </span>
                  {session.step ? (
                    <span className="shrink-0 rounded-full border border-[#05adca]/30 bg-[#05adca]/10 px-2.5 py-0.5 text-[10px] uppercase tracking-[0.25em] text-[#05adca]">
                      {stepLabel(session.step)}
                    </span>
                  ) : null}
                </div>

                {firstUser && (
                  <p className="line-clamp-3 text-sm text-[#9ba3c0]">{firstUser}</p>
                )}

                <div className="mt-auto flex items-center justify-between text-[10px] uppercase tracking-[0.35em] text-[#5c6383]">
                  <span>{msgs.length} mensagens</span>
                  <span>{new Date(session.createdAt).toLocaleTimeString("pt-BR")}</span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
