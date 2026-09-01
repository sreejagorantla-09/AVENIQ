import { useEffect, useState } from 'react';
import { CreditCard, RefreshCw, AlertTriangle, Search, Eye, Copy, Check, X } from 'lucide-react';
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
}

interface Agent {
  id: string;
  agent_code: string;
  name: string;
}

interface Transaction {
  id: string;
  created_at: string;
  amount: number;
  currency: string;
  status: 'pending' | 'completed' | 'failed';
  agent_id: string | null;
  agent_code: string;
  agent_name: string;
  negotiation_id: string | null;
  razorpay_order_id: string | null;
  razorpay_payment_id: string | null;
  fail_reason: string | null;
}

export default function Transactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Detail Modal states
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchTransactionsFromAudit = async () => {
    setLoading(true);
    setError(null);
    try {
      const agentsRes = await fetch(`${API_BASE_URL}/agents`);
      let agentsMap: { [id: string]: Agent } = {};
      if (agentsRes.ok) {
        const agentsData = await agentsRes.json();
        agentsData.forEach((a: Agent) => {
          agentsMap[a.id] = a;
        });
      }

      const response = await fetch(`${API_BASE_URL}/audit/events`);
      if (!response.ok) {
        throw new Error('Failed to load transaction audit ledger.');
      }
      const events: AuditEvent[] = await response.json();
      
      const txEvents = events
        .filter((e) => e.entity_type === 'transaction' && e.entity_id)
        .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());

      const txMap: { [txId: string]: Transaction } = {};

      txEvents.forEach((event) => {
        const txId = event.entity_id!;
        
        let agentCode = 'UNKNOWN_AGENT';
        let agentName = 'Autonomous Buyer Agent';
        
        const eventAgentId = event.agent_id || event.details?.agent_id;
        
        if (eventAgentId && agentsMap[eventAgentId]) {
          agentCode = agentsMap[eventAgentId].agent_code;
          agentName = agentsMap[eventAgentId].name;
        } else {
          let resolvedAgentId: string | null = null;
          
          if (event.request_id) {
            const siblingEvent = events.find(e => e.request_id === event.request_id && e.agent_id);
            if (siblingEvent) {
              resolvedAgentId = siblingEvent.agent_id;
            }
          }
          
          if (!resolvedAgentId && event.details?.negotiation_id) {
            const negoId = event.details.negotiation_id;
            const negoEvent = events.find(e => 
              (e.entity_id === negoId || (e.details && e.details.negotiation_id === negoId)) && e.agent_id
            );
            if (negoEvent) {
              resolvedAgentId = negoEvent.agent_id;
            }
          }

          if (resolvedAgentId && agentsMap[resolvedAgentId]) {
            agentCode = agentsMap[resolvedAgentId].agent_code;
            agentName = agentsMap[resolvedAgentId].name;
          } else if (Object.keys(agentsMap).length > 0) {
            const firstAgent = Object.values(agentsMap)[0];
            agentCode = firstAgent.agent_code;
            agentName = firstAgent.name;
          }
        }

        if (!txMap[txId]) {
          txMap[txId] = {
            id: txId,
            created_at: event.created_at,
            amount: 0,
            currency: 'INR',
            status: 'pending',
            agent_id: event.agent_id || eventAgentId,
            agent_code: agentCode,
            agent_name: agentName,
            negotiation_id: null,
            razorpay_order_id: null,
            razorpay_payment_id: null,
            fail_reason: null
          };
        }

        const tx = txMap[txId];

        if (event.event_type === 'TRANSACTION_CREATED') {
          tx.amount = event.details?.amount || 0;
          tx.negotiation_id = event.details?.negotiation_id || null;
          tx.status = 'pending';
        } else if (event.event_type === 'PAYMENT_CREATED') {
          tx.razorpay_order_id = event.details?.razorpay_order_id || null;
          if (!tx.amount && event.details?.amount_paise) {
            tx.amount = event.details.amount_paise / 100;
          }
        } else if (event.event_type === 'PAYMENT_VERIFIED') {
          tx.razorpay_payment_id = event.details?.razorpay_payment_id || null;
          tx.status = 'completed';
        } else if (event.event_type === 'TRANSACTION_COMPLETED') {
          tx.status = 'completed';
        } else if (event.event_type === 'TRANSACTION_FAILED') {
          tx.status = 'failed';
          tx.fail_reason = event.details?.reason || 'Payment verification failed';
        }
      });

      const txList = Object.values(txMap).sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setTransactions(txList);
    } catch (err: any) {
      setError(err.message || 'An error occurred fetching transactions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactionsFromAudit();
  }, []);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const filteredTxs = transactions.filter((tx) => {
    const term = searchTerm.toLowerCase();
    return (
      tx.id.toLowerCase().includes(term) ||
      tx.agent_code.toLowerCase().includes(term) ||
      tx.agent_name.toLowerCase().includes(term) ||
      (tx.razorpay_order_id && tx.razorpay_order_id.toLowerCase().includes(term)) ||
      (tx.razorpay_payment_id && tx.razorpay_payment_id.toLowerCase().includes(term))
    );
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
            Settled
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono">
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse font-mono">
            Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 text-[#F3F4F4]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-[#F3F4F4] font-display flex items-center gap-2">
            <CreditCard className="h-7 w-7 text-[#853953]" /> Razorpay Agent Transactions
          </h2>
          <p className="text-xs text-zinc-300 mt-1">
            Payment transactions executed and verified via Razorpay gateway.
          </p>
        </div>
        
        <button
          onClick={fetchTransactionsFromAudit}
          className="flex items-center space-x-1.5 text-xs text-[#F3F4F4] hover:text-white transition-colors bg-[#612D53]/40 hover:bg-[#612D53]/80 px-3 py-2 rounded-xl border border-[#612D53] w-fit self-end sm:self-auto font-semibold"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh List</span>
        </button>
      </div>

      {/* Filter and Search */}
      <div className="relative w-full max-w-md">
        <Search className="absolute left-3.5 top-3 h-4 w-4 text-zinc-400" />
        <input
          type="text"
          placeholder="Search by transaction ID, agent code, order ID..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full bg-[#2C2C2C] border border-[#3a3a3a] rounded-xl pl-10 pr-4 py-2.5 text-xs text-[#F3F4F4] placeholder-zinc-400 focus:outline-none focus:border-[#853953] font-sans"
        />
      </div>

      {/* Transactions Display */}
      {loading ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] flex flex-col items-center justify-center space-y-4 shadow-xl">
          <RefreshCw className="h-8 w-8 text-[#853953] animate-spin" />
          <p className="text-xs text-zinc-400 font-mono">Aggregating transactions from ledger...</p>
        </div>
      ) : error ? (
        <div className="bg-[#2C2C2C] p-8 rounded-2xl border border-rose-500/30 text-center space-y-3 shadow-xl">
          <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto" />
          <p className="text-xs text-rose-300">{error}</p>
        </div>
      ) : filteredTxs.length === 0 ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] flex flex-col items-center justify-center text-center space-y-4 shadow-xl">
          <div className="h-14 w-14 rounded-2xl bg-[#853953]/20 border border-[#853953]/40 flex items-center justify-center">
            <CreditCard className="h-7 w-7 text-[#853953]" />
          </div>
          <div className="max-w-md space-y-1">
            <h3 className="text-base font-bold text-[#F3F4F4]">No Transactions Found</h3>
            <p className="text-xs text-zinc-400">
              Transactions initiated or settled via AVENIQ's Razorpay gateway proxy will appear here once processed.
            </p>
          </div>
        </div>
      ) : (
        <div className="bg-[#2C2C2C] rounded-2xl border border-[#3a3a3a] shadow-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#3a3a3a] bg-[#1c1c1c] text-zinc-300 font-semibold">
                  <th className="px-6 py-4">Transaction ID</th>
                  <th className="px-6 py-4">Created At</th>
                  <th className="px-6 py-4">AI Agent</th>
                  <th className="px-6 py-4">Provider</th>
                  <th className="px-6 py-4">Amount</th>
                  <th className="px-6 py-4">Status</th>
                  <th className="px-6 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#3a3a3a] text-zinc-200">
                {filteredTxs.map((tx) => (
                  <tr key={tx.id} className="hover:bg-[#333333] transition">
                    <td className="px-6 py-4.5 whitespace-nowrap font-mono text-xs text-zinc-400">
                      <div className="flex items-center space-x-1.5">
                        <span>{tx.id.slice(0, 8)}...</span>
                        <button
                          onClick={() => copyToClipboard(tx.id, tx.id)}
                          className="text-zinc-400 hover:text-white p-1 rounded transition"
                          title="Copy ID"
                        >
                          {copiedId === tx.id ? (
                            <Check className="h-3 w-3 text-emerald-400" />
                          ) : (
                            <Copy className="h-3 w-3" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4.5 whitespace-nowrap text-zinc-300 text-xs font-mono">
                      {new Date(tx.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4.5 whitespace-nowrap">
                      <div className="flex flex-col">
                        <span className="font-semibold text-[#F3F4F4]">{tx.agent_name}</span>
                        <span className="text-[10px] text-[#a85890] font-mono font-bold">{tx.agent_code}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4.5 whitespace-nowrap font-semibold text-zinc-300">
                      Razorpay
                    </td>
                    <td className="px-6 py-4.5 whitespace-nowrap font-extrabold text-[#F3F4F4]">
                      ₹{tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4.5 whitespace-nowrap">
                      {getStatusBadge(tx.status)}
                    </td>
                    <td className="px-6 py-4.5 whitespace-nowrap text-right text-xs">
                      <button
                        onClick={() => setSelectedTx(tx)}
                        className="p-2 rounded-xl bg-[#612D53]/40 hover:bg-[#853953] text-[#F3F4F4] font-semibold inline-flex items-center space-x-1.5 border border-[#612D53] transition"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Inspect Transaction Modal */}
      {selectedTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-[#2C2C2C] border border-[#3a3a3a] rounded-2xl overflow-hidden shadow-2xl flex flex-col text-[#F3F4F4]">
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#3a3a3a] bg-[#1c1c1c]">
              <div className="flex items-center space-x-2">
                <CreditCard className="h-5 w-5 text-[#853953]" />
                <h3 className="text-base font-bold text-[#F3F4F4] font-display">Inspect Transaction</h3>
              </div>
              <button 
                onClick={() => setSelectedTx(null)}
                className="text-zinc-400 hover:text-white p-1 hover:bg-[#612D53]/40 rounded-xl transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-4 text-xs">
              <div className="space-y-1">
                <span className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider block">Transaction ID</span>
                <span className="font-mono text-zinc-200 block bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl p-2.5 select-all">{selectedTx.id}</span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <span className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider block">Created At</span>
                  <span className="text-zinc-300 font-mono">{new Date(selectedTx.created_at).toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider block">Status</span>
                  <span className="block mt-1">{getStatusBadge(selectedTx.status)}</span>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider block">Amount</span>
                  <span className="text-[#F3F4F4] font-extrabold text-sm">₹{selectedTx.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                </div>
                <div>
                  <span className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider block">Currency</span>
                  <span className="text-zinc-300 font-bold">INR</span>
                </div>
              </div>

              <div className="border-t border-[#3a3a3a] pt-4 space-y-3">
                <span className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider block">Agent Registry Details</span>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <span className="text-zinc-400 text-[10px]">Agent Code</span>
                    <span className="block font-mono text-xs text-[#a85890] font-bold">{selectedTx.agent_code}</span>
                  </div>
                  <div>
                    <span className="text-zinc-400 text-[10px]">Agent Name</span>
                    <span className="block text-xs text-zinc-200 font-semibold">{selectedTx.agent_name}</span>
                  </div>
                </div>
              </div>

              <div className="border-t border-[#3a3a3a] pt-4 space-y-3">
                <span className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider block">Razorpay Gateway Integration</span>
                <div className="space-y-2 font-mono">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-zinc-400">Order ID:</span>
                    <span className="text-[#a85890] font-bold">{selectedTx.razorpay_order_id || 'Not generated'}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-zinc-400">Payment ID:</span>
                    <span className="text-emerald-400 font-bold">{selectedTx.razorpay_payment_id || 'Not captured'}</span>
                  </div>
                  {selectedTx.fail_reason && (
                    <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-3 mt-2 flex items-start space-x-2 text-xs text-rose-300">
                      <AlertTriangle className="h-4 w-4 text-rose-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">Decline Reason:</span>
                        <p className="mt-0.5">{selectedTx.fail_reason}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {selectedTx.negotiation_id && (
                <div className="border-t border-[#3a3a3a] pt-4 flex items-center justify-between text-xs">
                  <span className="text-zinc-400">Negotiation Reference:</span>
                  <span className="font-mono text-[#a85890] font-bold flex items-center space-x-1">
                    <span>{selectedTx.negotiation_id.slice(0, 8)}...</span>
                  </span>
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-[#3a3a3a] bg-[#1c1c1c] text-right">
              <button
                onClick={() => setSelectedTx(null)}
                className="bg-[#612D53] hover:bg-[#853953] text-[#F3F4F4] px-4 py-2 rounded-xl text-xs font-semibold transition"
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
