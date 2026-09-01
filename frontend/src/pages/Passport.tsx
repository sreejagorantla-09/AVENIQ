import { useEffect, useState } from 'react';
import { Sparkles, ShieldCheck, Cpu, Key, FileJson, Copy, Check, RefreshCw, AlertTriangle } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

interface AgentPassport {
  aveniq_version: string;
  merchant: {
    business_name: string;
    merchant_code: string;
    country: string;
    currency: string;
  };
  endpoints: {
    base_url: string;
    product_discovery: string;
    negotiation: string;
    checkout: string;
  };
  supported_authentication: string[];
  supported_capabilities: string[];
  payment_provider: string;
  supported_currencies: string[];
  permission_scopes: string[];
  governance_policy_eval: boolean;
  webhook_support: boolean;
}

export default function Passport() {
  const [passport, setPassport] = useState<AgentPassport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [showJsonView, setShowJsonView] = useState(false);

  const fetchPassport = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/passport`);
      if (!response.ok) {
        throw new Error('Failed to load Agent Commerce Passport');
      }
      const data = await response.json();
      setPassport(data);
    } catch (err: any) {
      setError(err.message || 'An error occurred loading the passport manifest');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPassport();
  }, []);

  const copyPassportJson = () => {
    if (passport) {
      navigator.clipboard.writeText(JSON.stringify(passport, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <RefreshCw className="h-8 w-8 animate-spin text-[#853953]" />
          <p className="text-sm text-zinc-400 font-mono">Resolving Agent Passport manifest...</p>
        </div>
      </div>
    );
  }

  if (error || !passport) {
    return (
      <div className="bg-[#2C2C2C] p-8 rounded-2xl max-w-lg mx-auto text-center space-y-4 my-12 border border-rose-500/30 text-[#F3F4F4] shadow-xl">
        <AlertTriangle className="h-12 w-12 text-rose-500 mx-auto" />
        <h3 className="text-base font-bold">Passport Discovery Failed</h3>
        <p className="text-xs text-zinc-400">{error || 'Could not load passport.'}</p>
        <button
          onClick={fetchPassport}
          className="px-4 py-2 bg-[#612D53] border border-[#853953]/50 rounded-xl text-xs font-semibold hover:bg-[#853953] transition text-[#F3F4F4]"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8 text-[#F3F4F4]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-[#853953]/20 text-[#f3f4f4] border border-[#853953]/40">
              /.well-known/agent-passport.json
            </span>
          </div>
          <h2 className="text-2xl font-bold font-display text-[#F3F4F4] mt-1">Agent Commerce Passport</h2>
          <p className="text-xs text-zinc-300">
            Machine-readable discovery manifest detailing capabilities, endpoints, and governance scopes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowJsonView(!showJsonView)}
            className="flex items-center gap-2 px-4 py-2 bg-[#612D53]/40 hover:bg-[#612D53]/80 border border-[#612D53] text-xs font-semibold rounded-xl transition text-[#F3F4F4]"
          >
            <FileJson className="h-4 w-4 text-[#853953]" />
            {showJsonView ? 'Standard View' : 'AI Schema View'}
          </button>
          
          <button
            onClick={copyPassportJson}
            className="flex items-center gap-2 px-4 py-2 bg-[#853953] hover:bg-[#9c4362] text-xs font-semibold rounded-xl transition text-white shadow-lg shadow-[#853953]/30 border border-[#853953]/50"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied' : 'Copy Manifest'}
          </button>
        </div>
      </div>

      {showJsonView ? (
        <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-[#3a3a3a] pb-3">
            <span className="text-xs font-mono text-[#a85890]">GET /.well-known/agent-passport.json</span>
            <span className="text-[10px] font-mono text-zinc-400">Content-Type: application/json</span>
          </div>
          <pre className="bg-[#1c1c1c] p-4 rounded-xl border border-[#3a3a3a] text-xs font-mono text-[#F3F4F4] overflow-x-auto max-h-[500px]">
            {JSON.stringify(passport, null, 2)}
          </pre>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Identity & Merchant Profile */}
          <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-6 shadow-xl lg:col-span-1 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-[#3a3a3a] pb-3">
                <div className="flex items-center space-x-2">
                  <div className="h-8 w-8 rounded-xl bg-[#853953]/20 border border-[#853953]/40 flex items-center justify-center">
                    <Sparkles className="h-4 w-4 text-[#853953]" />
                  </div>
                  <h3 className="text-base font-bold text-[#F3F4F4]">Merchant Identity</h3>
                </div>
                <span className="text-[10px] font-mono bg-[#1c1c1c] text-[#a85890] border border-[#3a3a3a] px-2 py-0.5 rounded font-bold">
                  v{passport.aveniq_version}
                </span>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-zinc-400 text-[10px] block uppercase font-semibold">Business Name</span>
                  <span className="text-[#F3F4F4] font-bold text-sm">{passport.merchant.business_name}</span>
                </div>
                <div>
                  <span className="text-zinc-400 text-[10px] block uppercase font-semibold">Merchant Code</span>
                  <span className="text-[#a85890] font-mono font-bold">{passport.merchant.merchant_code}</span>
                </div>
                <div>
                  <span className="text-zinc-400 text-[10px] block uppercase font-semibold">Region / Currency</span>
                  <span className="text-zinc-200">{passport.merchant.country} ({passport.merchant.currency})</span>
                </div>
                <div>
                  <span className="text-zinc-400 text-[10px] block uppercase font-semibold">Payment Gateway</span>
                  <span className="text-emerald-400 font-bold uppercase">{passport.payment_provider}</span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-[#3a3a3a] flex items-center justify-between text-xs">
              <span className="text-zinc-400 flex items-center gap-1">
                <ShieldCheck className="h-4 w-4 text-emerald-400" /> Policy Engine Active
              </span>
              <span className="text-emerald-400 font-bold">Verified</span>
            </div>
          </div>

          {/* Capabilities & Scopes Registry */}
          <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-6 shadow-xl lg:col-span-2">
            <div className="flex items-center justify-between border-b border-[#3a3a3a] pb-3">
              <h3 className="text-base font-bold text-[#F3F4F4]">Supported Capabilities & Security Scopes</h3>
              <span className="text-xs text-zinc-400 font-mono">Razorpay Integration Verified</span>
            </div>

            {/* Capability Pills */}
            <div className="space-y-3">
              <span className="text-xs font-semibold text-zinc-300 block uppercase tracking-wider">Agent Capabilities</span>
              <div className="flex flex-wrap gap-2">
                {passport.supported_capabilities.map((cap, i) => (
                  <span key={i} className="px-3 py-1 rounded-xl text-xs bg-[#1c1c1c] border border-[#3a3a3a] text-zinc-200 flex items-center gap-1.5 font-medium">
                    <Cpu className="h-3.5 w-3.5 text-[#853953]" />
                    {cap.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>

            {/* Permission Scopes */}
            <div className="space-y-3">
              <span className="text-xs font-semibold text-zinc-300 block uppercase tracking-wider">OAuth / Security Scopes</span>
              <div className="flex flex-wrap gap-2">
                {passport.permission_scopes.map((scope, i) => (
                  <span key={i} className="px-3 py-1 rounded-xl text-xs bg-[#612D53]/30 border border-[#612D53] text-[#a85890] font-mono font-semibold flex items-center gap-1.5">
                    <Key className="h-3.5 w-3.5 text-[#853953]" />
                    {scope}
                  </span>
                ))}
              </div>
            </div>

            {/* API Endpoints */}
            <div className="space-y-3 pt-2">
              <span className="text-xs font-semibold text-zinc-300 block uppercase tracking-wider">Discovered API Endpoints</span>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                <div className="p-3 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a]">
                  <span className="text-zinc-400 text-[10px] block">Product Discovery</span>
                  <span className="text-[#a85890] font-bold">{passport.endpoints.product_discovery}</span>
                </div>
                <div className="p-3 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a]">
                  <span className="text-zinc-400 text-[10px] block">AI Negotiation</span>
                  <span className="text-[#a85890] font-bold">{passport.endpoints.negotiation}</span>
                </div>
                <div className="p-3 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a]">
                  <span className="text-zinc-400 text-[10px] block">Razorpay Checkout</span>
                  <span className="text-[#a85890] font-bold">{passport.endpoints.checkout}</span>
                </div>
                <div className="p-3 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a]">
                  <span className="text-zinc-400 text-[10px] block">Base Gateway URL</span>
                  <span className="text-[#a85890] font-bold">{passport.endpoints.base_url}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
