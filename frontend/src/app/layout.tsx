import type { Metadata } from "next";
import { Open_Sans, Roboto_Condensed } from "next/font/google";
import "./globals.css";
import { NanoAssistProvider } from "@/state/useNanoAssist";
import { AppChrome } from "@/components/layout/AppChrome";

const openSans = Open_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-sans" });
const robotoCondensed = Roboto_Condensed({ subsets: ["latin"], weight: ["300", "400", "700"], variable: "--font-condensed" });

export const metadata: Metadata = {
  title: "NanoAssist — Simulador de Testes",
  description: "Teste local dos fluxos WhatsApp da Nanofarmacos",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className="bg-[#090e1a]">
      <body
        className={`${openSans.variable} ${robotoCondensed.variable} antialiased text-[#dfdecf]`}
        suppressHydrationWarning
      >
        <NanoAssistProvider>
          <AppChrome>{children}</AppChrome>
        </NanoAssistProvider>
      </body>
    </html>
  );
}
