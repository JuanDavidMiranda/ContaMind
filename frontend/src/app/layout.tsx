import type { Metadata } from "next";
import { Geist } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ContaMind AI",
  description: "Conciliación de ventas entre ERP y DIAN",
};

const links = [
  { href: "/", label: "Inicio" },
  { href: "/companies", label: "Empresas" },
  { href: "/reconciliations", label: "Conciliaciones" },
];

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="es" className={`${geistSans.variable} h-full`}>
      <body className="min-h-full">
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
            <Link href="/" className="flex flex-col">
              <span className="text-lg font-semibold tracking-tight text-teal-900">ContaMind AI</span>
              <span className="text-xs text-slate-500">Conciliación de ventas</span>
            </Link>
            <nav className="flex gap-4 text-sm font-medium text-slate-700">
              {links.map((link) => (
                <Link key={link.href} href={link.href} className="hover:text-teal-800">
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
