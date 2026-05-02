"use client";
import React, { useState, useEffect } from "react";
import { DollarSign, Cpu, Layers, Clock, CheckCircle2, AlertCircle, FileText, Download, Printer, X, RefreshCw, Maximize2, Minimize2 } from "lucide-react";
import { getProjectLedger } from "@/lib/apiClient";
import styles from "./ProjectLedger.module.css";

interface LedgerEntry {
  timestamp: string;
  persona: string;
  provider: string;
  model: string;
  metrics: {
    total_tokens: number;
  };
  estimated_cost: number;
  unit: string;
  is_free: boolean;
  duration_seconds: number;
}

interface ProjectLedgerProps {
  folderPath: string;
  onClose: () => void;
}

export default function ProjectLedger({ folderPath, onClose }: ProjectLedgerProps) {
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMaximized, setIsMaximized] = useState(false);

  const fetchLedger = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getProjectLedger(folderPath);
      setLedger(data.ledger || []);
    } catch (err) {
      setError("Failed to retrieve ledger from the vault.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (folderPath) fetchLedger();
  }, [folderPath]);

  const totalCost = ledger.reduce((sum, entry) => sum + (entry.estimated_cost || 0), 0);
  const totalTokens = ledger.reduce((sum, entry) => sum + (entry.metrics?.total_tokens || 0), 0);
  const totalDuration = ledger.reduce((sum, entry) => sum + (entry.duration_seconds || 0), 0);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 4 }).format(val);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className={styles.overlay}>
      <div className={`${styles.modal} ${isMaximized ? styles.maximized : ""}`}>
        <div className={styles.header}>
          <div className={styles.titleGroup}>
            <Layers className={styles.headerIcon} />
            <div>
              <h1>AI Usage Ledger</h1>
              <p className={styles.path}>{folderPath}</p>
            </div>
          </div>
          <div className={styles.actions}>
            <button onClick={fetchLedger} className={styles.iconButton} title="Refesh Ledger">
              <RefreshCw className={isLoading ? styles.spinning : ""} />
            </button>
            <button onClick={handlePrint} className={styles.iconButton} title="Print Report">
              <Printer />
            </button>
            <button onClick={() => setIsMaximized(!isMaximized)} className={styles.iconButton} title={isMaximized ? "Restore" : "Maximize"}>
              {isMaximized ? <Minimize2 /> : <Maximize2 />}
            </button>
            <button onClick={onClose} className={styles.closeButton}>
              <X />
            </button>
          </div>
        </div>

        <div className={styles.summaryGrid}>
          <div className={styles.summaryCard}>
            <DollarSign className={styles.cardIcon} />
            <div className={styles.cardContent}>
              <span className={styles.cardLabel}>Estimated Expenditure</span>
              <span className={styles.cardValue}>{formatCurrency(totalCost)}</span>
            </div>
          </div>
          <div className={styles.summaryCard}>
            <Cpu className={styles.cardIcon} />
            <div className={styles.cardContent}>
              <span className={styles.cardLabel}>Total Token Density</span>
              <span className={styles.cardValue}>{totalTokens.toLocaleString()} tokens</span>
            </div>
          </div>
          <div className={styles.summaryCard}>
            <Clock className={styles.cardIcon} />
            <div className={styles.cardContent}>
              <span className={styles.cardLabel}>Sovereign Uptime</span>
              <span className={styles.cardValue}>{totalDuration.toFixed(1)}s</span>
            </div>
          </div>
        </div>

        <div className={styles.content}>
          {isLoading ? (
            <div className={styles.loader}>
              <RefreshCw className={styles.spinningLarge} />
              <p>Synchronizing with Project Vault...</p>
            </div>
          ) : error ? (
            <div className={styles.error}>
              <AlertCircle />
              <p>{error}</p>
            </div>
          ) : ledger.length === 0 ? (
            <div className={styles.empty}>
              <FileText className={styles.emptyIcon} />
              <p>The ledger is currently blank. Execute an AI audit to begin tracking.</p>
            </div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>specialist</th>
                  <th>provider</th>
                  <th>model</th>
                  <th>Duration</th>
                  <th>tokens</th>
                  <th>credit Cost</th>
                </tr>
              </thead>
              <tbody>
                {ledger.map((entry, idx) => (
                  <tr key={idx}>
                    <td>{new Date(entry.timestamp).toLocaleString()}</td>
                    <td><span className={styles.personaBadge}>{entry.persona}</span></td>
                    <td>{entry.provider}</td>
                    <td className={styles.mono}>{entry.model}</td>
                    <td>{entry.duration_seconds ? `${entry.duration_seconds}s` : '---'}</td>
                    <td>{entry.metrics?.total_tokens?.toLocaleString()}</td>
                    <td className={entry.is_free ? styles.free : styles.paid}>
                      {entry.is_free ? "FREE" : formatCurrency(entry.estimated_cost)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className={styles.footer}>
          <div className={styles.sovereignSeal}>
            <CheckCircle2 size={14} />
            <span>Handshake Verified: Sovereign Accounting Engine</span>
          </div>
          <p className={styles.disclaimer}>* Costs are locally estimated based on token density and current provider rates.</p>
        </div>
      </div>
    </div>
  );
}
