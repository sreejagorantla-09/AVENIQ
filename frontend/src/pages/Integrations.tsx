import { useEffect, useState } from 'react';
import { Database, Cpu, CreditCard, RefreshCw, AlertTriangle } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

interface IntegrationInfo {
  name: string;
  status: string;
  details: string;
}

interface IntegrationsStatus {
  supabase: IntegrationInfo;
  gemini: IntegrationInfo;
  razorpay: IntegrationInfo;
}

export default function Integrations() {
  const [status, setStatus] = useState<IntegrationsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      let response: Response | null = null;
      try {
        response = await fetch(`${API_BASE_URL}/integrations/status`);
      } catch (firstErr) {
        const fallbackUrl = API_BASE_URL.includes('localhost')
          ? API_BASE_URL.replace('localhost', '127.0.0.1')
          : API_BASE_URL.replace('127.0.0.1', 'localhost');
        try {
          response = await fetch(`${fallbackUrl}/integrations/status`);
        } catch {
          throw firstErr;
        }
      }

      if (!response || !response.ok) {
        throw new Error('Failed to load integration states.');
      }
      const data = await response.json();
      setStatus(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  if (loading && !status) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <RefreshCw className="h-8 w-8 animate-spin text-[#853953]" />
          <p className="text-sm text-zinc-400 font-mono">Querying integrations connectivity...</p>
        </div>
      </div>
    );
  }

  const getStatusColor = (s: string) => {
    switch (s) {
      case 'connected':
        return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10';
      case 'disconnected':
        return 'text-rose-400 border-rose-500/20 bg-rose-500/10';
      default:
        return 'text-amber-400 border-amber-500/20 bg-amber-500/10';
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'connected':
        return 'Connected';
      case 'disconnected':
        return 'Connection Failed';
      default:
        return 'Pending Config';
    }
  };

  return (
    <div className="space-y-8 text-[#F3F4F4]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold font-display text-[#F3F4F4]">External Platform Integrations</h2>
          <p className="text-xs text-zinc-300 mt-1">Connect your data stores, payment processors, and AI platforms</p>
        </div>
        <button
          onClick={fetchStatus}
          className="p-2 bg-[#612D53]/40 hover:bg-[#853953] border border-[#612D53] rounded-xl text-[#F3F4F4] transition"
          title="Refresh connection status"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {status && (
        <div className="grid gap-6 md:grid-cols-3">
          {/* Supabase connection card */}
          <div className="bg-[#2C2C2C] p-6 rounded-2xl flex flex-col justify-between min-h-[220px] border border-[#3a3a3a] shadow-xl">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded bg-[#1c1c1c] text-zinc-300 border border-[#3a3a3a] uppercase tracking-wider">
                  Database
                </span>
                <Database className="h-5 w-5 text-[#853953]" />
              </div>
              <div>
                <h3 className="text-base font-bold font-display text-[#F3F4F4]">{status.supabase.name}</h3>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold uppercase mt-2 border font-mono ${getStatusColor(status.supabase.status)}`}>
                  {getStatusBadge(status.supabase.status)}
                </span>
                <p className="text-[11px] text-zinc-400 mt-3 truncate font-mono" title={status.supabase.details}>
                  {status.supabase.details}
                </p>
              </div>
            </div>
            <div className="text-xs text-zinc-300 mt-4 leading-relaxed pt-3 border-t border-[#3a3a3a]">
              Primary data store for merchants, products, policies, and hash chains.
            </div>
          </div>

          {/* Gemini AI Gateway connection card */}
          <div className="bg-[#2C2C2C] p-6 rounded-2xl flex flex-col justify-between min-h-[220px] border border-[#3a3a3a] shadow-xl">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded bg-[#1c1c1c] text-zinc-300 border border-[#3a3a3a] uppercase tracking-wider">
                  Cognitive LLM
                </span>
                <Cpu className="h-5 w-5 text-[#853953]" />
              </div>
              <div>
                <h3 className="text-base font-bold font-display text-[#F3F4F4]">{status.gemini.name}</h3>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold uppercase mt-2 border font-mono ${getStatusColor(status.gemini.status)}`}>
                  {getStatusBadge(status.gemini.status)}
                </span>
                <p className="text-[11px] text-zinc-400 mt-3 font-mono">
                  {status.gemini.details}
                </p>
              </div>
            </div>
            <div className="text-xs text-zinc-300 mt-4 leading-relaxed pt-3 border-t border-[#3a3a3a]">
              Enables autonomous intent parsing and dynamically evaluates agent proposals.
            </div>
          </div>

          {/* Razorpay connection card */}
          <div className="bg-[#2C2C2C] p-6 rounded-2xl flex flex-col justify-between min-h-[220px] border border-[#3a3a3a] shadow-xl">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded bg-[#1c1c1c] text-zinc-300 border border-[#3a3a3a] uppercase tracking-wider">
                  Payments
                </span>
                <CreditCard className="h-5 w-5 text-[#853953]" />
              </div>
              <div>
                <h3 className="text-base font-bold font-display text-[#F3F4F4]">{status.razorpay.name}</h3>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[9px] font-bold uppercase mt-2 border font-mono ${getStatusColor(status.razorpay.status)}`}>
                  {getStatusBadge(status.razorpay.status)}
                </span>
                <p className="text-[11px] text-zinc-400 mt-3 font-mono">
                  {status.razorpay.details}
                </p>
              </div>
            </div>
            <div className="text-xs text-zinc-300 mt-4 leading-relaxed pt-3 border-t border-[#3a3a3a]">
              Clears payment checkouts and issues cryptographically signed approvals.
            </div>
          </div>
        </div>
      )}

      {/* Connectivity Guides */}
      <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-4 shadow-xl">
        <h3 className="text-base font-bold font-display text-[#F3F4F4]">Configuration Information</h3>
        <p className="text-xs text-zinc-300">
          Connections are established dynamically by providing valid secrets inside the root `.env` file of the project.
        </p>
        <div className="p-4 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a] space-y-3 font-mono text-xs text-zinc-300">
          <div>
            <span className="text-[#a85890] font-bold"># To configure Database:</span>
            <div className="text-zinc-400 pl-4 mt-0.5">Set SUPABASE_URL and SUPABASE_SECRET_KEY</div>
          </div>
          <div>
            <span className="text-[#a85890] font-bold"># To configure Gemini AI:</span>
            <div className="text-zinc-400 pl-4 mt-0.5">Set GEMINI_API_KEY</div>
          </div>
          <div>
            <span className="text-[#a85890] font-bold"># To configure Razorpay Checkout:</span>
            <div className="text-zinc-400 pl-4 mt-0.5">Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET</div>
          </div>
        </div>
      </div>
    </div>
  );
}
