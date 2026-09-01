import { useEffect, useState } from 'react';
import { MessageSquareCode, RefreshCw, AlertTriangle, ShieldCheck, Tag, ShoppingCart, TrendingDown, Clock, Cpu } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

interface Message {
  role: 'agent' | 'vendor';
  content: string;
}

interface NegotiationSession {
  id: string;
  request_id: string;
  merchant_id: string;
  agent_id: string;
  status: 'active' | 'accepted' | 'declined';
  sku: string;
  quantity: number;
  original_price: number;
  counter_offer_price: number;
  messages: Message[];
  created_at: string;
  updated_at: string;
  agent_requests?: {
    agent_code: string;
    raw_request: string;
  };
}

export default function Negotiation() {
  const [sessions, setSessions] = useState<NegotiationSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<NegotiationSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/negotiations`);
      if (!res.ok) {
        throw new Error('Failed to retrieve active negotiation sessions.');
      }
      const data = await res.json();
      setSessions(data);
      if (data.length > 0 && !selectedSession) {
        setSelectedSession(data[0]);
      } else if (selectedSession) {
        const updated = data.find((s: NegotiationSession) => s.id === selectedSession.id);
        if (updated) setSelectedSession(updated);
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred fetching negotiations.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'accepted':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'declined':
        return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
      default:
        return 'bg-[#853953]/20 text-[#a85890] border-[#853953]/40 animate-pulse';
    }
  };

  const getSavingsPercentage = (original: number, counter: number) => {
    if (original <= 0) return 0;
    const diff = original - counter;
    return ((diff / original) * 100).toFixed(1);
  };

  return (
    <div className="space-y-6 text-[#F3F4F4]">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-[#F3F4F4] font-display flex items-center gap-2">
            <MessageSquareCode className="h-7 w-7 text-[#853953]" /> Inter-Agent AI Bargaining & Negotiations
          </h2>
          <p className="text-xs text-zinc-300 mt-1">
            Real-time discount negotiations, volume checks, and counter-offer sequences.
          </p>
        </div>
        <button
          onClick={fetchSessions}
          className="flex items-center space-x-2 px-4 py-2 bg-[#612D53]/40 hover:bg-[#612D53]/80 text-[#F3F4F4] rounded-xl border border-[#612D53] transition text-xs font-semibold"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Sync logs</span>
        </button>
      </div>

      {loading && sessions.length === 0 ? (
        <div className="flex justify-center items-center h-64">
          <RefreshCw className="h-8 w-8 text-[#853953] animate-spin" />
        </div>
      ) : error ? (
        <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-rose-500/30 text-center space-y-4 shadow-xl">
          <AlertTriangle className="h-10 w-10 text-rose-400 mx-auto" />
          <p className="text-[#F3F4F4] font-medium text-sm">{error}</p>
          <p className="text-xs text-zinc-400">Please verify backend database connectivity.</p>
        </div>
      ) : sessions.length === 0 ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] flex flex-col items-center justify-center text-center space-y-4 shadow-xl">
          <div className="h-14 w-14 rounded-2xl bg-[#853953]/20 border border-[#853953]/40 flex items-center justify-center">
            <MessageSquareCode className="h-7 w-7 text-[#853953]" />
          </div>
          <div className="max-w-md space-y-1">
            <h3 className="text-base font-bold text-[#F3F4F4]">No Active Negotiations</h3>
            <p className="text-xs text-zinc-400">
              Pricing negotiations, volume discount bargaining, and counter-offer transcripts will appear here once initiated.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sidebar queue */}
          <div className="lg:col-span-4 space-y-3 max-h-[600px] overflow-y-auto pr-1">
            {sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => setSelectedSession(session)}
                className={`p-4 rounded-2xl cursor-pointer border transition flex flex-col justify-between space-y-3 shadow-xl ${
                  selectedSession?.id === session.id
                    ? 'border-[#853953] bg-[#612D53]/20'
                    : 'border-[#3a3a3a] hover:border-[#612D53] bg-[#2C2C2C]'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1c1c1c] text-[#a85890] flex items-center gap-1 border border-[#3a3a3a] font-bold">
                    <Cpu className="h-3 w-3 text-[#853953]" />
                    {session.agent_requests?.agent_code || 'AGENT'}
                  </span>
                  <span className={`text-[9px] uppercase tracking-wider font-bold border px-2 py-0.5 rounded-full ${getStatusColor(session.status)}`}>
                    {session.status}
                  </span>
                </div>
                
                <div>
                  <h4 className="text-xs font-bold text-[#F3F4F4] font-mono">SKU: {session.sku}</h4>
                  <p className="text-xs text-zinc-300 truncate mt-1">"{session.agent_requests?.raw_request}"</p>
                </div>

                <div className="flex items-center justify-between border-t border-[#3a3a3a] pt-2 text-xs">
                  <span className="text-zinc-400 text-[11px]">Qty: {session.quantity}</span>
                  <span className="font-bold text-[#F3F4F4]">
                    Counter: ₹{session.counter_offer_price.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Chat details panel */}
          <div className="lg:col-span-8 space-y-6">
            {selectedSession && (
              <div className="bg-[#2C2C2C] rounded-2xl border border-[#3a3a3a] flex flex-col min-h-[500px] shadow-xl">
                {/* Header */}
                <div className="p-4 border-b border-[#3a3a3a] flex items-center justify-between bg-[#1c1c1c] rounded-t-2xl">
                  <div>
                    <h3 className="text-base font-bold text-[#F3F4F4] font-display">Negotiation Transcript</h3>
                    <p className="text-xs text-zinc-400 mt-0.5 font-mono">Session ID: {selectedSession.id}</p>
                  </div>
                  <span className={`text-xs uppercase tracking-wider font-bold border px-2.5 py-1 rounded-full ${getStatusColor(selectedSession.status)}`}>
                    {selectedSession.status}
                  </span>
                </div>

                {/* Metrics Row */}
                <div className="grid grid-cols-3 gap-4 p-4 border-b border-[#3a3a3a] bg-[#1c1c1c]">
                  <div className="p-3.5 rounded-xl bg-[#2C2C2C] border border-[#3a3a3a] flex flex-col justify-center space-y-1">
                    <span className="text-[10px] uppercase text-zinc-400 font-semibold tracking-wider flex items-center gap-1">
                      <Tag className="h-3 w-3 text-zinc-400" /> Catalog Price
                    </span>
                    <span className="text-sm font-extrabold text-zinc-200">₹{selectedSession.original_price.toFixed(2)}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-[#2C2C2C] border border-[#3a3a3a] flex flex-col justify-center space-y-1">
                    <span className="text-[10px] uppercase text-zinc-400 font-semibold tracking-wider flex items-center gap-1">
                      <ShoppingCart className="h-3 w-3 text-[#853953]" /> Counter Offer
                    </span>
                    <span className="text-sm font-extrabold text-[#a85890]">₹{selectedSession.counter_offer_price.toFixed(2)}</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-[#2C2C2C] border border-[#3a3a3a] flex flex-col justify-center space-y-1">
                    <span className="text-[10px] uppercase text-zinc-400 font-semibold tracking-wider flex items-center gap-1">
                      <TrendingDown className="h-3 w-3 text-emerald-400" /> Savings
                    </span>
                    <span className="text-sm font-extrabold text-emerald-400">
                      -{getSavingsPercentage(selectedSession.original_price, selectedSession.counter_offer_price)}%
                    </span>
                  </div>
                </div>

                {/* Chat window */}
                <div className="flex-1 p-6 space-y-4 overflow-y-auto max-h-[300px]">
                  {selectedSession.messages && selectedSession.messages.map((msg, i) => (
                    <div
                      key={i}
                      className={`flex ${msg.role === 'agent' ? 'justify-start' : 'justify-end'}`}
                    >
                      <div className={`max-w-md p-4 rounded-2xl text-xs border ${
                        msg.role === 'agent'
                          ? 'bg-[#1c1c1c] text-zinc-200 border-[#3a3a3a] rounded-bl-none'
                          : 'bg-[#612D53]/30 text-[#F3F4F4] border-[#853953]/40 rounded-br-none'
                      }`}>
                        <div className="flex items-center gap-1 text-[10px] font-semibold text-zinc-400 mb-1">
                          <Cpu className="h-3 w-3" />
                          <span>{msg.role === 'agent' ? 'Buyer Agent' : 'Vendor Bot (AVENIQ)'}</span>
                        </div>
                        <p className="leading-relaxed">{msg.content}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Crypto ledger linkage footer */}
                <div className="p-4 border-t border-[#3a3a3a] bg-[#1c1c1c] rounded-b-2xl space-y-2">
                  <div className="flex items-center space-x-1.5 text-xs text-emerald-400 font-semibold">
                    <ShieldCheck className="h-4 w-4" />
                    <span>Cryptographic Audit Proof Link</span>
                  </div>
                  <div className="text-[10px] font-mono text-zinc-300 break-all space-y-1 bg-[#2C2C2C] p-3 rounded-xl border border-[#3a3a3a]">
                    <div>Session Hash Root: SHA256({selectedSession.id})</div>
                    <div className="flex items-center gap-2 mt-1">
                      <Clock className="h-3 w-3 text-zinc-400" />
                      <span className="text-zinc-400">Chained Steps: NEGOTIATION_STARTED → POLICY_CHECKED → COUNTER_OFFER_MADE</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
