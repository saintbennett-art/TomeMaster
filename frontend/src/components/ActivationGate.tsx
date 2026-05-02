"use client";

import { useEffect, useState } from "react";
import { Lock, Cpu, KeyRound, AlertTriangle } from "lucide-react";
import { checkLicenseStatus, activateLicense } from "@/lib/apiClient";
import { useWorkstationActions } from "@/context/WorkstationContext";

export default function ActivationGate({ children }: { children: React.ReactNode }) {
  const [isActivated, setIsActivated] = useState<boolean | null>(null);
  const [machineId, setMachineId] = useState<string>("");
  const [keyInput, setKeyInput] = useState("");
  const [error, setError] = useState("");
  const [backendError, setBackendError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const { setIsActivated: setContextActivated } = useWorkstationActions();

  useEffect(() => {
    // [SOVEREIGN SENTINEL]: Monitoring for license pulse...
    checkStatus(0);
  }, []);

  const checkStatus = async (currentRetry = 0) => {
    // [SAFETY TIMEOUT]: If the backend is dead, don't leave the user hanging in 'Initialization'
    const timer = setTimeout(() => {
        if (isLoading) setBackendError(true);
    }, 5000);

    try {
      const data = await checkLicenseStatus();
      clearTimeout(timer);
      setMachineId(data.machine_id || "DIAGNOSTIC_ID");
      
      if (data.error === "UNREACHABLE") {
          if (currentRetry < 3) { // Reduced retries for faster user feedback
              setTimeout(() => checkStatus(currentRetry + 1), 2000);
          } else {
              setBackendError(true);
          }
          return;
      }
      
      setIsActivated(data.is_activated === true); 
      setContextActivated(data.is_activated === true);
      setBackendError(false);
    } catch (err) {
      clearTimeout(timer);
      console.error("Failed to check license status", err);
      setIsActivated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyInput.trim()) return;
    
    setError("");
    setIsLoading(true);
    
    try {
      const data = await activateLicense(keyInput);
      setIsActivated(true);
      setContextActivated(true);
    } catch (err: any) {
      setError(err.message || "Server connection failed. Is the backend running?");
    } finally {
      setIsLoading(false);
    }
  };

  // Show a blank dark screen while checking initially to prevent layout flash
  if (isActivated === null) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex flex-col items-center justify-center text-zinc-600 font-mono text-sm tracking-widest uppercase gap-4">
        {backendError ? (
          <>
            <AlertTriangle className="w-8 h-8 text-amber-500 animate-bounce" />
            <div className="text-amber-500 font-bold">Backend Connection Failed</div>
            <div className="text-[10px] lowercase tracking-normal max-w-xs text-center opacity-70">
              Ensure the Python uvicorn server is running on port 8080.
            </div>
            <button 
                onClick={() => { setBackendError(false); setRetryCount(0); checkStatus(0); }}
                className="mt-4 px-6 py-2 bg-indigo-600/20 border border-indigo-500/30 rounded-full text-indigo-400 hover:bg-indigo-600/30 transition-all text-[10px]"
            >
                Retry Connection
            </button>
          </>
        ) : (
          <div className="animate-pulse flex flex-col items-center gap-4">
            <Cpu className="w-6 h-6 text-indigo-500/50" />
            Initializing Core Systems...
          </div>
        )}
      </div>
    );
  }

  if (!isActivated) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-[#111111] border border-[#222222] rounded-2xl p-8 shadow-2xl relative overflow-hidden group">
          {/* Animated Background Aura */}
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent"></div>
          
          <div className="flex flex-col items-center gap-6 relative z-10">
            <div className="w-16 h-16 bg-indigo-600/10 rounded-2xl flex items-center justify-center border border-indigo-500/20 group-hover:scale-110 transition-transform duration-500">
               <Lock className="w-8 h-8 text-indigo-500" />
            </div>
            
            <div className="text-center space-y-2">
               <h2 className="text-2xl font-bold text-white tracking-tight">Activation Required</h2>
               <p className="text-zinc-500 text-sm">Please verify your Directorial Status to unlock the Apex Engine.</p>
            </div>

            <form onSubmit={handleActivate} className="w-full space-y-4">
               <div className="relative">
                  <input
                    type="text"
                    value={keyInput}
                    onChange={(e) => setKeyInput(e.target.value.toUpperCase())}
                    placeholder="APEX-XXXX-XXXX-XXXX"
                    className="w-full bg-[#1a1a1a] border border-[#333333] rounded-xl px-4 py-4 text-white font-mono text-center tracking-widest placeholder:text-zinc-700 outline-none focus:border-indigo-500/50 transition-all uppercase"
                  />
                  <KeyRound className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-600" />
               </div>
               
               {error && (
                 <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 flex items-center gap-3 text-red-500 text-xs">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    {error}
                 </div>
               )}

               <button
                 type="submit"
                 disabled={isLoading || !keyInput}
                 className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-4 rounded-xl transition-all shadow-lg active:scale-[0.98]"
               >
                 {isLoading ? "Verifying..." : "Authorize Workstation"}
               </button>
            </form>

            <div className="border-t border-[#222222] pt-6 flex flex-col items-center gap-4 w-full">
               <button
                  type="button"
                  onClick={() => { setIsActivated(true); setContextActivated(true); }}
                  className="text-[10px] text-zinc-500 hover:text-indigo-400 uppercase tracking-[0.2em] font-bold transition-colors"
               >
                  Start Evaluation Session (Demo)
               </button>
               
               <div className="flex flex-col items-center gap-2">
                  <div className="text-[10px] text-zinc-600 uppercase tracking-widest">Machine Identity</div>
                  <div className="text-[11px] text-zinc-400 font-mono bg-[#1a1a1a] px-3 py-1 rounded-full border border-[#333333]">
                     {machineId}
                  </div>
               </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen flex flex-col">
        {children}
    </div>
  );
}

