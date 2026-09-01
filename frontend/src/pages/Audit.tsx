import { useEffect, useState } from 'react';
import { History, ShieldCheck, ShieldAlert, RefreshCw, Eye, Search, XCircle } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

interface AuditEvent {
  id: string;
  merchant_id: string;
  agent_id: string | null;
  request_id: string | null;
  event_type: string;
  actor_type: string;
  actor_id: string;
  entity_type: string;
  entity_id: string | null;
  action: string;
  decision: string;
  details: any;
  created_at: string;
  prev_hash: string | null;
  event_hash: string;
}

interface IntegrityVerification {
  is_valid: boolean;
  total_events: number;
  tampered_event_id: string | null;
  reason: string;
}

export default function Audit() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [verification, setVerification] = useState<IntegrityVerification | null>(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [tampering, setTampering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [isTamperedDemo, setIsTamperedDemo] = useState(false);

  const fetchAuditData = async () => {
    setLoading(true);
    setError(null);
    try {
      const eventsRes = await fetch(`${API_BASE_URL}/audit/events`);
      if (!eventsRes.ok) throw new Error('Failed to load cryptographic audit ledger.');
      const eventsData = await eventsRes.json();
      setEvents(eventsData);

      const verifyRes = await fetch(`${API_BASE_URL}/audit/verify`);
      if (verifyRes.ok) {
        const verifyData = await verifyRes.json();
        setVerification({
          is_valid: verifyData.valid ?? verifyData.is_valid ?? true,
          total_events: verifyData.total_blocks ?? verifyData.total_events ?? eventsData.length,
          tampered_event_id: verifyData.event_id || verifyData.tampered_event_id || null,
          reason: verifyData.reason || 'Cryptographic SHA-256 hash mismatch detected in audit chain.'
        });
        setIsTamperedDemo(!!verifyData.tamper_simulation_active);
      }
    } catch (err: any) {
      setError(err.message || 'Error retrieving audit ledger');
    } finally {
      setLoading(false);
    }
  };

  const verifyLedger = async () => {
    setVerifying(true);
    try {
      const verifyRes = await fetch(`${API_BASE_URL}/audit/verify`);
      if (verifyRes.ok) {
        const verifyData = await verifyRes.json();
        setVerification({
          is_valid: verifyData.valid ?? verifyData.is_valid ?? true,
          total_events: verifyData.total_blocks ?? verifyData.total_events ?? events.length,
          tampered_event_id: verifyData.event_id || verifyData.tampered_event_id || null,
          reason: verifyData.reason || 'Cryptographic SHA-256 hash mismatch detected in audit chain.'
        });
        setIsTamperedDemo(!!verifyData.tamper_simulation_active);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setVerifying(false);
    }
  };

  const toggleTamperDemo = async () => {
    setTampering(true);
    try {
      const targetState = !isTamperedDemo;
      const res = await fetch(`${API_BASE_URL}/audit/simulate-tamper?tamper=${targetState}`, {
        method: 'POST'
      });
      if (res.ok) {
        const data = await res.json();
        const verifyData = data.verification_result || {};
        setVerification({
          is_valid: verifyData.valid ?? verifyData.is_valid ?? !targetState,
          total_events: verifyData.total_blocks ?? verifyData.total_events ?? events.length,
          tampered_event_id: verifyData.event_id || verifyData.tampered_event_id || (events[1]?.id || 'evt_tampered_002'),
          reason: verifyData.reason || 'HASH_MISMATCH: Computed SHA256(Block #2) does not match stored prev_hash in Block #3.'
        });
        setIsTamperedDemo(targetState);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setTampering(false);
    }
  };

  useEffect(() => {
    fetchAuditData();
  }, []);

  const filteredEvents = events.filter((e) => {
    const term = searchTerm.toLowerCase();
    return (
      e.event_type.toLowerCase().includes(term) ||
      e.actor_id.toLowerCase().includes(term) ||
      e.action.toLowerCase().includes(term) ||
      e.event_hash.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-8 text-[#F3F4F4]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold font-display text-[#F3F4F4] flex items-center gap-2">
            <History className="h-7 w-7 text-[#853953]" /> Cryptographic Audit Ledger
          </h2>
          <p className="text-xs text-zinc-300 mt-1">
            Immutable SHA-256 hash-chained event logs for all agent proposals, governance checks, and Razorpay transactions.
          </p>
        </div>

        <button
          onClick={fetchAuditData}
          className="flex items-center space-x-2 px-4 py-2 bg-[#612D53]/40 hover:bg-[#612D53]/80 border border-[#612D53] rounded-xl text-xs font-semibold text-[#F3F4F4] transition self-start sm:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-950/30 border border-rose-500 text-rose-300 rounded-2xl text-xs">
          {error}
        </div>
      )}

      {/* Ledger Verification Banner */}
      {verification && (
        <div className={`p-6 rounded-2xl border transition-all duration-300 shadow-xl ${
          verification.is_valid
            ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-400'
            : 'bg-rose-950/30 border-rose-500 text-rose-300'
        }`}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-start space-x-3">
              {verification.is_valid ? (
                <ShieldCheck className="h-7 w-7 text-emerald-400 flex-shrink-0 mt-0.5" />
              ) : (
                <ShieldAlert className="h-7 w-7 text-rose-500 flex-shrink-0 mt-0.5 animate-bounce" />
              )}
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold font-display text-[#F3F4F4]">
                    Ledger Status: {verification.is_valid ? 'VALID (CRYPTOGRAPHICALLY VERIFIED)' : 'CORRUPTED (HASH MISMATCH)'}
                  </h3>
                  <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                    verification.is_valid ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                  }`}>
                    {verification.total_events} Chained Events
                  </span>
                </div>
                <p className="text-xs text-zinc-300">
                  {verification.is_valid
                    ? 'All historical blocks verified cleanly. Hash pointer integrity score: 100%.'
                    : verification.reason}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={verifyLedger}
                disabled={verifying || tampering}
                className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-[#853953] hover:bg-[#9c4362] text-white font-bold text-xs border border-[#853953]/50 transition flex items-center justify-center space-x-2 shadow-lg shadow-[#853953]/30"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${verifying ? 'animate-spin' : ''}`} />
                <span>Verify Ledger</span>
              </button>

              <button
                onClick={toggleTamperDemo}
                disabled={verifying || tampering}
                className={`w-full sm:w-auto px-4 py-2.5 rounded-xl text-xs font-semibold border transition ${
                  isTamperedDemo
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
                    : 'bg-[#612D53]/40 border-[#612D53] text-[#F3F4F4] hover:bg-[#612D53]'
                }`}
              >
                {isTamperedDemo ? 'Restore Original Hash Chain' : 'Simulate Hash Tampering'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filter and Search */}
      <div className="relative w-full max-w-md">
        <Search className="absolute left-3.5 top-3 h-4 w-4 text-zinc-400" />
        <input
          type="text"
          placeholder="Filter by event type, actor ID, action..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full bg-[#2C2C2C] border border-[#3a3a3a] rounded-xl pl-10 pr-4 py-2.5 text-xs text-[#F3F4F4] placeholder-zinc-400 focus:outline-none focus:border-[#853953]"
        />
      </div>

      {/* Events Table */}
      {loading ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] flex flex-col items-center justify-center space-y-4 shadow-xl">
          <RefreshCw className="h-8 w-8 text-[#853953] animate-spin" />
          <p className="text-xs text-zinc-400 font-mono">Fetching SHA-256 block records...</p>
        </div>
      ) : filteredEvents.length === 0 ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] text-center space-y-3 shadow-xl">
          <History className="h-10 w-10 text-[#853953] mx-auto opacity-60" />
          <p className="text-xs text-zinc-300">No matching audit events logged in ledger.</p>
        </div>
      ) : (
        <div className="bg-[#2C2C2C] rounded-2xl border border-[#3a3a3a] overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#3a3a3a] bg-[#1c1c1c] text-zinc-300 font-semibold">
                  <th className="p-4">Block / Event</th>
                  <th className="p-4">Actor</th>
                  <th className="p-4">Action</th>
                  <th className="p-4">Decision</th>
                  <th className="p-4">Timestamp</th>
                  <th className="p-4 font-mono">SHA-256 Hash</th>
                  <th className="p-4 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#3a3a3a] text-zinc-200">
                {filteredEvents.map((evt, idx) => (
                  <tr key={evt.id} className="hover:bg-[#333333] transition">
                    <td className="p-4 font-mono text-[#a85890] font-bold">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-zinc-400">#{idx + 1}</span>
                        <span>{evt.event_type}</span>
                      </div>
                    </td>
                    <td className="p-4">
                      <div className="flex flex-col">
                        <span className="font-semibold text-[#F3F4F4] capitalize">{evt.actor_type}</span>
                        <span className="text-[10px] font-mono text-zinc-400">{evt.actor_id}</span>
                      </div>
                    </td>
                    <td className="p-4 font-mono text-zinc-300">{evt.action}</td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${
                        evt.decision === 'ALLOW' || evt.decision === 'APPROVED'
                          ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                          : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                      }`}>
                        {evt.decision}
                      </span>
                    </td>
                    <td className="p-4 font-mono text-zinc-400 text-[11px]">
                      {new Date(evt.created_at).toLocaleString()}
                    </td>
                    <td className="p-4 font-mono text-[10px] text-[#a85890]" title={evt.event_hash}>
                      {evt.event_hash.slice(0, 16)}...
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => setSelectedEvent(evt)}
                        className="p-2 rounded-xl bg-[#612D53]/40 border border-[#612D53] hover:bg-[#853953] text-[#F3F4F4] transition"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Inspect Event Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-xl bg-[#2C2C2C] border border-[#3a3a3a] rounded-2xl overflow-hidden shadow-2xl space-y-4 p-6 text-[#F3F4F4]">
            <div className="flex items-center justify-between border-b border-[#3a3a3a] pb-3">
              <h3 className="text-base font-bold font-display text-[#F3F4F4]">AuditEvent Raw Payload</h3>
              <button
                onClick={() => setSelectedEvent(null)}
                className="p-1.5 rounded-xl hover:bg-[#612D53]/40 text-zinc-400 hover:text-white transition"
              >
                <XCircle className="h-5 w-5" />
              </button>
            </div>

            <pre className="bg-[#1c1c1c] p-4 rounded-xl border border-[#3a3a3a] text-xs font-mono text-[#F3F4F4] overflow-x-auto max-h-[400px]">
              {JSON.stringify(selectedEvent, null, 2)}
            </pre>

            <div className="text-right pt-2 border-t border-[#3a3a3a]">
              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 bg-[#612D53] hover:bg-[#853953] text-[#F3F4F4] text-xs font-semibold rounded-xl transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
