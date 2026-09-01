import { useEffect, useState } from 'react';
import { ShieldCheck, Plus, Search, Edit, RefreshCw, AlertTriangle, X, Code } from 'lucide-react';
import { API_BASE_URL, safeFetch } from '../config/api';

interface GovernancePolicy {
  id: string;
  merchant_id: string;
  name?: string;
  policy_name?: string;
  description: string | null;
  policy_type: string;
  rules: any;
  is_active: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export default function Policies() {
  const [policies, setPolicies] = useState<GovernancePolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Modal states
  const [isOpen, setIsOpen] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState<GovernancePolicy | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    policy_type: 'SPENDING_LIMIT',
    rulesJson: '{\n  "max_amount": 50000,\n  "require_approval_above": 25000\n}',
    is_active: true,
    priority: 10,
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchPolicies = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await safeFetch(`${API_BASE_URL}/policies`);
      if (!response || !response.ok) throw new Error('Failed to fetch governance policies.');
      const data = await response.json();
      setPolicies(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Error loading policies.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, []);

  const handleOpenAdd = () => {
    setEditingPolicy(null);
    setFormData({
      name: '',
      description: '',
      policy_type: 'SPENDING_LIMIT',
      rulesJson: '{\n  "max_amount": 50000,\n  "require_approval_above": 25000\n}',
      is_active: true,
      priority: 10,
    });
    setFormError(null);
    setIsOpen(true);
  };

  const handleOpenEdit = (p: GovernancePolicy) => {
    setEditingPolicy(p);
    setFormData({
      name: p.policy_name || p.name || '',
      description: p.description || '',
      policy_type: p.policy_type || 'SPENDING_LIMIT',
      rulesJson: JSON.stringify(p.rules || {}, null, 2),
      is_active: p.is_active,
      priority: p.priority || 10,
    });
    setFormError(null);
    setIsOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);

    let parsedRules = {};
    try {
      parsedRules = JSON.parse(formData.rulesJson);
    } catch (err) {
      setFormError('Invalid JSON format in policy rules structure.');
      setFormSubmitting(false);
      return;
    }

    const payload = {
      name: formData.name.trim(),
      policy_name: formData.name.trim(),
      description: formData.description.trim() || null,
      policy_type: formData.policy_type,
      rules: parsedRules,
      is_active: formData.is_active,
      priority: Number(formData.priority),
    };

    try {
      const url = editingPolicy
        ? `${API_BASE_URL}/policies/${editingPolicy.id}`
        : `${API_BASE_URL}/policies`;
      const method = editingPolicy ? 'PUT' : 'POST';

      const res = await safeFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to save governance policy.');
      }

      setIsOpen(false);
      fetchPolicies();
    } catch (err: any) {
      setFormError(err.message || 'An error occurred.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const togglePolicyStatus = async (policy: GovernancePolicy) => {
    try {
      const res = await safeFetch(`${API_BASE_URL}/policies/${policy.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...policy,
          is_active: !policy.is_active,
        }),
      });
      if (!res.ok) throw new Error('Failed to update status.');
      fetchPolicies();
    } catch (err: any) {
      alert(err.message || 'Status toggle failed.');
    }
  };

  const filteredPolicies = policies.filter((p) => {
    const pName = p.policy_name || p.name || '';
    const pType = p.policy_type || '';
    const pDesc = p.description || '';
    const term = searchTerm.toLowerCase();
    return (
      pName.toLowerCase().includes(term) ||
      pType.toLowerCase().includes(term) ||
      pDesc.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6 text-[#F3F4F4]">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold font-display text-[#F3F4F4] flex items-center gap-2">
            <ShieldCheck className="h-7 w-7 text-[#853953]" /> Merchant Governance & Compliance
          </h2>
          <p className="text-xs text-zinc-300 mt-1">
            Configure automated spending caps, vendor whitelist requirements, and human-in-the-loop approval triggers.
          </p>
        </div>

        <button
          onClick={handleOpenAdd}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-[#853953] hover:bg-[#9c4362] text-xs font-bold text-white rounded-xl shadow-lg shadow-[#853953]/30 border border-[#853953]/50 transition"
        >
          <Plus className="h-4 w-4" />
          <span>New Governance Policy</span>
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="relative w-full max-w-md">
        <Search className="absolute left-3.5 top-3 h-4 w-4 text-zinc-400" />
        <input
          type="text"
          placeholder="Filter policies by name, policy type..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full bg-[#2C2C2C] border border-[#3a3a3a] rounded-xl pl-10 pr-4 py-2.5 text-xs text-[#F3F4F4] placeholder-zinc-400 focus:outline-none focus:border-[#853953]"
        />
      </div>

      {/* Grid Display */}
      {loading ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] flex flex-col items-center justify-center space-y-4 shadow-xl">
          <RefreshCw className="h-8 w-8 text-[#853953] animate-spin" />
          <p className="text-xs text-zinc-400 font-mono">Evaluating active governance rules...</p>
        </div>
      ) : error ? (
        <div className="bg-[#2C2C2C] p-8 rounded-2xl border border-rose-500/30 text-center space-y-3 shadow-xl">
          <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto" />
          <p className="text-xs text-rose-300">{error}</p>
        </div>
      ) : filteredPolicies.length === 0 ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] text-center space-y-4 shadow-xl">
          <ShieldCheck className="h-10 w-10 text-[#853953] mx-auto opacity-60" />
          <h3 className="text-base font-bold text-[#F3F4F4]">No Active Policies Configured</h3>
          <p className="text-xs text-zinc-400 max-w-sm mx-auto">Create a policy to enforce spending limits or approval workflows on incoming AI agent proposals.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredPolicies.map((policy) => (
            <div 
              key={policy.id} 
              className={`bg-[#2C2C2C] p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-6 border transition shadow-xl ${
                policy.is_active ? 'border-[#3a3a3a]' : 'border-[#3a3a3a] opacity-60'
              }`}
            >
              <div className="space-y-2 max-w-xl">
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1c1c1c] text-[#a85890] font-bold border border-[#3a3a3a]">
                    {policy.policy_type}
                  </span>
                  <h3 className="text-base font-bold text-[#F3F4F4] font-display">{policy.policy_name || policy.name || 'Governance Policy'}</h3>
                  <span className="text-[10px] text-zinc-400 font-mono">Priority: {policy.priority}</span>
                </div>
                <p className="text-xs text-zinc-300 leading-relaxed">
                  {policy.description || 'No description provided.'}
                </p>
                <div className="pt-2">
                  <pre className="bg-[#1c1c1c] p-3 rounded-xl border border-[#3a3a3a] text-[11px] font-mono text-zinc-300 overflow-x-auto">
                    {JSON.stringify(policy.rules, null, 2)}
                  </pre>
                </div>
              </div>

              <div className="flex items-center justify-between md:justify-end gap-3 pt-2 md:pt-0 border-t md:border-t-0 border-[#3a3a3a]">
                <button
                  onClick={() => togglePolicyStatus(policy)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition ${
                    policy.is_active 
                      ? 'bg-emerald-500/10 hover:bg-emerald-500/20 border-emerald-500/20 text-emerald-400' 
                      : 'bg-[#612D53]/40 hover:bg-[#612D53]/80 border-[#612D53] text-zinc-400'
                  }`}
                >
                  {policy.is_active ? 'Active' : 'Disabled'}
                </button>

                <button
                  onClick={() => handleOpenEdit(policy)}
                  className="p-2 bg-[#612D53]/40 border border-[#612D53] hover:bg-[#853953] rounded-xl text-[#F3F4F4] transition"
                  title="Edit Rule Configuration"
                >
                  <Edit className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add / Edit Policy Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-[#2C2C2C] border border-[#3a3a3a] rounded-2xl shadow-2xl p-6 relative space-y-4 text-[#F3F4F4]">
            <div className="flex items-center justify-between border-b border-[#3a3a3a] pb-3">
              <h3 className="text-base font-bold font-display text-[#F3F4F4]">
                {editingPolicy ? 'Edit Governance Policy' : 'Create Governance Policy'}
              </h3>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1.5 hover:bg-[#612D53]/40 rounded-xl text-zinc-400 hover:text-white transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
                {formError}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-zinc-300 mb-1 font-semibold">Policy Title</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953]"
                  placeholder="e.g. Executive Procurement Spending Limit"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-300 mb-1 font-semibold">Policy Type</label>
                  <select
                    value={formData.policy_type}
                    onChange={(e) => setFormData({ ...formData, policy_type: e.target.value })}
                    className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953]"
                  >
                    <option value="SPENDING_LIMIT">SPENDING_LIMIT</option>
                    <option value="VENDOR_WHITELIST">VENDOR_WHITELIST</option>
                    <option value="APPROVAL_REQUIRED">APPROVAL_REQUIRED</option>
                    <option value="TIME_WINDOW">TIME_WINDOW</option>
                  </select>
                </div>

                <div>
                  <label className="block text-zinc-300 mb-1 font-semibold">Priority Index</label>
                  <input
                    type="number"
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: Number(e.target.value) })}
                    className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-300 mb-1 font-semibold flex items-center justify-between">
                  <span>Rule Logic JSON Configuration</span>
                  <Code className="h-3.5 w-3.5 text-[#853953]" />
                </label>
                <textarea
                  rows={5}
                  required
                  value={formData.rulesJson}
                  onChange={(e) => setFormData({ ...formData, rulesJson: e.target.value })}
                  className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl p-3 text-xs font-mono text-zinc-200 focus:outline-none focus:border-[#853953] resize-none"
                />
              </div>

              <div className="pt-4 border-t border-[#3a3a3a] flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="px-4 py-2 bg-[#612D53]/40 border border-[#612D53] hover:bg-[#612D53]/80 rounded-xl text-xs font-semibold text-[#F3F4F4] transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="px-4 py-2 bg-[#853953] hover:bg-[#9c4362] text-white text-xs font-bold rounded-xl transition shadow-lg shadow-[#853953]/30 border border-[#853953]/50"
                >
                  {formSubmitting ? 'Saving...' : editingPolicy ? 'Update Policy' : 'Create Policy'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
