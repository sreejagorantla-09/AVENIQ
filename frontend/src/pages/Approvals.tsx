import { useEffect, useState } from 'react';
import { ShieldAlert, CheckCircle, RefreshCw, AlertTriangle, Clock, Check, X } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

interface ApprovalRequest {
  id: string;
  agent_id: string;
  agent_code: string;
  agent_name: string;
  proposal_id: string;
  amount: number;
  currency: string;
  reason: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  risk_score: number;
  created_at: string;
}

export default function Approvals() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [submittingId, setSubmittingId] = useState<string | null>(null);

  const fetchApprovals = async () => {
    setLoading(true);
    setError(null);
    try {
      let response: Response | null = null;
      try {
        response = await fetch(`${API_BASE_URL}/approvals/pending`);
      } catch (firstErr) {
        const fallbackUrl = API_BASE_URL.includes('localhost')
          ? API_BASE_URL.replace('localhost', '127.0.0.1')
          : API_BASE_URL.replace('127.0.0.1', 'localhost');
        try {
          response = await fetch(`${fallbackUrl}/approvals/pending`);
        } catch {
          throw firstErr;
        }
      }

      if (!response || !response.ok) {
        throw new Error('Failed to load pending approval requests.');
      }
      const data = await response.json();
      setApprovals(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'An error occurred.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApprovals();
  }, []);

  const handleDecision = async (id: string, decision: 'APPROVE' | 'REJECT') => {
    setSubmittingId(id);
    try {
      const endpoint = decision === 'APPROVE' ? 'approve' : 'reject';
      const res = await fetch(`${API_BASE_URL}/approvals/${id}/${endpoint}`, {
        method: 'POST',
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `Failed to ${decision.toLowerCase()} request.`);
      }

      fetchApprovals();
      if (selectedApproval?.id === id) {
        setSelectedApproval(null);
      }
    } catch (err: any) {
      alert(err.message || 'Action failed.');
    } finally {
      setSubmittingId(null);
    }
  };

  const getRiskBadge = (score: number) => {
    if (score >= 75) {
      return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">High Risk ({score})</span>;
    } else if (score >= 40) {
      return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">Medium Risk ({score})</span>;
    }
    return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Low Risk ({score})</span>;
  };

  return (
    <div className="space-y-6 text-[#F3F4F4]">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold font-display text-[#F3F4F4] flex items-center gap-2">
            <ShieldAlert className="h-7 w-7 text-[#853953]" /> Human-in-the-Loop Approvals Queue
          </h2>
          <p className="text-xs text-zinc-300 mt-1">
            Review agent procurement proposals that trigger policy thresholds prior to Razorpay checkout settlement.
          </p>
        </div>

        <button
          onClick={fetchApprovals}
          className="flex items-center gap-2 px-4 py-2 bg-[#612D53]/40 border border-[#612D53] rounded-xl text-xs font-semibold text-[#F3F4F4] hover:bg-[#612D53]/80 transition self-start sm:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Queue</span>
        </button>
      </div>

      {/* Grid Display */}
      {loading ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] flex flex-col items-center justify-center space-y-4 shadow-xl">
          <RefreshCw className="h-8 w-8 text-[#853953] animate-spin" />
          <p className="text-xs text-zinc-400 font-mono">Fetching pending approval proposals...</p>
        </div>
      ) : error ? (
        <div className="bg-[#2C2C2C] p-8 rounded-2xl border border-rose-500/30 text-center space-y-3 shadow-xl">
          <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto" />
          <p className="text-xs text-rose-300">{error}</p>
        </div>
      ) : approvals.length === 0 ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] text-center space-y-4 shadow-xl">
          <CheckCircle className="h-10 w-10 text-emerald-400 mx-auto opacity-80" />
          <h3 className="text-base font-bold text-[#F3F4F4]">Approvals Queue Clean</h3>
          <p className="text-xs text-zinc-400 max-w-sm mx-auto">No pending agent purchase proposals currently require human authorization.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((req) => (
            <div key={req.id} className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl">
              <div className="space-y-2 max-w-xl">
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1c1c1c] text-[#a85890] font-bold border border-[#3a3a3a]">
                    {req.agent_code}
                  </span>
                  <h3 className="text-base font-bold text-[#F3F4F4] font-display">{req.agent_name}</h3>
                  {getRiskBadge(req.risk_score)}
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed font-mono">
                  Reason: {req.reason}
                </p>
                <div className="text-xs text-zinc-400 flex items-center gap-3 pt-1">
                  <span>Proposal ID: {req.proposal_id.slice(0, 8)}...</span>
                  <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {new Date(req.created_at).toLocaleString()}</span>
                </div>
              </div>

              <div className="flex items-center justify-between md:justify-end gap-3 pt-3 md:pt-0 border-t md:border-t-0 border-[#3a3a3a]">
                <div className="text-right mr-4 hidden sm:block">
                  <span className="text-[10px] text-zinc-400 block uppercase">Requested Amount</span>
                  <span className="text-lg font-extrabold text-[#F3F4F4] font-mono">₹{req.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleDecision(req.id, 'REJECT')}
                    disabled={submittingId === req.id}
                    className="flex items-center gap-1.5 px-3 py-2 bg-rose-950/40 border border-rose-800 hover:bg-rose-900 text-rose-300 rounded-xl text-xs font-bold transition disabled:opacity-50"
                  >
                    <X className="h-4 w-4" /> Reject
                  </button>

                  <button
                    onClick={() => handleDecision(req.id, 'APPROVE')}
                    disabled={submittingId === req.id}
                    className="flex items-center gap-1.5 px-4 py-2 bg-[#853953] hover:bg-[#9c4362] text-white rounded-xl text-xs font-bold transition shadow-lg shadow-[#853953]/30 border border-[#853953]/50 disabled:opacity-50"
                  >
                    <Check className="h-4 w-4" /> Approve Order
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
