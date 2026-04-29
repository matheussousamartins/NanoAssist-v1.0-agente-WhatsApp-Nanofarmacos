"use client";

import clsx from "clsx";
import { useNanoAssist, stepLabel } from "@/state/useNanoAssist";
import { Button } from "@/components/ui/button";

interface SidebarProps {
  isMobile?: boolean;
}

export function Sidebar({ isMobile = false }: SidebarProps) {
  const { sessions, currentPhone, selectSession, createSession, messagesByPhone } = useNanoAssist();

  return (
    <aside
      className={clsx(
        "relative flex w-80 flex-col gap-6 border-white/10 bg-gradient-to-b from-[#111a32]/90 via-[#0c1324]/92 to-[#080f1b]/95 p-7 text-[#dfdecf] shadow-[0_30px_80px_rgba(0,0,0,0.65)] backdrop-blur-2xl",
        isMobile
          ? "w-full max-w-[22rem] rounded-2xl border border-white/15 max-h-[calc(100vh-1.5rem)] overflow-y-auto"
          : "sticky top-0 h-screen border-r",
      )}
    >
      <section className="space-y-3">
        <div>
          <p className="text-[10px] uppercase tracking-[0.35em] text-[#05adca]/70">Simulador de Testes</p>
          <h2 className="text-2xl font-black uppercase text-white" style={{ fontFamily: "var(--font-condensed)" }}>
            NanoAssist
          </h2>
          <p className="mt-1 text-xs uppercase tracking-[0.3em] text-[#7f8baf]">Sessões Ativas</p>
        </div>
        <Button
          onClick={createSession}
          className="w-full justify-center border border-white/20 bg-white/5 text-sm uppercase tracking-[0.35em] text-white hover:border-[#1086ad] hover:bg-[#1086ad]/15"
        >
          Nova Sessão
        </Button>
      </section>

      <div className="h-px w-full bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      <section className="flex-1 overflow-hidden">
        <div className="-mr-3 flex h-full flex-col gap-2 overflow-y-auto pr-3">
          {sessions.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-white/12 bg-white/5 p-6 text-center text-xs text-[#7f8baf]">
              Nenhuma sessão ativa.
            </div>
          ) : (
            sessions.map((session) => {
              const active = session.phone === currentPhone;
              const msgs = messagesByPhone[session.phone] ?? [];
              const lastMsg = msgs.slice(-1)[0]?.text ?? "";
              const createdLabel = new Date(session.createdAt).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
              return (
                <button
                  key={session.phone}
                  onClick={() => selectSession(session.phone)}
                  className={clsx(
                    "flex flex-col gap-1 rounded-2xl border px-4 py-3 text-left transition-all",
                    active
                      ? "border-[#1086ad]/70 bg-[#1086ad]/12 text-white shadow-[0_20px_45px_rgba(6,12,24,0.65)]"
                      : "border-white/10 bg-white/5 text-[#dfdecf] hover:border-[#1086ad]/40 hover:bg-white/10",
                  )}
                >
                  <span
                    className="text-sm font-semibold uppercase tracking-wide text-white"
                    style={{ fontFamily: "var(--font-condensed)" }}
                  >
                    {session.phone.slice(-4)}
                  </span>
                  {session.step ? (
                    <span className="text-[10px] text-[#05adca]">{stepLabel(session.step)}</span>
                  ) : null}
                  <p className="line-clamp-2 text-xs text-[#9ba3c0]">
                    {lastMsg || "Sem mensagens ainda."}
                  </p>
                  <div className="text-[10px] uppercase tracking-[0.35em] text-[#5c6383]">
                    <span>{msgs.length} msgs · {createdLabel}</span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </section>

      <div className="rounded-2xl border border-white/15 bg-white/5 p-4">
        <p className="text-[11px] uppercase tracking-[0.35em] text-[#7f8baf]">Atenção</p>
        <p className="mt-1 text-xs text-[#9ba3c0]">
          Mensagens enviadas via <code className="text-[#05adca]">/webhook/test</code>. Nenhuma mensagem real é enviada ao cliente.
        </p>
      </div>
    </aside>
  );
}
