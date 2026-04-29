"use client";

import { ReactNode, useState } from "react";
import clsx from "clsx";
import { Sidebar } from "@/components/app/Sidebar";
import { TopBar } from "@/components/app/TopBar";

interface AppChromeProps {
  children: ReactNode;
}

export function AppChrome({ children }: AppChromeProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const closeSidebar = () => setIsSidebarOpen(false);

  return (
    <div className="relative h-screen overflow-hidden">
      <div className="relative flex h-full flex-col lg:flex-row">
        <div className="hidden lg:block">
          <Sidebar />
        </div>

        <div className="flex flex-1 flex-col lg:h-full">
          <TopBar onToggleSidebar={() => setIsSidebarOpen(true)} />
          <main className="flex-1 overflow-y-auto backdrop-blur-sm">{children}</main>
        </div>

        {/* Mobile sidebar */}
        <div
          className={clsx(
            "fixed inset-y-0 left-0 z-50 w-[min(90vw,22rem)] max-w-full transform transition-transform duration-300 lg:hidden",
            isSidebarOpen ? "translate-x-0" : "-translate-x-full",
          )}
          aria-hidden={!isSidebarOpen}
        >
          <Sidebar isMobile />
          <button
            type="button"
            onClick={closeSidebar}
            className="absolute right-3 top-3 rounded-full border border-white/20 bg-black/30 px-3 py-1 text-[11px] uppercase tracking-[0.35em] text-white hover:border-[#1086ad]"
          >
            Fechar
          </button>
        </div>

        {isSidebarOpen ? (
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            onClick={closeSidebar}
            aria-label="Fechar navegação"
          />
        ) : null}
      </div>
    </div>
  );
}
