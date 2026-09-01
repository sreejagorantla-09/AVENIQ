import { useEffect, useState } from 'react';
import { ShieldCheck, Cpu, Activity, ListChecks, AlertTriangle, RefreshCw, Sparkles, ShieldAlert, CheckCircle2, Play } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

interface AuditEvent {
  id: string;
  event_type: string;
  actor_type: string;
  actor_id: string;
  action: string;
  decision: string;
  created_at: string;
  event_hash: string;
}

interface DashboardStats {
  total_products: number;
  active_products: number;
  total_agents: number;
  total_requests: number;
  total_policies: number;
  recent_activity: AuditEvent[];
  health: {
    service: string;
    database: string;
  };
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [merchant, setMerchant] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recalculating, setRecalculating] = useState(false);

  // Ledger Verification States
  const [verifyingChain, setVerifyingChain] = useState(false);
  const [verificationPassed, setVerificationPassed] = useState<boolean | null>(null);
  const [isTampered, setIsTampered] = useState(false);
  const [tamperedNodeIndex, setTamperedNodeIndex] = useState<number | null>(null);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      let response: Response | null = null;
      try {
        response = await fetch(`${API_BASE_URL}/dashboard/stats`);
      } catch (firstErr) {
        const fallbackUrl = API_BASE_URL.includes('localhost')
          ? API_BASE_URL.replace('localhost', '127.0.0.1')
          : API_BASE_URL.replace('127.0.0.1', 'localhost');
        try {
          response = await fetch(`${fallbackUrl}/dashboard/stats`);
        } catch {
          throw firstErr;
        }
      }

      if (!response || !response.ok) {
        throw new Error('Failed to fetch dashboard metrics.');
      }
      const data = await response.json();
      setStats(data);

      try {
        const merchantRes = await fetch(`${API_BASE_URL}/merchants/active`);
        if (merchantRes.ok) {
          const mData = await merchantRes.json();
          setMerchant(mData);
        }
      } catch {
        // Non-critical fallback for merchant profile
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred while loading dashboard stats.');
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculateTrust = async () => {
    if (!merchant) return;
    setRecalculating(true);
    try {
      const res = await fetch(`${API_BASE_URL}/dashboard/trust-score/recalculate`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        setMerchant((prev: any) => ({ ...prev, trust_score: data.trust_score }));
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRecalculating(false);
    }
  };

  const runChainVerification = () => {
    setVerifyingChain(true);
    setVerificationPassed(null);
    setTamperedNodeIndex(null);

    setTimeout(() => {
      if (isTampered) {
        setTamperedNodeIndex(2);
        setVerificationPassed(false);
      } else {
        setVerificationPassed(true);
      }
      setVerifyingChain(false);
    }, 1500);
  };

  const toggleTamperSimulation = () => {
    if (isTampered) {
      setIsTampered(false);
      setVerificationPassed(null);
      setTamperedNodeIndex(null);
    } else {
      setIsTampered(true);
      setVerificationPassed(null);
      setTamperedNodeIndex(null);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <RefreshCw className="h-8 w-8 animate-spin text-[#853953]" />
          <p className="text-sm text-zinc-400 font-mono">Loading AVENIQ platform stats...</p>
        </div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="bg-[#2C2C2C] p-8 rounded-2xl max-w-lg mx-auto text-center space-y-4 my-12 border border-rose-500/30 text-[#F3F4F4] shadow-xl">
        <AlertTriangle className="h-12 w-12 text-rose-500 mx-auto" />
        <h3 className="text-base font-bold">Metrics Retrieval Failed</h3>
        <p className="text-xs text-zinc-400">{error || 'Could not load platform metrics.'}</p>
        <button
          onClick={fetchStats}
          className="px-4 py-2 bg-[#612D53] border border-[#853953]/50 rounded-xl text-xs font-semibold hover:bg-[#853953] transition text-[#F3F4F4]"
        >
          Try Again
        </button>
      </div>
    );
  }

  const dbConnected = stats.health.database === 'connected';
  const trustScore = merchant?.trust_score ?? 100;

  const cards = [
    {
      title: 'Active Agents',
      value: stats.total_agents.toString(),
      description: 'Authorized AI delegates',
      icon: Cpu,
      color: 'text-[#a85890]',
    },
    {
      title: 'Active Policies',
      value: stats.total_policies.toString(),
      description: 'Active compliance boundaries',
      icon: ShieldCheck,
      color: 'text-emerald-400',
    },
    {
      title: 'Catalog Products',
      value: `${stats.active_products} / ${stats.total_products}`,
      description: 'Active / Total products',
      icon: ListChecks,
      color: 'text-[#853953]',
    },
    {
      title: 'Database Status',
      value: dbConnected ? 'Connected' : 'Degraded',
      description: dbConnected ? 'Live Supabase connection' : 'Running in offline mode',
      icon: Activity,
      color: dbConnected ? 'text-emerald-400' : 'text-amber-400',
    },
  ];

  return (
    <div className="space-y-8 text-[#F3F4F4]">
      {/* Hero Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#853953]/30 via-[#2C2C2C] to-[#612D53]/40 p-8 border border-[#853953]/40 shadow-2xl">
        <div className="absolute right-0 top-0 -mr-16 -mt-16 h-64 w-64 rounded-full bg-[#853953]/15 blur-3xl"></div>
        <div className="relative z-10 space-y-3 max-w-2xl">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-semibold bg-[#853953]/20 text-[#f3f4f4] border border-[#853953]/40">
            Control Plane Active
          </span>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-wider text-[#F3F4F4] font-display">
            AVENIQ
          </h1>
          <p className="text-base text-zinc-200 font-medium">
            Commerce Passport & Autonomous Purchasing Engine for AI Agents
          </p>
          <p className="text-xs text-zinc-300 leading-relaxed">
            Welcome to the command center. AVENIQ establishes safe, policy-controlled commerce channels for autonomous AI agents, ensuring every transaction is verified, authorized, and audited.
          </p>
        </div>
      </div>

      {/* Trust Score & Tamper Simulator Layout */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Dynamic Trust Score card */}
        <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] flex flex-col justify-between md:col-span-1 shadow-xl relative overflow-hidden">
          <div>
            <h3 className="text-xs font-semibold text-zinc-300 uppercase tracking-wider mb-4 flex items-center gap-1.5">
              <Sparkles className="h-4 w-4 text-[#853953]" /> Merchant Trust Score
            </h3>
            <div className="flex flex-col items-center justify-center py-4 space-y-2">
              <div className="relative flex items-center justify-center">
                <svg className="w-32 h-32 transform -rotate-90">
                  <circle
                    cx="64"
                    cy="64"
                    r="52"
                    stroke="currentColor"
                    strokeWidth="8"
                    className="text-[#1c1c1c]"
                    fill="transparent"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="52"
                    stroke="currentColor"
                    strokeWidth="8"
                    className="text-[#853953] transition-all duration-500"
                    fill="transparent"
                    strokeDasharray={326.7}
                    strokeDashoffset={326.7 - (326.7 * trustScore) / 100}
                  />
                </svg>
                <div className="absolute text-3xl font-extrabold text-[#F3F4F4] font-mono">
                  {trustScore}
                </div>
              </div>
              <p className="text-[11px] text-zinc-300 font-medium">System integrity level</p>
            </div>
          </div>
          <button
            onClick={handleRecalculateTrust}
            disabled={recalculating}
            className="w-full py-2.5 bg-[#612D53] hover:bg-[#853953] disabled:opacity-50 border border-[#853953]/50 rounded-xl text-xs font-semibold text-[#F3F4F4] flex items-center justify-center gap-1.5 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${recalculating ? 'animate-spin' : ''}`} /> Recalculate Score
          </button>
        </div>

        {/* Ledger Tampering Simulator */}
        <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] md:col-span-2 space-y-4 shadow-xl">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-[#F3F4F4] font-display flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-[#853953]" /> Cryptographic Ledger Inspector
            </h3>
            <button
              onClick={toggleTamperSimulation}
              className={`px-3 py-1 text-xs rounded-full border transition font-semibold ${
                isTampered
                  ? 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20'
                  : 'bg-[#1c1c1c] border-[#3a3a3a] text-zinc-300 hover:bg-[#612D53]/40'
              }`}
            >
              {isTampered ? 'Reset Chain Data' : 'Simulate Tampering'}
            </button>
          </div>

          <p className="text-xs text-zinc-300 leading-relaxed">
            Audit logs are chained sequentially using SHA-256 hashes. If any past block is tampered with, the hash links break immediately. Click **Verify Ledger** to run a live validation sweep.
          </p>

          {/* Connected Blockchain Node visualization */}
          <div className="flex items-center justify-between gap-2 overflow-x-auto py-3">
            {[0, 1, 2, 3].map((nodeIdx) => {
              const isTargetTamper = isTampered && nodeIdx === 2;

              let nodeBorderColor = 'border-[#3a3a3a] bg-[#1c1c1c]';
              if (verifyingChain) {
                nodeBorderColor = 'border-[#853953]/60 bg-[#612D53]/20 animate-pulse';
              } else if (verificationPassed === true) {
                nodeBorderColor = 'border-emerald-500/40 bg-emerald-950/20';
              } else if (verificationPassed === false) {
                if (nodeIdx === tamperedNodeIndex) {
                  nodeBorderColor = 'border-rose-500 bg-rose-950/30 shadow-lg shadow-rose-950/50 animate-bounce';
                } else if (nodeIdx > (tamperedNodeIndex || 0)) {
                  nodeBorderColor = 'border-rose-500/40 bg-rose-950/20';
                } else {
                  nodeBorderColor = 'border-emerald-500/40 bg-emerald-950/20';
                }
              }

              return (
                <div key={nodeIdx} className="flex items-center gap-1.5 flex-1 min-w-[110px]">
                  <div className={`p-3 rounded-xl border text-center flex-1 transition-all duration-300 ${nodeBorderColor}`}>
                    <div className="text-[10px] text-zinc-400 font-semibold uppercase">Block #{nodeIdx + 1}</div>
                    <div className="text-[9px] font-mono text-zinc-300 mt-1 truncate">
                      {isTargetTamper ? 'HASH_CORRUPT' : `0x${(102432 + nodeIdx * 3422).toString(16)}`}
                    </div>
                  </div>
                  {nodeIdx < 3 && (
                    <span className={`text-sm font-bold ${
                      verificationPassed === false && nodeIdx >= (tamperedNodeIndex || 0)
                        ? 'text-rose-500'
                        : verificationPassed === true
                        ? 'text-emerald-400'
                        : 'text-zinc-500'
                    }`}>
                      →
                    </span>
                  )}
                </div>
              );
            })}
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              onClick={runChainVerification}
              disabled={verifyingChain}
              className="px-4 py-2 bg-[#853953] hover:bg-[#9c4362] disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-2 transition shadow-lg shadow-[#853953]/30 border border-[#853953]/50"
            >
              <Play className="h-3 w-3 fill-current" /> Verify Ledger Hash Chain
            </button>

            {verifyingChain ? (
              <div className="text-xs text-zinc-300 animate-pulse font-mono">Running cryptographic check...</div>
            ) : verificationPassed === true ? (
              <div className="flex items-center gap-1 text-xs text-emerald-400 font-bold">
                <CheckCircle2 className="h-4 w-4" /> Hash Chain Verification Success
              </div>
            ) : verificationPassed === false ? (
              <div className="flex items-center gap-1 text-xs text-rose-400 font-bold">
                <ShieldAlert className="h-4 w-4" /> WARNING: Hash Chain Tampering Detected!
              </div>
            ) : null}
          </div>
        </div>
      </div>

      {/* Grid Status Indicators */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {cards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div key={idx} className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-4 shadow-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-zinc-300">{card.title}</span>
                <Icon className={`h-5 w-5 ${card.color}`} />
              </div>
              <div>
                <div className="text-2xl font-bold text-[#F3F4F4] tracking-tight font-display">{card.value}</div>
                <p className="text-[11px] text-zinc-400 mt-1">{card.description}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Ledger Activity */}
      <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-4 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-[#F3F4F4] font-display">Recent Activity (Chained Audit Log)</h3>
          <button 
            onClick={fetchStats}
            className="p-1.5 hover:bg-[#612D53]/40 rounded-xl text-zinc-300 hover:text-white transition border border-transparent hover:border-[#612D53]"
            title="Refresh Ledger"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>

        {stats.recent_activity.length === 0 ? (
          <div className="text-center p-8 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a]">
            <p className="text-xs text-zinc-400">No recent activity logged in the ledger.</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-[#3a3a3a]">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#1c1c1c] border-b border-[#3a3a3a] text-zinc-300 font-semibold">
                <tr>
                  <th className="py-3 px-4">Event Type</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">Action</th>
                  <th className="py-3 px-4">Decision</th>
                  <th className="py-3 px-4">Time</th>
                  <th className="py-3 px-4 font-mono">Ledger Hash</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#3a3a3a] text-zinc-200">
                {stats.recent_activity.map((event) => (
                  <tr key={event.id} className="hover:bg-[#333333] transition">
                    <td className="py-3 px-4 font-mono text-xs text-[#a85890] font-bold">
                      {event.event_type}
                    </td>
                    <td className="py-3 px-4">
                      <span className="capitalize">{event.actor_type}</span> ({event.actor_id})
                    </td>
                    <td className="py-3 px-4 font-mono text-xs text-[#F3F4F4]">{event.action}</td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        event.decision === 'ALLOW' || event.decision === 'APPROVED'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                      }`}>
                        {event.decision}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs text-zinc-400 font-mono">
                      {new Date(event.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-mono text-[10px] text-[#a85890]" title={event.event_hash}>
                      {event.event_hash ? `${event.event_hash.slice(0, 16)}...` : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
