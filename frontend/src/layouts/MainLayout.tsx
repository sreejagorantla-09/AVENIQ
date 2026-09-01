import { useState, useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Bot,
  ShieldCheck,
  ShieldAlert,
  Cpu,
  MessageSquareCode,
  CreditCard,
  History,
  Blocks,
  Settings as SettingsIcon,
  Menu,
  X,
  Sparkles,
  Package
} from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export default function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [backendStatus, setBackendStatus] = useState<'online' | 'offline' | 'checking'>('checking');
  const location = useLocation();

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Playground', path: '/playground', icon: Bot },
    { name: 'Passport', path: '/passport', icon: Sparkles },
    { name: 'Products', path: '/products', icon: Package },
    { name: 'Policies', path: '/policies', icon: ShieldCheck },
    { name: 'Agents', path: '/agents', icon: Cpu },
    { name: 'Approvals', path: '/approvals', icon: ShieldAlert },
    { name: 'Negotiation', path: '/negotiation', icon: MessageSquareCode },
    { name: 'Transactions', path: '/transactions', icon: CreditCard },
    { name: 'Audit & Logs', path: '/audit', icon: History },
    { name: 'Integrations', path: '/integrations', icon: Blocks },
    { name: 'Settings', path: '/settings', icon: SettingsIcon },
  ];

  useEffect(() => {
    fetch(`${API_BASE_URL}/health`)
      .then((res) => {
        if (res.ok) {
          setBackendStatus('online');
        } else {
          setBackendStatus('offline');
        }
      })
      .catch(() => {
        setBackendStatus('offline');
      });
  }, [location.pathname]);

  return (
    <div className="min-h-screen flex bg-[#000000] text-[#F3F4F4] font-sans">
      {/* Sidebar Navigation */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-[#000000] border-r border-[#2C2C2C] transition-transform duration-300 md:translate-x-0 md:static md:flex md:flex-col ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-[#2C2C2C] bg-[#000000]">
          <NavLink to="/" className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-[#853953] to-[#612D53] flex items-center justify-center shadow-lg shadow-[#853953]/30 border border-[#853953]/50">
              <ShieldCheck className="h-5 w-5 text-[#F3F4F4]" />
            </div>
            <div>
              <span className="text-xl font-bold tracking-widest text-[#F3F4F4] font-display">AVENIQ</span>
              <span className="block text-[9px] uppercase font-mono tracking-widest text-[#a85890] -mt-1 font-semibold">
                Agentic Commerce
              </span>
            </div>
          </NavLink>
          <button className="md:hidden text-zinc-400 hover:text-[#F3F4F4]" onClick={() => setSidebarOpen(false)}>
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 overflow-y-auto px-3.5 py-6 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 ${
                    isActive
                      ? 'bg-[#853953] text-[#F3F4F4] shadow-lg shadow-[#853953]/40 border border-[#9c4362]/50 font-bold'
                      : 'text-zinc-400 hover:text-[#F3F4F4] hover:bg-[#612D53]/40'
                  }`
                }
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Footer Area with Backend Health Indicator */}
        <div className="p-4 border-t border-[#2C2C2C] bg-[#000000]">
          <div className="flex items-center justify-between rounded-xl bg-[#2C2C2C] border border-[#3a3a3a] p-3">
            <span className="text-xs text-zinc-300 font-medium">Control Plane</span>
            <div className="flex items-center space-x-2">
              <div
                className={`h-2 w-2 rounded-full ${
                  backendStatus === 'online'
                    ? 'bg-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.8)] animate-pulse'
                    : backendStatus === 'offline'
                    ? 'bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.8)]'
                    : 'bg-amber-400 animate-pulse'
                }`}
              />
              <span className="text-[10px] uppercase font-mono font-bold text-[#F3F4F4]">
                {backendStatus === 'online' ? 'Online' : backendStatus === 'offline' ? 'Offline' : 'Checking'}
              </span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen bg-[#000000]">
        {/* Mobile Header */}
        <header className="h-16 border-b border-[#2C2C2C] bg-[#000000] px-6 flex items-center justify-between md:hidden flex-shrink-0">
          <button className="text-zinc-400 hover:text-[#F3F4F4]" onClick={() => setSidebarOpen(true)}>
            <Menu className="h-6 w-6" />
          </button>
          <span className="text-lg font-bold text-[#F3F4F4] tracking-widest font-display">AVENIQ</span>
          <div className="h-6 w-6" />
        </header>

        {/* Dynamic Route Slot */}
        <main className="flex-1 p-6 md:p-8 overflow-y-auto max-w-7xl w-full mx-auto space-y-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
