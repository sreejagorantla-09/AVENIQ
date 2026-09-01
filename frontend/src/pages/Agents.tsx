import { useEffect, useState } from 'react';
import { Cpu, Plus, Key, Copy, CheckCircle2, RefreshCw, AlertTriangle, X } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

interface Agent {
  id: string;
  agent_code: string;
  name: string;
  description: string | null;
  agent_type: string;
  status: string;
  created_at: string;
}

interface ApiKey {
  id: string;
  key_prefix: string;
  name: string;
  scopes: string[];
  is_active: boolean;
  created_at: string;
}

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Agent Modal States
  const [isAgentOpen, setIsAgentOpen] = useState(false);
  const [agentForm, setAgentForm] = useState({
    agent_code: '',
    name: '',
    description: '',
    agent_type: 'PROCUREMENT_BOT',
  });
  const [agentSubmitting, setAgentSubmitting] = useState(false);

  // Key Modal States
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [keysLoading, setKeysLoading] = useState(false);

  // Create Key Form
  const [isKeyCreateOpen, setIsKeyCreateOpen] = useState(false);
  const [keyForm, setKeyForm] = useState({
    name: 'Default Agent Key',
    scopes: ['read:products', 'write:proposals', 'write:checkout'],
  });
  const [createdRawKey, setCreatedRawKey] = useState<string | null>(null);
  const [keySubmitting, setKeySubmitting] = useState(false);
  const [copied, setCopied] = useState(false);

  const fetchAgents = async () => {
    setLoading(true);
    setError(null);
    try {
      let res: Response | null = null;
      try {
        res = await fetch(`${API_BASE_URL}/agents`);
      } catch (firstErr) {
        const fallbackUrl = API_BASE_URL.includes('localhost')
          ? API_BASE_URL.replace('localhost', '127.0.0.1')
          : API_BASE_URL.replace('127.0.0.1', 'localhost');
        try {
          res = await fetch(`${fallbackUrl}/agents`);
        } catch {
          throw firstErr;
        }
      }
      if (!res || !res.ok) throw new Error('Failed to fetch registered agents.');
      const data = await res.json();
      setAgents(Array.isArray(data) ? data : []);
    } catch (err: any) {
      setError(err.message || 'Error loading agents.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    setAgentSubmitting(true);
    try {
      let res: Response | null = null;
      try {
        res = await fetch(`${API_BASE_URL}/agents`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(agentForm),
        });
      } catch (firstErr) {
        const fallbackUrl = API_BASE_URL.includes('localhost')
          ? API_BASE_URL.replace('localhost', '127.0.0.1')
          : API_BASE_URL.replace('127.0.0.1', 'localhost');
        try {
          res = await fetch(`${fallbackUrl}/agents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(agentForm),
          });
        } catch {
          throw firstErr;
        }
      }

      if (!res || !res.ok) {
        const data = await res?.json().catch(() => ({}));
        throw new Error(data?.detail || 'Failed to register agent.');
      }

      const createdAgent = await res.json();
      setIsAgentOpen(false);
      setAgentForm({ agent_code: '', name: '', description: '', agent_type: 'PROCUREMENT_BOT' });
      setAgents((prev) => [createdAgent, ...prev.filter(a => a.id !== createdAgent.id)]);
      fetchAgents();
    } catch (err: any) {
      alert(err.message || 'Agent creation failed.');
    } finally {
      setAgentSubmitting(false);
    }
  };

  const fetchApiKeys = async (agentId: string) => {
    setKeysLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/agents/${agentId}/keys`);
      if (res.ok) {
        const data = await res.json();
        setApiKeys(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setKeysLoading(false);
    }
  };

  const handleOpenKeys = (agent: Agent) => {
    setSelectedAgent(agent);
    setCreatedRawKey(null);
    setIsKeyCreateOpen(false);
    setIsKeyModalOpen(true);
    fetchApiKeys(agent.id);
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgent) return;
    setKeySubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/agents/${selectedAgent.id}/keys`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(keyForm),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to issue API key.');
      }

      const data = await res.json();
      setCreatedRawKey(data.raw_api_key);
      fetchApiKeys(selectedAgent.id);
      setIsKeyCreateOpen(false);
    } catch (err: any) {
      alert(err.message || 'Key generation failed.');
    } finally {
      setKeySubmitting(false);
    }
  };

  const copyToClipboard = () => {
    if (createdRawKey) {
      navigator.clipboard.writeText(createdRawKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-6 text-[#F3F4F4]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold font-display text-[#F3F4F4] flex items-center gap-2">
            <Cpu className="h-7 w-7 text-[#853953]" /> Authorized AI Agent Registry
          </h2>
          <p className="text-xs text-zinc-300 mt-1">
            Register buyer agents, manage scoped credentials, and issue cryptographic API keys.
          </p>
        </div>

        <button
          onClick={() => setIsAgentOpen(true)}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-[#853953] hover:bg-[#9c4362] text-xs font-bold text-white rounded-xl shadow-lg shadow-[#853953]/30 border border-[#853953]/50 transition"
        >
          <Plus className="h-4 w-4" />
          <span>Register New Agent</span>
        </button>
      </div>

      {/* Grid Display */}
      {loading ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] flex flex-col items-center justify-center space-y-4 shadow-xl">
          <RefreshCw className="h-8 w-8 text-[#853953] animate-spin" />
          <p className="text-xs text-zinc-400 font-mono">Loading registered agent directory...</p>
        </div>
      ) : error ? (
        <div className="bg-[#2C2C2C] p-8 rounded-2xl border border-rose-500/30 text-center space-y-3 shadow-xl">
          <AlertTriangle className="h-8 w-8 text-rose-400 mx-auto" />
          <p className="text-xs text-rose-300">{error}</p>
        </div>
      ) : agents.length === 0 ? (
        <div className="bg-[#2C2C2C] p-12 rounded-2xl border border-[#3a3a3a] text-center space-y-4 shadow-xl">
          <Cpu className="h-10 w-10 text-[#853953] mx-auto opacity-60" />
          <h3 className="text-base font-bold text-[#F3F4F4]">No Agents Registered</h3>
          <p className="text-xs text-zinc-400 max-w-sm mx-auto">Register your autonomous buyer bots to issue API access keys.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <div 
              key={agent.id} 
              className={`bg-[#2C2C2C] p-6 rounded-2xl flex flex-col justify-between gap-4 border transition shadow-xl ${
                agent.status === 'active' ? 'border-[#3a3a3a]' : 'border-[#3a3a3a] opacity-60'
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono bg-[#1c1c1c] text-[#a85890] border border-[#3a3a3a] px-2 py-0.5 rounded font-bold">
                      {agent.agent_code}
                    </span>
                    <h3 className="text-base font-bold text-[#F3F4F4] mt-1 font-display">{agent.name}</h3>
                  </div>
                  <span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full border ${
                    agent.status === 'active' 
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                      : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                  }`}>
                    {agent.status}
                  </span>
                </div>

                <p className="text-xs text-zinc-300 leading-relaxed">
                  {agent.description || 'No agent description supplied.'}
                </p>
              </div>

              <div className="space-y-3 pt-2 border-t border-[#3a3a3a]">
                <div className="flex items-center justify-between text-xs text-zinc-400 font-mono">
                  <span>Type: {agent.agent_type}</span>
                  <span>Registered: {new Date(agent.created_at).toLocaleDateString()}</span>
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    onClick={() => handleOpenKeys(agent)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-[#612D53]/40 border border-[#612D53] hover:bg-[#853953] rounded-xl text-xs font-semibold text-[#F3F4F4] transition"
                  >
                    <Key className="h-3.5 w-3.5 text-[#853953]" />
                    Credentials & Keys
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Keys Modal */}
      {isKeyModalOpen && selectedAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-[#2C2C2C] border border-[#3a3a3a] rounded-2xl shadow-2xl p-6 relative space-y-4 text-[#F3F4F4]">
            <div className="flex items-center justify-between border-b border-[#3a3a3a] pb-3">
              <div>
                <h3 className="text-base font-bold font-display text-[#F3F4F4]">
                  API Credentials: {selectedAgent.name}
                </h3>
                <span className="text-xs text-zinc-400 font-mono">Agent Code: {selectedAgent.agent_code}</span>
              </div>
              <button
                onClick={() => setIsKeyModalOpen(false)}
                className="p-1.5 hover:bg-[#612D53]/40 rounded-xl text-zinc-400 hover:text-white transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {createdRawKey && (
              <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/40 space-y-2">
                <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                  <CheckCircle2 className="h-4 w-4" /> New API Key Generated!
                </span>
                <p className="text-[11px] text-zinc-300">Copy this raw secret key now. It will not be shown again:</p>
                <div className="flex items-center gap-2">
                  <pre className="flex-1 bg-[#1c1c1c] p-2.5 rounded-xl border border-emerald-500/30 text-xs font-mono text-emerald-300 select-all overflow-x-auto">
                    {createdRawKey}
                  </pre>
                  <button
                    onClick={copyToClipboard}
                    className="px-3 py-2 bg-[#612D53]/40 border border-[#612D53] hover:bg-[#853953] rounded-xl flex items-center justify-center text-[#F3F4F4] transition"
                    title="Copy to clipboard"
                  >
                    {copied ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            )}

            {/* List Active Keys */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-300 uppercase tracking-wider">Active Key Prefixes</span>
                <button
                  onClick={() => setIsKeyCreateOpen(!isKeyCreateOpen)}
                  className="text-xs text-[#a85890] hover:underline font-bold flex items-center gap-1"
                >
                  <Plus className="h-3.5 w-3.5" /> Issue New Key
                </button>
              </div>

              {isKeyCreateOpen && (
                <form onSubmit={handleCreateKey} className="p-4 bg-[#1c1c1c] rounded-xl border border-[#3a3a3a] space-y-3 text-xs">
                  <div>
                    <label className="block text-zinc-300 mb-1 font-semibold">Key Identifier Label</label>
                    <input
                      type="text"
                      required
                      value={keyForm.name}
                      onChange={(e) => setKeyForm({ ...keyForm, name: e.target.value })}
                      className="w-full bg-[#2C2C2C] border border-[#3a3a3a] rounded-xl px-3 py-1.5 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953]"
                    />
                  </div>
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setIsKeyCreateOpen(false)}
                      className="px-3 py-1.5 bg-[#612D53]/40 border border-[#612D53] hover:bg-[#612D53]/80 rounded-xl text-xs transition text-[#F3F4F4]"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={keySubmitting}
                      className="px-3 py-1.5 bg-[#853953] hover:bg-[#9c4362] text-white text-xs font-bold rounded-xl transition"
                    >
                      {keySubmitting ? 'Generating...' : 'Generate Key'}
                    </button>
                  </div>
                </form>
              )}

              {keysLoading ? (
                <div className="text-center p-4 text-xs text-zinc-400">Loading keys...</div>
              ) : apiKeys.length === 0 ? (
                <div className="p-4 text-center text-xs text-zinc-400 bg-[#1c1c1c] rounded-xl border border-[#3a3a3a]">
                  No active keys issued for this agent.
                </div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {apiKeys.map((key) => (
                    <div key={key.id} className="p-3 bg-[#1c1c1c] rounded-xl border border-[#3a3a3a] flex items-center justify-between text-xs font-mono">
                      <div>
                        <span className="text-[#a85890] font-bold block">{key.key_prefix}...</span>
                        <span className="text-[10px] text-zinc-400">{key.name}</span>
                      </div>
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">
                        Active
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-[#3a3a3a] text-right">
              <button
                onClick={() => setIsKeyModalOpen(false)}
                className="px-4 py-2 bg-[#612D53] hover:bg-[#853953] text-[#F3F4F4] text-xs font-semibold rounded-xl transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Agent Modal */}
      {isAgentOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-lg bg-[#2C2C2C] border border-[#3a3a3a] rounded-2xl shadow-2xl p-6 relative space-y-4 text-[#F3F4F4]">
            <div className="flex items-center justify-between border-b border-[#3a3a3a] pb-3">
              <h3 className="text-base font-bold font-display text-[#F3F4F4]">Register Buyer Agent</h3>
              <button
                onClick={() => setIsAgentOpen(false)}
                className="p-1.5 hover:bg-[#612D53]/40 rounded-xl text-zinc-400 hover:text-white transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateAgent} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-zinc-300 mb-1 font-semibold">Agent Code</label>
                  <input
                    type="text"
                    required
                    value={agentForm.agent_code}
                    onChange={(e) => setAgentForm({ ...agentForm, agent_code: e.target.value })}
                    className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953] font-mono"
                    placeholder="AGENT_PURCHASER_PRO"
                  />
                </div>
                <div>
                  <label className="block text-zinc-300 mb-1 font-semibold">Agent Name</label>
                  <input
                    type="text"
                    required
                    value={agentForm.name}
                    onChange={(e) => setAgentForm({ ...agentForm, name: e.target.value })}
                    className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953]"
                    placeholder="Corporate Buyer Bot"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-300 mb-1 font-semibold">Description</label>
                <textarea
                  rows={2}
                  value={agentForm.description}
                  onChange={(e) => setAgentForm({ ...agentForm, description: e.target.value })}
                  className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl px-3 py-2 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953] resize-none font-sans"
                  placeholder="Automates IT equipment procurement..."
                />
              </div>

              <div className="pt-4 border-t border-[#3a3a3a] flex items-center justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setIsAgentOpen(false)}
                  className="px-4 py-2 bg-[#612D53]/40 border border-[#612D53] hover:bg-[#612D53]/80 rounded-xl text-xs font-semibold text-[#F3F4F4] transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={agentSubmitting}
                  className="px-4 py-2 bg-[#853953] hover:bg-[#9c4362] text-white text-xs font-bold rounded-xl transition shadow-lg shadow-[#853953]/30 border border-[#853953]/50"
                >
                  {agentSubmitting ? 'Registering...' : 'Register Agent'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
