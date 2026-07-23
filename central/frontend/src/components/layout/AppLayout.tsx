import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Camera, Settings, Wifi, WifiOff } from 'lucide-react';
import Logo from "../../assets/vigilai_premium-modified.png"

interface AppLayoutProps {
  children: React.ReactNode;
  /** Live connection state, surfaced in the topbar. Defaults to true so the
   *  indicator degrades gracefully if a page doesn't wire it up yet. */
  isConnected?: boolean;
}

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/cameras', label: 'Cameras', icon: Camera, end: true },
  { to: '/settings', label: 'Settings', icon: Settings, end: true },
];

// const pageMeta: Record<string, { section: string; title: string }> = {
//   '/': { section: 'Monitor', title: 'Dashboard' },
//   '/cameras': { section: 'Monitor', title: 'Cameras' },
//   '/settings': { section: 'Configure', title: 'Settings' },
// };

export function AppLayout({ children, isConnected = true }: AppLayoutProps) {
  const navItemClass = ({ isActive }: { isActive: boolean }) =>
    `group flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[13px] font-medium transition-colors ${isActive
      ? 'bg-zinc-100 text-zinc-900'
      : 'text-zinc-400 hover:bg-zinc-900 hover:text-zinc-100'
    }`;

  return (
    <div className="flex h-screen w-full bg-zinc-950 text-zinc-100 antialiased">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 border-r border-zinc-900 flex flex-col">
        <div className="h-12 flex items-center gap-2 px-4 border-b border-zinc-900">
          {/* <span className="h-5 w-5 rounded-md bg-indigo-500 flex items-center justify-center text-[10px] font-bold text-white">
            V
          </span>
          <span className="text-[13px] font-semibold tracking-tight text-zinc-100">
            Vigil
          </span> */}

          <img
            src={Logo}
            alt="Logo"
            className="w-8 h-8 rounded-full border border-zinc-700 shrink-0"
          />
          <div className="hidden sm:flex flex-col leading-tight">
            <span className="text-xs font-bold tracking-widest text-white uppercase">
              Vigil-AI
            </span>
            <span className="text-[10px] text-zinc-500 tracking-wide">
              AI Detection System
            </span>
          </div>
        </div>


        <nav className="flex-1 px-2 py-3 space-y-0.5">
          <p className="px-2.5 pb-1.5 pt-1 text-[10px] font-medium tracking-wider text-zinc-600 uppercase">
            Monitor
          </p>
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={navItemClass}>
              <Icon className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-3 border-t border-zinc-900">
          <div className="flex items-center gap-1.5 text-[11px] text-zinc-600">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Air-gapped mode
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar */}
        <header className="h-12 shrink-0 border-b border-zinc-900 flex items-center justify-between px-5">
          <div className="flex items-center gap-1.5 text-[13px] text-zinc-400">
            <span className="text-zinc-600">Monitor</span>
            <span className="text-zinc-700">/</span>
            <span className="text-zinc-100 font-medium">Overview</span>
          </div>

          <div
            className="flex items-center gap-1.5 text-[11px] font-medium text-zinc-500"
            role="status"
            aria-live="polite"
          >
            {isConnected ? (
              <>
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <Wifi className="h-3 w-3" strokeWidth={2} />
                <span>Connected</span>
              </>
            ) : (
              <>
                <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                <WifiOff className="h-3 w-3" strokeWidth={2} />
                <span>Disconnected</span>
              </>
            )}
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
