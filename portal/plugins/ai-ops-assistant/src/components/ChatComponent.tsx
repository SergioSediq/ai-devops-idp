import React, { useState } from 'react';

// ─── Types ───────────────────────────────────────────────────
interface FixCommand {
  command: string;
  description: string;
  risk_level: string;
}

interface RelatedRunbook {
  title: string;
  filename: string;
  relevance_score: number;
}

interface DiagnoseResponse {
  request_id: string;
  timestamp: string;
  severity: string;
  error_category: string;
  root_cause: string;
  explanation: string;
  fix_commands: FixCommand[];
  prevention_tips: string[];
  related_runbooks: RelatedRunbook[];
  k8s_context?: Record<string, unknown>;
  classified_errors?: Array<Record<string, unknown>>;
}

// ─── Severity Color Map ─────────────────────────────────────
const SEVERITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  CRITICAL: { bg: '#fef2f2', text: '#dc2626', border: '#fca5a5' },
  HIGH: { bg: '#fff7ed', text: '#ea580c', border: '#fdba74' },
  MEDIUM: { bg: '#fffbeb', text: '#d97706', border: '#fcd34d' },
  LOW: { bg: '#f0fdf4', text: '#16a34a', border: '#86efac' },
  INFO: { bg: '#eff6ff', text: '#2563eb', border: '#93c5fd' },
};

const RISK_COLORS: Record<string, string> = {
  LOW: '#16a34a',
  MEDIUM: '#d97706',
  HIGH: '#dc2626',
};

// ─── Styles ─────────────────────────────────────────────────
const styles: Record<string, React.CSSProperties> = {
  container: {
    maxWidth: 900,
    margin: '0 auto',
    padding: 24,
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginBottom: 24,
  },
  headerIcon: {
    fontSize: 28,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 700,
    color: '#1e293b',
    margin: 0,
  },
  inputSection: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 12,
    marginBottom: 32,
  },
  textarea: {
    width: '100%',
    minHeight: 120,
    padding: 16,
    border: '2px solid #e2e8f0',
    borderRadius: 12,
    fontSize: 14,
    fontFamily: 'monospace',
    resize: 'vertical' as const,
    outline: 'none',
    transition: 'border-color 0.2s',
  },
  inputRow: {
    display: 'flex',
    gap: 12,
    flexWrap: 'wrap' as const,
    alignItems: 'center',
  },
  input: {
    flex: 1,
    minWidth: 150,
    padding: '10px 14px',
    border: '2px solid #e2e8f0',
    borderRadius: 8,
    fontSize: 14,
    outline: 'none',
  },
  button: {
    padding: '12px 28px',
    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    color: '#fff',
    border: 'none',
    borderRadius: 10,
    fontSize: 15,
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'transform 0.15s, box-shadow 0.15s',
  },
  buttonDisabled: {
    opacity: 0.6,
    cursor: 'not-allowed',
  },
  // Response sections
  responseCard: {
    border: '1px solid #e2e8f0',
    borderRadius: 16,
    overflow: 'hidden',
    marginTop: 20,
    boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
  },
  severityBanner: {
    padding: '14px 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  badge: {
    padding: '4px 12px',
    borderRadius: 20,
    fontSize: 12,
    fontWeight: 700,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.5,
  },
  section: {
    padding: '16px 20px',
    borderTop: '1px solid #f1f5f9',
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: 700,
    textTransform: 'uppercase' as const,
    letterSpacing: 0.8,
    color: '#64748b',
    marginBottom: 10,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  rootCause: {
    fontSize: 17,
    fontWeight: 600,
    color: '#1e293b',
    margin: 0,
  },
  explanation: {
    fontSize: 14,
    lineHeight: 1.7,
    color: '#475569',
    margin: 0,
    whiteSpace: 'pre-wrap' as const,
  },
  commandCard: {
    background: '#1e293b',
    borderRadius: 10,
    padding: 14,
    marginBottom: 10,
    position: 'relative' as const,
  },
  commandText: {
    fontFamily: '"Fira Code", "Cascadia Code", monospace',
    fontSize: 13,
    color: '#e2e8f0',
    margin: 0,
    wordBreak: 'break-all' as const,
  },
  commandDesc: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 8,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  copyBtn: {
    position: 'absolute' as const,
    top: 10,
    right: 10,
    padding: '4px 10px',
    background: 'rgba(255,255,255,0.1)',
    border: '1px solid rgba(255,255,255,0.2)',
    borderRadius: 6,
    color: '#94a3b8',
    fontSize: 11,
    cursor: 'pointer',
  },
  tipItem: {
    display: 'flex',
    gap: 8,
    marginBottom: 8,
    fontSize: 14,
    color: '#475569',
  },
  runbookLink: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 14px',
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    fontSize: 13,
    color: '#6366f1',
    textDecoration: 'none',
    marginRight: 8,
    marginBottom: 8,
    cursor: 'pointer',
  },
  errorBox: {
    padding: 16,
    background: '#fef2f2',
    border: '1px solid #fca5a5',
    borderRadius: 12,
    color: '#dc2626',
    fontSize: 14,
    marginTop: 20,
  },
  loadingDots: {
    display: 'flex',
    gap: 6,
    padding: 32,
    justifyContent: 'center',
  },
};

// ─── Component ──────────────────────────────────────────────
const ChatComponent: React.FC = () => {
  const [errorMessage, setErrorMessage] = useState('');
  const [podName, setPodName] = useState('');
  const [namespace, setNamespace] = useState('default');
  const [deploymentName, setDeploymentName] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<DiagnoseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const API_BASE = process.env.REACT_APP_AI_AGENT_URL || 'http://localhost:8000';

  const handleDiagnose = async () => {
    if (!errorMessage.trim()) return;
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch(`${API_BASE}/diagnose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error_message: errorMessage,
          pod_name: podName || undefined,
          namespace: namespace || 'default',
          deployment_name: deploymentName || undefined,
          include_cluster_health: true,
        }),
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || `HTTP ${res.status}`);
      }

      const data: DiagnoseResponse = await res.json();
      setResponse(data);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to AI Agent');
    } finally {
      setLoading(false);
    }
  };

  const copyCommand = (cmd: string, idx: number) => {
    navigator.clipboard.writeText(cmd);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const sev = response ? SEVERITY_COLORS[response.severity] || SEVERITY_COLORS.INFO : null;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.headerIcon}>🤖</span>
        <h1 style={styles.headerTitle}>AI DevOps Assistant</h1>
      </div>

      {/* Input Section */}
      <div style={styles.inputSection}>
        <textarea
          style={styles.textarea}
          placeholder="Paste your error logs, kubectl output, or describe the issue..."
          value={errorMessage}
          onChange={e => setErrorMessage(e.target.value)}
          onFocus={e => (e.target.style.borderColor = '#6366f1')}
          onBlur={e => (e.target.style.borderColor = '#e2e8f0')}
        />
        <div style={styles.inputRow}>
          <input
            style={styles.input}
            placeholder="Pod name (optional)"
            value={podName}
            onChange={e => setPodName(e.target.value)}
          />
          <input
            style={styles.input}
            placeholder="Namespace"
            value={namespace}
            onChange={e => setNamespace(e.target.value)}
          />
          <input
            style={styles.input}
            placeholder="Deployment (optional)"
            value={deploymentName}
            onChange={e => setDeploymentName(e.target.value)}
          />
          <button
            style={{
              ...styles.button,
              ...(loading ? styles.buttonDisabled : {}),
            }}
            onClick={handleDiagnose}
            disabled={loading || !errorMessage.trim()}
          >
            {loading ? '⏳ Analyzing...' : '🔍 Diagnose'}
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div style={styles.loadingDots}>
          {[0, 1, 2].map(i => (
            <div
              key={i}
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: '#6366f1',
                animation: `pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </div>
      )}

      {/* Error */}
      {error && <div style={styles.errorBox}>❌ {error}</div>}

      {/* Response */}
      {response && sev && (
        <div style={styles.responseCard}>
          {/* Severity Banner */}
          <div style={{ ...styles.severityBanner, background: sev.bg, borderBottom: `2px solid ${sev.border}` }}>
            <span style={{ ...styles.badge, color: sev.text, border: `1.5px solid ${sev.border}` }}>
              {response.severity}
            </span>
            <span style={{ ...styles.badge, color: '#64748b', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
              {response.error_category}
            </span>
            <span style={{ fontSize: 11, color: '#94a3b8' }}>
              ID: {response.request_id}
            </span>
          </div>

          {/* Root Cause */}
          <div style={styles.section}>
            <div style={styles.sectionTitle}>🎯 Root Cause</div>
            <p style={styles.rootCause}>{response.root_cause}</p>
          </div>

          {/* Explanation */}
          <div style={styles.section}>
            <div style={styles.sectionTitle}>📋 Explanation</div>
            <p style={styles.explanation}>{response.explanation}</p>
          </div>

          {/* Fix Commands */}
          {response.fix_commands.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>🔧 Fix Commands</div>
              {response.fix_commands.map((cmd, idx) => (
                <div key={idx} style={styles.commandCard}>
                  <button
                    style={styles.copyBtn}
                    onClick={() => copyCommand(cmd.command, idx)}
                  >
                    {copiedIdx === idx ? '✅ Copied' : '📋 Copy'}
                  </button>
                  <pre style={styles.commandText}>$ {cmd.command}</pre>
                  <div style={styles.commandDesc}>
                    <span>{cmd.description}</span>
                    <span style={{
                      color: RISK_COLORS[cmd.risk_level] || '#64748b',
                      fontWeight: 600,
                      fontSize: 11,
                    }}>
                      Risk: {cmd.risk_level}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Prevention Tips */}
          {response.prevention_tips.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>🛡️ Prevention Tips</div>
              {response.prevention_tips.map((tip, idx) => (
                <div key={idx} style={styles.tipItem}>
                  <span>💡</span>
                  <span>{tip}</span>
                </div>
              ))}
            </div>
          )}

          {/* Related Runbooks */}
          {response.related_runbooks.length > 0 && (
            <div style={styles.section}>
              <div style={styles.sectionTitle}>📚 Related Runbooks</div>
              <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                {response.related_runbooks.map((rb, idx) => (
                  <span key={idx} style={styles.runbookLink}>
                    📖 {rb.title || rb.filename}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ChatComponent;
