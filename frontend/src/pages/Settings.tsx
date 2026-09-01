import { useEffect, useState } from 'react';
import { Settings as SettingsIcon, ShieldCheck, Key, Code, RefreshCw, AlertTriangle } from 'lucide-react';
import { API_BASE_URL, API_ROOT } from '../config/api';

interface MerchantAccount {
  id: string;
  merchant_code: string;
  business_name: string;
  business_type: string;
  country: string;
  currency: string;
}

export default function Settings() {
  const [account, setAccount] = useState<MerchantAccount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [complianceMode, setComplianceMode] = useState(true);
  const [cryptoCheck, setCryptoCheck] = useState(true);

  useEffect(() => {
    const fetchAccount = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/merchants/active`);
        if (!response.ok) {
          throw new Error('Failed to fetch merchant details.');
        }
        const data = await response.json();
        setAccount(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load settings data.');
      } finally {
        setLoading(false);
      }
    };
    fetchAccount();
  }, []);

  return (
    <div className="space-y-8 text-[#F3F4F4]">
      <div>
        <h2 className="text-2xl font-bold font-display text-[#F3F4F4]">System Settings</h2>
        <p className="text-xs text-zinc-300 mt-1">Configure global control plane settings and API properties</p>
      </div>

      {loading ? (
        <div className="flex h-[30vh] items-center justify-center">
          <RefreshCw className="h-8 w-8 animate-spin text-[#853953]" />
        </div>
      ) : error || !account ? (
        <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-rose-500/30 text-center max-w-md mx-auto space-y-3 shadow-xl">
          <AlertTriangle className="h-10 w-10 text-rose-500 mx-auto" />
          <h3 className="text-sm font-bold text-[#F3F4F4]">System Status Unavailable</h3>
          <p className="text-xs text-zinc-400">Could not retrieve active merchant credentials.</p>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Left panel: Control Plane and Security Settings */}
          <div className="lg:col-span-2 space-y-6">
            <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-6 shadow-xl">
              <div className="flex items-center space-x-3">
                <SettingsIcon className="h-6 w-6 text-[#853953]" />
                <h3 className="text-base font-bold font-display text-[#F3F4F4]">Governance Policies</h3>
              </div>

              <div className="border-t border-[#3a3a3a] pt-4 space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-bold text-[#F3F4F4]">Strict Compliance Enforcements</p>
                    <p className="text-[11px] text-zinc-300">Require absolute policy match prior to checkout signature release</p>
                  </div>
                  <button 
                    onClick={() => setComplianceMode(!complianceMode)}
                    className={`h-6 w-11 rounded-full p-1 flex items-center transition ${
                      complianceMode ? 'bg-[#853953] justify-end' : 'bg-[#1c1c1c] border border-[#3a3a3a] justify-start'
                    }`}
                  >
                    <div className="h-4 w-4 rounded-full bg-white shadow"></div>
                  </button>
                </div>
                
                <div className="flex items-center justify-between border-t border-[#3a3a3a] pt-4">
                  <div>
                    <p className="text-xs font-bold text-[#F3F4F4]">Cryptographic Verification Required</p>
                    <p className="text-[11px] text-zinc-300">Validate ECDSA signatures for all inbound agent proposals</p>
                  </div>
                  <button 
                    onClick={() => setCryptoCheck(!cryptoCheck)}
                    className={`h-6 w-11 rounded-full p-1 flex items-center transition ${
                      cryptoCheck ? 'bg-[#853953] justify-end' : 'bg-[#1c1c1c] border border-[#3a3a3a] justify-start'
                    }`}
                  >
                    <div className="h-4 w-4 rounded-full bg-white shadow"></div>
                  </button>
                </div>
              </div>
            </div>

            {/* API and Environment Info */}
            <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-4 shadow-xl">
              <div className="flex items-center space-x-3">
                <Code className="h-5 w-5 text-[#853953]" />
                <h3 className="text-base font-bold font-display text-[#F3F4F4]">API Details & Docs</h3>
              </div>
              <p className="text-xs text-zinc-300 leading-relaxed">
                Expose these endpoint variables to configure your external automated procurement and negotiation systems.
              </p>
              <div className="p-4 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a] space-y-3 font-mono text-xs text-zinc-300">
                <div>
                  <span className="text-zinc-400">API Root:</span> {API_BASE_URL}
                </div>
                <div>
                  <span className="text-zinc-400">Swagger OpenAPI Specification:</span>{' '}
                  <a href={`${API_ROOT}/docs`} target="_blank" rel="noreferrer" className="text-[#a85890] hover:underline">
                    {`${API_ROOT}/docs`}
                  </a>
                </div>
                <div>
                  <span className="text-zinc-400">Redoc UI:</span>{' '}
                  <a href={`${API_ROOT}/redoc`} target="_blank" rel="noreferrer" className="text-[#a85890] hover:underline">
                    {`${API_ROOT}/redoc`}
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Right panel: Account Meta Info */}
          <div className="space-y-6">
            <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-4 shadow-xl">
              <div className="flex items-center space-x-2.5">
                <Key className="h-5 w-5 text-[#853953]" />
                <h4 className="text-xs font-bold font-display uppercase tracking-wider text-[#F3F4F4]">Account Information</h4>
              </div>

              <div className="space-y-3 text-xs pt-2">
                <div>
                  <span className="text-zinc-400 block uppercase text-[10px] font-semibold">Business Name</span>
                  <span className="text-[#F3F4F4] font-bold">{account.business_name}</span>
                </div>
                <div>
                  <span className="text-zinc-400 block uppercase text-[10px] font-semibold">Merchant ID</span>
                  <span className="text-zinc-300 font-mono text-[10px] break-all">{account.id}</span>
                </div>
                <div>
                  <span className="text-zinc-400 block uppercase text-[10px] font-semibold">Merchant Code</span>
                  <span className="text-[#a85890] font-mono font-bold">{account.merchant_code}</span>
                </div>
                <div>
                  <span className="text-zinc-400 block uppercase text-[10px] font-semibold">Region & Currency</span>
                  <span className="text-zinc-200 font-semibold">{account.country} ({account.currency})</span>
                </div>
                <div className="pt-3 border-t border-[#3a3a3a]">
                  <span className="text-zinc-400 block uppercase text-[10px] font-semibold">Security Mode</span>
                  <span className="inline-flex items-center gap-1.5 text-emerald-400 font-bold mt-1 text-xs">
                    <ShieldCheck className="h-4 w-4" />
                    Encrypted Service Connection
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
