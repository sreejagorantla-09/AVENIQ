import { useState, useEffect } from 'react';
import { Bot, Play, CheckCircle2, AlertCircle, RefreshCw, Sparkles, ShieldCheck, CreditCard, DollarSign, FileCheck, Layers } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

declare global {
  interface Window {
    Razorpay: any;
  }
}

interface StepLog {
  step: number;
  title: string;
  status: 'idle' | 'running' | 'success' | 'failed';
  details?: any;
  error?: string;
}

export default function Playground() {
  const [prompt, setPrompt] = useState('Procure 2 units of Smart Watch Pro for team with budget under ₹25,000 per unit.');
  const [isRunning, setIsRunning] = useState(false);

  // Execution Flow State
  const [logs, setLogs] = useState<StepLog[]>([
    { step: 1, title: 'Product & Catalog Discovery', status: 'idle' },
    { step: 2, title: 'AI Price & Discount Negotiation', status: 'idle' },
    { step: 3, title: 'Merchant Policy & Compliance Check', status: 'idle' },
    { step: 4, title: 'Transaction & Razorpay Order Creation', status: 'idle' },
    { step: 5, title: 'Payment Verification & Cryptographic Settlement', status: 'idle' },
  ]);

  const [discoveredProduct, setDiscoveredProduct] = useState<any>(null);
  const [negotiationResult, setNegotiationResult] = useState<any>(null);
  const [policyResult, setPolicyResult] = useState<any>(null);
  const [transactionResult, setTransactionResult] = useState<any>(null);
  const [razorpayOrder, setRazorpayOrder] = useState<any>(null);
  const [paymentVerificationResult, setPaymentVerificationResult] = useState<any>(null);
  const [checkoutError, setCheckoutError] = useState<string | null>(null);

  const resetFlow = () => {
    setIsRunning(false);
    setDiscoveredProduct(null);
    setNegotiationResult(null);
    setPolicyResult(null);
    setTransactionResult(null);
    setRazorpayOrder(null);
    setPaymentVerificationResult(null);
    setCheckoutError(null);
    setLogs([
      { step: 1, title: 'Product & Catalog Discovery', status: 'idle' },
      { step: 2, title: 'AI Price & Discount Negotiation', status: 'idle' },
      { step: 3, title: 'Merchant Policy & Compliance Check', status: 'idle' },
      { step: 4, title: 'Transaction & Razorpay Order Creation', status: 'idle' },
      { step: 5, title: 'Payment Verification & Cryptographic Settlement', status: 'idle' },
    ]);
  };

  const updateStepStatus = (stepNum: number, status: 'idle' | 'running' | 'success' | 'failed', details?: any, error?: string) => {
    setLogs((prev) =>
      prev.map((log) =>
        log.step === stepNum ? { ...log, status, details: details !== undefined ? details : log.details, error } : log
      )
    );
  };

  const safeFetch = async (url: string, options?: RequestInit): Promise<Response> => {
    try {
      return await fetch(url, options);
    } catch (firstErr) {
      const fallbackUrl = url.includes('localhost')
        ? url.replace('localhost', '127.0.0.1')
        : url.replace('127.0.0.1', 'localhost');
      try {
        return await fetch(fallbackUrl, options);
      } catch {
        throw firstErr;
      }
    }
  };

  const handleRunFlow = async () => {
    resetFlow();
    setIsRunning(true);
    let activeStep = 1;

    try {
      // STEP 1: Product Discovery
      activeStep = 1;
      updateStepStatus(1, 'running');

      const productsRes = await safeFetch(`${API_BASE_URL}/products`);
      if (!productsRes.ok) throw new Error('Failed to query merchant catalog');
      const products = await productsRes.json();
      
      let matchedProduct = products.find((p: any) => 
        p.is_active && prompt.toLowerCase().includes(p.name.toLowerCase().split(' ')[0])
      );
      
      if (!matchedProduct && products.length > 0) {
        matchedProduct = products.find((p: any) => 
          p.is_active && prompt.toLowerCase().split(' ').some((word: string) => word.length > 2 && p.name.toLowerCase().includes(word))
        ) || products.find((p: any) => p.is_active) || products[0];
      }

      if (!matchedProduct) {
        throw new Error('No active products found in catalog for agent procurement.');
      }

      setDiscoveredProduct(matchedProduct);
      updateStepStatus(1, 'success', matchedProduct);

      // STEP 2: AI Price & Discount Negotiation
      activeStep = 2;
      updateStepStatus(2, 'running');
      await new Promise((resolve) => setTimeout(resolve, 800));

      const negotiateRes = await safeFetch(`${API_BASE_URL}/agent/negotiate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Agent-API-Key': 'ave_live_smart_purchaser_agent_key_001'
        },
        body: JSON.stringify({
          raw_request: prompt,
          product_sku: matchedProduct.sku,
          proposed_price: Math.floor(matchedProduct.price * 0.85),
          quantity: 1
        })
      });

      if (!negotiateRes.ok) {
        const errData = await negotiateRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'AI negotiation engine rejected bargain proposal');
      }
      const negoData = await negotiateRes.json();
      setNegotiationResult(negoData);
      updateStepStatus(2, 'success', negoData);

      // STEP 3: Merchant Policy & Compliance Check
      activeStep = 3;
      updateStepStatus(3, 'running');
      await new Promise((resolve) => setTimeout(resolve, 800));

      const policyRes = await safeFetch(`${API_BASE_URL}/policies/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: negoData.counter_offer_price,
          sku: matchedProduct.sku,
          quantity: 1,
          agent_code: 'AGENT_PURCHASER_PRO'
        })
      });

      if (!policyRes.ok) throw new Error('Merchant policy evaluation engine blocked checkout');
      const polData = await policyRes.json();
      setPolicyResult(polData);

      if (polData.decision === 'DENY' || polData.decision === 'DECLINED') {
        throw new Error(`Policy violation: ${polData.reason || 'Transaction exceeds merchant governance boundary'}`);
      }

      updateStepStatus(3, 'success', polData);

      // STEP 4: Accept Proposal & Create Razorpay Order
      activeStep = 4;
      updateStepStatus(4, 'running');
      await new Promise((resolve) => setTimeout(resolve, 800));

      // Accept negotiation proposal to create transaction
      const acceptRes = await safeFetch(`${API_BASE_URL}/agent/negotiate/${negoData.session_id}/accept`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Agent-API-Key': 'ave_live_smart_purchaser_agent_key_001'
        }
      });

      if (!acceptRes.ok) throw new Error('Failed to accept negotiation proposal and record transaction');
      const acceptData = await acceptRes.json();
      setTransactionResult(acceptData);

      // Generate Razorpay checkout order
      const rzpOrderRes = await safeFetch(`${API_BASE_URL}/agent/checkout`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Agent-API-Key': 'ave_live_smart_purchaser_agent_key_001'
        },
        body: JSON.stringify({
          transaction_id: acceptData.transaction_id
        })
      });

      if (!rzpOrderRes.ok) throw new Error('Failed to initialize Razorpay checkout order');
      const rzpData = await rzpOrderRes.json();
      setRazorpayOrder(rzpData);
      updateStepStatus(4, 'success', { transaction: acceptData, razorpay_order: rzpData });

      setIsRunning(false);

    } catch (err: any) {
      updateStepStatus(activeStep, 'failed', undefined, err.message || 'Execution error');
      setIsRunning(false);
    }
  };

  const [isRzpLoaded, setIsRzpLoaded] = useState<boolean>(typeof window !== 'undefined' && !!window.Razorpay);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.Razorpay) {
      setIsRzpLoaded(true);
      return;
    }
    const checkRzp = setInterval(() => {
      if (typeof window !== 'undefined' && window.Razorpay) {
        setIsRzpLoaded(true);
        clearInterval(checkRzp);
      }
    }, 300);
    return () => clearInterval(checkRzp);
  }, []);

  const handleOpenRazorpayModal = () => {
    const orderId = razorpayOrder?.razorpay_order_id || razorpayOrder?.order_id;
    const amount = razorpayOrder?.amount || razorpayOrder?.amount_paise;
    const keyId = razorpayOrder?.razorpay_key_id || razorpayOrder?.key_id;
    const txId = transactionResult?.transaction_id || transactionResult?.id;

    if (!orderId || !window.Razorpay) {
      setCheckoutError('Razorpay Checkout SDK not loaded or order uninitialized');
      return;
    }

    setCheckoutError(null);

    const options = {
      key: keyId,
      amount: amount,
      currency: razorpayOrder.currency || 'INR',
      name: 'AVENIQ Agent Commerce',
      description: `Automated Settlement for Order #${orderId}`,
      order_id: orderId,
      prefill: {
        name: 'AI Agent Purchaser',
        email: 'agent@aveniq.ai',
        contact: '9999999999'
      },
      theme: {
        color: '#853953'
      },
      method: {
        upi: true,
        card: true,
        netbanking: true,
        wallet: true
      },
      handler: async function (response: any) {
        try {
          updateStepStatus(5, 'running');

          const verifyRes = await fetch(`${API_BASE_URL}/agent/checkout/verify`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Agent-API-Key': 'ave_live_smart_purchaser_agent_key_001'
            },
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              transaction_id: txId
            })
          });

          if (!verifyRes.ok) {
            const errData = await verifyRes.json().catch(() => ({}));
            throw new Error(errData.detail || 'Razorpay cryptographic signature verification failed');
          }

          const verifyData = await verifyRes.json();
          setPaymentVerificationResult(verifyData);
          updateStepStatus(5, 'success', verifyData);
        } catch (err: any) {
          updateStepStatus(5, 'failed', undefined, err.message);
          setCheckoutError(err.message);
        }
      },
      modal: {
        ondismiss: function () {
          console.log('Razorpay modal dismissed');
        }
      }
    };

    const rzp = new window.Razorpay(options);
    rzp.open();
  };

  const handleSimulatePayment = async () => {
    if (!transactionResult || !razorpayOrder) return;
    try {
      updateStepStatus(5, 'running');

      const orderId = razorpayOrder.razorpay_order_id || razorpayOrder.order_id;
      const txId = transactionResult?.transaction_id || transactionResult?.id;

      const mockPaymentId = `pay_sim_${Math.random().toString(36).substring(2, 10)}`;
      const verifyRes = await fetch(`${API_BASE_URL}/agent/checkout/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Agent-API-Key': 'ave_live_smart_purchaser_agent_key_001'
        },
        body: JSON.stringify({
          razorpay_order_id: orderId,
          razorpay_payment_id: mockPaymentId,
          razorpay_signature: 'sig_mock_qa_test',
          transaction_id: txId
        })
      });

      if (!verifyRes.ok) {
        const errData = await verifyRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'Signature verification failed');
      }

      const verifyData = await verifyRes.json();
      setPaymentVerificationResult(verifyData);
      updateStepStatus(5, 'success', verifyData);
    } catch (err: any) {
      updateStepStatus(5, 'failed', undefined, err.message);
      setCheckoutError(err.message);
    }
  };

  const presets = [
    { label: 'Smart Watch Bulk Buy', text: 'Procure 2 units of Smart Watch Pro for team with budget under ₹25,000 per unit.' },
    { label: 'Wireless Earbuds Order', text: 'Order 5 Noise Cancelling Earbuds for new engineering hires.' },
    { label: 'Developer Laptop Request', text: 'Negotiate price for M3 Pro Laptop for lead architect.' },
  ];

  return (
    <div className="space-y-8 text-[#F3F4F4]">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold font-display text-[#F3F4F4] flex items-center gap-2">
            <Bot className="h-7 w-7 text-[#853953]" /> AI Agent Commerce Playground
          </h2>
          <p className="text-xs text-zinc-300 mt-1">
            Simulate end-to-end autonomous agent procurement, AI bargaining, policy enforcement, and Razorpay settlement.
          </p>
        </div>

        <button
          onClick={resetFlow}
          disabled={isRunning}
          className="flex items-center space-x-2 px-4 py-2 bg-[#612D53]/40 hover:bg-[#612D53]/80 border border-[#612D53] rounded-xl text-xs font-semibold text-[#F3F4F4] transition self-start md:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${isRunning ? 'animate-spin' : ''}`} />
          <span>Reset Playground</span>
        </button>
      </div>

      {/* Input Prompt Panel */}
      <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] space-y-4 shadow-xl">
        <label className="text-xs font-semibold uppercase tracking-wider text-zinc-300 block">
          Agent Intent & Procurement Prompt
        </label>
        
        <div className="relative">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isRunning}
            rows={3}
            className="w-full bg-[#1c1c1c] border border-[#3a3a3a] rounded-xl p-4 text-xs text-[#F3F4F4] focus:outline-none focus:border-[#853953] resize-none font-sans"
            placeholder="Type your agent procurement prompt..."
          />
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
          <div className="flex flex-wrap gap-2">
            <span className="text-[11px] text-zinc-400 self-center font-medium mr-1">Presets:</span>
            {presets.map((p, idx) => (
              <button
                key={idx}
                onClick={() => setPrompt(p.text)}
                disabled={isRunning}
                className="text-xs px-3 py-1.5 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a] hover:border-[#853953]/50 hover:bg-[#612D53]/40 text-zinc-200 transition text-left"
              >
                {p.label}
              </button>
            ))}
          </div>

          <button
            onClick={handleRunFlow}
            disabled={isRunning || !prompt.trim()}
            className="px-6 py-2.5 bg-[#853953] hover:bg-[#9c4362] disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center space-x-2 transition shadow-lg shadow-[#853953]/30 border border-[#853953]/50"
          >
            <Play className="h-4 w-4 fill-current" />
            <span>{isRunning ? 'Executing Agent Pipeline...' : 'Execute Agent Flow'}</span>
          </button>
        </div>
      </div>

      {/* Execution Stepper Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Step Navigation Cards */}
        <div className="lg:col-span-5 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-300 mb-2 flex items-center gap-1.5">
            <Layers className="h-4 w-4 text-[#853953]" /> Execution Pipeline Steps
          </h3>

          {logs.map((log) => {
            const isSuccess = log.status === 'success';
            const isFailed = log.status === 'failed';
            const isRunningStep = log.status === 'running';

            let cardBorder = 'border-[#3a3a3a] bg-[#2C2C2C]';
            if (isRunningStep) cardBorder = 'border-[#853953] bg-[#612D53]/30 animate-pulse';
            else if (isSuccess) cardBorder = 'border-emerald-500/40 bg-[#2C2C2C]';
            else if (isFailed) cardBorder = 'border-rose-500/40 bg-rose-950/20';

            return (
              <div
                key={log.step}
                className={`p-4 rounded-2xl border transition shadow-xl flex items-center justify-between ${cardBorder}`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`h-8 w-8 rounded-xl flex items-center justify-center font-bold text-xs font-mono border ${
                    isSuccess
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                      : isFailed
                      ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                      : isRunningStep
                      ? 'bg-[#853953] text-white border-[#853953]'
                      : 'bg-[#1c1c1c] text-zinc-400 border-[#3a3a3a]'
                  }`}>
                    {log.step}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-[#F3F4F4]">{log.title}</h4>
                    <span className="text-[10px] font-mono text-zinc-400 capitalize">{log.status}</span>
                  </div>
                </div>

                <div>
                  {isSuccess && <CheckCircle2 className="h-5 w-5 text-emerald-400" />}
                  {isFailed && <AlertCircle className="h-5 w-5 text-rose-400" />}
                  {isRunningStep && <RefreshCw className="h-5 w-5 text-[#853953] animate-spin" />}
                </div>
              </div>
            );
          })}
        </div>

        {/* Detailed Inspection Slot */}
        <div className="lg:col-span-7 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-300 mb-2 flex items-center gap-1.5">
            <FileCheck className="h-4 w-4 text-[#853953]" /> Live Step Output Inspector
          </h3>

          <div className="bg-[#2C2C2C] p-6 rounded-2xl border border-[#3a3a3a] min-h-[420px] flex flex-col justify-between shadow-xl">
            {/* Step Details Container */}
            <div className="space-y-4">
              {discoveredProduct && (
                <div className="p-4 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a] space-y-2">
                  <div className="flex justify-between items-center text-xs font-bold text-[#F3F4F4]">
                    <span>Catalog Product Matched: {discoveredProduct.name}</span>
                    <span className="text-[#a85890] font-mono">₹{discoveredProduct.price}</span>
                  </div>
                  <p className="text-[11px] text-zinc-400">SKU: {discoveredProduct.sku} | In Stock: {discoveredProduct.stock}</p>
                </div>
              )}

              {negotiationResult && (
                <div className="p-4 rounded-xl bg-[#1c1c1c] border border-[#853953]/40 space-y-2">
                  <div className="flex justify-between items-center text-xs font-bold text-[#F3F4F4]">
                    <span className="flex items-center gap-1"><DollarSign className="h-4 w-4 text-[#853953]" /> AI Counter-Offer Agreed</span>
                    <span className="text-emerald-400 font-mono">₹{negotiationResult.counter_offer_price} / unit</span>
                  </div>
                  <p className="text-[11px] text-zinc-300 font-mono">Original: ₹{negotiationResult.original_price} → Agreed Discount: {(((negotiationResult.original_price - negotiationResult.counter_offer_price)/negotiationResult.original_price)*100).toFixed(1)}%</p>
                </div>
              )}

              {policyResult && (
                <div className="p-4 rounded-xl bg-[#1c1c1c] border border-[#3a3a3a] space-y-1">
                  <div className="flex justify-between items-center text-xs font-bold">
                    <span className="text-zinc-200">Merchant Policy Decision:</span>
                    <span className="text-emerald-400 font-mono">{policyResult.decision}</span>
                  </div>
                  <p className="text-[11px] text-zinc-400">Verified rule signatures against spending limit policies.</p>
                </div>
              )}

              {razorpayOrder && (
                <div className="p-5 rounded-2xl bg-gradient-to-br from-[#612D53]/30 via-[#2C2C2C] to-[#853953]/20 border border-[#853953]/50 space-y-4 shadow-xl">
                  <div className="flex items-center justify-between border-b border-[#3a3a3a] pb-3">
                    <div className="flex items-center space-x-2">
                      <CreditCard className="h-5 w-5 text-[#853953]" />
                      <h4 className="text-sm font-bold text-[#F3F4F4]">Razorpay Order Ready</h4>
                    </div>
                    <span className="text-xs font-mono font-bold text-emerald-400">₹{(((razorpayOrder.amount || razorpayOrder.amount_paise || 0) / 100)).toFixed(2)}</span>
                  </div>

                  <div className="text-xs space-y-1 font-mono text-zinc-300">
                    <div>Order ID: <span className="text-[#a85890]">{razorpayOrder.razorpay_order_id || razorpayOrder.order_id}</span></div>
                    <div>Key ID: <span className="text-zinc-400">{razorpayOrder.razorpay_key_id || razorpayOrder.key_id}</span></div>
                  </div>

                  {checkoutError && (
                    <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300">
                      {checkoutError}
                    </div>
                  )}

                  {/* Prominent Razorpay Checkout Action */}
                  <div className="space-y-2 pt-2">
                    <button
                      onClick={handleOpenRazorpayModal}
                      disabled={!isRzpLoaded || !razorpayOrder || (!razorpayOrder.razorpay_order_id && !razorpayOrder.order_id)}
                      className="w-full py-3 rounded-xl bg-[#853953] hover:bg-[#9c4362] disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-xs shadow-lg shadow-[#853953]/40 border border-[#853953]/60 transition flex items-center justify-center space-x-2"
                    >
                      <CreditCard className="h-4 w-4" />
                      <span>Pay with Razorpay Checkout UI</span>
                    </button>

                    <button
                      onClick={handleSimulatePayment}
                      className="w-full py-2.5 rounded-xl bg-[#1c1c1c] hover:bg-[#612D53]/40 text-zinc-300 font-semibold text-xs border border-[#3a3a3a] transition flex items-center justify-center space-x-2"
                    >
                      <ShieldCheck className="h-4 w-4 text-zinc-400" />
                      <span>Quick Signature Verification (Test Mode)</span>
                    </button>
                  </div>
                </div>
              )}

              {paymentVerificationResult && (
                <div className="p-5 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 space-y-3">
                  <div className="flex items-center space-x-2 text-emerald-400 font-bold text-xs">
                    <CheckCircle2 className="h-5 w-5" />
                    <span>Payment Verification & Settlement Complete!</span>
                  </div>
                  <div className="text-xs font-mono text-zinc-300 space-y-1">
                    <div>Status: <span className="text-emerald-400 font-bold">PAID / SETTLED</span></div>
                    <div>Payment ID: <span className="text-zinc-300">{paymentVerificationResult.payment_id || 'Captured'}</span></div>
                    <div>Inventory Deducted: <span className="text-emerald-400">Yes</span></div>
                  </div>
                </div>
              )}

              {!discoveredProduct && !isRunning && (
                <div className="flex flex-col items-center justify-center h-64 text-center space-y-3 text-zinc-400">
                  <Sparkles className="h-10 w-10 text-[#853953] opacity-60" />
                  <p className="text-xs max-w-sm">Click "Execute Agent Flow" above to trigger autonomous agent procurement and Razorpay checkout.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
