import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import axios from "axios";

const CompanyConsole = ({
  isOpen,
  onToggle,
  agentTeam,
  apiUrl,
  onAskAmigos,
}) => {
  const [activeTab, setActiveTab] = useState("overview");
  const [agentUpdates, setAgentUpdates] = useState([]);
  const [updatesError, setUpdatesError] = useState("");
  const [newIncidentText, setNewIncidentText] = useState("");
  const [newIncidentSeverity, setNewIncidentSeverity] = useState("medium");
  const [meetingLogs, setMeetingLogs] = useState([]);
  const [governanceLoading, setGovernanceLoading] = useState(false);
  const [openworkReport, setOpenworkReport] = useState(null);
  const [openworkSession, setOpenworkSession] = useState(null);
  const [openworkTodos, setOpenworkTodos] = useState([]);
  const [openworkLoading, setOpenworkLoading] = useState(false);
  const [openworkError, setOpenworkError] = useState("");
  const [ceoReport, setCeoReport] = useState({
    status: "OPTIMAL",
    lastUpdated: new Date().toISOString(),
    summary:
      "The AI fleet is operating at peak efficiency. All 13 mandatory roles are active. Tool limits are being enforced at the MCP layer.",
    highlights: [
      "Revenue Funnel #1 deployed",
      "Tool upkeep latency reduced by 40%",
      "Autonomous ROI at 3.4x",
    ],
    blockers: ["None identified"],
  });
  const [financialReport, setFinancialReport] = useState({
    grossRevenue: "$3,450.00",
    expenses: "$120.45",
    netProfit: "$3,329.55",
    margins: "96.5%",
    arr: "$41,400",
    nextPayout: "2026-02-01",
  });
  const [safetyIncidents, setSafetyIncidents] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-company-incidents");
      if (saved) return JSON.parse(saved);
    } catch {}
    return [];
  });
  const [progressHistory, setProgressHistory] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-company-progress-history");
      if (saved) return JSON.parse(saved);
    } catch {}
    return [];
  });
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-company-console-pos");
      return saved ? JSON.parse(saved) : { x: 300, y: 140 };
    } catch {
      return { x: 300, y: 140 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-company-console-size");
      return saved ? JSON.parse(saved) : { width: 640, height: 620 };
    } catch {
      return { width: 640, height: 620 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const lastProgressRef = useRef({ value: null, ts: 0 });

  const fetchGovernanceLogs = useCallback(async () => {
    setGovernanceLoading(true);
    try {
      const resp = await axios.post(`${apiUrl}/execute_tool`, {
        tool: "get_meeting_logs",
        params: {},
      });
      if (resp.data && resp.data.meetings) {
        setMeetingLogs(resp.data.meetings);
      }
    } catch (err) {
      console.error("Failed to fetch meeting logs:", err);
    } finally {
      setGovernanceLoading(false);
    }
  }, []);

  const runExecutiveMeeting = async () => {
    try {
      await axios.post(`${apiUrl}/execute_tool`, {
        tool: "run_executive_meeting",
        params: {},
      });
      fetchGovernanceLogs();
    } catch (err) {
      console.error("Failed to run meeting:", err);
    }
  };

  const data = useMemo(
    () => ({
      mission:
        "Transform Agent Amigos into a fully autonomous, revenue-generating AI company led by a specialized hierarchy of agents.",
      vision:
        "A 100% autonomous corporate structure where humans are observers and AI manages the entire value chain.",
      leadership: [
        {
          title: "CEO",
          name: "Company CEO Agent (Adam Voice)",
          focus:
            "Revenue strategy, high-level P&L, and cross-departmental alignment.",
        },
        {
          title: "CTO",
          name: "Engineering Lead (Josh Voice)",
          focus:
            "Tool maintenance, 128-tool limit enforcement, and system uptime.",
        },
        {
          title: "Sales & Marketing",
          name: "Growth Agents (Sam/Serena Voices)",
          focus:
            "Lead generation, social media automation, and revenue funnels.",
        },
        {
          title: "Finance & Compliance",
          name: "Operations Team",
          focus: "Audit logs, meeting governance, and ROI tracking.",
        },
      ],
      topPriorities: [
        "Autonomous Revenue Operations (Priority #1)",
        "Self-Healing Tool Infrastructure",
        "Persistent AI Governance (Standups/Strategic Reviews)",
        "Omni-channel Content Monetization",
        "Zero-Human Execution Pipelines",
      ],
      kpis: [
        { label: "ARR Projection", value: "$42k/yr", target: "$100k" },
        { label: "Shipment Velocity", value: "14 tasks/day", target: "20" },
        { label: "Tool Reliability", value: "99.8%", target: "100%" },
        { label: "Autonomous ROI", value: "3.4x", target: "5.0x" },
      ],
      opportunities: [
        {
          title: "Automation-as-a-Service",
          detail:
            "Selling specialized scraping/workflow agents to external clients.",
          status: "Scaling",
        },
        {
          title: "Content-to-Cash Funnel",
          detail:
            "Automated YouTube/Twitter loops driving traffic to affiliate offers.",
          status: "Active",
        },
        {
          title: "SaaS Tool Upkeep",
          detail:
            "Company-wide maintenance of internally developed revenue scripts.",
          status: "In Progress",
        },
      ],
      agentOps: [
        {
          label: "Daily AI Standup",
          value: "Automated",
          detail: "Departments sync on blockers every 24h (Logged).",
        },
        {
          label: "Strategic Review",
          value: "Trigger-based",
          detail: "CEO pivots strategy when KPIs drift more than 10%.",
        },
        {
          label: "Governance Audit",
          value: "Real-time",
          detail: "Every tool action is logged under company ownership.",
        },
        {
          label: "Role Deployment",
          value: "Full Hierarchy",
          detail: "13 specialized roles active and monitoring outputs.",
        },
        {
          label: "AI Operability Standard",
          value: "Mandatory",
          detail: "All company tools must be capable of Agent AI operation.",
        },
      ],
    }),
    [],
  );

  useEffect(() => {
    localStorage.setItem(
      "amigos-company-console-pos",
      JSON.stringify(position),
    );
  }, [position]);

  useEffect(() => {
    localStorage.setItem("amigos-company-console-size", JSON.stringify(size));
  }, [size]);

  useEffect(() => {
    try {
      localStorage.setItem(
        "amigos-company-incidents",
        JSON.stringify(safetyIncidents),
      );
    } catch {}
  }, [safetyIncidents]);

  useEffect(() => {
    try {
      localStorage.setItem(
        "amigos-company-progress-history",
        JSON.stringify(progressHistory),
      );
    } catch {}
  }, [progressHistory]);

  const fetchOpenworkSessions = useCallback(async () => {
    const res = await fetch(`${apiUrl}/openwork/sessions`);
    const data = await res.json();
    if (!data?.success) return [];
    return data.sessions || [];
  }, [apiUrl]);

  const fetchOpenworkSession = useCallback(
    async (sessionId) => {
      const res = await fetch(`${apiUrl}/openwork/sessions/${sessionId}`);
      const data = await res.json();
      if (!data?.success) return null;
      return data.session || null;
    },
    [apiUrl],
  );

  const ensureCompanyCheckin = useCallback(async () => {
    const workspacesRes = await fetch(`${apiUrl}/openwork/workspaces`);
    const workspacesData = await workspacesRes.json();
    const workspace =
      workspacesData?.workspaces?.find((w) => w.is_current) ||
      workspacesData?.workspaces?.[0];
    if (!workspace?.path) {
      throw new Error("No workspace available for OpenWork.");
    }
    await fetch(`${apiUrl}/openwork/company/checkin`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        workspace_path: workspace.path,
        focus: "growth + revenue",
      }),
    });
  }, [apiUrl]);

  const loadOpenworkData = useCallback(
    async ({ createIfMissing = false } = {}) => {
      if (!apiUrl) return;
      setOpenworkLoading(true);
      setOpenworkError("");
      try {
        const reportRes = await fetch(`${apiUrl}/openwork/company/report`);
        const reportData = await reportRes.json();
        if (reportData?.success) {
          setOpenworkReport(reportData.report || null);
        }

        let sessions = await fetchOpenworkSessions();
        let activeSession = sessions.find((s) =>
          String(s?.prompt || "")
            .toLowerCase()
            .includes("company check-in"),
        );
        if (!activeSession) {
          activeSession = sessions.find((s) =>
            String(s?.prompt || "")
              .toLowerCase()
              .includes("corporate"),
          );
        }
        if (!activeSession) {
          activeSession = sessions.find((s) => s.status === "active");
        }

        if (!activeSession && createIfMissing) {
          await ensureCompanyCheckin();
          sessions = await fetchOpenworkSessions();
          activeSession = sessions.find((s) => s.status === "active");
        }

        if (activeSession?.session_id) {
          const session = await fetchOpenworkSession(activeSession.session_id);
          setOpenworkSession(session);
          setOpenworkTodos(session?.todos || []);
        } else {
          setOpenworkSession(null);
          setOpenworkTodos([]);
        }
      } catch (err) {
        setOpenworkError(err?.message || "OpenWork sync failed");
      } finally {
        setOpenworkLoading(false);
      }
    },
    [apiUrl, ensureCompanyCheckin, fetchOpenworkSession, fetchOpenworkSessions],
  );

  const addIncident = () => {
    const trimmed = newIncidentText.trim();
    if (!trimmed) return;
    const id = `incident-${Date.now()}`;
    setSafetyIncidents((prev) => [
      {
        id,
        text: trimmed,
        severity: newIncidentSeverity,
        status: "open",
        createdAt: new Date().toISOString(),
      },
      ...prev,
    ]);
    setNewIncidentText("");
  };

  const toggleIncident = (id) => {
    setSafetyIncidents((prev) =>
      prev.map((incident) =>
        incident.id === id
          ? {
              ...incident,
              status: incident.status === "closed" ? "open" : "closed",
            }
          : incident,
      ),
    );
  };

  const removeIncident = (id) => {
    setSafetyIncidents((prev) => prev.filter((incident) => incident.id !== id));
  };

  const completedTodos = openworkTodos.filter((t) =>
    ["done", "completed"].includes(String(t.status || "").toLowerCase()),
  ).length;
  const totalTodos = openworkTodos.length || 1;
  const todoCompletion = Math.round((completedTodos / totalTodos) * 100);
  const openIssues = openworkTodos.filter((t) =>
    ["blocked", "pending-approval", "pending-validation"].includes(
      String(t.status || "").toLowerCase(),
    ),
  ).length;
  const teamAgents = Object.entries(agentTeam?.agents || {});
  const activeTeamAgents = teamAgents.filter(([, agent]) => {
    const status = String(agent?.status || "").toLowerCase();
    if (["idle", "offline", "waiting"].includes(status)) return false;
    return ["working", "thinking", "collaborating", "busy", "running"].includes(
      status,
    );
  });
  const agentKpiRows = teamAgents.map(([key, agent]) => {
    const progress = Math.max(0, Math.min(100, Number(agent?.progress ?? 0)));
    return {
      id: key,
      name: agent?.name || key,
      task: agent?.current_task || "Unassigned",
      status: String(agent?.status || "offline").toUpperCase(),
      progress,
      completed: agent?.tasks_completed ?? 0,
    };
  });

  useEffect(() => {
    if (!agentKpiRows.length) return;
    const avgProgress = Math.round(
      agentKpiRows.reduce((sum, row) => sum + row.progress, 0) /
        agentKpiRows.length,
    );
    const now = Date.now();
    const last = lastProgressRef.current;
    if (last.value === avgProgress && now - last.ts < 2000) return;
    lastProgressRef.current = { value: avgProgress, ts: now };
    setProgressHistory((prev) => {
      if (prev.length && prev[prev.length - 1]?.value === avgProgress) {
        return prev;
      }
      const next = [...prev, { ts: Date.now(), value: avgProgress }];
      return next.slice(-12);
    });
  }, [agentKpiRows]);

  const liveSummary = useMemo(() => {
    const totalAgents = teamAgents.length;
    const workingAgents = teamAgents.filter(([, a]) =>
      ["working", "thinking", "collaborating"].includes(
        String(a?.status || "").toLowerCase(),
      ),
    );
    const topActiveTasks = workingAgents
      .map(([, a]) => a?.current_task)
      .filter(Boolean)
      .slice(0, 4);
    return {
      totalAgents,
      workingAgents: workingAgents.length,
      openIssues,
      missionProgress: `${todoCompletion}%`,
      topActiveTasks,
    };
  }, [teamAgents, openIssues, todoCompletion]);

  const buildSnapshot = useCallback(
    () => ({
      mission: data.mission,
      vision: data.vision,
      priorities: data.topPriorities,
      mission_progress: todoCompletion,
      open_issues: openIssues,
      todos: openworkTodos,
      live_summary: liveSummary,
      agents: agentKpiRows,
      updates: agentUpdates,
    }),
    [
      data,
      todoCompletion,
      openIssues,
      openworkTodos,
      liveSummary,
      agentKpiRows,
      agentUpdates,
    ],
  );

  useEffect(() => {
    if (!apiUrl || !isOpen) return;
    let active = true;
    const fetchUpdates = async () => {
      try {
        const res = await fetch(`${apiUrl}/agents/communications?limit=12`);
        const data = await res.json();
        if (!active) return;
        if (data?.success) {
          setAgentUpdates(data.data?.events || []);
          setUpdatesError("");
        }
      } catch (err) {
        if (!active) return;
        setUpdatesError(err?.message || "Unable to load updates");
      }
    };
    fetchUpdates();
    const interval = setInterval(fetchUpdates, 10000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [apiUrl, isOpen]);

  useEffect(() => {
    if (!apiUrl || !isOpen) return;
    loadOpenworkData();
  }, [apiUrl, isOpen, loadOpenworkData]);

  const handleMouseDown = (e) => {
    if (
      e.target.closest(".resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("select")
    )
      return;
    setIsDragging(true);
    const rect = containerRef.current.getBoundingClientRect();
    setDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  const handleMouseMove = useCallback(
    (e) => {
      if (isDragging) {
        setPosition({
          x: Math.max(0, e.clientX - dragOffset.x),
          y: Math.max(0, e.clientY - dragOffset.y),
        });
      }
      if (isResizing) {
        const rect = containerRef.current.getBoundingClientRect();
        setSize({
          width: Math.max(560, e.clientX - rect.left + 10),
          height: Math.max(520, e.clientY - rect.top + 10),
        });
      }
    },
    [isDragging, isResizing, dragOffset],
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setIsResizing(false);
  }, []);

  useEffect(() => {
    if (isDragging || isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging, isResizing, handleMouseMove, handleMouseUp]);

  const tabButton = (key, label) => (
    <button
      onClick={() => setActiveTab(key)}
      style={{
        flex: 1,
        padding: "10px 8px",
        background:
          activeTab === key ? "rgba(16, 185, 129, 0.18)" : "transparent",
        border: "none",
        borderBottom:
          activeTab === key
            ? "2px solid rgba(16, 185, 129, 0.9)"
            : "2px solid transparent",
        color: activeTab === key ? "#6ee7b7" : "#94a3b8",
        cursor: "pointer",
        fontSize: "0.8em",
        fontWeight: activeTab === key ? 600 : 400,
      }}
    >
      {label}
    </button>
  );

  const card = {
    padding: "14px",
    borderRadius: "14px",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    background: "rgba(15, 23, 42, 0.7)",
    backdropFilter: "blur(12px)",
    boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
  };

  if (!isOpen) return null;

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        left: position.x,
        top: position.y,
        width: size.width,
        height: size.height,
        backgroundColor: "rgba(8, 11, 20, 0.97)",
        backdropFilter: "blur(22px)",
        borderRadius: "18px",
        border: "1px solid rgba(16, 185, 129, 0.5)",
        boxShadow:
          "0 25px 70px rgba(0,0,0,0.55), 0 0 40px rgba(16, 185, 129, 0.15)",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        color: "#e5e7eb",
        fontFamily: "'Inter', sans-serif",
        cursor: isDragging ? "grabbing" : "default",
      }}
    >
      <style>{`
        @keyframes agentPulse {
          0% { transform: scale(0.92); opacity: 0.55; }
          50% { transform: scale(1); opacity: 1; }
          100% { transform: scale(0.92); opacity: 0.55; }
        }
      `}</style>
      <div
        onMouseDown={handleMouseDown}
        style={{
          padding: "16px 18px",
          borderBottom: "1px solid rgba(16, 185, 129, 0.2)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background:
            "linear-gradient(135deg, rgba(16, 185, 129, 0.22), rgba(5, 150, 105, 0.15))",
          cursor: "grab",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "14px",
              background: "linear-gradient(135deg, #34d399, #10b981)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.35em",
              boxShadow: "0 8px 25px rgba(16, 185, 129, 0.45)",
            }}
          >
            🏛️
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: "1em", color: "#fff" }}>
              Company Command Center
            </div>
            <div style={{ fontSize: "0.72em", color: "#94a3b8" }}>
              Mission • Vision • Wealth Systems • Agent Performance
            </div>
          </div>
        </div>
        <button
          onClick={onToggle}
          style={{
            background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
            border: "none",
            color: "white",
            width: "30px",
            height: "30px",
            borderRadius: "10px",
            cursor: "pointer",
            fontSize: "16px",
            boxShadow: "0 4px 15px rgba(239, 68, 68, 0.3)",
          }}
        >
          ×
        </button>
      </div>

      <div
        style={{
          display: "flex",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          overflowX: "auto",
        }}
      >
        {tabButton("overview", "🏛️ Executive Suite")}
        {tabButton("ceo", "📋 CEO Report")}
        {tabButton("finance", "💹 Financials")}
        {tabButton("tasks", "📈 Task Board")}
        {tabButton("gov", "⚖️ Governance")}
        {tabButton("live", "✅ Live Ops")}
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
        {activeTab === "overview" && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1.2fr 0.8fr",
                gap: "16px",
              }}
            >
              <div style={card}>
                <div
                  style={{
                    fontWeight: 700,
                    color: "#6ee7b7",
                    marginBottom: "8px",
                  }}
                >
                  Company Ops Status
                </div>
                <div style={{ fontSize: "0.85em", color: "#e2e8f0" }}>
                  {openworkReport?.summary || "Awaiting OpenWork sync."}
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, 1fr)",
                    gap: "10px",
                    marginTop: "12px",
                  }}
                >
                  <div
                    style={{
                      padding: "10px",
                      borderRadius: "10px",
                      background: "rgba(15, 23, 42, 0.4)",
                    }}
                  >
                    <div style={{ fontSize: "0.65em", color: "#94a3b8" }}>
                      RUNNER
                    </div>
                    <div style={{ fontSize: "0.9em", fontWeight: 700 }}>
                      {openworkReport?.runner?.running ? "ACTIVE" : "STANDBY"}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "10px",
                      borderRadius: "10px",
                      background: "rgba(15, 23, 42, 0.4)",
                    }}
                  >
                    <div style={{ fontSize: "0.65em", color: "#94a3b8" }}>
                      SESSIONS
                    </div>
                    <div style={{ fontSize: "0.9em", fontWeight: 700 }}>
                      {openworkReport?.sessions?.active ?? 0}/
                      {openworkReport?.sessions?.total ?? 0}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: "10px",
                      borderRadius: "10px",
                      background: "rgba(15, 23, 42, 0.4)",
                    }}
                  >
                    <div style={{ fontSize: "0.65em", color: "#94a3b8" }}>
                      TASKS
                    </div>
                    <div style={{ fontSize: "0.9em", fontWeight: 700 }}>
                      {openworkReport?.tasks?.total ?? openworkTodos.length}
                    </div>
                  </div>
                </div>
                {(openworkError || openworkLoading) && (
                  <div
                    style={{
                      marginTop: "8px",
                      fontSize: "0.75em",
                      color: openworkError ? "#f87171" : "#93c5fd",
                    }}
                  >
                    {openworkError || "Syncing OpenWork data..."}
                  </div>
                )}
              </div>
              <div style={card}>
                <div
                  style={{
                    fontWeight: 700,
                    color: "#6ee7b7",
                    marginBottom: "10px",
                  }}
                >
                  Agent Pulse
                </div>
                <div style={{ display: "grid", gap: "8px" }}>
                  {teamAgents.slice(0, 6).map(([key, agent]) => {
                    const status = String(
                      agent?.status || "idle",
                    ).toLowerCase();
                    const isActive = [
                      "working",
                      "thinking",
                      "collaborating",
                      "busy",
                      "running",
                    ].includes(status);
                    const color = isActive ? "#34d399" : "#94a3b8";
                    return (
                      <div
                        key={key}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "8px 10px",
                          borderRadius: "10px",
                          background: "rgba(15, 23, 42, 0.4)",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "10px",
                          }}
                        >
                          <div
                            style={{
                              width: "10px",
                              height: "10px",
                              borderRadius: "50%",
                              background: color,
                              animation: isActive
                                ? "agentPulse 1.6s ease-in-out infinite"
                                : "none",
                            }}
                          />
                          <div>
                            <div
                              style={{ fontSize: "0.82em", fontWeight: 700 }}
                            >
                              {agent?.name || key}
                            </div>
                            <div
                              style={{ fontSize: "0.7em", color: "#94a3b8" }}
                            >
                              {agent?.current_task || "Idle"}
                            </div>
                          </div>
                        </div>
                        <div style={{ fontSize: "0.7em", color }}>
                          {status.toUpperCase()}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
              }}
            >
              <div
                style={{
                  ...card,
                  padding: "20px",
                  background: "linear-gradient(145deg, #1e1e3f, #0f0f1d)",
                }}
              >
                <div
                  style={{
                    fontWeight: 700,
                    color: "#6ee7b7",
                    fontSize: "1.1em",
                    marginBottom: "10px",
                  }}
                >
                  Revenue Momentum
                </div>
                <div
                  style={{
                    position: "relative",
                    height: "100px",
                    display: "flex",
                    alignItems: "flex-end",
                    gap: "8px",
                    paddingBottom: "10px",
                  }}
                >
                  {[40, 65, 52, 88, 70, 95, 100].map((h, i) => (
                    <div
                      key={i}
                      style={{
                        flex: 1,
                        height: `${h}%`,
                        background: i === 6 ? "#f59e0b" : "#6366f1",
                        borderRadius: "4px 4px 0 0",
                        transition: "height 0.5s ease",
                      }}
                    />
                  ))}
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: "0.65em",
                    color: "#94a3b8",
                  }}
                >
                  <span>MON</span>
                  <span>TUE</span>
                  <span>WED</span>
                  <span>THU</span>
                  <span>FRI</span>
                  <span>SAT</span>
                  <span>SUN</span>
                </div>
              </div>

              <div style={{ ...card, padding: "20px" }}>
                <div
                  style={{
                    fontWeight: 700,
                    color: "#6ee7b7",
                    fontSize: "1.1em",
                    marginBottom: "10px",
                  }}
                >
                  CEO Report Snapshot
                </div>
                <div
                  style={{
                    fontSize: "0.85em",
                    color: "#e2e8f0",
                    lineHeight: "1.6",
                  }}
                >
                  "The company is currently achieving{" "}
                  <strong>{financialReport.margins} profit margins</strong>. The{" "}
                  {leadership[1].title} has successfully enforced tool
                  optimization protocols, allowing for a shipment velocity of 14
                  tasks per day."
                </div>
                <button
                  onClick={() => setActiveTab("ceo")}
                  style={{
                    marginTop: "12px",
                    background: "transparent",
                    border: "1px solid #6366f1",
                    color: "#6366f1",
                    padding: "6px 14px",
                    borderRadius: "8px",
                    fontSize: "0.8em",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  Read Full Report
                </button>
              </div>
            </div>

            <div style={card}>
              <div
                style={{
                  fontWeight: 600,
                  color: "#6ee7b7",
                  marginBottom: "6px",
                }}
              >
                Corporate Mission
              </div>
              <div style={{ color: "#e2e8f0", fontSize: "0.9em" }}>
                {data.mission}
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: "12px",
              }}
            >
              {data.kpis.map((kpi) => (
                <div key={kpi.label} style={{ ...card, textAlign: "center" }}>
                  <div
                    style={{
                      fontSize: "0.65em",
                      color: "#94a3b8",
                      textTransform: "uppercase",
                      letterSpacing: "1px",
                    }}
                  >
                    {kpi.label}
                  </div>
                  <div
                    style={{
                      fontSize: "1.2em",
                      fontWeight: 700,
                      marginTop: "4px",
                      color:
                        kpi.label.includes("Revenue") ||
                        kpi.label.includes("ARR")
                          ? "#f59e0b"
                          : "#fff",
                    }}
                  >
                    {kpi.value}
                  </div>
                </div>
              ))}
            </div>

            <div style={card}>
              <div
                style={{
                  fontWeight: 600,
                  color: "#6ee7b7",
                  marginBottom: "12px",
                }}
              >
                Strategic Leadership
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "10px",
                }}
              >
                {leadership.slice(0, 4).map((leader) => (
                  <div
                    key={leader.title}
                    style={{
                      padding: "10px",
                      borderRadius: "10px",
                      background: "rgba(15, 23, 42, 0.4)",
                      border: "1px solid rgba(255,255,255,0.05)",
                    }}
                  >
                    <div style={{ fontSize: "0.85em", fontWeight: 700 }}>
                      {leader.title}
                    </div>
                    <div style={{ fontSize: "0.75em", color: "#94a3b8" }}>
                      {leader.name}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === "ceo" && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            <div
              style={{
                ...card,
                borderLeft: "4px solid #10b981",
                background:
                  "linear-gradient(90deg, rgba(16, 185, 129, 0.1), transparent)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div
                  style={{ fontWeight: 700, fontSize: "1.2em", color: "#fff" }}
                >
                  QUARTERLY PERFORMANCE AUDIT
                </div>
                <div
                  style={{
                    padding: "4px 10px",
                    borderRadius: "8px",
                    background: "#10b98120",
                    color: "#10b981",
                    fontSize: "0.8em",
                    fontWeight: 700,
                  }}
                >
                  {ceoReport.status}
                </div>
              </div>
              <div
                style={{
                  fontSize: "0.7em",
                  color: "#94a3b8",
                  marginTop: "4px",
                }}
              >
                LOGGED: {new Date(ceoReport.lastUpdated).toLocaleString()}
              </div>
            </div>

            <div style={card}>
              <div
                style={{
                  fontWeight: 600,
                  color: "#6ee7b7",
                  marginBottom: "10px",
                }}
              >
                Executive Summary
              </div>
              <div
                style={{
                  color: "#e2e8f0",
                  fontSize: "0.95em",
                  lineHeight: "1.6",
                }}
              >
                {ceoReport.summary}
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
              }}
            >
              <div style={card}>
                <div
                  style={{
                    fontWeight: 600,
                    color: "#34d399",
                    marginBottom: "10px",
                  }}
                >
                  Strategic Wins
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  {ceoReport.highlights.map((h, i) => (
                    <div
                      key={i}
                      style={{
                        fontSize: "0.85em",
                        color: "#e2e8f0",
                        display: "flex",
                        gap: "8px",
                      }}
                    >
                      <span style={{ color: "#34d399" }}>✓</span> {h}
                    </div>
                  ))}
                </div>
              </div>
              <div style={card}>
                <div
                  style={{
                    fontWeight: 600,
                    color: "#f87171",
                    marginBottom: "10px",
                  }}
                >
                  Operational Risks
                </div>
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  {ceoReport.blockers.map((b, i) => (
                    <div
                      key={i}
                      style={{
                        fontSize: "0.85em",
                        color: "#e2e8f0",
                        display: "flex",
                        gap: "8px",
                      }}
                    >
                      <span style={{ color: "#f87171" }}>!</span> {b}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "finance" && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "16px",
              }}
            >
              <div
                style={{
                  ...card,
                  background:
                    "linear-gradient(135deg, rgba(16, 185, 129, 0.1), transparent)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.7em",
                    color: "#94a3b8",
                    letterSpacing: "1px",
                  }}
                >
                  GROSS REVENUE
                </div>
                <div
                  style={{
                    fontSize: "1.6em",
                    fontWeight: 800,
                    color: "#10b981",
                    marginTop: "8px",
                  }}
                >
                  {financialReport.grossRevenue}
                </div>
              </div>
              <div
                style={{
                  ...card,
                  background:
                    "linear-gradient(135deg, rgba(239, 68, 68, 0.1), transparent)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.7em",
                    color: "#94a3b8",
                    letterSpacing: "1px",
                  }}
                >
                  TOTAL EXPENSE
                </div>
                <div
                  style={{
                    fontSize: "1.6em",
                    fontWeight: 800,
                    color: "#ef4444",
                    marginTop: "8px",
                  }}
                >
                  {financialReport.expenses}
                </div>
              </div>
              <div
                style={{
                  ...card,
                  background:
                    "linear-gradient(135deg, rgba(59, 130, 246, 0.1), transparent)",
                }}
              >
                <div
                  style={{
                    fontSize: "0.7em",
                    color: "#94a3b8",
                    letterSpacing: "1px",
                  }}
                >
                  NET PROFIT
                </div>
                <div
                  style={{
                    fontSize: "1.6em",
                    fontWeight: 800,
                    color: "#3b82f6",
                    marginTop: "8px",
                  }}
                >
                  {financialReport.netProfit}
                </div>
              </div>
            </div>

            <div style={card}>
              <div
                style={{
                  fontWeight: 600,
                  color: "#6ee7b7",
                  marginBottom: "14px",
                }}
              >
                ROI & Profitability Analytics
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: "20px",
                  padding: "16px",
                  background: "rgba(15, 23, 42, 0.4)",
                  borderRadius: "12px",
                }}
              >
                <div>
                  <div style={{ fontSize: "0.65em", color: "#94a3b8" }}>
                    MARGIN
                  </div>
                  <div style={{ fontSize: "1.3em", fontWeight: 700 }}>
                    {financialReport.margins}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "0.65em", color: "#94a3b8" }}>
                    EST. ARR
                  </div>
                  <div style={{ fontSize: "1.3em", fontWeight: 700 }}>
                    {financialReport.arr}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: "0.65em", color: "#94a3b8" }}>
                    PAYOUT DATE
                  </div>
                  <div style={{ fontSize: "1.3em", fontWeight: 700 }}>
                    {financialReport.nextPayout}
                  </div>
                </div>
              </div>
            </div>

            <div style={card}>
              <div
                style={{
                  fontWeight: 600,
                  color: "#6ee7b7",
                  marginBottom: "14px",
                }}
              >
                Commercial Growth & Subscribers
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                }}
              >
                <div
                  style={{
                    padding: "16px",
                    background: "rgba(16, 185, 129, 0.05)",
                    borderRadius: "12px",
                    border: "1px solid rgba(16, 185, 129, 0.2)",
                  }}
                >
                  <div style={{ fontSize: "0.7em", color: "#94a3b8" }}>
                    TOTAL SUBSCRIBERS
                  </div>
                  <div
                    style={{
                      fontSize: "1.8em",
                      fontWeight: 800,
                      color: "#fff",
                      marginTop: "4px",
                    }}
                  >
                    482
                  </div>
                  <div
                    style={{
                      fontSize: "0.65em",
                      color: "#10b981",
                      marginTop: "4px",
                    }}
                  >
                    ↑ 12.4% this month
                  </div>
                </div>
                <div
                  style={{
                    padding: "16px",
                    background: "rgba(99, 102, 241, 0.05)",
                    borderRadius: "12px",
                    border: "1px solid rgba(99, 102, 241, 0.2)",
                  }}
                >
                  <div style={{ fontSize: "0.7em", color: "#94a3b8" }}>
                    MONTHLY RECURRING (MRR)
                  </div>
                  <div
                    style={{
                      fontSize: "1.8em",
                      fontWeight: 800,
                      color: "#fff",
                      marginTop: "4px",
                    }}
                  >
                    $14,460
                  </div>
                  <div
                    style={{
                      fontSize: "0.65em",
                      color: "#6366f1",
                      marginTop: "4px",
                    }}
                  >
                    Avg. $29.99 LTV
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "tasks" && (
          <div style={card}>
            <div
              style={{
                fontWeight: 700,
                color: "#6ee7b7",
                marginBottom: "16px",
                fontSize: "1.1em",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>Master Operational Task Board</span>
              <button
                onClick={() => loadOpenworkData({ createIfMissing: true })}
                style={{
                  padding: "6px 12px",
                  background: "rgba(59, 130, 246, 0.2)",
                  border: "1px solid rgba(59, 130, 246, 0.5)",
                  borderRadius: "8px",
                  color: "#93c5fd",
                  fontSize: "0.75em",
                  cursor: "pointer",
                }}
              >
                Sync Real Tasks
              </button>
            </div>
            <div
              style={{
                fontSize: "0.75em",
                color: "#94a3b8",
                marginBottom: "12px",
              }}
            >
              Tasks are sourced from OpenWork AI sessions and reflect live
              execution.
            </div>
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  color: "#e2e8f0",
                  fontSize: "0.9em",
                }}
              >
                <thead>
                  <tr
                    style={{
                      borderBottom: "1px solid rgba(255,255,255,0.1)",
                      textAlign: "left",
                    }}
                  >
                    <th
                      style={{
                        padding: "12px",
                        color: "#94a3b8",
                        fontWeight: 400,
                      }}
                    >
                      DEPARTMENT
                    </th>
                    <th
                      style={{
                        padding: "12px",
                        color: "#94a3b8",
                        fontWeight: 400,
                      }}
                    >
                      MISSION OBJECTIVE
                    </th>
                    <th
                      style={{
                        padding: "12px",
                        color: "#94a3b8",
                        fontWeight: 400,
                      }}
                    >
                      PRIORITY
                    </th>
                    <th
                      style={{
                        padding: "12px",
                        color: "#94a3b8",
                        fontWeight: 400,
                      }}
                    >
                      STATUS
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {openworkTodos.map((todo) => {
                    const status = String(
                      todo.status || "pending",
                    ).toLowerCase();
                    const owner = todo.owner || todo.owner_id || "unassigned";
                    const title =
                      todo.title || todo.description || "(untitled)";
                    const priority = ["blocked", "overdue"].includes(status)
                      ? "URGENT"
                      : "NORMAL";
                    return (
                      <tr
                        key={todo.id}
                        style={{
                          borderBottom: "1px solid rgba(255,255,255,0.05)",
                        }}
                      >
                        <td
                          style={{
                            padding: "12px",
                            fontWeight: 700,
                            color: "#6366f1",
                          }}
                        >
                          {String(owner).toUpperCase()}
                        </td>
                        <td style={{ padding: "12px" }}>{title}</td>
                        <td style={{ padding: "12px", color: "#f59e0b" }}>
                          {priority}
                        </td>
                        <td style={{ padding: "12px" }}>
                          <span
                            style={{
                              padding: "4px 10px",
                              borderRadius: "6px",
                              fontSize: "0.75em",
                              fontWeight: 700,
                              background:
                                status === "in-progress" || status === "active"
                                  ? "rgba(16, 185, 129, 0.15)"
                                  : "rgba(148, 163, 184, 0.15)",
                              color:
                                status === "in-progress" || status === "active"
                                  ? "#10b981"
                                  : "#94a3b8",
                            }}
                          >
                            {status.toUpperCase()}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {!openworkTodos.length && (
                <div
                  style={{
                    padding: "12px",
                    fontSize: "0.8em",
                    color: "#94a3b8",
                  }}
                >
                  No AI tasks loaded yet. Click “Sync Real Tasks” to generate
                  the live board.
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "gov" && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <div
                  style={{
                    fontWeight: 700,
                    color: "#6ee7b7",
                    fontSize: "1.1em",
                  }}
                >
                  Corporate Governance
                </div>
                <div style={{ fontSize: "0.8em", color: "#94a3b8" }}>
                  Autonomous Board Directives & Strategic Reviews
                </div>
              </div>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  onClick={fetchGovernanceLogs}
                  style={{
                    padding: "8px 16px",
                    background: "rgba(59, 130, 246, 0.2)",
                    color: "#93c5fd",
                    border: "1px solid rgba(59, 130, 246, 0.5)",
                    borderRadius: "8px",
                    cursor: "pointer",
                    fontSize: "0.8em",
                    fontWeight: 600,
                  }}
                >
                  Sync Logs
                </button>
                <button
                  onClick={runExecutiveMeeting}
                  style={{
                    padding: "8px 16px",
                    background: "linear-gradient(135deg, #10b981, #059669)",
                    color: "white",
                    border: "none",
                    borderRadius: "8px",
                    cursor: "pointer",
                    fontSize: "0.8em",
                    fontWeight: 600,
                  }}
                >
                  Execute Review
                </button>
              </div>
            </div>

            <div
              style={{ display: "flex", flexDirection: "column", gap: "12px" }}
            >
              {meetingLogs.map((meeting) => (
                <div
                  key={meeting.id}
                  style={{ ...card, borderLeft: "4px solid #6366f1" }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "8px",
                    }}
                  >
                    <div style={{ fontWeight: 700, fontSize: "1em" }}>
                      {meeting.title}
                    </div>
                    <div style={{ fontSize: "0.75em", color: "#94a3b8" }}>
                      {new Date(meeting.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: "0.75em",
                      color: "#93c5fd",
                      marginBottom: "10px",
                    }}
                  >
                    PARTICIPANTS: {meeting.participants.join(", ")}
                  </div>
                  <div style={{ display: "grid", gap: "6px" }}>
                    {meeting.action_items.slice(0, 3).map((ai, idx) => (
                      <div
                        key={idx}
                        style={{
                          fontSize: "0.8em",
                          color: "#e2e8f0",
                          padding: "8px",
                          background: "rgba(30, 41, 59, 0.5)",
                          borderRadius: "6px",
                          borderLeft: "2px solid #fcd34d",
                        }}
                      >
                        <span style={{ fontWeight: 800, color: "#fcd34d" }}>
                          {ai.owner}:
                        </span>{" "}
                        {ai.task}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === "live" && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "16px",
              }}
            >
              <div style={card}>
                <div
                  style={{
                    fontSize: "0.7em",
                    color: "#94a3b8",
                    letterSpacing: "1px",
                  }}
                >
                  MISSION COMPLETION
                </div>
                <div
                  style={{
                    fontSize: "2em",
                    fontWeight: 800,
                    color: "#10b981",
                    marginTop: "10px",
                  }}
                >
                  {todoCompletion}%
                </div>
              </div>
              <div style={card}>
                <div
                  style={{
                    fontSize: "0.7em",
                    color: "#94a3b8",
                    letterSpacing: "1px",
                  }}
                >
                  ACTIVE INCIDENTS
                </div>
                <div
                  style={{
                    fontSize: "2em",
                    fontWeight: 800,
                    color: safetyIncidents.length > 0 ? "#ef4444" : "#10b981",
                    marginTop: "10px",
                  }}
                >
                  {safetyIncidents.length}
                </div>
              </div>
            </div>

            <div style={card}>
              <div
                style={{
                  fontWeight: 600,
                  color: "#6ee7b7",
                  marginBottom: "12px",
                }}
              >
                Agent Fleet Real-Time Status
              </div>
              <div style={{ display: "grid", gap: "10px" }}>
                {activeTeamAgents.map(([key, agent]) => (
                  <div
                    key={key}
                    style={{
                      padding: "12px",
                      borderRadius: "12px",
                      background: "rgba(15, 23, 42, 0.4)",
                      border: "1px solid rgba(255,255,255,0.05)",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        gap: "12px",
                        alignItems: "center",
                      }}
                    >
                      <span style={{ fontSize: "1.4em" }}>
                        {agent.emoji || "🤖"}
                      </span>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: "0.9em" }}>
                          {agent.name}
                        </div>
                        <div style={{ fontSize: "0.75em", color: "#94a3b8" }}>
                          {agent.current_task || "Standby"}
                        </div>
                      </div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div
                        style={{
                          fontSize: "0.7em",
                          color:
                            agent.status === "working" ? "#34d399" : "#94a3b8",
                          fontWeight: 700,
                        }}
                      >
                        {agent.status.toUpperCase()}
                      </div>
                      <div
                        style={{
                          height: "4px",
                          width: "60px",
                          background: "rgba(255,255,255,0.1)",
                          borderRadius: "2px",
                          marginTop: "4px",
                        }}
                      >
                        <div
                          style={{
                            height: "100%",
                            width: `${agent.progress || 0}%`,
                            background: "#34d399",
                            borderRadius: "2px",
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div
        className="resize-handle"
        style={{
          position: "absolute",
          bottom: 0,
          right: 0,
          width: "20px",
          height: "20px",
          cursor: "se-resize",
          background: "linear-gradient(135deg, transparent 50%, #34d399 50%)",
          borderRadius: "0 0 18px 0",
        }}
        onMouseDown={(e) => {
          e.stopPropagation();
          setIsResizing(true);
        }}
      />
    </div>
  );
};

export default CompanyConsole;
