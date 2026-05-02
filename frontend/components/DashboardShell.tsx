"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode } from "react";
import {
  Activity, Crosshair, Database, LayoutDashboard, LogOut,
  Shield, Users,
} from "lucide-react";
import { useAuth } from "./AuthContext";

const NAV = [
  { href: "/dashboard", label: "Dashboard",   icon: LayoutDashboard, phase: null },
  { href: "/soldiers",  label: "Soldiers",     icon: Users,           phase: "01" },
  { href: "/assess",    label: "Assess",        icon: Database,        phase: "01" },
  { href: "/teams",     label: "Team Builder",  icon: Shield,          phase: "02" },
  { href: "/battlespace", label: "Battlespace", icon: Crosshair,       phase: "03" },
];

const PHASE_COLORS: Record<string, string> = {
  "01": "text-[#3fb950]",
  "02": "text-[#f59e0b]",
  "03": "text-[#f85149]",
};

export default function DashboardShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router   = useRouter();
  const { user, logout } = useAuth();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#0d1117]">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 flex flex-col bg-[#161b22] border-r border-[#30363d]">
        {/* Logo */}
        <div className="px-4 py-5 border-b border-[#30363d]">
          <div className="text-xl font-black text-white tracking-tight">C2D2</div>
          <div className="text-[10px] text-[#8b949e] uppercase tracking-widest mt-0.5">
            Combat Decision Dominance
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto">
          {NAV.map(({ href, label, icon: Icon, phase }) => {
            const active = pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  active
                    ? "bg-[#21262d] text-white"
                    : "text-[#8b949e] hover:text-white hover:bg-[#21262d]"
                }`}
              >
                <Icon size={16} />
                <span className="flex-1">{label}</span>
                {phase && (
                  <span className={`text-[10px] font-bold ${PHASE_COLORS[phase] ?? ""}`}>
                    P{phase}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        {user && (
          <div className="px-4 py-3 border-t border-[#30363d]">
            <div className="text-xs text-[#8b949e] truncate">{user.full_name ?? user.email}</div>
            <div className="text-[10px] text-[#3fb950] uppercase mt-0.5">{user.role}</div>
            <button
              onClick={handleLogout}
              className="mt-2 flex items-center gap-1.5 text-[11px] text-[#8b949e] hover:text-[#f85149] transition-colors"
            >
              <LogOut size={12} /> Sign out
            </button>
          </div>
        )}
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>
    </div>
  );
}
