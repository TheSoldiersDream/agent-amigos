import React, { useEffect, useState, useCallback, useRef } from "react";
import axios from "axios";

const GameTrainerConsole = ({ isOpen, onToggle, apiUrl }) => {
  const backendUrl = apiUrl || "http://127.0.0.1:65252";
  const [activeTab, setActiveTab] = useState("session");

  // AI Trainer Session
  const [gameName, setGameName] = useState("");
  const [platform, setPlatform] = useState("PC");
  const [notes, setNotes] = useState("");
  const [session, setSession] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [trainerMode, setTrainerMode] = useState("training");
  const [autoRun, setAutoRun] = useState(true);
  const [allowMemoryTools, setAllowMemoryTools] = useState(false);

  // Dragging state
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("gameTrainerPosition");
      if (saved) {
        const pos = JSON.parse(saved);
        // Ensure position is within screen bounds
        return {
          x: Math.max(0, Math.min(pos.x, window.innerWidth - 400)),
          y: Math.max(0, Math.min(pos.y, window.innerHeight - 200)),
        };
      }
    } catch (err) {
      // ignore malformed storage
    }
    return { x: 100, y: 50 };
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("gameTrainerSize");
      if (saved) {
        const val = JSON.parse(saved);
        return {
          width: Math.max(640, val.width || 900),
          height: Math.max(520, val.height || 680),
        };
      }
    } catch (err) {
      // ignore malformed storage
    }
    return { width: 900, height: 680 };
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const consoleRef = useRef(null);

  // Process Management
  const [processes, setProcesses] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [attachedProcess, setAttachedProcess] = useState(null);
  const [loadingProcesses, setLoadingProcesses] = useState(false);

  // Memory Scanner
  const [scanValue, setScanValue] = useState("");
  const [scanType, setScanType] = useState("int");
  const [scanResults, setScanResults] = useState([]);
  const [selectedAddress, setSelectedAddress] = useState(null);
  const [frozenValues, setFrozenValues] = useState([]);

  // Status
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const parseNumericInput = useCallback((rawValue, type) => {
    const text = rawValue == null ? "" : String(rawValue).trim();
    if (!text) {
      return { ok: false, error: "Value is required" };
    }

    if (type === "float") {
      const parsed = Number.parseFloat(text);
      if (!Number.isFinite(parsed)) {
        return { ok: false, error: "Enter a valid float value" };
      }
      return { ok: true, value: parsed };
    }

    const normalized = text.toLowerCase();
    const parsed = normalized.startsWith("0x")
      ? Number.parseInt(normalized, 16)
      : Number.parseInt(normalized, 10);
    if (Number.isNaN(parsed)) {
      return { ok: false, error: "Enter a valid integer value" };
    }
    return { ok: true, value: parsed };
  }, []);

  // Drag handlers
  const handleMouseDown = (e) => {
    if (e.target.closest(".no-drag") || e.target.closest(".resize-handle"))
      return;
    setIsDragging(true);
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    });
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging) {
        const newX = Math.max(
          0,
          Math.min(e.clientX - dragOffset.x, window.innerWidth - size.width),
        );
        const newY = Math.max(
          0,
          Math.min(e.clientY - dragOffset.y, window.innerHeight - 80),
        );
        setPosition({ x: newX, y: newY });
      }
      if (isResizing && consoleRef.current) {
        const rect = consoleRef.current.getBoundingClientRect();
        const nextWidth = Math.max(640, e.clientX - rect.left);
        const nextHeight = Math.max(520, e.clientY - rect.top);
        setSize({
          width: Math.min(window.innerWidth - rect.left, nextWidth),
          height: Math.min(window.innerHeight - rect.top, nextHeight),
        });
      }
    };

    const handleMouseUp = () => {
      if (isDragging) {
        setIsDragging(false);
        localStorage.setItem("gameTrainerPosition", JSON.stringify(position));
      }
      if (isResizing) {
        setIsResizing(false);
        localStorage.setItem("gameTrainerSize", JSON.stringify(size));
      }
    };

    if (isDragging || isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging, isResizing, dragOffset, position, size, consoleRef]);

  const handleResizeStart = (e) => {
    e.stopPropagation();
    setIsResizing(true);
  };

  // Auto-refresh processes and status (advanced tools only)
  useEffect(() => {
    if (isOpen && allowMemoryTools) {
      loadProcesses();
      loadStatus();
      const interval = setInterval(() => {
        loadProcesses();
        loadStatus();
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [isOpen, allowMemoryTools]);

  // Load session status when console opens
  useEffect(() => {
    if (!isOpen) return;
    loadSessionStatus();
  }, [isOpen]);

  // Auto-run analysis tick
  useEffect(() => {
    if (!isOpen || !session || !autoRun) return;
    const interval = setInterval(() => {
      runAnalysis();
    }, 2500);
    return () => clearInterval(interval);
  }, [isOpen, session, autoRun]);

  const loadSessionStatus = async () => {
    try {
      const res = await axios.get(`${backendUrl}/trainer/session/status`);
      if (res.data?.active) {
        setSession(res.data);
        setTrainerMode(res.data.trainer_mode || "training");
        setAllowMemoryTools(!!res.data.allow_memory_tools);
      } else {
        setSession(null);
      }
    } catch (err) {
      console.error("Failed to load trainer session:", err);
    }
  };

  const startSession = async () => {
    if (!gameName.trim()) {
      setError("Game name is required");
      return;
    }
    try {
      setError("");
      const res = await axios.post(`${backendUrl}/trainer/session/start`, {
        game_name: gameName.trim(),
        platform,
        notes,
        allow_memory_tools: allowMemoryTools,
      });
      setSession(res.data);
      setTrainerMode(res.data.trainer_mode || "training");
      setActiveTab("analysis");
      setSuccess(`Session started for ${res.data.game_name}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to start session");
    }
  };

  const updateTrainerMode = async (mode) => {
    if (!session) return;
    try {
      await axios.post(`${backendUrl}/trainer/session/mode`, { mode });
      setTrainerMode(mode);
      setSession((prev) => ({ ...prev, trainer_mode: mode }));
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update mode");
    }
  };

  const runAnalysis = async () => {
    if (!session) return;
    try {
      const res = await axios.post(`${backendUrl}/trainer/session/analysis`);
      setAnalysis(res.data);
    } catch (err) {
      console.error("Analysis tick failed:", err);
    }
  };

  const toggleMemoryTools = async (enabled) => {
    if (!session) {
      setAllowMemoryTools(enabled);
      return;
    }
    try {
      const res = await axios.post(
        `${backendUrl}/trainer/session/memory-tools`,
        {
          enabled,
        },
      );
      setAllowMemoryTools(!!res.data.allow_memory_tools);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to update memory tools");
    }
  };

  const loadProcesses = async () => {
    try {
      setLoadingProcesses(true);
      const res = await axios.get(`${backendUrl}/trainer/processes`);
      setProcesses(res.data || []);
    } catch (err) {
      console.error("Failed to load processes:", err);
    } finally {
      setLoadingProcesses(false);
    }
  };

  const loadStatus = async () => {
    try {
      const res = await axios.get(`${backendUrl}/trainer/status`);
      setStatus(res.data);
      setAttachedProcess(res.data.attached_process);
      setFrozenValues(res.data.frozen || []);
    } catch (err) {
      console.error("Failed to load status:", err);
    }
  };

  const attachToProcess = async (pid, name) => {
    try {
      setError("");
      setSuccess("");
      await axios.post(`${backendUrl}/trainer/attach/pid`, { pid });
      setSuccess(`Attached to ${name} (PID: ${pid})`);
      setActiveTab("memory-tools");
      await loadStatus();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to attach");
    }
  };

  const detachProcess = async () => {
    try {
      await axios.post(`${backendUrl}/trainer/detach`);
      setAttachedProcess(null);
      setScanResults([]);
      setSuccess("Detached from process");
      await loadStatus();
    } catch (err) {
      setError("Failed to detach");
    }
  };

  const scanMemory = async () => {
    if (!attachedProcess) {
      setError("Attach to a process first");
      return;
    }
    try {
      setError("");
      const parsed = parseNumericInput(scanValue, scanType);
      if (!parsed.ok) {
        setError(parsed.error);
        return;
      }
      const res = await axios.post(`${backendUrl}/trainer/scan/value`, {
        value: parsed.value,
        type: scanType,
      });
      setScanResults(res.data.addresses || []);
      setSuccess(`Found ${res.data.count} matches`);
    } catch (err) {
      setError(err.response?.data?.detail || "Scan failed");
    }
  };

  const writeMemory = async (address, value) => {
    try {
      const parsed = parseNumericInput(value, scanType);
      if (!parsed.ok) {
        setError(parsed.error);
        return;
      }
      await axios.post(`${backendUrl}/trainer/write`, {
        address: parseInt(address),
        type: scanType,
        value: parsed.value,
      });
      setSuccess(`Written to 0x${address.toString(16)}`);
    } catch (err) {
      setError("Write failed");
    }
  };

  const freezeMemory = async (address, value) => {
    try {
      const parsed = parseNumericInput(value, scanType);
      if (!parsed.ok) {
        setError(parsed.error);
        return;
      }
      await axios.post(`${backendUrl}/trainer/freeze`, {
        address: parseInt(address),
        type: scanType,
        value: parsed.value,
        interval_ms: 100,
      });
      setSuccess("Value frozen");
      await loadStatus();
    } catch (err) {
      setError("Freeze failed");
    }
  };

  const unfreezeMemory = async (address) => {
    try {
      await axios.post(`${backendUrl}/trainer/unfreeze`, {
        address: parseInt(address),
      });
      setSuccess("Value unfrozen");
      await loadStatus();
    } catch (err) {
      setError("Unfreeze failed");
    }
  };

  const filteredProcesses = processes.filter(
    (p) =>
      (p.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.exe || "").toLowerCase().includes(searchTerm.toLowerCase()),
  );

  if (!isOpen) return null;

  return (
    <div
      ref={consoleRef}
      style={{
        position: "fixed",
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: `${size.width}px`,
        height: `${size.height}px`,
        maxHeight: "90vh",
        background: "linear-gradient(135deg, #0f0f23 0%, #1a1a2e 100%)",
        boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        border: "1px solid #2d2d44",
        borderRadius: "12px",
        overflow: "hidden",
        cursor: isDragging ? "grabbing" : "default",
      }}
    >
      {/* Header */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          padding: "20px 24px",
          borderBottom: "1px solid #2d2d44",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "rgba(0,0,0,0.3)",
          cursor: isDragging ? "grabbing" : "grab",
          userSelect: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "40px",
              height: "40px",
              background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
              borderRadius: "10px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "20px",
            }}
          >
            🎮
          </div>
          <div>
            <h2
              style={{
                margin: 0,
                color: "#fff",
                fontSize: "20px",
                fontWeight: 600,
              }}
            >
              AMIGOS::AI_GAME_TRAINER
            </h2>
            <p style={{ margin: "2px 0 0 0", color: "#888", fontSize: "12px" }}>
              {session
                ? `${session.game_name} • ${session.platform} • ${
                    session.trainer_mode || "training"
                  }`
                : "Provide game name and platform to begin"}
            </p>
          </div>
        </div>
        <button
          onClick={onToggle}
          className="no-drag"
          style={{
            width: "36px",
            height: "36px",
            background: "#2d2d44",
            border: "none",
            borderRadius: "8px",
            color: "#fff",
            cursor: "pointer",
            fontSize: "20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          ×
        </button>
      </div>

      {/* Status Bar */}
      {attachedProcess && allowMemoryTools && (
        <div
          style={{
            padding: "12px 24px",
            background: "rgba(102, 126, 234, 0.1)",
            borderBottom: "1px solid #2d2d44",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
            <div
              style={{
                background: "#10b981",
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                boxShadow: "0 0 8px #10b981",
              }}
            />
            <span style={{ color: "#fff", fontSize: "14px" }}>
              {attachedProcess.name} • PID {attachedProcess.pid} •{" "}
              {attachedProcess.memory_mb?.toFixed(1) || "?"} MB
            </span>
          </div>
          <button
            onClick={detachProcess}
            style={{
              padding: "6px 12px",
              background: "#ef4444",
              border: "none",
              borderRadius: "6px",
              color: "#fff",
              cursor: "pointer",
              fontSize: "12px",
              fontWeight: 500,
            }}
          >
            Disconnect
          </button>
        </div>
      )}

      {/* Tabs */}
      <div
        className="no-drag"
        style={{
          display: "flex",
          gap: "4px",
          padding: "16px 24px 0",
          borderBottom: "1px solid #2d2d44",
        }}
      >
        {["session", "analysis", "memory-tools"].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: "10px 20px",
              background: activeTab === tab ? "#667eea" : "transparent",
              border: "none",
              borderRadius: "8px 8px 0 0",
              color: activeTab === tab ? "#fff" : "#888",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: 500,
              textTransform: "capitalize",
              transition: "all 0.2s",
            }}
          >
            {tab.replace("-", " ")}
          </button>
        ))}
      </div>

      {/* Messages */}
      {(error || success) && (
        <div
          style={{
            margin: "16px 24px 0",
            padding: "12px 16px",
            background: error
              ? "rgba(239, 68, 68, 0.1)"
              : "rgba(16, 185, 129, 0.1)",
            border: `1px solid ${error ? "#ef4444" : "#10b981"}`,
            borderRadius: "8px",
            color: error ? "#ef4444" : "#10b981",
            fontSize: "13px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{error || success}</span>
          <button
            onClick={() => {
              setError("");
              setSuccess("");
            }}
            style={{
              background: "none",
              border: "none",
              color: "inherit",
              cursor: "pointer",
              fontSize: "16px",
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* Content */}
      <div
        className="no-drag"
        style={{ flex: 1, overflow: "auto", padding: "24px" }}
      >
        {activeTab === "session" && (
          <div>
            <div
              style={{
                padding: "18px",
                background: "#1a1a2e",
                border: "1px solid #2d2d44",
                borderRadius: "12px",
                marginBottom: "16px",
              }}
            >
              <h3 style={{ color: "#fff", marginBottom: "10px" }}>
                🎮 Declare Game
              </h3>
              <div style={{ display: "grid", gap: "12px" }}>
                <input
                  type="text"
                  placeholder="Game name (e.g., Valorant, Elden Ring)"
                  value={gameName}
                  onChange={(e) => setGameName(e.target.value)}
                  style={{
                    padding: "12px 14px",
                    background: "#0f0f23",
                    border: "1px solid #2d2d44",
                    borderRadius: "8px",
                    color: "#fff",
                    fontSize: "14px",
                    outline: "none",
                  }}
                />
                <div style={{ display: "flex", gap: "12px" }}>
                  <select
                    value={platform}
                    onChange={(e) => setPlatform(e.target.value)}
                    style={{
                      flex: 1,
                      padding: "12px 14px",
                      background: "#0f0f23",
                      border: "1px solid #2d2d44",
                      borderRadius: "8px",
                      color: "#fff",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  >
                    {[
                      "PC",
                      "Console (PlayStation)",
                      "Console (Xbox)",
                      "Console (Switch)",
                      "Emulator",
                    ].map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={startSession}
                    style={{
                      padding: "12px 20px",
                      background: "#667eea",
                      border: "none",
                      borderRadius: "8px",
                      color: "#fff",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    Start Session
                  </button>
                </div>
                <textarea
                  placeholder="Optional notes (playstyle, goals, constraints)"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  style={{
                    padding: "12px 14px",
                    background: "#0f0f23",
                    border: "1px solid #2d2d44",
                    borderRadius: "8px",
                    color: "#fff",
                    fontSize: "13px",
                    outline: "none",
                    resize: "vertical",
                  }}
                />
                <label
                  style={{
                    display: "flex",
                    gap: "10px",
                    alignItems: "center",
                    fontSize: "12px",
                    color: "#94a3b8",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={allowMemoryTools}
                    onChange={(e) => setAllowMemoryTools(e.target.checked)}
                  />
                  Enable advanced memory tools (explicit). No memory
                  modification unless you allow it.
                </label>
              </div>
            </div>

            {session && (
              <div
                style={{
                  padding: "18px",
                  background: "rgba(102, 126, 234, 0.08)",
                  border: "1px solid #2d2d44",
                  borderRadius: "12px",
                }}
              >
                <h3 style={{ color: "#fff", marginBottom: "10px" }}>
                  🧠 Boot Sequence
                </h3>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                    gap: "12px",
                    fontSize: "13px",
                    color: "#e2e8f0",
                  }}
                >
                  <div>Game: {session.game_name}</div>
                  <div>Platform: {session.platform}</div>
                  <div>Engine: {session.engine}</div>
                  <div>Genre: {session.genre}</div>
                  <div>Mode: {session.online}</div>
                </div>
                <div
                  style={{
                    marginTop: "12px",
                    fontSize: "12px",
                    color: "#94a3b8",
                  }}
                >
                  Knowledge graph loaded with safe, explainable strategies.
                  Autonomy runs in the selected mode.
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "memory-tools" && (
          <div>
            {!allowMemoryTools ? (
              <div
                style={{
                  padding: "24px",
                  background: "#1a1a2e",
                  border: "1px solid #2d2d44",
                  borderRadius: "12px",
                  color: "#94a3b8",
                }}
              >
                <h3 style={{ color: "#fff", marginBottom: "8px" }}>
                  🛡️ Advanced Tools Disabled
                </h3>
                <p style={{ fontSize: "13px" }}>
                  Memory inspection and modification are disabled by default.
                  Enable only if you explicitly allow it.
                </p>
                <button
                  onClick={() => toggleMemoryTools(true)}
                  style={{
                    marginTop: "12px",
                    padding: "10px 16px",
                    background: "#667eea",
                    border: "none",
                    borderRadius: "8px",
                    color: "#fff",
                    cursor: "pointer",
                  }}
                >
                  Enable Advanced Tools
                </button>
              </div>
            ) : (
              <div>
                <div style={{ marginBottom: "16px" }}>
                  <input
                    type="text"
                    placeholder="🔍 Search processes..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    style={{
                      width: "100%",
                      padding: "12px 16px",
                      background: "#1a1a2e",
                      border: "1px solid #2d2d44",
                      borderRadius: "8px",
                      color: "#fff",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                </div>

                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                  }}
                >
                  {filteredProcesses.map((proc) => (
                    <div
                      key={proc.pid}
                      onClick={() => attachToProcess(proc.pid, proc.name)}
                      style={{
                        padding: "16px",
                        background:
                          attachedProcess?.pid === proc.pid
                            ? "rgba(102, 126, 234, 0.2)"
                            : "#1a1a2e",
                        border:
                          attachedProcess?.pid === proc.pid
                            ? "1px solid #667eea"
                            : "1px solid #2d2d44",
                        borderRadius: "8px",
                        cursor: "pointer",
                        transition: "all 0.2s",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                      onMouseEnter={(e) => {
                        if (attachedProcess?.pid !== proc.pid) {
                          e.currentTarget.style.background = "#2d2d44";
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (attachedProcess?.pid !== proc.pid) {
                          e.currentTarget.style.background = "#1a1a2e";
                        }
                      }}
                    >
                      <div>
                        <div
                          style={{
                            color: "#fff",
                            fontWeight: 500,
                            marginBottom: "4px",
                          }}
                        >
                          {proc.name}
                        </div>
                        <div style={{ color: "#888", fontSize: "12px" }}>
                          PID {proc.pid} • {proc.memory_mb?.toFixed(1) || "?"}{" "}
                          MB
                        </div>
                      </div>
                      {attachedProcess?.pid === proc.pid && (
                        <div
                          style={{
                            background: "#10b981",
                            padding: "4px 12px",
                            borderRadius: "6px",
                            color: "#fff",
                            fontSize: "11px",
                            fontWeight: 600,
                          }}
                        >
                          CONNECTED
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {!attachedProcess ? (
                  <div
                    style={{
                      textAlign: "center",
                      padding: "60px 20px",
                      color: "#888",
                    }}
                  >
                    <div style={{ fontSize: "48px", marginBottom: "16px" }}>
                      🎯
                    </div>
                    <h3 style={{ color: "#fff", marginBottom: "8px" }}>
                      No Process Attached
                    </h3>
                    <p>Select a game process above to use memory tools.</p>
                  </div>
                ) : (
                  <div>
                    {/* Frozen Values */}
                    {frozenValues.length > 0 && (
                      <div style={{ marginBottom: "24px" }}>
                        <h3
                          style={{
                            color: "#fff",
                            marginBottom: "12px",
                            fontSize: "16px",
                          }}
                        >
                          🔒 Frozen Values ({frozenValues.length})
                        </h3>
                        <div
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: "8px",
                          }}
                        >
                          {frozenValues.map((frozen) => (
                            <div
                              key={frozen.address}
                              style={{
                                padding: "12px",
                                background: "#1a1a2e",
                                border: "1px solid #2d2d44",
                                borderRadius: "8px",
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                              }}
                            >
                              <div
                                style={{
                                  color: "#fff",
                                  fontFamily: "monospace",
                                  fontSize: "13px",
                                }}
                              >
                                {frozen.address} = {frozen.value}
                              </div>
                              <button
                                onClick={() =>
                                  unfreezeMemory(parseInt(frozen.address, 16))
                                }
                                style={{
                                  padding: "4px 12px",
                                  background: "#ef4444",
                                  border: "none",
                                  borderRadius: "6px",
                                  color: "#fff",
                                  cursor: "pointer",
                                  fontSize: "11px",
                                }}
                              >
                                Unfreeze
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Memory Scanner */}
                    <div
                      style={{
                        padding: "20px",
                        background: "#1a1a2e",
                        border: "1px solid #2d2d44",
                        borderRadius: "12px",
                        marginBottom: "16px",
                      }}
                    >
                      <h3
                        style={{
                          color: "#fff",
                          marginBottom: "16px",
                          fontSize: "16px",
                        }}
                      >
                        🔍 Memory Scanner
                      </h3>
                      <div
                        style={{
                          display: "flex",
                          gap: "12px",
                          marginBottom: "16px",
                        }}
                      >
                        <input
                          type="text"
                          placeholder="Enter value to scan..."
                          value={scanValue}
                          onChange={(e) => setScanValue(e.target.value)}
                          style={{
                            flex: 1,
                            padding: "10px 14px",
                            background: "#0f0f23",
                            border: "1px solid #2d2d44",
                            borderRadius: "8px",
                            color: "#fff",
                            fontSize: "14px",
                            outline: "none",
                          }}
                        />
                        <select
                          value={scanType}
                          onChange={(e) => setScanType(e.target.value)}
                          style={{
                            padding: "10px 14px",
                            background: "#0f0f23",
                            border: "1px solid #2d2d44",
                            borderRadius: "8px",
                            color: "#fff",
                            fontSize: "14px",
                            outline: "none",
                            cursor: "pointer",
                          }}
                        >
                          <option value="int">Integer</option>
                          <option value="float">Float</option>
                        </select>
                        <button
                          onClick={scanMemory}
                          disabled={!scanValue}
                          style={{
                            padding: "10px 24px",
                            background: scanValue ? "#667eea" : "#2d2d44",
                            border: "none",
                            borderRadius: "8px",
                            color: "#fff",
                            cursor: scanValue ? "pointer" : "not-allowed",
                            fontSize: "14px",
                            fontWeight: 500,
                          }}
                        >
                          Scan
                        </button>
                      </div>

                      {scanResults.length > 0 && (
                        <div>
                          <div
                            style={{
                              color: "#888",
                              marginBottom: "12px",
                              fontSize: "13px",
                            }}
                          >
                            Found {scanResults.length} addresses
                          </div>
                          <div
                            style={{
                              maxHeight: "300px",
                              overflow: "auto",
                              display: "flex",
                              flexDirection: "column",
                              gap: "6px",
                            }}
                          >
                            {scanResults.slice(0, 50).map((addr) => (
                              <div
                                key={addr}
                                style={{
                                  padding: "10px",
                                  background: "#0f0f23",
                                  border: "1px solid #2d2d44",
                                  borderRadius: "6px",
                                  display: "flex",
                                  justifyContent: "space-between",
                                  alignItems: "center",
                                }}
                              >
                                <span
                                  style={{
                                    color: "#667eea",
                                    fontFamily: "monospace",
                                    fontSize: "13px",
                                  }}
                                >
                                  0x{addr.toString(16).toUpperCase()}
                                </span>
                                <div style={{ display: "flex", gap: "6px" }}>
                                  <button
                                    onClick={() => {
                                      const val = prompt("Enter new value:");
                                      if (val) writeMemory(addr, val);
                                    }}
                                    style={{
                                      padding: "4px 10px",
                                      background: "#10b981",
                                      border: "none",
                                      borderRadius: "4px",
                                      color: "#fff",
                                      cursor: "pointer",
                                      fontSize: "11px",
                                    }}
                                  >
                                    Write
                                  </button>
                                  <button
                                    onClick={() => {
                                      const val = prompt(
                                        "Enter value to freeze:",
                                      );
                                      if (val) freezeMemory(addr, val);
                                    }}
                                    style={{
                                      padding: "4px 10px",
                                      background: "#667eea",
                                      border: "none",
                                      borderRadius: "4px",
                                      color: "#fff",
                                      cursor: "pointer",
                                      fontSize: "11px",
                                    }}
                                  >
                                    Freeze
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === "analysis" && (
          <div>
            {!session ? (
              <div
                style={{
                  textAlign: "center",
                  padding: "60px 20px",
                  color: "#888",
                }}
              >
                <div style={{ fontSize: "48px", marginBottom: "16px" }}>🧠</div>
                <h3 style={{ color: "#fff", marginBottom: "8px" }}>
                  No Active Session
                </h3>
                <p>Declare a game to begin autonomous analysis.</p>
              </div>
            ) : (
              <div style={{ display: "grid", gap: "16px" }}>
                <div
                  style={{
                    display: "flex",
                    gap: "12px",
                    flexWrap: "wrap",
                    alignItems: "center",
                  }}
                >
                  <select
                    value={trainerMode}
                    onChange={(e) => updateTrainerMode(e.target.value)}
                    style={{
                      padding: "10px 12px",
                      background: "#0f0f23",
                      border: "1px solid #2d2d44",
                      borderRadius: "8px",
                      color: "#fff",
                    }}
                  >
                    <option value="training">🧪 Training Mode</option>
                    <option value="performance">⚔️ Performance Mode</option>
                    <option value="meta">🧠 Meta Mode</option>
                  </select>
                  <label
                    style={{
                      display: "flex",
                      gap: "8px",
                      alignItems: "center",
                      color: "#cbd5e1",
                      fontSize: "12px",
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={autoRun}
                      onChange={(e) => setAutoRun(e.target.checked)}
                    />
                    Auto-run analysis
                  </label>
                  <button
                    onClick={runAnalysis}
                    style={{
                      padding: "10px 16px",
                      background: "#667eea",
                      border: "none",
                      borderRadius: "8px",
                      color: "#fff",
                      cursor: "pointer",
                    }}
                  >
                    Run Analysis
                  </button>
                </div>

                <div
                  style={{
                    padding: "18px",
                    background: "#1a1a2e",
                    border: "1px solid #2d2d44",
                    borderRadius: "12px",
                  }}
                >
                  <h3 style={{ color: "#fff", marginBottom: "8px" }}>
                    📊 Dashboard Output
                  </h3>
                  <div style={{ color: "#94a3b8", fontSize: "12px" }}>
                    {analysis?.analysis_summary ||
                      "Awaiting analysis tick. Autonomy will infer playstyle and intent as telemetry becomes available."}
                  </div>
                  <div
                    style={{
                      marginTop: "12px",
                      display: "grid",
                      gridTemplateColumns:
                        "repeat(auto-fit, minmax(180px, 1fr))",
                      gap: "10px",
                      fontSize: "12px",
                      color: "#e2e8f0",
                    }}
                  >
                    <div>Risk: {analysis?.risk_level || "Low"}</div>
                    <div>
                      Expected improvement:{" "}
                      {analysis?.expected_improvement_pct || 0}%
                    </div>
                    <div>Mode: {analysis?.trainer_mode || trainerMode}</div>
                  </div>
                </div>

                {analysis?.recommendations?.length > 0 && (
                  <div style={{ display: "grid", gap: "12px" }}>
                    {analysis.recommendations.map((rec, idx) => (
                      <div
                        key={`${rec.title}-${idx}`}
                        style={{
                          padding: "16px",
                          background: "rgba(102, 126, 234, 0.08)",
                          border: "1px solid #2d2d44",
                          borderRadius: "12px",
                        }}
                      >
                        <div style={{ color: "#fff", fontWeight: 600 }}>
                          {rec.title}
                        </div>
                        <div style={{ color: "#cbd5e1", fontSize: "12px" }}>
                          {rec.why}
                        </div>
                        <div
                          style={{
                            marginTop: "8px",
                            display: "grid",
                            gridTemplateColumns:
                              "repeat(auto-fit, minmax(160px, 1fr))",
                            gap: "8px",
                            fontSize: "12px",
                            color: "#94a3b8",
                          }}
                        >
                          <div>Risk: {rec.risk}</div>
                          <div>Expected: {rec.expected_improvement_pct}%</div>
                        </div>
                        {rec.comparison && (
                          <div
                            style={{
                              marginTop: "8px",
                              fontSize: "12px",
                              color: "#e2e8f0",
                            }}
                          >
                            {rec.comparison}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div
        className="resize-handle"
        onMouseDown={handleResizeStart}
        style={{
          position: "absolute",
          right: 4,
          bottom: 4,
          width: 16,
          height: 16,
          cursor: "nwse-resize",
          background: "rgba(148, 163, 184, 0.3)",
          borderRadius: 4,
        }}
        title="Resize"
      />
    </div>
  );
};

export default GameTrainerConsole;
