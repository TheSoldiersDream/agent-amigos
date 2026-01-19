import React, { useState, useEffect, useRef } from "react";
import axios from "axios";

const MacroConsole = ({ isOpen, onClose, apiUrl }) => {
  const [activeTab, setActiveTab] = useState("autonomous"); // autonomous, macros, patterns, history
  const [macros, setMacros] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [history, setHistory] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [executingMacro, setExecutingMacro] = useState(null);
  const [isRecording, setIsRecording] = useState(false);

  // Autonomous Agent State
  const [autonomousGoal, setAutonomousGoal] = useState("");
  const [autonomousDomain, setAutonomousDomain] = useState("");
  const [permissionScope, setPermissionScope] = useState("read");
  const [visualPerception, setVisualPerception] = useState(true);
  const [isExecutingAutonomous, setIsExecutingAutonomous] = useState(false);
  const [autonomousLogs, setAutonomousLogs] = useState([]);
  const [executionStatus, setExecutionStatus] = useState(null);

  // Editor State
  const [editingMacro, setEditingMacro] = useState(null); // If set, shows editor
  const [editForm, setEditForm] = useState({
    name: "",
    description: "",
    steps: [],
    settings: { speed: 1.0, loops: 1 },
  });

  // Draggable state
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-macro-console-pos");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      fetchData();
    }
  }, [isOpen, activeTab]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y,
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, dragOffset]);

  const handleMouseDown = (e) => {
    // Only allow dragging from the header area (not buttons/inputs)
    if (
      e.target.tagName === "BUTTON" ||
      e.target.tagName === "INPUT" ||
      e.target.tagName === "TEXTAREA"
    )
      return;

    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setDragOffset({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      });
      setPosition({
        x: rect.left,
        y: rect.top,
      });
      setIsDragging(true);
    }
  };

  const getBaseUrl = () => {
    const base = apiUrl || "http://127.0.0.1:65252";
    return base.endsWith("/") ? base.slice(0, -1) : base;
  };

  useEffect(() => {
    if (!position) return;
    try {
      localStorage.setItem(
        "amigos-macro-console-pos",
        JSON.stringify(position),
      );
    } catch {
      // ignore storage errors
    }
  }, [position]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const baseUrl = getBaseUrl();

      if (activeTab === "macros") {
        const res = await axios.get(`${baseUrl}/macros`);
        setMacros(res.data.macros || []);
      } else if (activeTab === "patterns") {
        const res = await axios.get(`${baseUrl}/macros/patterns`);
        setPatterns(res.data.patterns || []);
      } else if (activeTab === "history") {
        const res = await axios.get(`${baseUrl}/macros/history`);
        setHistory(res.data.history || []);
      }
    } catch (err) {
      console.error("Failed to fetch macro data", err);
    } finally {
      setIsLoading(false);
    }
  };

  const executeMacro = async (macroId) => {
    setExecutingMacro(macroId);
    try {
      const baseUrl = getBaseUrl();
      // Get current settings from the macro object if available, or defaults
      const macro = macros.find((m) => m.id === macroId);
      const settings = macro?.settings || { speed: 1.0, loops: 1 };

      await axios.post(`${baseUrl}/macros/${macroId}/execute`, {
        speed: settings.speed,
        loops: settings.loops,
      });
      alert("Macro executed successfully!");
    } catch (err) {
      alert("Failed to execute macro: " + err.message);
    } finally {
      setExecutingMacro(null);
    }
  };

  const createMacro = async (pattern, name) => {
    try {
      const baseUrl = getBaseUrl();
      await axios.post(`${baseUrl}/macros`, {
        name: name,
        description: "Created from pattern",
        pattern_sequence: pattern.sequence,
      });
      alert("Macro created!");
      setActiveTab("macros");
      fetchData();
    } catch (err) {
      alert("Failed to create macro: " + err.message);
    }
  };

  const toggleRecording = async () => {
    try {
      const baseUrl = getBaseUrl();
      if (isRecording) {
        const name = prompt("Enter a name for this macro:");
        if (!name) return;

        const res = await axios.post(`${baseUrl}/macros/record/stop`, {
          name: name,
          description: "Recorded macro",
        });

        if (res.data.status === "success") {
          alert("Macro recorded successfully!");
          setIsRecording(false);
          setActiveTab("macros");
          fetchData();
        } else {
          alert("Error: " + res.data.message);
          setIsRecording(false);
        }
      } else {
        await axios.post(`${baseUrl}/macros/record/start`);
        setIsRecording(true);
        alert(
          "Recording started! Perform actions and then click Stop Recording.",
        );
        onClose(); // Close console so user can perform actions
      }
    } catch (err) {
      console.error("Recording error", err);
      alert("Recording failed: " + err.message);
      setIsRecording(false);
    }
  };

  // Autonomous Agent Execution
  const executeAutonomous = async () => {
    if (!autonomousGoal.trim()) {
      alert("Please enter a goal for the autonomous agent");
      return;
    }

    setIsExecutingAutonomous(true);
    setAutonomousLogs([]);
    setExecutionStatus({
      status: "running",
      message: "Initializing autonomous agent...",
    });

    try {
      const baseUrl = getBaseUrl();
      const response = await axios.post(`${baseUrl}/macro/autonomous`, {
        goal: autonomousGoal,
        domain: autonomousDomain || null,
        permission_scope: permissionScope,
        visual_perception: visualPerception,
        confirmation_required: permissionScope !== "read",
      });

      const result = response.data;

      if (result.success) {
        setExecutionStatus({
          status: "success",
          message: "Task completed successfully!",
        });
        setAutonomousLogs(result.logs || []);

        // Show summary
        if (result.summary) {
          alert(`✓ Task Complete!\n\n${result.summary}`);
        }
      } else {
        setExecutionStatus({
          status: "error",
          message: result.error || "Execution failed",
        });
        setAutonomousLogs(result.logs || []);
      }
    } catch (err) {
      console.error("Autonomous execution error:", err);
      setExecutionStatus({
        status: "error",
        message: err.response?.data?.error || err.message || "Unknown error",
      });

      if (err.response?.data?.logs) {
        setAutonomousLogs(err.response.data.logs);
      }
    } finally {
      setIsExecutingAutonomous(false);
    }
  };

  // --- Editor Functions ---

  const startEditing = (macro) => {
    setEditingMacro(macro);
    setEditForm({
      name: macro.name,
      description: macro.description,
      steps: [...macro.steps],
      settings: macro.settings || { speed: 1.0, loops: 1 },
    });
  };

  const saveMacro = async () => {
    try {
      const baseUrl = getBaseUrl();
      await axios.put(`${baseUrl}/macros/${editingMacro.id}`, editForm);
      setEditingMacro(null);
      fetchData();
    } catch (err) {
      alert("Failed to save macro: " + err.message);
    }
  };

  const deleteMacro = async () => {
    if (!confirm("Are you sure you want to delete this macro?")) return;
    try {
      const baseUrl = getBaseUrl();
      await axios.delete(`${baseUrl}/macros/${editingMacro.id}`);
      setEditingMacro(null);
      fetchData();
    } catch (err) {
      alert("Failed to delete macro: " + err.message);
    }
  };

  const moveStep = (index, direction) => {
    const newSteps = [...editForm.steps];
    if (direction === -1 && index > 0) {
      [newSteps[index], newSteps[index - 1]] = [
        newSteps[index - 1],
        newSteps[index],
      ];
    } else if (direction === 1 && index < newSteps.length - 1) {
      [newSteps[index], newSteps[index + 1]] = [
        newSteps[index + 1],
        newSteps[index],
      ];
    }
    setEditForm({ ...editForm, steps: newSteps });
  };

  const deleteStep = (index) => {
    const newSteps = editForm.steps.filter((_, i) => i !== index);
    setEditForm({ ...editForm, steps: newSteps });
  };

  if (!isOpen) return null;

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        top: position ? position.y : "15%",
        left: position ? position.x : "15%",
        width: "70%",
        height: "70%",
        minWidth: "600px",
        minHeight: "400px",
        backgroundColor: "#1e1e2e",
        color: "#fff",
        zIndex: 2000,
        borderRadius: "10px",
        boxShadow: "0 0 30px rgba(0,0,0,0.7)",
        display: "flex",
        flexDirection: "column",
        padding: "20px",
        resize: "both",
        overflow: "hidden", // Handle overflow in inner containers
        border: "1px solid #444",
      }}
    >
      {/* Header */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "20px",
          cursor: "move",
          userSelect: "none",
          borderBottom: "1px solid #333",
          paddingBottom: "10px",
        }}
      >
        <h2 style={{ margin: 0 }}>
          {editingMacro
            ? `Editing: ${editingMacro.name}`
            : "🤖 Behavioral Macro Studio"}
        </h2>
        <div style={{ display: "flex", gap: "10px" }}>
          {!editingMacro && (
            <button
              onClick={toggleRecording}
              style={{
                padding: "5px 15px",
                backgroundColor: isRecording ? "#ff4444" : "#44ff44",
                color: "#000",
                border: "none",
                borderRadius: "5px",
                cursor: "pointer",
                fontWeight: "bold",
              }}
            >
              {isRecording ? "⏹ Stop Recording" : "⏺ Record New"}
            </button>
          )}
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              color: "#fff",
              fontSize: "1.5em",
              cursor: "pointer",
            }}
          >
            ×
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Editor View */}
        {editingMacro ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              height: "100%",
              gap: "15px",
            }}
          >
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "15px",
              }}
            >
              <div>
                <label
                  style={{
                    display: "block",
                    color: "#aaa",
                    marginBottom: "5px",
                  }}
                >
                  Name
                </label>
                <input
                  value={editForm.name}
                  onChange={(e) =>
                    setEditForm({ ...editForm, name: e.target.value })
                  }
                  style={{
                    width: "100%",
                    padding: "8px",
                    background: "#333",
                    border: "1px solid #555",
                    color: "#fff",
                    borderRadius: "4px",
                  }}
                />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    color: "#aaa",
                    marginBottom: "5px",
                  }}
                >
                  Description
                </label>
                <input
                  value={editForm.description}
                  onChange={(e) =>
                    setEditForm({ ...editForm, description: e.target.value })
                  }
                  style={{
                    width: "100%",
                    padding: "8px",
                    background: "#333",
                    border: "1px solid #555",
                    color: "#fff",
                    borderRadius: "4px",
                  }}
                />
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "15px",
                background: "#252535",
                padding: "10px",
                borderRadius: "5px",
              }}
            >
              <div>
                <label
                  style={{
                    display: "block",
                    color: "#aaa",
                    marginBottom: "5px",
                  }}
                >
                  Playback Speed (x)
                </label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="10"
                  value={editForm.settings.speed}
                  onChange={(e) =>
                    setEditForm({
                      ...editForm,
                      settings: {
                        ...editForm.settings,
                        speed: parseFloat(e.target.value),
                      },
                    })
                  }
                  style={{
                    width: "100%",
                    padding: "8px",
                    background: "#333",
                    border: "1px solid #555",
                    color: "#fff",
                    borderRadius: "4px",
                  }}
                />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    color: "#aaa",
                    marginBottom: "5px",
                  }}
                >
                  Loops
                </label>
                <input
                  type="number"
                  min="1"
                  value={editForm.settings.loops}
                  onChange={(e) =>
                    setEditForm({
                      ...editForm,
                      settings: {
                        ...editForm.settings,
                        loops: parseInt(e.target.value),
                      },
                    })
                  }
                  style={{
                    width: "100%",
                    padding: "8px",
                    background: "#333",
                    border: "1px solid #555",
                    color: "#fff",
                    borderRadius: "4px",
                  }}
                />
              </div>
            </div>

            <div
              style={{
                flex: 1,
                overflowY: "auto",
                background: "#1a1a2e",
                borderRadius: "5px",
                padding: "10px",
                border: "1px solid #333",
              }}
            >
              <h4
                style={{
                  marginTop: 0,
                  color: "#888",
                  borderBottom: "1px solid #333",
                  paddingBottom: "5px",
                }}
              >
                Action Timeline ({editForm.steps.length} steps)
              </h4>
              {editForm.steps.map((step, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "8px",
                    borderBottom: "1px solid #2a2a3a",
                    background: idx % 2 === 0 ? "#222233" : "transparent",
                  }}
                >
                  <span style={{ color: "#666", width: "30px" }}>
                    {idx + 1}.
                  </span>
                  <span
                    style={{
                      color: step.tool === "click" ? "#60a5fa" : "#f472b6",
                      fontWeight: "bold",
                      width: "80px",
                    }}
                  >
                    {step.tool}
                  </span>
                  <span
                    style={{
                      flex: 1,
                      color: "#ccc",
                      fontFamily: "monospace",
                      fontSize: "0.9em",
                    }}
                  >
                    {JSON.stringify(step.params)}
                  </span>
                  <div style={{ display: "flex", gap: "5px" }}>
                    <button
                      onClick={() => moveStep(idx, -1)}
                      disabled={idx === 0}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#aaa",
                        cursor: "pointer",
                      }}
                    >
                      ▲
                    </button>
                    <button
                      onClick={() => moveStep(idx, 1)}
                      disabled={idx === editForm.steps.length - 1}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#aaa",
                        cursor: "pointer",
                      }}
                    >
                      ▼
                    </button>
                    <button
                      onClick={() => deleteStep(idx)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#ef4444",
                        cursor: "pointer",
                      }}
                    >
                      🗑
                    </button>
                  </div>
                </div>
              ))}
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                paddingTop: "10px",
                borderTop: "1px solid #333",
              }}
            >
              <button
                onClick={deleteMacro}
                style={{
                  padding: "8px 16px",
                  background: "#ef4444",
                  border: "none",
                  borderRadius: "5px",
                  color: "#fff",
                  cursor: "pointer",
                }}
              >
                Delete Macro
              </button>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  onClick={() => setEditingMacro(null)}
                  style={{
                    padding: "8px 16px",
                    background: "#555",
                    border: "none",
                    borderRadius: "5px",
                    color: "#fff",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={saveMacro}
                  style={{
                    padding: "8px 16px",
                    background: "#3b82f6",
                    border: "none",
                    borderRadius: "5px",
                    color: "#fff",
                    cursor: "pointer",
                    fontWeight: "bold",
                  }}
                >
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* List View */
          <>
            <div
              style={{
                display: "flex",
                gap: "10px",
                marginBottom: "20px",
                flexWrap: "wrap",
              }}
            >
              <button
                onClick={() => setActiveTab("autonomous")}
                style={{
                  padding: "10px 15px",
                  background: activeTab === "autonomous" ? "#8b5cf6" : "#333",
                  border: "none",
                  color: "#fff",
                  borderRadius: "5px",
                  cursor: "pointer",
                  fontWeight: activeTab === "autonomous" ? "bold" : "normal",
                }}
              >
                🤖 Autonomous AI
              </button>
              <button
                onClick={() => setActiveTab("macros")}
                style={{
                  padding: "10px 15px",
                  background: activeTab === "macros" ? "#6366f1" : "#333",
                  border: "none",
                  color: "#fff",
                  borderRadius: "5px",
                  cursor: "pointer",
                }}
              >
                Saved Macros
              </button>
              <button
                onClick={() => setActiveTab("patterns")}
                style={{
                  padding: "10px 15px",
                  background: activeTab === "patterns" ? "#6366f1" : "#333",
                  border: "none",
                  color: "#fff",
                  borderRadius: "5px",
                  cursor: "pointer",
                }}
              >
                Detected Patterns
              </button>
              <button
                onClick={() => setActiveTab("history")}
                style={{
                  padding: "10px 15px",
                  background: activeTab === "history" ? "#6366f1" : "#333",
                  border: "none",
                  color: "#fff",
                  borderRadius: "5px",
                  cursor: "pointer",
                }}
              >
                Action History
              </button>
            </div>

            <div style={{ flex: 1, overflowY: "auto" }}>
              {isLoading ? (
                <div>Loading...</div>
              ) : (
                <>
                  {activeTab === "autonomous" && (
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        gap: "20px",
                        height: "100%",
                      }}
                    >
                      {/* Autonomous Agent Control Panel */}
                      <div
                        style={{
                          background:
                            "linear-gradient(135deg, #1e1e2e 0%, #2d1b4e 100%)",
                          padding: "20px",
                          borderRadius: "10px",
                          border: "1px solid #8b5cf6",
                        }}
                      >
                        <h3 style={{ margin: "0 0 15px 0", color: "#a78bfa" }}>
                          🤖 Natural Language Task Execution
                        </h3>
                        <p
                          style={{
                            color: "#999",
                            fontSize: "0.9em",
                            marginBottom: "15px",
                          }}
                        >
                          Describe what you want the AI to do in plain English.
                          It will understand the page, plan actions, and execute
                          them autonomously with self-healing.
                        </p>

                        {/* Goal Input */}
                        <div style={{ marginBottom: "15px" }}>
                          <label
                            style={{
                              display: "block",
                              color: "#aaa",
                              marginBottom: "5px",
                              fontWeight: "bold",
                            }}
                          >
                            Task Goal
                          </label>
                          <textarea
                            value={autonomousGoal}
                            onChange={(e) => setAutonomousGoal(e.target.value)}
                            placeholder="Example: Fill out the contact form with my name and email, then submit it"
                            disabled={isExecutingAutonomous}
                            style={{
                              width: "100%",
                              padding: "12px",
                              background: "#1a1a2e",
                              border: "1px solid #555",
                              color: "#fff",
                              borderRadius: "8px",
                              minHeight: "80px",
                              fontFamily: "inherit",
                              resize: "vertical",
                            }}
                          />
                        </div>

                        {/* Settings Grid */}
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: "1fr 1fr",
                            gap: "15px",
                            marginBottom: "15px",
                          }}
                        >
                          {/* Domain */}
                          <div>
                            <label
                              style={{
                                display: "block",
                                color: "#aaa",
                                marginBottom: "5px",
                              }}
                            >
                              Target Domain (optional)
                            </label>
                            <input
                              value={autonomousDomain}
                              onChange={(e) =>
                                setAutonomousDomain(e.target.value)
                              }
                              placeholder="example.com"
                              disabled={isExecutingAutonomous}
                              style={{
                                width: "100%",
                                padding: "10px",
                                background: "#1a1a2e",
                                border: "1px solid #555",
                                color: "#fff",
                                borderRadius: "6px",
                              }}
                            />
                          </div>

                          {/* Permission Scope */}
                          <div>
                            <label
                              style={{
                                display: "block",
                                color: "#aaa",
                                marginBottom: "5px",
                              }}
                            >
                              Permission Scope
                            </label>
                            <select
                              value={permissionScope}
                              onChange={(e) =>
                                setPermissionScope(e.target.value)
                              }
                              disabled={isExecutingAutonomous}
                              style={{
                                width: "100%",
                                padding: "10px",
                                background: "#1a1a2e",
                                border: "1px solid #555",
                                color: "#fff",
                                borderRadius: "6px",
                                cursor: "pointer",
                              }}
                            >
                              <option value="read">Read Only (Safe)</option>
                              <option value="write">Write (Fill forms)</option>
                              <option value="submit">
                                Submit (Click buttons)
                              </option>
                              <option value="payment">
                                Payment (High risk)
                              </option>
                            </select>
                          </div>
                        </div>

                        {/* Visual Perception Toggle */}
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "10px",
                            padding: "12px",
                            background: "#252535",
                            borderRadius: "6px",
                            marginBottom: "15px",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={visualPerception}
                            onChange={(e) =>
                              setVisualPerception(e.target.checked)
                            }
                            disabled={isExecutingAutonomous}
                            style={{
                              width: "20px",
                              height: "20px",
                              cursor: "pointer",
                            }}
                          />
                          <div>
                            <label
                              style={{
                                color: "#fff",
                                fontWeight: "bold",
                                display: "block",
                              }}
                            >
                              Enable Visual Perception (OCR)
                            </label>
                            <span style={{ color: "#999", fontSize: "0.85em" }}>
                              Uses screenshots + OCR to understand page layout
                              and text
                            </span>
                          </div>
                        </div>

                        {/* Execute Button */}
                        <button
                          onClick={executeAutonomous}
                          disabled={
                            isExecutingAutonomous || !autonomousGoal.trim()
                          }
                          style={{
                            width: "100%",
                            padding: "15px",
                            background: isExecutingAutonomous
                              ? "linear-gradient(135deg, #6b7280, #4b5563)"
                              : "linear-gradient(135deg, #8b5cf6, #6366f1)",
                            border: "none",
                            borderRadius: "8px",
                            color: "#fff",
                            cursor: isExecutingAutonomous
                              ? "not-allowed"
                              : "pointer",
                            fontWeight: "bold",
                            fontSize: "1.1em",
                            boxShadow: isExecutingAutonomous
                              ? "none"
                              : "0 4px 15px rgba(139, 92, 246, 0.4)",
                          }}
                        >
                          {isExecutingAutonomous
                            ? "🔄 Executing Task..."
                            : "▶ Execute Autonomous Task"}
                        </button>
                      </div>

                      {/* Execution Status */}
                      {executionStatus && (
                        <div
                          style={{
                            padding: "15px",
                            borderRadius: "8px",
                            background:
                              executionStatus.status === "success"
                                ? "rgba(16, 185, 129, 0.1)"
                                : executionStatus.status === "error"
                                  ? "rgba(239, 68, 68, 0.1)"
                                  : "rgba(99, 102, 241, 0.1)",
                            border: `1px solid ${
                              executionStatus.status === "success"
                                ? "#10b981"
                                : executionStatus.status === "error"
                                  ? "#ef4444"
                                  : "#6366f1"
                            }`,
                          }}
                        >
                          <div
                            style={{
                              color:
                                executionStatus.status === "success"
                                  ? "#10b981"
                                  : executionStatus.status === "error"
                                    ? "#ef4444"
                                    : "#6366f1",
                              fontWeight: "bold",
                              marginBottom: "5px",
                            }}
                          >
                            {executionStatus.status === "success" &&
                              "✓ Success"}
                            {executionStatus.status === "error" && "✗ Error"}
                            {executionStatus.status === "running" &&
                              "⚡ Running"}
                          </div>
                          <div style={{ color: "#ccc" }}>
                            {executionStatus.message}
                          </div>
                        </div>
                      )}

                      {/* Execution Logs */}
                      {autonomousLogs.length > 0 && (
                        <div
                          style={{
                            flex: 1,
                            background: "#1a1a2e",
                            borderRadius: "8px",
                            padding: "15px",
                            overflowY: "auto",
                            border: "1px solid #333",
                          }}
                        >
                          <h4
                            style={{
                              margin: "0 0 10px 0",
                              color: "#888",
                              fontSize: "0.9em",
                            }}
                          >
                            Execution Log ({autonomousLogs.length} steps)
                          </h4>
                          {autonomousLogs.map((log, idx) => (
                            <div
                              key={idx}
                              style={{
                                padding: "10px",
                                marginBottom: "8px",
                                background: "#252535",
                                borderRadius: "6px",
                                borderLeft: `3px solid ${
                                  log.level === "error"
                                    ? "#ef4444"
                                    : log.level === "warning"
                                      ? "#f59e0b"
                                      : log.level === "success"
                                        ? "#10b981"
                                        : "#6366f1"
                                }`,
                              }}
                            >
                              <div
                                style={{
                                  display: "flex",
                                  justifyContent: "space-between",
                                  marginBottom: "5px",
                                }}
                              >
                                <span
                                  style={{
                                    color:
                                      log.level === "error"
                                        ? "#ef4444"
                                        : log.level === "warning"
                                          ? "#f59e0b"
                                          : log.level === "success"
                                            ? "#10b981"
                                            : "#6366f1",
                                    fontWeight: "bold",
                                    fontSize: "0.85em",
                                  }}
                                >
                                  {log.step || `Step ${idx + 1}`}
                                </span>
                                <span
                                  style={{ color: "#666", fontSize: "0.75em" }}
                                >
                                  {log.timestamp ||
                                    new Date().toLocaleTimeString()}
                                </span>
                              </div>
                              <div style={{ color: "#ccc", fontSize: "0.9em" }}>
                                {log.message}
                              </div>
                              {log.details && (
                                <div
                                  style={{
                                    marginTop: "5px",
                                    padding: "8px",
                                    background: "#1a1a2e",
                                    borderRadius: "4px",
                                    fontFamily: "monospace",
                                    fontSize: "0.8em",
                                    color: "#999",
                                  }}
                                >
                                  {JSON.stringify(log.details, null, 2)}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Help Text */}
                      {!executionStatus && autonomousLogs.length === 0 && (
                        <div
                          style={{
                            padding: "20px",
                            background: "#1a1a2e",
                            borderRadius: "8px",
                            border: "1px solid #333",
                          }}
                        >
                          <h4 style={{ color: "#a78bfa", marginTop: 0 }}>
                            💡 How It Works
                          </h4>
                          <ul style={{ color: "#999", lineHeight: "1.8" }}>
                            <li>
                              <strong>Planner:</strong> Converts your goal into
                              actionable steps
                            </li>
                            <li>
                              <strong>Perception:</strong> Uses OCR + DOM
                              analysis to understand the page
                            </li>
                            <li>
                              <strong>Executor:</strong> Performs actions with
                              human-like timing
                            </li>
                            <li>
                              <strong>Recovery:</strong> Self-heals when actions
                              fail (6 strategies)
                            </li>
                            <li>
                              <strong>Memory:</strong> Learns from successful
                              executions
                            </li>
                          </ul>
                          <div
                            style={{
                              marginTop: "15px",
                              padding: "10px",
                              background: "#252535",
                              borderRadius: "6px",
                            }}
                          >
                            <strong style={{ color: "#fbbf24" }}>
                              Example Tasks:
                            </strong>
                            <ul style={{ marginTop: "8px", color: "#ccc" }}>
                              <li>Search for "Python tutorials" on Google</li>
                              <li>Fill out contact form with my details</li>
                              <li>
                                Add item to shopping cart and proceed to
                                checkout
                              </li>
                              <li>Login to my account with credentials</li>
                            </ul>
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === "macros" && (
                    <div style={{ display: "grid", gap: "10px" }}>
                      {macros.length === 0 && <p>No macros saved yet.</p>}
                      {macros.map((macro) => (
                        <div
                          key={macro.id}
                          style={{
                            background: "#2d2d3d",
                            padding: "15px",
                            borderRadius: "8px",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                          }}
                        >
                          <div>
                            <h3>{macro.name}</h3>
                            <p style={{ color: "#aaa", fontSize: "0.9em" }}>
                              {macro.description}
                            </p>
                            <div
                              style={{
                                marginTop: "5px",
                                fontSize: "0.8em",
                                color: "#888",
                              }}
                            >
                              {macro.steps.length} steps •{" "}
                              {macro.settings?.speed || 1}x speed
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: "10px" }}>
                            <button
                              onClick={() => startEditing(macro)}
                              style={{
                                padding: "8px 16px",
                                background: "#4b5563",
                                border: "none",
                                borderRadius: "5px",
                                color: "#fff",
                                cursor: "pointer",
                              }}
                            >
                              ✎ Edit
                            </button>
                            <button
                              onClick={() => executeMacro(macro.id)}
                              disabled={executingMacro === macro.id}
                              style={{
                                padding: "8px 16px",
                                background: "#10b981",
                                border: "none",
                                borderRadius: "5px",
                                color: "#fff",
                                cursor: "pointer",
                              }}
                            >
                              {executingMacro === macro.id
                                ? "Running..."
                                : "▶ Run"}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {activeTab === "patterns" && (
                    <div style={{ display: "grid", gap: "10px" }}>
                      {patterns.length === 0 && (
                        <p>
                          No patterns detected yet. Use Agent Amigos to generate
                          history!
                        </p>
                      )}
                      {patterns.map((pattern, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: "#2d2d3d",
                            padding: "15px",
                            borderRadius: "8px",
                          }}
                        >
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              alignItems: "center",
                            }}
                          >
                            <div>
                              <h3 style={{ color: "#fbbf24" }}>
                                Pattern Found (Confidence:{" "}
                                {(pattern.confidence * 100).toFixed(0)}%)
                              </h3>
                              <p style={{ color: "#aaa" }}>
                                Occurred {pattern.count} times
                              </p>
                            </div>
                            <button
                              onClick={() => {
                                const name = prompt("Name this macro:");
                                if (name) createMacro(pattern, name);
                              }}
                              style={{
                                padding: "8px 16px",
                                background: "#6366f1",
                                border: "none",
                                borderRadius: "5px",
                                color: "#fff",
                                cursor: "pointer",
                              }}
                            >
                              + Save as Macro
                            </button>
                          </div>
                          <div
                            style={{
                              marginTop: "10px",
                              background: "#1a1a2e",
                              padding: "10px",
                              borderRadius: "5px",
                              fontFamily: "monospace",
                            }}
                          >
                            {pattern.sequence.join(" → ")}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {activeTab === "history" && (
                    <div style={{ fontFamily: "monospace" }}>
                      {history.map((entry, idx) => (
                        <div
                          key={idx}
                          style={{
                            padding: "8px",
                            borderBottom: "1px solid #333",
                          }}
                        >
                          <span style={{ color: "#888" }}>
                            {new Date(entry.timestamp).toLocaleTimeString()}
                          </span>
                          <span style={{ color: "#10b981", margin: "0 10px" }}>
                            {entry.tool}
                          </span>
                          <span style={{ color: "#aaa" }}>
                            {JSON.stringify(entry.params)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default MacroConsole;
