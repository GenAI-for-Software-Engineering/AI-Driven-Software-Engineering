import React, { useState, useRef, useEffect, useCallback } from "react";

// ─────────────────────────────────────────────────────────────
//  Constants
// ─────────────────────────────────────────────────────────────
const API_BASE = "http://localhost:3001/api";

const PHASES = [
  { id: 1, name: "Repository Clone" },
  { id: 2, name: "Env Setup" },
  { id: 3, name: "Baseline Tests" },
  { id: 4, name: "Static Analysis" },
  { id: 5, name: "LLM Fix Loop" },
  { id: 6, name: "Final Report" },
];

// ─────────────────────────────────────────────────────────────
//  Styles (injected via style tag)
// ─────────────────────────────────────────────────────────────
const GLOBAL_CSS = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0a0b0e;
    --bg2: #111318;
    --bg3: #181b22;
    --border: #252830;
    --border2: #2e3240;
    --text: #e8eaf0;
    --text2: #8b909e;
    --text3: #555b6e;
    --accent: #00d4aa;
    --accent2: #0099ff;
    --accent3: #ff6b35;
    --red: #ff4d6d;
    --green: #00d4aa;
    --yellow: #ffd166;
    --purple: #b19af7;
    --font-mono: 'JetBrains Mono', monospace;
    --font-display: 'Syne', sans-serif;
  }

  html, body { height: 100%; background: var(--bg); color: var(--text); }
  body { font-family: var(--font-display); overflow-x: hidden; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg2); }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }

  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 0 rgba(0, 212, 170, 0.15); }
    50% { box-shadow: 0 0 20px 4px rgba(0, 212, 170, 0.25); }
  }

  @keyframes slide-in {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @keyframes scan {
    0% { top: 0; }
    100% { top: 100%; }
  }

  .animate-in { animation: slide-in 0.25s ease forwards; }

  .spinner {
    width: 16px; height: 16px;
    border: 2px solid var(--border2);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    display: inline-block;
  }
`;

// ─────────────────────────────────────────────────────────────
//  Small UI Components
// ─────────────────────────────────────────────────────────────

function Badge({ children, color = "accent", style = {} }) {
  const colors = {
    accent: { bg: "rgba(0,212,170,0.12)", color: "var(--accent)", border: "rgba(0,212,170,0.25)" },
    blue: { bg: "rgba(0,153,255,0.12)", color: "var(--accent2)", border: "rgba(0,153,255,0.25)" },
    red: { bg: "rgba(255,77,109,0.12)", color: "var(--red)", border: "rgba(255,77,109,0.25)" },
    yellow: { bg: "rgba(255,209,102,0.12)", color: "var(--yellow)", border: "rgba(255,209,102,0.25)" },
    purple: { bg: "rgba(177,154,247,0.12)", color: "var(--purple)", border: "rgba(177,154,247,0.25)" },
    gray: { bg: "rgba(139,144,158,0.1)", color: "var(--text2)", border: "rgba(139,144,158,0.2)" },
  };
  const c = colors[color] || colors.accent;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      padding: "2px 8px", borderRadius: "4px", fontSize: "11px",
      fontFamily: "var(--font-mono)", fontWeight: 600,
      background: c.bg, color: c.color,
      border: `1px solid ${c.border}`, ...style
    }}>
      {children}
    </span>
  );
}

function Card({ children, style = {}, glow = false }) {
  return (
    <div style={{
      background: "var(--bg2)", border: "1px solid var(--border)",
      borderRadius: "12px", overflow: "hidden",
      animation: glow ? "pulse-glow 2s ease-in-out infinite" : "none",
      ...style
    }}>
      {children}
    </div>
  );
}

function CardHeader({ title, badge, right }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      padding: "12px 16px", borderBottom: "1px solid var(--border)",
      background: "var(--bg3)",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <span style={{ fontWeight: 700, fontSize: "13px", letterSpacing: "0.02em" }}>{title}</span>
        {badge}
      </div>
      {right}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
//  Phase Progress Bar
// ─────────────────────────────────────────────────────────────
function PhaseBar({ currentPhase }) {
  return (
    <div style={{ display: "flex", gap: "4px", marginBottom: "20px" }}>
      {PHASES.map((p) => {
        const done = currentPhase > p.id;
        const active = currentPhase === p.id;
        return (
          <div key={p.id} style={{ flex: 1 }}>
            <div style={{
              height: "3px", borderRadius: "2px", marginBottom: "6px",
              background: done ? "var(--accent)" : active ? "var(--accent2)" : "var(--border2)",
              transition: "background 0.4s ease",
            }} />
            <div style={{
              fontSize: "10px", fontFamily: "var(--font-mono)",
              color: done ? "var(--accent)" : active ? "var(--accent2)" : "var(--text3)",
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
              transition: "color 0.4s ease",
            }}>
              {p.id}. {p.name}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
//  Terminal Log
// ─────────────────────────────────────────────────────────────
function Terminal({ logs }) {
  const bottomRef = useRef(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [logs]);

  return (
    <Card style={{ height: "340px", display: "flex", flexDirection: "column" }}>
      <CardHeader
        title="PIPELINE LOG"
        badge={<Badge color="gray">{logs.length} lines</Badge>}
        right={
          <div style={{ display: "flex", gap: "6px" }}>
            {["#ff5f57", "#febc2e", "#28c840"].map((c, i) => (
              <div key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />
            ))}
          </div>
        }
      />
      <div style={{
        flex: 1, overflowY: "auto", padding: "12px 16px",
        fontFamily: "var(--font-mono)", fontSize: "12px", lineHeight: "1.7",
      }}>
        {logs.length === 0 && (
          <div style={{ color: "var(--text3)" }}>Waiting for pipeline to start...</div>
        )}
        {logs.map((log, i) => (
          <div key={i} style={{ color: "var(--text2)", animation: "slide-in 0.15s ease forwards" }}>
            <span style={{ color: "var(--text3)", marginRight: "8px", userSelect: "none" }}>
              {String(i + 1).padStart(3, "0")}
            </span>
            {log}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
//  Iteration Metrics Table
// ─────────────────────────────────────────────────────────────
function MetricsTable({ iterations }) {
  if (!iterations || iterations.length === 0) return null;
  return (
    <Card>
      <CardHeader title="ITERATION METRICS" badge={<Badge color="blue">{iterations.length} iterations</Badge>} />
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--font-mono)", fontSize: "12px" }}>
          <thead>
            <tr style={{ background: "var(--bg3)" }}>
              {["Iteration", "Tests Passed", "Tests Failed", "Bugs Found", "Fixes Applied", "Status"].map((h) => (
                <th key={h} style={{
                  padding: "10px 14px", textAlign: "left",
                  color: "var(--text2)", fontWeight: 600, fontSize: "11px",
                  borderBottom: "1px solid var(--border2)",
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {iterations.map((row, i) => (
              <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                <td style={{ padding: "10px 14px", color: "var(--text2)" }}>
                  {row.iteration === 0 ? "Baseline" : `#${row.iteration}`}
                </td>
                <td style={{ padding: "10px 14px", color: "var(--green)", fontWeight: 700 }}>
                  {row.passed ?? "—"}
                </td>
                <td style={{ padding: "10px 14px", color: row.failed > 0 ? "var(--red)" : "var(--green)", fontWeight: 700 }}>
                  {row.failed ?? "—"}
                </td>
                <td style={{ padding: "10px 14px", color: "var(--yellow)" }}>
                  {row.bugsFound ?? "—"}
                </td>
                <td style={{ padding: "10px 14px", color: "var(--accent2)" }}>
                  {row.fixesApplied ?? "—"}
                </td>
                <td style={{ padding: "10px 14px" }}>
                  <Badge color={
                    row.status === "resolved" || row.status === "clean" ? "accent" :
                    row.status === "partial" ? "yellow" : "red"
                  }>
                    {row.status?.toUpperCase()}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
//  Bug Card
// ─────────────────────────────────────────────────────────────
function BugCard({ bug, index }) {
  const [expanded, setExpanded] = useState(false);
  const severityColor = { critical: "red", high: "red", medium: "yellow", low: "accent" }[bug.severity] || "gray";

  return (
    <div style={{
      border: "1px solid var(--border2)", borderRadius: "8px",
      overflow: "hidden", marginBottom: "8px", animation: "slide-in 0.2s ease forwards",
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: "flex", alignItems: "center", gap: "12px",
          padding: "12px 14px", cursor: "pointer",
          background: expanded ? "var(--bg3)" : "transparent",
          transition: "background 0.2s",
        }}
      >
        <Badge color="gray" style={{ fontWeight: 700 }}>{bug.id}</Badge>
        <Badge color={severityColor}>{bug.severity?.toUpperCase()}</Badge>
        <span style={{ fontSize: "13px", flex: 1, color: "var(--text)" }}>{bug.description}</span>
        <span style={{ color: "var(--text2)", fontSize: "12px", fontFamily: "var(--font-mono)" }}>{bug.file}</span>
        <span style={{ color: "var(--text3)", fontSize: "18px" }}>{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && (
        <div style={{ padding: "14px", background: "var(--bg3)", borderTop: "1px solid var(--border)" }}>
          <div style={{ marginBottom: "12px" }}>
            <div style={{ fontSize: "11px", color: "var(--text3)", marginBottom: "4px", fontFamily: "var(--font-mono)" }}>ROOT CAUSE</div>
            <div style={{ fontSize: "13px", color: "var(--text2)", lineHeight: 1.6 }}>{bug.root_cause}</div>
          </div>

          {bug.explanation && (
            <div style={{ marginBottom: "12px" }}>
              <div style={{ fontSize: "11px", color: "var(--text3)", marginBottom: "4px", fontFamily: "var(--font-mono)" }}>EXPLANATION</div>
              <div style={{ fontSize: "13px", color: "var(--text2)", lineHeight: 1.6 }}>{bug.explanation}</div>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <div style={{ fontSize: "11px", color: "var(--red)", marginBottom: "6px", fontFamily: "var(--font-mono)", fontWeight: 700 }}>— BEFORE (Buggy)</div>
              <pre style={{
                background: "rgba(255,77,109,0.07)", border: "1px solid rgba(255,77,109,0.2)",
                borderRadius: "6px", padding: "10px", fontSize: "11px",
                fontFamily: "var(--font-mono)", overflow: "auto", color: "var(--text)",
                maxHeight: "200px",
              }}>{bug.original_code}</pre>
            </div>
            <div>
              <div style={{ fontSize: "11px", color: "var(--green)", marginBottom: "6px", fontFamily: "var(--font-mono)", fontWeight: 700 }}>+ AFTER (Fixed)</div>
              <pre style={{
                background: "rgba(0,212,170,0.07)", border: "1px solid rgba(0,212,170,0.2)",
                borderRadius: "6px", padding: "10px", fontSize: "11px",
                fontFamily: "var(--font-mono)", overflow: "auto", color: "var(--text)",
                maxHeight: "200px",
              }}>{bug.fixed_code}</pre>
            </div>
          </div>

          <div style={{ marginTop: "10px", display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "11px", color: "var(--text3)" }}>Confidence:</span>
            <div style={{ flex: 1, background: "var(--border2)", borderRadius: "4px", height: "4px" }}>
              <div style={{
                height: "4px", borderRadius: "4px",
                background: bug.confidence > 0.7 ? "var(--green)" : bug.confidence > 0.4 ? "var(--yellow)" : "var(--red)",
                width: `${(bug.confidence || 0) * 100}%`,
              }} />
            </div>
            <span style={{ fontSize: "11px", fontFamily: "var(--font-mono)", color: "var(--text2)" }}>
              {Math.round((bug.confidence || 0) * 100)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
//  Static Issues Panel
// ─────────────────────────────────────────────────────────────
function StaticIssuesPanel({ issues }) {
  if (!issues || issues.length === 0) return null;
  const sevColor = { critical: "var(--red)", high: "var(--red)", medium: "var(--yellow)", low: "var(--text2)" };
  return (
    <Card>
      <CardHeader
        title="STATIC ANALYSIS"
        badge={<Badge color={issues.filter(i => i.severity === "critical" || i.severity === "high").length > 0 ? "red" : "yellow"}>{issues.length} issues</Badge>}
      />
      <div style={{ padding: "12px 16px", maxHeight: "220px", overflowY: "auto" }}>
        {issues.map((issue, i) => (
          <div key={i} style={{
            display: "flex", gap: "10px", padding: "8px 0",
            borderBottom: i < issues.length - 1 ? "1px solid var(--border)" : "none",
            animation: "slide-in 0.2s ease forwards",
          }}>
            <span style={{
              width: "8px", height: "8px", borderRadius: "50%", marginTop: "5px", flexShrink: 0,
              background: sevColor[issue.severity] || "var(--text3)",
            }} />
            <div>
              <div style={{ fontSize: "12px", color: "var(--text)", lineHeight: 1.4 }}>{issue.issue}</div>
              <div style={{ fontSize: "11px", color: "var(--text3)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>
                {issue.file}{issue.line ? `:${issue.line}` : ""}
                {" "}
                <Badge color="gray">{issue.category}</Badge>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ─────────────────────────────────────────────────────────────
//  Final Report Banner
// ─────────────────────────────────────────────────────────────
function FinalReportBanner({ report }) {
  if (!report) return null;
  const isSuccess = report.finalStatus === "success";
  const isPartial = report.finalStatus === "partial";

  return (
    <div style={{
      border: `1px solid ${isSuccess ? "rgba(0,212,170,0.4)" : isPartial ? "rgba(255,209,102,0.4)" : "rgba(255,77,109,0.4)"}`,
      borderRadius: "12px", padding: "20px",
      background: isSuccess ? "rgba(0,212,170,0.06)" : isPartial ? "rgba(255,209,102,0.06)" : "rgba(255,77,109,0.06)",
      animation: "slide-in 0.3s ease forwards",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
        <span style={{ fontSize: "28px" }}>{isSuccess ? "✅" : isPartial ? "⚠️" : "❌"}</span>
        <div>
          <div style={{
            fontSize: "18px", fontWeight: 800,
            color: isSuccess ? "var(--green)" : isPartial ? "var(--yellow)" : "var(--red)",
          }}>
            {isSuccess ? "All Tests Passing" : isPartial ? "Partial Fix Applied" : "Bugs Remain"}
          </div>
          <div style={{ fontSize: "13px", color: "var(--text2)" }}>
            {report.repoName} · {report.language} · {report.framework !== "none" ? report.framework : ""}
          </div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
        {[
          { label: "Final Passed", value: report.finalPassed, color: "var(--green)" },
          { label: "Final Failed", value: report.finalFailed, color: report.finalFailed > 0 ? "var(--red)" : "var(--green)" },
          { label: "Iterations Run", value: report.iterations?.length, color: "var(--accent2)" },
          { label: "Fixes Applied", value: report.totalFixesApplied, color: "var(--purple)" },
        ].map((stat) => (
          <div key={stat.label} style={{
            background: "var(--bg2)", borderRadius: "8px", padding: "12px",
            border: "1px solid var(--border)",
          }}>
            <div style={{ fontSize: "24px", fontWeight: 800, fontFamily: "var(--font-mono)", color: stat.color }}>
              {stat.value ?? "—"}
            </div>
            <div style={{ fontSize: "11px", color: "var(--text3)", marginTop: "2px" }}>{stat.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
//  Main App
// ─────────────────────────────────────────────────────────────
export default function App() {
  const [repoUrl, setRepoUrl] = useState("");
  const [running, setRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [currentPhase, setCurrentPhase] = useState(0);
  const [repoInfo, setRepoInfo] = useState(null);
  const [allBugs, setAllBugs] = useState([]);
  const [staticIssues, setStaticIssues] = useState([]);
  const [testHistory, setTestHistory] = useState([]);
  const [iterationResults, setIterationResults] = useState([]);
  const [finalReport, setFinalReport] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | running | complete | error
  const [activeTab, setActiveTab] = useState("terminal");
  const [appliedFixes, setAppliedFixes] = useState([]);

  const eventSourceRef = useRef(null);
  const addLog = useCallback((msg) => setLogs((l) => [...l, msg]), []);

  function reset() {
    setLogs([]); setCurrentPhase(0); setRepoInfo(null); setAllBugs([]);
    setStaticIssues([]); setTestHistory([]); setIterationResults([]);
    setFinalReport(null); setStatus("idle"); setAppliedFixes([]);
  }

  async function startPipeline() {
    if (!repoUrl.trim()) return;
    reset();
    setRunning(true);
    setStatus("running");

    try {
      // Step 1: Create session
      const res = await fetch(`http://localhost:3001/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repoUrl: repoUrl.trim() }),
      });
      const { sessionId } = await res.json();

      // Step 2: Connect SSE
      const es = new EventSource(`http://localhost:3001/api/stream/${sessionId}`);
      eventSourceRef.current = es;

      es.onmessage = (evt) => {
        const { type, payload } = JSON.parse(evt.data);

        switch (type) {
          case "log": addLog(payload); break;
          case "phase": setCurrentPhase(payload.phase); break;
          case "repo_info": setRepoInfo(payload); break;
          case "static_results":
            setStaticIssues(payload.issues || []);
            break;
          case "test_results":
            setTestHistory((h) => [...h, payload]);
            break;
          case "llm_analysis":
            if (payload.bugs?.length > 0) {
              setAllBugs((b) => {
                const ids = new Set(b.map((x) => x.id));
                const newOnes = payload.bugs.filter((x) => !ids.has(x.id));
                return [...b, ...newOnes];
              });
            }
            break;
          case "fixes_applied":
            setAppliedFixes((f) => [...f, ...payload.diffs]);
            break;
          case "iteration_complete":
            setIterationResults((r) => [...r, payload]);
            break;
          case "final_report":
            setFinalReport(payload);
            setIterationResults(payload.iterations || []);
            setCurrentPhase(6);
            break;
          case "complete":
            setStatus(payload.status === "error" ? "error" : "complete");
            setRunning(false);
            es.close();
            break;
          case "error":
            addLog(`❌ ERROR: ${payload.message}`);
            setStatus("error");
            setRunning(false);
            es.close();
            break;
        }
      };

      es.onerror = () => {
        setStatus("error");
        setRunning(false);
        es.close();
      };
    } catch (err) {
      addLog(`❌ Failed to start: ${err.message}`);
      setStatus("error");
      setRunning(false);
    }
  }

  const lastTest = testHistory[testHistory.length - 1];

  const tabs = [
    { id: "terminal", label: "Terminal", count: logs.length },
    { id: "bugs", label: "Bugs & Fixes", count: allBugs.length },
    { id: "static", label: "Static", count: staticIssues.length },
    { id: "metrics", label: "Metrics", count: iterationResults.length },
    { id: "diffs", label: "Diffs", count: appliedFixes.length },
  ];

  return (
    <>
      <style>{GLOBAL_CSS}</style>
      <div style={{
        minHeight: "100vh", background: "var(--bg)",
        backgroundImage: "radial-gradient(ellipse at 20% 0%, rgba(0,212,170,0.04) 0%, transparent 60%), radial-gradient(ellipse at 80% 0%, rgba(0,153,255,0.04) 0%, transparent 60%)",
      }}>
        {/* ── Header ── */}
        <div style={{
          borderBottom: "1px solid var(--border)", padding: "0 32px",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          height: "56px", position: "sticky", top: 0, zIndex: 10,
          background: "rgba(10,11,14,0.92)", backdropFilter: "blur(12px)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{
              width: "28px", height: "28px", borderRadius: "6px",
              background: "linear-gradient(135deg, var(--accent), var(--accent2))",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "14px",
            }}>🐛</div>
            <div>
              <span style={{ fontWeight: 800, fontSize: "16px", letterSpacing: "-0.02em" }}>AutoDebug</span>
              <span style={{ color: "var(--text3)", fontSize: "12px", marginLeft: "8px", fontFamily: "var(--font-mono)" }}>IT568 · Q3</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <Badge color="purple">llama-3.3-70b-versatile</Badge>
            <Badge color={status === "running" ? "blue" : status === "complete" ? "accent" : status === "error" ? "red" : "gray"}>
              {status.toUpperCase()}
            </Badge>
          </div>
        </div>

        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "28px 24px" }}>

          {/* ── Input Section ── */}
          <div style={{ marginBottom: "24px" }}>
            <div style={{ marginBottom: "20px" }}>
              <h1 style={{ fontSize: "26px", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: "6px" }}>
                Automated Bug Detection Pipeline
              </h1>
              <p style={{ color: "var(--text2)", fontSize: "14px", lineHeight: 1.6 }}>
                Paste a GitHub repository URL. The pipeline will clone it, run tests, detect bugs via static + dynamic analysis,
                generate LLM fixes using Groq, apply them, and validate — iteratively.
              </p>
            </div>

            <div style={{ display: "flex", gap: "10px" }}>
              <div style={{ flex: 1, position: "relative" }}>
                <div style={{
                  position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)",
                  color: "var(--text3)", fontSize: "14px", pointerEvents: "none",
                }}>🔗</div>
                <input
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && !running && startPipeline()}
                  placeholder="https://github.com/username/repository"
                  disabled={running}
                  style={{
                    width: "100%", padding: "12px 14px 12px 38px",
                    background: "var(--bg2)", border: "1px solid var(--border2)",
                    borderRadius: "8px", color: "var(--text)", fontSize: "14px",
                    fontFamily: "var(--font-mono)", outline: "none",
                    transition: "border-color 0.2s",
                  }}
                  onFocus={(e) => { e.target.style.borderColor = "var(--accent)"; }}
                  onBlur={(e) => { e.target.style.borderColor = "var(--border2)"; }}
                />
              </div>

              {!running && status !== "idle" && (
                <button
                  onClick={reset}
                  style={{
                    padding: "12px 18px", background: "var(--bg3)",
                    border: "1px solid var(--border2)", borderRadius: "8px",
                    color: "var(--text2)", cursor: "pointer", fontSize: "13px", fontWeight: 600,
                  }}
                >
                  Reset
                </button>
              )}

              <button
                onClick={startPipeline}
                disabled={running || !repoUrl.trim()}
                style={{
                  padding: "12px 24px", borderRadius: "8px", fontWeight: 700,
                  fontSize: "14px", cursor: running ? "not-allowed" : "pointer",
                  border: "none", display: "flex", alignItems: "center", gap: "8px",
                  background: running || !repoUrl.trim()
                    ? "var(--bg3)"
                    : "linear-gradient(135deg, var(--accent), var(--accent2))",
                  color: running || !repoUrl.trim() ? "var(--text3)" : "#000",
                  transition: "all 0.2s",
                  fontFamily: "var(--font-display)",
                }}
              >
                {running ? <><div className="spinner" /> Analyzing...</> : "▶ Run Pipeline"}
              </button>
            </div>
          </div>

          {/* ── Phase Progress ── */}
          {status !== "idle" && <PhaseBar currentPhase={currentPhase} />}

          {/* ── Repo Info Strip ── */}
          {repoInfo && (
            <div style={{
              display: "flex", gap: "8px", flexWrap: "wrap",
              marginBottom: "16px", animation: "slide-in 0.3s ease forwards",
            }}>
              <Badge color="accent">{repoInfo.repoName}</Badge>
              <Badge color="blue">{repoInfo.language}</Badge>
              {repoInfo.framework !== "none" && <Badge color="purple">{repoInfo.framework}</Badge>}
              <Badge color="gray">{repoInfo.sourceFiles} files</Badge>
              <Badge color="gray">{repoInfo.testFiles} test files</Badge>
              <Badge color="gray">{repoInfo.testRunner}</Badge>
            </div>
          )}

          {/* ── Live Stats Strip ── */}
          {(lastTest || allBugs.length > 0) && (
            <div style={{
              display: "flex", gap: "8px", marginBottom: "16px",
              animation: "slide-in 0.3s ease forwards",
            }}>
              {lastTest && <>
                <div style={{
                  padding: "8px 14px", background: "rgba(0,212,170,0.08)",
                  border: "1px solid rgba(0,212,170,0.2)", borderRadius: "6px",
                  fontFamily: "var(--font-mono)", fontSize: "12px",
                }}>
                  <span style={{ color: "var(--text3)" }}>PASSED </span>
                  <span style={{ color: "var(--green)", fontWeight: 700 }}>{lastTest.passed}</span>
                </div>
                <div style={{
                  padding: "8px 14px",
                  background: lastTest.failed > 0 ? "rgba(255,77,109,0.08)" : "rgba(0,212,170,0.08)",
                  border: `1px solid ${lastTest.failed > 0 ? "rgba(255,77,109,0.2)" : "rgba(0,212,170,0.2)"}`,
                  borderRadius: "6px", fontFamily: "var(--font-mono)", fontSize: "12px",
                }}>
                  <span style={{ color: "var(--text3)" }}>FAILED </span>
                  <span style={{ color: lastTest.failed > 0 ? "var(--red)" : "var(--green)", fontWeight: 700 }}>
                    {lastTest.failed}
                  </span>
                </div>
              </>}
              {allBugs.length > 0 && (
                <div style={{
                  padding: "8px 14px", background: "rgba(255,209,102,0.08)",
                  border: "1px solid rgba(255,209,102,0.2)", borderRadius: "6px",
                  fontFamily: "var(--font-mono)", fontSize: "12px",
                }}>
                  <span style={{ color: "var(--text3)" }}>BUGS FOUND </span>
                  <span style={{ color: "var(--yellow)", fontWeight: 700 }}>{allBugs.length}</span>
                </div>
              )}
              {appliedFixes.length > 0 && (
                <div style={{
                  padding: "8px 14px", background: "rgba(0,153,255,0.08)",
                  border: "1px solid rgba(0,153,255,0.2)", borderRadius: "6px",
                  fontFamily: "var(--font-mono)", fontSize: "12px",
                }}>
                  <span style={{ color: "var(--text3)" }}>FIXES </span>
                  <span style={{ color: "var(--accent2)", fontWeight: 700 }}>{appliedFixes.length}</span>
                </div>
              )}
            </div>
          )}

          {/* ── Final Report ── */}
          {finalReport && <div style={{ marginBottom: "20px" }}><FinalReportBanner report={finalReport} /></div>}

          {/* ── Tabs ── */}
          {status !== "idle" && (
            <div>
              <div style={{
                display: "flex", gap: "2px", marginBottom: "14px",
                borderBottom: "1px solid var(--border)", paddingBottom: "0",
              }}>
                {tabs.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    style={{
                      padding: "8px 16px", background: "none", border: "none",
                      cursor: "pointer", fontSize: "13px", fontWeight: 600,
                      color: activeTab === tab.id ? "var(--accent)" : "var(--text3)",
                      borderBottom: activeTab === tab.id ? "2px solid var(--accent)" : "2px solid transparent",
                      marginBottom: "-1px", display: "flex", alignItems: "center", gap: "6px",
                      transition: "color 0.2s",
                      fontFamily: "var(--font-display)",
                    }}
                  >
                    {tab.label}
                    {tab.count > 0 && (
                      <span style={{
                        background: activeTab === tab.id ? "var(--accent)" : "var(--border2)",
                        color: activeTab === tab.id ? "#000" : "var(--text2)",
                        borderRadius: "10px", padding: "1px 7px", fontSize: "10px",
                      }}>
                        {tab.count}
                      </span>
                    )}
                  </button>
                ))}
              </div>

              {/* Terminal Tab */}
              {activeTab === "terminal" && <Terminal logs={logs} />}

              {/* Bugs Tab */}
              {activeTab === "bugs" && (
                <div>
                  {allBugs.length === 0 ? (
                    <div style={{
                      padding: "40px", textAlign: "center", color: "var(--text3)",
                      fontFamily: "var(--font-mono)", fontSize: "13px",
                    }}>
                      {running ? "Waiting for LLM analysis..." : "No bugs detected."}
                    </div>
                  ) : (
                    <div>
                      <div style={{ marginBottom: "10px", fontSize: "12px", color: "var(--text3)" }}>
                        Click a bug to expand its details and before/after code
                      </div>
                      {allBugs.map((bug, i) => <BugCard key={bug.id + i} bug={bug} index={i} />)}
                    </div>
                  )}
                </div>
              )}

              {/* Static Tab */}
              {activeTab === "static" && <StaticIssuesPanel issues={staticIssues} />}

              {/* Metrics Tab */}
              {activeTab === "metrics" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <MetricsTable iterations={iterationResults} />
                  {testHistory.length > 0 && (
                    <Card>
                      <CardHeader title="TEST RUN HISTORY" badge={<Badge color="blue">{testHistory.length} runs</Badge>} />
                      <div style={{ padding: "12px 16px", overflowX: "auto" }}>
                        {testHistory.map((t, i) => (
                          <div key={i} style={{
                            display: "flex", gap: "12px", alignItems: "center",
                            padding: "8px 0", borderBottom: i < testHistory.length - 1 ? "1px solid var(--border)" : "none",
                          }}>
                            <Badge color="gray">{t.label}</Badge>
                            <span style={{ color: "var(--green)", fontFamily: "var(--font-mono)", fontSize: "12px" }}>
                              ✓ {t.passed}
                            </span>
                            <span style={{ color: t.failed > 0 ? "var(--red)" : "var(--text3)", fontFamily: "var(--font-mono)", fontSize: "12px" }}>
                              ✗ {t.failed}
                            </span>
                            <Badge color={t.allPassed ? "accent" : t.failed > 0 ? "red" : "yellow"}>
                              {t.allPassed ? "PASS" : `${t.failed} FAIL`}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    </Card>
                  )}
                </div>
              )}

              {/* Diffs Tab */}
              {activeTab === "diffs" && (
                <div>
                  {appliedFixes.length === 0 ? (
                    <div style={{
                      padding: "40px", textAlign: "center", color: "var(--text3)",
                      fontFamily: "var(--font-mono)", fontSize: "13px",
                    }}>
                      {running ? "Waiting for fixes to be applied..." : "No fixes applied yet."}
                    </div>
                  ) : (
                    appliedFixes.map((diff, i) => (
                      <Card key={i} style={{ marginBottom: "12px" }}>
                        <CardHeader
                          title={diff.file}
                          badge={<Badge color="gray">{diff.bugId}</Badge>}
                          right={<span style={{ fontSize: "12px", color: "var(--text3)" }}>{diff.description?.slice(0, 60)}</span>}
                        />
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0" }}>
                          <div style={{ padding: "14px", borderRight: "1px solid var(--border)" }}>
                            <div style={{ fontSize: "11px", color: "var(--red)", marginBottom: "8px", fontFamily: "var(--font-mono)", fontWeight: 700 }}>— BEFORE</div>
                            <pre style={{
                              background: "rgba(255,77,109,0.05)", border: "1px solid rgba(255,77,109,0.15)",
                              borderRadius: "6px", padding: "10px", fontSize: "11px",
                              fontFamily: "var(--font-mono)", overflow: "auto", color: "var(--text2)",
                              maxHeight: "250px", whiteSpace: "pre-wrap",
                            }}>{diff.before?.slice(0, 1500)}</pre>
                          </div>
                          <div style={{ padding: "14px" }}>
                            <div style={{ fontSize: "11px", color: "var(--green)", marginBottom: "8px", fontFamily: "var(--font-mono)", fontWeight: 700 }}>+ AFTER</div>
                            <pre style={{
                              background: "rgba(0,212,170,0.05)", border: "1px solid rgba(0,212,170,0.15)",
                              borderRadius: "6px", padding: "10px", fontSize: "11px",
                              fontFamily: "var(--font-mono)", overflow: "auto", color: "var(--text2)",
                              maxHeight: "250px", whiteSpace: "pre-wrap",
                            }}>{diff.after?.slice(0, 1500)}</pre>
                          </div>
                        </div>
                        {diff.explanation && (
                          <div style={{
                            padding: "10px 14px", borderTop: "1px solid var(--border)",
                            fontSize: "12px", color: "var(--text2)", lineHeight: 1.6,
                            background: "var(--bg3)",
                          }}>
                            💡 {diff.explanation}
                          </div>
                        )}
                      </Card>
                    ))
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── Idle State ── */}
          {status === "idle" && (
            <div style={{
              marginTop: "32px", padding: "40px", textAlign: "center",
              border: "1px dashed var(--border2)", borderRadius: "12px",
              color: "var(--text3)",
            }}>
              <div style={{ fontSize: "40px", marginBottom: "12px" }}>🔬</div>
              <div style={{ fontWeight: 700, fontSize: "16px", color: "var(--text2)", marginBottom: "8px" }}>
                Pipeline ready
              </div>
              <div style={{ fontSize: "13px", lineHeight: 1.7, maxWidth: "500px", margin: "0 auto" }}>
                Enter a GitHub repo URL above to start the automated bug detection and repair pipeline.
                The system will run up to <span style={{ color: "var(--accent)", fontFamily: "var(--font-mono)" }}>3 fix iterations</span> using
                the Groq <span style={{ color: "var(--accent2)", fontFamily: "var(--font-mono)" }}>llama-3.3-70b-versatile</span> model.
              </div>
              <div style={{ marginTop: "20px", display: "flex", gap: "8px", justifyContent: "center", flexWrap: "wrap" }}>
                {["Clone", "→", "Install", "→", "Test", "→", "LLM Analyze", "→", "Fix", "→", "Validate"].map((s, i) => (
                  <span key={i} style={{
                    color: s === "→" ? "var(--border2)" : "var(--text3)",
                    fontSize: "12px", fontFamily: "var(--font-mono)",
                  }}>{s}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}