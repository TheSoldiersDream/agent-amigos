import React, { useState, useEffect } from "react";
import axios from "axios";

const OpenWorkConsole = ({ apiUrl }) => {
  const API_BASE =
    apiUrl || import.meta.env.VITE_AGENT_API_URL || "http://127.0.0.1:65252";
  const [sessions, setSessions] = useState([]);
  const [workspaces, setWorkspaces] = useState([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState("");
  const [newSessionPrompt, setNewSessionPrompt] = useState("");
  const [selectedSession, setSelectedSession] = useState(null);
  const [taskLibrary, setTaskLibrary] = useState([]);
  const [selectedLibraryTask, setSelectedLibraryTask] = useState("");
  const [librarySchedule, setLibrarySchedule] = useState("");
  const [rescheduleDrafts, setRescheduleDrafts] = useState({});
  const [templates, setTemplates] = useState([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState("");
  const [templatePreview, setTemplatePreview] = useState("");
  const [companyFocus, setCompanyFocus] = useState("growth + revenue");
  const [runnerStatus, setRunnerStatus] = useState(null);
  const [runnerIntervalSec, setRunnerIntervalSec] = useState(60);
  const [serverStatus, setServerStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [leadershipLog, setLeadershipLog] = useState([]);
  const [kpiStatus, setKpiStatus] = useState(null);
  const [companyReport, setCompanyReport] = useState(null);
  const [taskArtifacts, setTaskArtifacts] = useState([]);
  const [artifactViewer, setArtifactViewer] = useState({
    open: false,
    path: "",
    content: "",
  });

  const agentPresence = serverStatus?.server_running ? "Online" : "Offline";
  const agentActivity = sessions.length ? "Active workflows" : "Standing by";

  useEffect(() => {
    loadWorkspaces();
    loadSessions();
    loadServerStatus();
    loadTaskLibrary();
    loadTemplates();
    loadRunnerStatus();
    loadLeadershipLog();
    loadKpiStatus();
    loadCompanyReport();
    loadTaskArtifacts();

    // Poll for updates every 5 seconds
    const interval = setInterval(() => {
      loadSessions();
      loadServerStatus();
      loadRunnerStatus();
      loadLeadershipLog();
      loadKpiStatus();
      loadCompanyReport();
      loadTaskArtifacts();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const loadLeadershipLog = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/leader/log`);
      if (data.success) {
        setLeadershipLog(Array.isArray(data.log) ? data.log : []);
      }
    } catch (err) {
      console.error("Failed to load leadership log:", err);
    }
  };

  const loadKpiStatus = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/kpi/last-updated`);
      if (data.success) {
        setKpiStatus(data.kpi || null);
      }
    } catch (err) {
      console.error("Failed to load KPI status:", err);
    }
  };

  const loadCompanyReport = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/company/report`);
      if (data.success) {
        setCompanyReport(data.report || null);
      }
    } catch (err) {
      console.error("Failed to load company report:", err);
    }
  };

  const loadTaskArtifacts = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/task-artifacts`);
      if (data.success) {
        setTaskArtifacts(Array.isArray(data.artifacts) ? data.artifacts : []);
      }
    } catch (err) {
      console.error("Failed to load task artifacts:", err);
    }
  };

  const openArtifact = async (path) => {
    if (!path) return;
    try {
      const { data } = await axios.get(
        `${API_BASE}/openwork/task-artifacts/read`,
        { params: { path } },
      );
      if (data.success) {
        setArtifactViewer({
          open: true,
          path: data.path,
          content: data.content,
        });
      } else {
        setArtifactViewer({
          open: true,
          path,
          content: data.error || "Read failed",
        });
      }
    } catch (err) {
      setArtifactViewer({ open: true, path, content: "Read failed" });
    }
  };

  const loadWorkspaces = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/workspaces`);
      if (data.success) {
        setWorkspaces(data.workspaces);
        if (data.workspaces.length > 0 && !selectedWorkspace) {
          setSelectedWorkspace(data.workspaces[0].path);
        }
      }
    } catch (err) {
      console.error("Failed to load workspaces:", err);
    }
  };

  const loadSessions = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/sessions`);
      if (data.success) {
        setSessions(data.sessions);
      }
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  };

  const loadServerStatus = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/status`);
      setServerStatus(data);
    } catch (err) {
      console.error("Failed to load server status:", err);
    }
  };

  const loadTaskLibrary = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/task-library`);
      if (data.success) {
        setTaskLibrary(Array.isArray(data.library) ? data.library : []);
        if (data.library?.length && !selectedLibraryTask) {
          setSelectedLibraryTask(data.library[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to load task library:", err);
    }
  };

  const loadTemplates = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/templates`);
      if (data.success) {
        const list = Array.isArray(data.templates) ? data.templates : [];
        setTemplates(list);
        if (list.length && !selectedTemplateId) {
          setSelectedTemplateId(list[0].id);
          setTemplatePreview(list[0].content || "");
        }
      }
    } catch (err) {
      console.error("Failed to load templates:", err);
    }
  };

  const loadRunnerStatus = async () => {
    try {
      const { data } = await axios.get(`${API_BASE}/openwork/runner`);
      if (data.success) {
        setRunnerStatus(data.runner);
        if (data.runner?.interval_sec) {
          setRunnerIntervalSec(data.runner.interval_sec);
        }
      }
    } catch (err) {
      console.error("Failed to load runner status:", err);
    }
  };

  const toDateTimeLocalValue = (isoString) => {
    if (!isoString) return "";
    const d = new Date(isoString);
    if (Number.isNaN(d.getTime())) return "";
    const local = new Date(d.getTime() - d.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
  };

  const toIsoFromLocalValue = (localValue) => {
    if (!localValue) return "";
    const d = new Date(localValue);
    if (Number.isNaN(d.getTime())) return "";
    return d.toISOString();
  };

  const startServer = async () => {
    if (!selectedWorkspace) {
      setError("Please select a workspace first");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { data } = await axios.post(`${API_BASE}/openwork/server/start`, {
        workspace_path: selectedWorkspace,
      });

      if (data.success) {
        await loadServerStatus();
      } else {
        setError(data.error || "Failed to start server");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start OpenCode server");
    } finally {
      setLoading(false);
    }
  };

  const stopServer = async () => {
    setLoading(true);
    try {
      await axios.post(`${API_BASE}/openwork/server/stop`);
      await loadServerStatus();
    } catch (err) {
      setError("Failed to stop server");
    } finally {
      setLoading(false);
    }
  };

  const createSession = async () => {
    if (!newSessionPrompt.trim() || !selectedWorkspace) {
      setError("Please enter a prompt and select a workspace");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { data } = await axios.post(`${API_BASE}/openwork/sessions`, {
        workspace_path: selectedWorkspace,
        prompt: newSessionPrompt,
      });

      setNewSessionPrompt("");
      await loadSessions();
      if (data?.session_id) {
        await loadSessionDetails(data.session_id);
      }
    } catch (err) {
      setError("Failed to create session");
    } finally {
      setLoading(false);
    }
  };

  const createSessionFromTemplate = async () => {
    if (!selectedWorkspace) {
      setError("Please select a workspace first");
      return;
    }
    const template = templates.find((t) => t.id === selectedTemplateId);
    if (!template) {
      setError("Select a template first");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await axios.post(
        `${API_BASE}/openwork/sessions/from-template`,
        {
          workspace_path: selectedWorkspace,
          template_id: template.id,
        },
      );
      await loadSessions();
      if (data?.session_id) {
        await loadSessionDetails(data.session_id);
      }
    } catch (err) {
      setError("Failed to create session from template");
    } finally {
      setLoading(false);
    }
  };

  const runCompanyCheckin = async () => {
    if (!selectedWorkspace) {
      setError("Please select a workspace first");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await axios.post(
        `${API_BASE}/openwork/company/checkin`,
        {
          workspace_path: selectedWorkspace,
          focus: companyFocus,
        },
      );
      await loadSessions();
      if (data?.session_id) {
        await loadSessionDetails(data.session_id);
      }
    } catch (err) {
      setError("Failed to run company check-in");
    } finally {
      setLoading(false);
    }
  };

  const startCompany = async () => {
    if (!selectedWorkspace) {
      setError("Please select a workspace first");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await axios.post(`${API_BASE}/openwork/company/start`, {
        workspace_path: selectedWorkspace,
        focus: companyFocus,
      });
      if (data?.opencode && data.opencode.success === false) {
        setError(data.opencode.error || "OpenCode failed to start");
      }
      if (data?.runner) {
        setRunnerStatus(data.runner);
      }
      await loadSessions();
      if (data?.session?.session_id) {
        await loadSessionDetails(data.session.session_id);
      }
    } catch (err) {
      setError("Failed to start company");
    } finally {
      setLoading(false);
    }
  };

  const pauseCompany = async () => {
    await stopRunner();
  };

  const startRunner = async () => {
    try {
      const { data } = await axios.post(`${API_BASE}/openwork/runner/start`, {
        interval_sec: runnerIntervalSec,
      });
      if (data.success) setRunnerStatus(data.runner);
    } catch (err) {
      setError("Failed to start live runner");
    }
  };

  const stopRunner = async () => {
    try {
      const { data } = await axios.post(`${API_BASE}/openwork/runner/stop`);
      if (data.success) setRunnerStatus(data.runner);
    } catch (err) {
      setError("Failed to stop live runner");
    }
  };

  const tickRunner = async () => {
    try {
      const { data } = await axios.post(`${API_BASE}/openwork/runner/tick`);
      if (data.success) {
        setRunnerStatus(data.runner);
        loadSessions();
        if (selectedSession) {
          loadSessionDetails(selectedSession.session_id);
        }
      }
    } catch (err) {
      setError("Failed to trigger runner tick");
    }
  };

  const updateTodoStatus = async (todoId, newStatus) => {
    if (!selectedSession?.session_id) return;
    try {
      await axios.put(
        `${API_BASE}/openwork/sessions/${selectedSession.session_id}/todos/${todoId}`,
        { status: newStatus },
      );
      await loadSessionDetails(selectedSession.session_id);
    } catch (err) {
      setError(`Failed to update task to ${newStatus}`);
    }
  };

  const approveTodo = async (todoId) => {
    if (!selectedSession?.session_id) return;
    try {
      await axios.post(
        `${API_BASE}/openwork/sessions/${selectedSession.session_id}/todos/${todoId}/approve`,
        { approved_by: "CEO" },
      );
      await loadSessionDetails(selectedSession.session_id);
    } catch (err) {
      setError("Failed to approve outbound task");
    }
  };

  const deleteSession = async (sessionId) => {
    if (!window.confirm("Are you sure you want to delete this session?"))
      return;
    try {
      await axios.delete(`${API_BASE}/openwork/sessions/${sessionId}`);
      await loadSessions();
      if (selectedSession?.session_id === sessionId) {
        setSelectedSession(null);
      }
    } catch (err) {
      setError("Failed to delete session");
    }
  };

  const loadSessionDetails = async (sessionId) => {
    try {
      const { data } = await axios.get(
        `${API_BASE}/openwork/sessions/${sessionId}`,
      );
      if (data.success) {
        setSelectedSession(data.session);
      }
    } catch (err) {
      console.error("Failed to load session details:", err);
    }
  };

  const closeSession = async (sessionId) => {
    try {
      await axios.post(`${API_BASE}/openwork/sessions/${sessionId}/close`);
      await loadSessions();
      if (selectedSession?.session_id === sessionId) {
        setSelectedSession(null);
      }
    } catch (err) {
      setError("Failed to close session");
    }
  };

  const addTaskFromLibrary = async () => {
    if (!selectedSession?.session_id) {
      setError("Select a session before adding tasks");
      return;
    }

    const template = taskLibrary.find((t) => t.id === selectedLibraryTask);
    if (!template) {
      setError("Select a task template first");
      return;
    }

    try {
      setLoading(true);
      const scheduled_for = toIsoFromLocalValue(librarySchedule);
      await axios.post(
        `${API_BASE}/openwork/sessions/${selectedSession.session_id}/todos`,
        {
          title: template.title,
          description: template.description,
          status: "pending",
          scheduled_for: scheduled_for || undefined,
          source: "library",
          template_id: template.id,
        },
      );
      setLibrarySchedule("");
      await loadSessionDetails(selectedSession.session_id);
    } catch (err) {
      setError("Failed to add task from library");
    } finally {
      setLoading(false);
    }
  };

  const rescheduleTask = async (todoId, scheduledFor) => {
    if (!selectedSession?.session_id || !todoId || !scheduledFor) return;
    try {
      await axios.post(
        `${API_BASE}/openwork/sessions/${selectedSession.session_id}/todos/${todoId}/reschedule`,
        {
          scheduled_for: scheduledFor,
          reason: "manual",
        },
      );
      await loadSessionDetails(selectedSession.session_id);
    } catch (err) {
      setError("Failed to reschedule task");
    }
  };

  return (
    <div
      className="openwork-console"
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "#1a1a2e",
        color: "#fff",
      }}
    >
      <div
        style={{
          padding: "20px",
          borderBottom: "1px solid #2a2a3e",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "16px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <h2 style={{ margin: 0, marginBottom: "10px" }}>
              OpenWork - Agentic Workflow System
            </h2>
            <p style={{ margin: 0, color: "#888", fontSize: "14px" }}>
              Extensible AI-powered workspace management
            </p>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              background: "rgba(59, 130, 246, 0.12)",
              border: "1px solid rgba(59, 130, 246, 0.4)",
              borderRadius: "12px",
              padding: "10px 14px",
              minWidth: "240px",
            }}
          >
            <div
              style={{
                width: "42px",
                height: "42px",
                borderRadius: "12px",
                background: "linear-gradient(135deg, #6366f1, #3b82f6)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "1.3em",
                boxShadow: "0 8px 20px rgba(59, 130, 246, 0.35)",
              }}
            >
              🧠
            </div>
            <div>
              <div style={{ fontWeight: 700, color: "#fff" }}>
                OpenWork Agent (Amigos)
              </div>
              <div style={{ fontSize: "12px", color: "#cbd5e1" }}>
                Role: CEO Chief of Staff • Mode: Autonomous Delegation
              </div>
              <div
                style={{
                  fontSize: "12px",
                  color: agentPresence === "Online" ? "#4ade80" : "#f87171",
                }}
              >
                Presence: {agentPresence} • {agentActivity}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
            <button
              onClick={() => {
                loadWorkspaces();
                loadServerStatus();
                loadRunnerStatus();
                loadSessions();
                loadTemplates();
                loadTaskLibrary();
                loadLeadershipLog();
                loadKpiStatus();
                loadCompanyReport();
                loadTaskArtifacts();
              }}
              style={{
                background: "transparent",
                border: "1px solid #3a3a4e",
                borderRadius: "4px",
                color: "#aaa",
                padding: "4px 8px",
                cursor: "pointer",
                fontSize: "12px",
              }}
            >
              Refresh System
            </button>
            {/* Workspace selector in Header */}
            <div style={{ width: "200px" }}>
              <div
                style={{ fontSize: "11px", color: "#888", marginBottom: "4px" }}
              >
                Workspace
              </div>
              <select
                value={selectedWorkspace}
                onChange={(e) => setSelectedWorkspace(e.target.value)}
                style={{
                  width: "100%",
                  padding: "4px 8px",
                  backgroundColor: "#2a2a3e",
                  color: "#fff",
                  border: "1px solid #3a3a4e",
                  borderRadius: "4px",
                  fontSize: "13px",
                }}
              >
                {workspaces.map((ws) => (
                  <option key={ws.path} value={ws.path}>
                    {ws.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Server Status in Header */}
            <div
              style={{ display: "flex", flexDirection: "column", gap: "4px" }}
            >
              <div style={{ fontSize: "11px", color: "#888" }}>
                OpenCode{" "}
                {serverStatus?.server_running
                  ? `(${serverStatus.host}:${serverStatus.port})`
                  : "Offline"}
              </div>
              <button
                onClick={
                  serverStatus?.server_running ? stopServer : startServer
                }
                disabled={loading}
                style={{
                  padding: "4px 12px",
                  backgroundColor: serverStatus?.server_running
                    ? "#dc2626"
                    : "#22c55e",
                  color: "#fff",
                  border: "none",
                  borderRadius: "4px",
                  cursor: loading ? "not-allowed" : "pointer",
                  fontSize: "12px",
                  fontWeight: 600,
                }}
              >
                {loading
                  ? "..."
                  : serverStatus?.server_running
                    ? "Stop"
                    : "Start"}
              </button>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div
          style={{
            padding: "10px 20px",
            backgroundColor: "#ff4444",
            color: "#fff",
          }}
        >
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              float: "right",
              background: "transparent",
              border: "none",
              color: "#fff",
              cursor: "pointer",
            }}
          >
            ×
          </button>
        </div>
      )}

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Left sidebar */}
        <div
          style={{
            width: "320px",
            borderRight: "1px solid #2a2a3e",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Scrollable Upper Section */}
          <div
            style={{
              flex: "0 1 auto",
              overflowY: "auto",
              borderBottom: "1px solid #2a2a3e",
            }}
          >
            {/* Unified Company Control */}
            <div
              style={{
                padding: "20px",
                borderBottom: "1px solid #2a2a3e",
                background: runnerStatus?.running
                  ? "rgba(34, 197, 94, 0.1)"
                  : "rgba(249, 115, 22, 0.1)",
                textAlign: "center",
              }}
            >
              <h3
                style={{
                  margin: "0 0 15px 0",
                  fontSize: "16px",
                  color: "#fff",
                }}
              >
                Company Master Switch
              </h3>
              <button
                onClick={runnerStatus?.running ? stopRunner : startCompany}
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "16px",
                  backgroundColor: runnerStatus?.running
                    ? "#f97316"
                    : "#22c55e",
                  color: "#fff",
                  border: "none",
                  borderRadius: "12px",
                  cursor: loading ? "not-allowed" : "pointer",
                  fontWeight: "bold",
                  fontSize: "18px",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                  transition: "all 0.2s",
                }}
              >
                {loading
                  ? "PROCESSING..."
                  : runnerStatus?.running
                    ? "PAUSE COMPANY"
                    : "START COMPANY"}
              </button>

              <div
                style={{ marginTop: "12px", fontSize: "12px", color: "#888" }}
              >
                Mode:{" "}
                <span
                  style={{
                    color: runnerStatus?.running ? "#4ade80" : "#f87171",
                    fontWeight: "bold",
                  }}
                >
                  {runnerStatus?.running ? "AI AUTOPILOT" : "MANUAL STANDBY"}
                </span>
              </div>

              <div
                style={{
                  marginTop: "16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  textAlign: "left",
                }}
              >
                <div>
                  <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                    Company Focus
                  </div>
                  <input
                    value={companyFocus}
                    onChange={(e) => setCompanyFocus(e.target.value)}
                    placeholder="growth + revenue"
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      backgroundColor: "#1f2937",
                      color: "#fff",
                      border: "1px solid #334155",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                  />
                </div>

                <div>
                  <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                    Runner Interval (seconds)
                  </div>
                  <input
                    type="number"
                    min="10"
                    step="10"
                    value={runnerIntervalSec}
                    onChange={(e) =>
                      setRunnerIntervalSec(
                        Number.parseInt(e.target.value || "0", 10) || 10,
                      )
                    }
                    style={{
                      width: "100%",
                      padding: "8px 10px",
                      backgroundColor: "#1f2937",
                      color: "#fff",
                      border: "1px solid #334155",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                  />
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px",
                  }}
                >
                  <button
                    onClick={runCompanyCheckin}
                    disabled={loading}
                    style={{
                      padding: "8px",
                      backgroundColor: "#6366f1",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      fontSize: "12px",
                      cursor: loading ? "not-allowed" : "pointer",
                    }}
                  >
                    Run Check-in
                  </button>
                  <button
                    onClick={tickRunner}
                    disabled={loading}
                    style={{
                      padding: "8px",
                      backgroundColor: "#0ea5e9",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      fontSize: "12px",
                      cursor: loading ? "not-allowed" : "pointer",
                    }}
                  >
                    Runner Tick
                  </button>
                  <button
                    onClick={startRunner}
                    disabled={loading || runnerStatus?.running}
                    style={{
                      padding: "8px",
                      backgroundColor: "#22c55e",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      fontSize: "12px",
                      cursor:
                        loading || runnerStatus?.running
                          ? "not-allowed"
                          : "pointer",
                    }}
                  >
                    Start Runner
                  </button>
                  <button
                    onClick={stopRunner}
                    disabled={loading || !runnerStatus?.running}
                    style={{
                      padding: "8px",
                      backgroundColor: "#ef4444",
                      color: "#fff",
                      border: "none",
                      borderRadius: "6px",
                      fontSize: "12px",
                      cursor:
                        loading || !runnerStatus?.running
                          ? "not-allowed"
                          : "pointer",
                    }}
                  >
                    Stop Runner
                  </button>
                </div>

                <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                  Last tick:{" "}
                  {runnerStatus?.last_tick
                    ? new Date(runnerStatus.last_tick).toLocaleTimeString()
                    : "--"}
                </div>
              </div>
            </div>

            {/* Delegation Input */}
            <div style={{ padding: "15px", borderBottom: "1px solid #2a2a3e" }}>
              <strong
                style={{
                  display: "block",
                  marginBottom: "8px",
                  fontSize: "14px",
                }}
              >
                Delegate New Objective
              </strong>
              <textarea
                value={newSessionPrompt}
                onChange={(e) => setNewSessionPrompt(e.target.value)}
                placeholder="CEO's next objective..."
                style={{
                  width: "100%",
                  minHeight: "50px",
                  maxHeight: "100px",
                  padding: "10px",
                  backgroundColor: "#2a2a3e",
                  color: "#fff",
                  border: "1px solid #3a3a4e",
                  borderRadius: "6px",
                  fontSize: "13px",
                  marginBottom: "8px",
                }}
              />
              <button
                onClick={createSession}
                disabled={loading || !newSessionPrompt.trim()}
                style={{
                  width: "100%",
                  padding: "10px",
                  backgroundColor: "#3b82f6",
                  color: "#fff",
                  border: "none",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: 600,
                }}
              >
                Launch with AI Leader
              </button>
            </div>
          </div>

          {/* Sessions list - Fixed Header matching sidebar theme */}
          <div style={{ padding: "12px 15px 8px", background: "#1a1a2e" }}>
            <strong
              style={{
                fontSize: "13px",
                color: "#888",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Active Sessions ({sessions.length})
            </strong>
          </div>

          {/* Sessions List - Flex Grow Scrollable */}
          <div style={{ flex: 1, overflowY: "auto", padding: "0 15px 15px" }}>
            {sessions.length === 0 ? (
              <div style={{ color: "#888", fontSize: "14px" }}>
                No active sessions
              </div>
            ) : (
              sessions.map((session) => (
                <div
                  key={session.session_id}
                  onClick={() => loadSessionDetails(session.session_id)}
                  style={{
                    padding: "10px",
                    marginBottom: "8px",
                    backgroundColor:
                      selectedSession?.session_id === session.session_id
                        ? "#3b82f6"
                        : "#2a2a3e",
                    borderRadius: "4px",
                    cursor: "pointer",
                    transition: "background-color 0.2s",
                  }}
                >
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: "bold",
                      marginBottom: "4px",
                    }}
                  >
                    {session.prompt.substring(0, 50)}
                    {session.prompt.length > 50 ? "..." : ""}
                  </div>
                  <div style={{ fontSize: "12px", color: "#888" }}>
                    {session.todo_count} todos • {session.message_count}{" "}
                    messages
                  </div>
                  <div
                    style={{
                      fontSize: "11px",
                      color: "#666",
                      marginTop: "4px",
                    }}
                  >
                    {new Date(session.created_at).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Main content area */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {selectedSession ? (
            <>
              <div
                style={{
                  padding: "20px",
                  borderBottom: "1px solid #2a2a3e",
                }}
              >
                <h3 style={{ margin: 0, marginBottom: "10px" }}>
                  {selectedSession.prompt}
                </h3>
                <div style={{ fontSize: "12px", color: "#888" }}>
                  Created:{" "}
                  {new Date(selectedSession.created_at).toLocaleString()}
                  <span style={{ marginLeft: "20px" }}>
                    Status: {selectedSession.status}
                  </span>
                  {companyReport?.summary ? (
                    <span style={{ marginLeft: "20px", color: "#a3e635" }}>
                      {companyReport.summary}
                    </span>
                  ) : null}
                </div>
                <div
                  style={{ display: "flex", gap: "10px", marginTop: "10px" }}
                >
                  <button
                    onClick={() => closeSession(selectedSession.session_id)}
                    style={{
                      padding: "6px 12px",
                      backgroundColor: "#f59e0b",
                      color: "#111827",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    Archive Session
                  </button>
                  <button
                    onClick={() => deleteSession(selectedSession.session_id)}
                    style={{
                      padding: "6px 12px",
                      backgroundColor: "#dc2626",
                      color: "#fff",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                    }}
                  >
                    Delete Session
                  </button>
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                  padding: "12px 20px",
                  borderBottom: "1px solid #2a2a3e",
                  background: "rgba(15, 23, 42, 0.4)",
                }}
              >
                <div
                  style={{
                    background: "#1e1e2e",
                    border: "1px solid #2a2a3e",
                    borderRadius: "8px",
                    padding: "12px",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                    KPI Last Updated
                  </div>
                  {kpiStatus ? (
                    <div style={{ marginTop: "6px", fontSize: "13px" }}>
                      <div style={{ fontWeight: 600 }}>{kpiStatus.title}</div>
                      <div style={{ color: "#a1a1aa", fontSize: "12px" }}>
                        Updated by: {kpiStatus.updated_by || "unknown"}
                      </div>
                      <div style={{ color: "#a1a1aa", fontSize: "12px" }}>
                        Owner: {kpiStatus.owner_id || "unassigned"}
                      </div>
                      <div style={{ color: "#94a3b8", fontSize: "11px" }}>
                        {kpiStatus.updated_at
                          ? new Date(kpiStatus.updated_at).toLocaleString()
                          : "no update"}
                      </div>
                    </div>
                  ) : (
                    <div
                      style={{
                        marginTop: "6px",
                        color: "#64748b",
                        fontSize: "12px",
                      }}
                    >
                      No KPI updates yet
                    </div>
                  )}
                </div>

                <div
                  style={{
                    background: "#1e1e2e",
                    border: "1px solid #2a2a3e",
                    borderRadius: "8px",
                    padding: "12px",
                    maxHeight: "150px",
                    overflowY: "auto",
                  }}
                >
                  <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                    Leadership Log (latest)
                  </div>
                  {leadershipLog?.length ? (
                    <ul style={{ padding: "8px 0 0 16px", margin: 0 }}>
                      {leadershipLog.slice(0, 6).map((entry, idx) => (
                        <li
                          key={idx}
                          style={{
                            fontSize: "12px",
                            color: "#cbd5e1",
                            marginBottom: "6px",
                          }}
                        >
                          <span style={{ color: "#94a3b8" }}>
                            {entry.timestamp
                              ? new Date(entry.timestamp).toLocaleTimeString()
                              : "--"}
                            :
                          </span>{" "}
                          {entry.action}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div
                      style={{
                        marginTop: "6px",
                        color: "#64748b",
                        fontSize: "12px",
                      }}
                    >
                      No leadership actions logged yet
                    </div>
                  )}
                </div>
              </div>

              <div style={{ flex: 1, overflow: "auto", padding: "20px" }}>
                <div
                  style={{
                    marginBottom: "24px",
                    padding: "14px",
                    borderRadius: "8px",
                    border: "1px solid #2a2a3e",
                    background: "#0f172a",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "10px",
                    }}
                  >
                    <h4 style={{ margin: 0, fontSize: "14px" }}>
                      Proof Artifacts (Live Output)
                    </h4>
                    <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                      Latest AI execution evidence
                    </span>
                  </div>
                  {taskArtifacts.length ? (
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: "10px",
                      }}
                    >
                      {taskArtifacts.slice(0, 4).map((artifact) => (
                        <div
                          key={artifact.path}
                          style={{
                            padding: "10px",
                            borderRadius: "6px",
                            background: "#111827",
                            border: "1px solid #1f2937",
                          }}
                        >
                          <div
                            style={{
                              fontSize: "11px",
                              color: "#94a3b8",
                              marginBottom: "6px",
                            }}
                          >
                            {artifact.modified
                              ? new Date(artifact.modified).toLocaleString()
                              : "--"}
                          </div>
                          <button
                            onClick={() => openArtifact(artifact.path)}
                            style={{
                              marginBottom: "6px",
                              background: "transparent",
                              border: "1px solid #334155",
                              color: "#93c5fd",
                              padding: "4px 8px",
                              borderRadius: "6px",
                              fontSize: "11px",
                              cursor: "pointer",
                            }}
                          >
                            View Output
                          </button>
                          <pre
                            style={{
                              margin: 0,
                              fontSize: "11px",
                              color: "#e2e8f0",
                              whiteSpace: "pre-wrap",
                            }}
                          >
                            {artifact.preview || "No preview available"}
                          </pre>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: "#94a3b8", fontSize: "12px" }}>
                      No artifacts yet. Execute a task to generate proof.
                    </div>
                  )}
                </div>
                <div
                  style={{
                    marginBottom: "24px",
                    padding: "14px",
                    borderRadius: "8px",
                    border: "1px solid #2a2a3e",
                    background: "#111827",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "10px",
                    }}
                  >
                    <h4 style={{ margin: 0, fontSize: "14px" }}>
                      Task Library
                    </h4>
                    <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                      Inject focused tasks into this session
                    </span>
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "2fr 1fr auto",
                      gap: "10px",
                      alignItems: "center",
                    }}
                  >
                    <select
                      value={selectedLibraryTask}
                      onChange={(e) => setSelectedLibraryTask(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "8px",
                        backgroundColor: "#1f2937",
                        color: "#fff",
                        border: "1px solid #334155",
                        borderRadius: "6px",
                        fontSize: "12px",
                      }}
                    >
                      {taskLibrary.map((task) => (
                        <option key={task.id} value={task.id}>
                          {task.title}
                        </option>
                      ))}
                    </select>
                    <input
                      type="datetime-local"
                      value={librarySchedule}
                      onChange={(e) => setLibrarySchedule(e.target.value)}
                      style={{
                        width: "100%",
                        padding: "8px",
                        backgroundColor: "#1f2937",
                        color: "#fff",
                        border: "1px solid #334155",
                        borderRadius: "6px",
                        fontSize: "12px",
                      }}
                    />
                    <button
                      onClick={addTaskFromLibrary}
                      disabled={loading}
                      style={{
                        padding: "8px 12px",
                        backgroundColor: "#3b82f6",
                        color: "#fff",
                        border: "none",
                        borderRadius: "6px",
                        fontSize: "12px",
                        cursor: loading ? "not-allowed" : "pointer",
                      }}
                    >
                      Add Task
                    </button>
                  </div>
                </div>

                {/* Todos */}
                <div style={{ marginBottom: "30px" }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "15px",
                    }}
                  >
                    <h4 style={{ margin: 0 }}>
                      Active Assignment Queue (
                      {selectedSession.todos?.length || 0})
                    </h4>
                    <span
                      style={{
                        fontSize: "12px",
                        color: "#22c55e",
                        fontWeight: "bold",
                      }}
                    >
                      ● AI LEADERSHIP ENGAGED
                    </span>
                  </div>
                  {selectedSession.todos?.length ? (
                    selectedSession.todos.map((todo, idx) => {
                      const todoKey = todo.id || `idx-${idx}`;
                      const draftValue =
                        rescheduleDrafts[todoKey] ??
                        toDateTimeLocalValue(todo.scheduled_for);
                      return (
                        <div
                          key={todoKey}
                          style={{
                            padding: "12px",
                            marginBottom: "8px",
                            backgroundColor: "#2a2a3e",
                            borderRadius: "4px",
                            borderLeft: `4px solid ${
                              todo.status === "completed"
                                ? "#22c55e"
                                : todo.status === "in-progress"
                                  ? "#3b82f6"
                                  : todo.status === "awaiting-consensus"
                                    ? "#f59e0b"
                                    : todo.status === "blocked"
                                      ? "#dc2626"
                                      : "#888"
                            }`,
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                            }}
                          >
                            <div style={{ fontWeight: "bold" }}>
                              {todo.title || todo.description}
                            </div>
                            <div style={{ display: "flex", gap: "6px" }}>
                              <div
                                style={{
                                  fontSize: "11px",
                                  backgroundColor: "rgba(255,255,255,0.1)",
                                  padding: "2px 6px",
                                  borderRadius: "4px",
                                  color: "#ccc",
                                }}
                              >
                                {todo.owner || "No owner"}
                              </div>
                              <div
                                style={{
                                  fontSize: "11px",
                                  backgroundColor: todo.ai_validated
                                    ? "rgba(34,197,94,0.2)"
                                    : "rgba(248,113,113,0.2)",
                                  padding: "2px 6px",
                                  borderRadius: "4px",
                                  color: todo.ai_validated
                                    ? "#4ade80"
                                    : "#f87171",
                                }}
                              >
                                {todo.ai_validated
                                  ? "AI-validated"
                                  : "Needs AI validation"}
                              </div>
                              {todo.approval_required ? (
                                <div
                                  style={{
                                    fontSize: "11px",
                                    backgroundColor:
                                      todo.approval_status === "approved"
                                        ? "rgba(34,197,94,0.2)"
                                        : "rgba(251,146,60,0.2)",
                                    padding: "2px 6px",
                                    borderRadius: "4px",
                                    color:
                                      todo.approval_status === "approved"
                                        ? "#4ade80"
                                        : "#fb923c",
                                  }}
                                >
                                  {todo.approval_status === "approved"
                                    ? "CEO-approved"
                                    : "Needs CEO approval"}
                                </div>
                              ) : null}
                            </div>
                          </div>
                          <div
                            style={{
                              fontSize: "12px",
                              color: "#888",
                              marginTop: "4px",
                            }}
                          >
                            Status: {todo.status}{" "}
                            {todo.source ? `• Source: ${todo.source}` : ""}
                            {todo.validation_status
                              ? ` • Validation: ${todo.validation_status}`
                              : ""}
                            {todo.approval_status
                              ? ` • Approval: ${todo.approval_status}`
                              : ""}
                          </div>
                          <div
                            style={{
                              fontSize: "11px",
                              color: "#94a3b8",
                              marginTop: "4px",
                            }}
                          >
                            Assigned:{" "}
                            {todo.assigned_agent ||
                              todo.owner_id ||
                              "unassigned"}
                            {todo.updated_by
                              ? ` • Updated by: ${todo.updated_by}`
                              : ""}
                            {todo.started_at
                              ? ` • Started: ${new Date(todo.started_at).toLocaleTimeString()}`
                              : ""}
                          </div>
                          {todo.scheduled_for ? (
                            <div
                              style={{
                                fontSize: "12px",
                                color: "#94a3b8",
                                marginTop: "4px",
                              }}
                            >
                              Scheduled:{" "}
                              {new Date(todo.scheduled_for).toLocaleString()}
                            </div>
                          ) : null}
                          {todo.artifact_path ? (
                            <div
                              style={{
                                fontSize: "11px",
                                color: "#a3e635",
                                marginTop: "6px",
                                wordBreak: "break-all",
                              }}
                            >
                              Proof: {todo.artifact_path}
                              <button
                                onClick={() => openArtifact(todo.artifact_path)}
                                style={{
                                  marginLeft: "8px",
                                  background: "transparent",
                                  border: "1px solid #334155",
                                  color: "#93c5fd",
                                  padding: "2px 6px",
                                  borderRadius: "6px",
                                  fontSize: "10px",
                                  cursor: "pointer",
                                }}
                              >
                                View Output
                              </button>
                            </div>
                          ) : (
                            <div
                              style={{
                                fontSize: "11px",
                                color: "#64748b",
                                marginTop: "6px",
                              }}
                            >
                              Proof: pending artifact
                            </div>
                          )}

                          <div
                            style={{
                              display: "flex",
                              flexWrap: "wrap",
                              gap: "8px",
                              marginTop: "10px",
                              alignItems: "center",
                            }}
                          >
                            <select
                              value={todo.status || "pending"}
                              onChange={(e) =>
                                updateTodoStatus(todo.id, e.target.value)
                              }
                              style={{
                                padding: "6px",
                                backgroundColor: "#111827",
                                color: "#fff",
                                border: "1px solid #334155",
                                borderRadius: "6px",
                                fontSize: "11px",
                              }}
                            >
                              <option value="pending">pending</option>
                              <option value="scheduled">scheduled</option>
                              <option value="in-progress">in-progress</option>
                              <option value="completed">completed</option>
                              <option value="blocked">blocked</option>
                              <option value="awaiting-consensus">
                                awaiting-consensus
                              </option>
                              <option value="cancelled">cancelled</option>
                            </select>
                            <input
                              type="datetime-local"
                              value={draftValue}
                              onChange={(e) =>
                                setRescheduleDrafts((prev) => ({
                                  ...prev,
                                  [todoKey]: e.target.value,
                                }))
                              }
                              style={{
                                padding: "6px",
                                backgroundColor: "#111827",
                                color: "#fff",
                                border: "1px solid #334155",
                                borderRadius: "6px",
                                fontSize: "11px",
                              }}
                            />
                            <button
                              onClick={() =>
                                rescheduleTask(
                                  todo.id,
                                  toIsoFromLocalValue(draftValue),
                                )
                              }
                              disabled={!todo.id || !draftValue}
                              style={{
                                padding: "6px 10px",
                                backgroundColor: "#0ea5e9",
                                color: "#fff",
                                border: "none",
                                borderRadius: "6px",
                                fontSize: "11px",
                                cursor:
                                  !todo.id || !draftValue
                                    ? "not-allowed"
                                    : "pointer",
                              }}
                            >
                              Reschedule
                            </button>
                            {todo.approval_required &&
                            todo.approval_status !== "approved" ? (
                              <button
                                onClick={() => approveTodo(todo.id)}
                                style={{
                                  padding: "6px 10px",
                                  backgroundColor: "#f59e0b",
                                  color: "#111827",
                                  border: "none",
                                  borderRadius: "6px",
                                  fontSize: "11px",
                                  cursor: "pointer",
                                  fontWeight: 600,
                                }}
                              >
                                Approve Outbound
                              </button>
                            ) : null}
                          </div>

                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                              marginTop: "12px",
                              paddingTop: "12px",
                              borderTop: "1px solid rgba(255,255,255,0.05)",
                            }}
                          >
                            <span
                              style={{
                                fontSize: "11px",
                                color: "#888",
                                textTransform: "uppercase",
                                letterSpacing: "0.1em",
                              }}
                            >
                              Status: {todo.status || "PULSED"}
                            </span>

                            <div
                              style={{
                                fontSize: "11px",
                                color: "#444",
                                fontStyle: "italic",
                              }}
                            >
                              Leader Managed
                            </div>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div style={{ color: "#888" }}>No tasks yet</div>
                  )}
                </div>

                {/* Messages */}
                <div>
                  <h4 style={{ marginBottom: "15px" }}>
                    Messages ({selectedSession.messages?.length || 0})
                  </h4>
                  {selectedSession.messages?.length ? (
                    selectedSession.messages.map((msg, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: "12px",
                          marginBottom: "8px",
                          backgroundColor: "#2a2a3e",
                          borderRadius: "4px",
                        }}
                      >
                        <div
                          style={{
                            fontSize: "12px",
                            color: "#888",
                            marginBottom: "4px",
                          }}
                        >
                          {msg.role} •{" "}
                          {msg.timestamp
                            ? new Date(msg.timestamp).toLocaleTimeString()
                            : ""}
                        </div>
                        <div>{msg.content}</div>
                      </div>
                    ))
                  ) : (
                    <div style={{ color: "#888" }}>No messages yet</div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div
              style={{
                flex: 1,
                padding: "40px",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "flex-start",
                color: "#94a3b8",
                overflowY: "auto",
                background: "#0f0f1e",
              }}
            >
              <div style={{ maxWidth: "1000px", width: "100%" }}>
                <h1
                  style={{
                    color: "#fff",
                    marginBottom: "10px",
                    fontSize: "28px",
                  }}
                >
                  OpenWork Control Center
                </h1>
                <p style={{ marginBottom: "30px", fontSize: "16px" }}>
                  Manage your AI company orchestrations, tasks, and automated
                  workflows.
                </p>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "25px",
                  }}
                >
                  {/* Workflow Templates */}
                  <div
                    style={{
                      background: "#1e1e2e",
                      padding: "25px",
                      borderRadius: "12px",
                      border: "1px solid #2a2a3e",
                      boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                    }}
                  >
                    <h2
                      style={{
                        color: "#fff",
                        fontSize: "20px",
                        marginBottom: "8px",
                      }}
                    >
                      Workflow Blueprints
                    </h2>
                    <p style={{ fontSize: "13px", marginBottom: "20px" }}>
                      Quick-start your automation with pre-defined company
                      templates.
                    </p>

                    <select
                      value={selectedTemplateId}
                      onChange={(e) => {
                        const id = e.target.value;
                        setSelectedTemplateId(id);
                        const found = templates.find((t) => t.id === id);
                        setTemplatePreview(found?.content || "");
                      }}
                      style={{
                        width: "100%",
                        padding: "12px",
                        backgroundColor: "#2a2a3e",
                        color: "#fff",
                        border: "1px solid #3a3a4e",
                        borderRadius: "6px",
                        marginBottom: "15px",
                        fontSize: "14px",
                      }}
                    >
                      <option value="">Choose a Template...</option>
                      {templates.map((tpl) => (
                        <option key={tpl.id} value={tpl.id}>
                          {tpl.title}
                        </option>
                      ))}
                    </select>

                    {selectedTemplateId && (
                      <div style={{ transition: "all 0.3s ease" }}>
                        <textarea
                          readOnly
                          value={templatePreview}
                          style={{
                            width: "100%",
                            minHeight: "180px",
                            padding: "12px",
                            backgroundColor: "#161625",
                            color: "#94a3b8",
                            border: "1px solid #3a3a4e",
                            borderRadius: "6px",
                            fontFamily: "Fira Code, monospace",
                            fontSize: "12px",
                            marginBottom: "15px",
                            resize: "none",
                          }}
                        />
                        <button
                          onClick={createSessionFromTemplate}
                          style={{
                            width: "100%",
                            padding: "14px",
                            backgroundColor: "#6366f1",
                            color: "#fff",
                            border: "none",
                            borderRadius: "6px",
                            fontWeight: 600,
                            cursor: "pointer",
                            fontSize: "15px",
                          }}
                        >
                          Deploy Workflow
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Operational Guide/Stats */}
                  <div
                    style={{
                      background: "#1e1e2e",
                      padding: "25px",
                      borderRadius: "12px",
                      border: "1px solid #2a2a3e",
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                    }}
                  >
                    <div>
                      <h2
                        style={{
                          color: "#fff",
                          fontSize: "20px",
                          marginBottom: "8px",
                        }}
                      >
                        Company Overview
                      </h2>
                      <div style={{ marginTop: "20px" }}>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            marginBottom: "12px",
                            padding: "10px",
                            background: "rgba(255,255,255,0.03)",
                            borderRadius: "6px",
                          }}
                        >
                          <span>Active Workflows</span>
                          <span style={{ color: "#fff", fontWeight: "bold" }}>
                            {companyReport?.sessions?.active ?? sessions.length}
                          </span>
                        </div>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            marginBottom: "12px",
                            padding: "10px",
                            background: "rgba(255,255,255,0.03)",
                            borderRadius: "6px",
                          }}
                        >
                          <span>Server Status</span>
                          <span
                            style={{
                              color:
                                (companyReport?.opencode?.running ??
                                serverStatus?.server_running)
                                  ? "#4ade80"
                                  : "#f87171",
                              fontWeight: "bold",
                            }}
                          >
                            {(companyReport?.opencode?.running ??
                            serverStatus?.server_running)
                              ? "ONLINE"
                              : "OFFLINE"}
                          </span>
                        </div>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            marginBottom: "12px",
                            padding: "10px",
                            background: "rgba(255,255,255,0.03)",
                            borderRadius: "6px",
                          }}
                        >
                          <span>Runner Active</span>
                          <span
                            style={{
                              color:
                                (companyReport?.runner?.running ??
                                runnerStatus?.running)
                                  ? "#4ade80"
                                  : "#f87171",
                              fontWeight: "bold",
                            }}
                          >
                            {(companyReport?.runner?.running ??
                            runnerStatus?.running)
                              ? "YES"
                              : "NO"}
                          </span>
                        </div>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            marginBottom: "12px",
                            padding: "10px",
                            background: "rgba(255,255,255,0.03)",
                            borderRadius: "6px",
                          }}
                        >
                          <span>Tasks In Progress</span>
                          <span style={{ color: "#fff", fontWeight: "bold" }}>
                            {companyReport?.tasks?.by_status?.["in-progress"] ??
                              0}
                          </span>
                        </div>
                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            marginBottom: "12px",
                            padding: "10px",
                            background: "rgba(255,255,255,0.03)",
                            borderRadius: "6px",
                          }}
                        >
                          <span>Total Tasks</span>
                          <span style={{ color: "#fff", fontWeight: "bold" }}>
                            {companyReport?.tasks?.total ?? 0}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div
                      style={{
                        padding: "15px",
                        background: "rgba(59, 130, 246, 0.1)",
                        borderRadius: "8px",
                        border: "1px solid rgba(59, 130, 246, 0.2)",
                      }}
                    >
                      <strong
                        style={{
                          color: "#3b82f6",
                          display: "block",
                          marginBottom: "5px",
                        }}
                      >
                        Pro Tip:
                      </strong>
                      <span style={{ fontSize: "12px" }}>
                        Select a session from the sidebar to inject specific
                        tasks from the Task Library or review live logs.
                      </span>
                    </div>
                  </div>
                </div>

                <div
                  style={{
                    marginTop: "40px",
                    padding: "20px",
                    borderTop: "1px solid #2a2a3e",
                    textAlign: "center",
                    fontSize: "12px",
                    color: "#4b5563",
                  }}
                >
                  ✨ Agent Amigos © 2025 Darrell Buttigieg. System Ready.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {artifactViewer.open ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.75)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 2000,
            padding: "24px",
          }}
          onClick={() =>
            setArtifactViewer({ open: false, path: "", content: "" })
          }
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              maxWidth: "800px",
              width: "100%",
              background: "#0f172a",
              borderRadius: "12px",
              border: "1px solid #1f2937",
              padding: "16px",
              color: "#e2e8f0",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "10px",
              }}
            >
              <div style={{ fontSize: "12px", color: "#94a3b8" }}>
                {artifactViewer.path}
              </div>
              <button
                onClick={() =>
                  setArtifactViewer({ open: false, path: "", content: "" })
                }
                style={{
                  background: "transparent",
                  border: "1px solid #334155",
                  color: "#e2e8f0",
                  padding: "4px 8px",
                  borderRadius: "6px",
                  cursor: "pointer",
                }}
              >
                Close
              </button>
            </div>
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                fontSize: "12px",
                lineHeight: 1.5,
              }}
            >
              {artifactViewer.content}
            </pre>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default OpenWorkConsole;
