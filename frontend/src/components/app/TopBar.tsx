"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useNanoAssist, stepLabel } from "@/state/useNanoAssist";

interface TopBarProps {
  onToggleSidebar?: () => void;
}

export function TopBar({ onToggleSidebar }: TopBarProps) {
  const pathname = usePathname();
  const { currentPhone, currentStep } = useNanoAssist();

  return (
    <header className="sticky top-0 z-30 grid grid-cols-[1fr_auto_1fr] items-center gap-3 bg-[rgba(9,14,26,0.9)] px-4 py-3 text-[#dfdecf] shadow-[0_1px_0_rgba(255,255,255,0.04),0_25px_80px_rgba(0,0,0,0.45)] backdrop-blur-2xl sm:px-6 md:px-8">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-white/20 bg-white/5 text-white transition hover:border-[#1086ad] hover:bg-[#1086ad]/15 lg:hidden"
          aria-label="Abrir menu"
        >
          <span className="flex flex-col gap-1.5">
            <span className="block h-0.5 w-5 bg-white" />
            <span className="block h-0.5 w-5 bg-white" />
            <span className="block h-0.5 w-5 bg-white" />
          </span>
        </button>
        <nav className="hidden items-center gap-2 text-[12px] uppercase tracking-[0.25em] md:flex">
          <Link
            href="/"
            className={clsx(
              "rounded-full border px-3 py-2 transition sm:px-4",
              pathname === "/"
                ? "border-white/60 bg-white/10 text-white"
                : "border-transparent text-[#9ba3c0] hover:border-white/20 hover:bg-white/5",
            )}
          >
            Simulador
          </Link>
        </nav>
      </div>

      <div className="flex flex-col items-center justify-center">
        <p className="text-[9px] uppercase tracking-[0.45em] text-[#7f8baf]">Nanofarmacos</p>
        <p
          className="text-lg font-black uppercase tracking-widest text-white"
          style={{ fontFamily: "var(--font-condensed)" }}
        >
          NanoAssist
        </p>
      </div>

      <div className="flex flex-col items-end justify-center gap-0.5">
        {currentPhone ? (
          <>
            <span className="font-mono text-[10px] text-[#5c6383]">{currentPhone}</span>
            {currentStep ? (
              <span className="max-w-[180px] truncate rounded-full border border-[#05adca]/30 bg-[#05adca]/10 px-2 py-0.5 text-[10px] uppercase tracking-[0.25em] text-[#05adca]">
                {stepLabel(currentStep)}
              </span>
            ) : null}
          </>
        ) : (
          <span className="text-[11px] uppercase tracking-[0.35em] text-[#7f8baf]">Sem sessão</span>
        )}
      </div>
    </header>
  );
}
