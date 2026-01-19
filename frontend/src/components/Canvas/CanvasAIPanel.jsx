/**
 * 🧠 Canvas AI Assist Panel
 *
 * UI controls for AI-assisted Canvas features:
 * - Discuss: Explain ideas
 * - Draw: Add sketches and visuals
 * - Plan: Create structured plans
 * - Design: Generate diagrams
 * - Brainstorm: Mind mapping
 * - Annotate: Add notes
 * - Ask: Visual questions
 *
 * Created by Darrell Buttigieg (@darrellbuttigieg) #thesoldiersdream
 */

import React, { useState, useEffect } from "react";
import axios from "axios";
import { startListening, isSpeechRecognitionSupported } from "../../utils/stt";

const CanvasAIPanel = ({
  onCommandIssued,
  onRealtimeEvent,
  liveText,
  liveImage,
  getCanvasSnapshot,
  apiUrl,
  layers,
}) => {
  const [aiEnabled, setAiEnabled] = useState(true);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedMode, setSelectedMode] = useState(null);
  const [inputText, setInputText] = useState("");
  const [position, setPosition] = useState({ x: 100, y: 100 });
  const [isListening, setIsListening] = useState(false);
  const [recognitionInstance, setRecognitionInstance] = useState(null);

  const handleMicClick = () => {
    if (isListening && recognitionInstance) {
      recognitionInstance.stop();
      setIsListening(false);
      setRecognitionInstance(null);
    } else {
      if (!isSpeechRecognitionSupported()) {
        alert("Speech recognition not supported in this browser.");
        return;
      }
      const rec = startListening({
        onStart: () => setIsListening(true),
        onEnd: () => {
          setIsListening(false);
          setRecognitionInstance(null);
        },
        onError: (err) => {
          console.error("STT Error:", err);
          setIsListening(false);
          setRecognitionInstance(null);
        },
        onResult: (text) => setInputText(text),
      });
      setRecognitionInstance(rec);
    }
  };

  const API_BASE = apiUrl
    ? `${apiUrl}/canvas/ai`
    : "http://127.0.0.1:65252/canvas/ai";

  // Load AI status on mount
  useEffect(() => {
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE}/status`);
      if (response.data.success) {
        setStatus(response.data);
        setAiEnabled(response.data.enabled);
      }
    } catch (error) {
      console.error("Failed to load AI status:", error);
    }
  };

  const toggleAI = async () => {
    try {
      const endpoint = aiEnabled ? "disable" : "enable";
      const response = await axios.post(`${API_BASE}/${endpoint}`);
      if (response.data.success) {
        setAiEnabled(response.data.enabled);
      }
    } catch (error) {
      console.error("Failed to toggle AI:", error);
    }
  };

  const executeAICommand = async (mode, payload) => {
    if (!aiEnabled) {
      alert("AI Assist is disabled. Enable it first.");
      return;
    }

    setLoading(true);

    // Inject context (objects and snapshot)
    if (layers) {
      const allObjects = layers.flatMap((l) => l.objects || []);
      payload.context_objects = allObjects;
    }

    if (
      getCanvasSnapshot &&
      [
        "draw",
        "discuss",
        "ask",
        "plan",
        "design",
        "brainstorm",
        "annotate",
      ].includes(mode)
    ) {
      try {
        const snapshot = getCanvasSnapshot();
        if (snapshot) {
          payload.snapshot = snapshot;
        }
      } catch (e) {
        console.warn("Failed to get canvas snapshot:", e);
      }
    }

    try {
      onRealtimeEvent?.({
        type: "start",
        mode,
        text: `Working on ${mode}...`,
        payload,
      });
    } catch {
      // ignore
    }
    try {
      const response = await axios.post(`${API_BASE}/${mode}`, payload);
      if (response.data.success) {
        // Extract full command objects from response
        const commands = response.data.commands || [];
        const count = Array.isArray(commands) ? commands.length : 0;

        let summaryText = "";
        if (response.data.conversational_response) {
          summaryText = response.data.conversational_response;
        } else {
          const parts = [];
          parts.push(`Done: ${mode}`);
          parts.push(`I produced ${count} command${count === 1 ? "" : "s"}.`);
          if (response.data.central_idea)
            parts.push(`Central idea: ${response.data.central_idea}.`);
          if (response.data.goal) parts.push(`Goal: ${response.data.goal}.`);
          if (response.data.topic) parts.push(`Topic: ${response.data.topic}.`);
          summaryText = parts.join(" ");
        }

        console.log(
          `✨ ${mode} returned ${commands.length} commands:`,
          commands
        );
        onCommandIssued?.(commands); // Pass the full commands array to CanvasPanel

        try {
          onRealtimeEvent?.({
            type: "success",
            mode,
            text: summaryText,
            commandsCount: count,
            data: response.data,
          });
        } catch {
          // ignore
        }

        setInputText("");
        setSelectedMode(null);
      }
    } catch (error) {
      console.error(`AI ${mode} error:`, error);
      const msg =
        error?.response?.data?.detail ||
        error?.message ||
        `Failed to execute ${mode}`;
      try {
        onRealtimeEvent?.({ type: "error", mode, text: `Error: ${msg}` });
      } catch {
        // ignore
      }
      alert(`Failed to execute ${mode}`);
    } finally {
      setLoading(false);
    }
  };

  const handleArchitect = () => {
    if (!inputText.trim()) {
      alert("Describe the house or floor plan you want to design");
      return;
    }
    executeAICommand("design", {
      design_type: "floor plan: " + inputText,
      position,
    });
  };

  const handleDiscuss = () => {
    if (!inputText.trim()) {
      alert("Enter a topic to discuss");
      return;
    }
    executeAICommand("discuss", {
      topic: inputText,
      position,
    });
  };

  const handleDraw = () => {
    if (!inputText.trim()) {
      alert("Describe what to draw");
      return;
    }
    executeAICommand("draw", {
      description: inputText,
      position,
    });
  };

  const handlePlan = () => {
    if (!inputText.trim()) {
      alert("Enter a planning goal");
      return;
    }
    const steps = inputText.includes(",")
      ? inputText.split(",").map((s) => s.trim())
      : null;
    executeAICommand("plan", {
      goal: inputText,
      steps,
      position,
    });
  };

  const handleDesign = () => {
    if (!inputText.trim()) {
      alert("Enter design type (flowchart, wireframe, etc.)");
      return;
    }
    executeAICommand("design", {
      design_type: inputText,
      position,
    });
  };

  const handleBrainstorm = () => {
    // Accept commas or newlines; provide a sensible default if empty
    const normalized = inputText
      .split(/\n|,/)
      .map((s) => s.trim())
      .filter(Boolean);

    if (normalized.length === 0) {
      // Auto-fill a minimal prompt instead of blocking the user
      executeAICommand("brainstorm", {
        central_idea: "Brainstorm",
        branches: ["Idea 1", "Idea 2", "Idea 3"],
        position,
      });
      return;
    }

    const [central, ...rest] = normalized;

    executeAICommand("brainstorm", {
      central_idea: central,
      branches: rest.length ? rest : null,
      position,
    });
  };

  const handleAnnotate = () => {
    if (!inputText.trim()) {
      alert("Enter annotation text");
      return;
    }
    executeAICommand("annotate", {
      target: "user drawing",
      note: inputText,
      position,
    });
  };

  const handleAsk = () => {
    if (!inputText.trim()) {
      alert("Enter a question");
      return;
    }
    const [question, ...options] = inputText.split(",").map((s) => s.trim());
    executeAICommand("ask", {
      question,
      options: options.length > 0 ? options : ["Yes", "No", "Maybe"],
      position,
    });
  };

  const handlePlaywright = () => {
    if (!inputText.trim()) {
      alert(
        "Describe a test scenario first (e.g. 'user can log in and see dashboard')"
      );
      return;
    }
    executeAICommand("playwright", {
      scenario: inputText,
    });
  };

  const showStartupNote = async () => {
    try {
      await axios.post(`${API_BASE}/startup`);
    } catch (error) {
      console.error("Failed to show startup note:", error);
    }
  };

  const modes = [
    {
      id: "architect",
      label: "🏠 Architect",
      handler: handleArchitect,
      placeholder: "Describe your house (e.g. 3 bedroom ranch)...",
    },
    {
      id: "discuss",
      label: "💭 Discuss",
      handler: handleDiscuss,
      placeholder: "Enter topic to discuss...",
    },
    {
      id: "draw",
      label: "🎨 Draw",
      handler: handleDraw,
      placeholder: "Describe what to draw...",
    },
    {
      id: "plan",
      label: "📋 Plan",
      handler: handlePlan,
      placeholder: "Enter goal (add steps with commas)...",
    },
    {
      id: "design",
      label: "🏗️ Design",
      handler: handleDesign,
      placeholder: "Design type (flowchart, wireframe)...",
    },
    {
      id: "brainstorm",
      label: "💡 Brainstorm",
      handler: handleBrainstorm,
      placeholder: "Central idea, branch1, branch2...",
    },
    {
      id: "annotate",
      label: "📌 Annotate",
      handler: handleAnnotate,
      placeholder: "Add annotation text...",
    },
    {
      id: "ask",
      label: "❓ Ask",
      handler: handleAsk,
      placeholder: "Question, Option1, Option2...",
    },
    {
      id: "playwright",
      label: "🧪 Playwright",
      handler: handlePlaywright,
      placeholder: "Describe scenario to generate Playwright test...",
    },
  ];

  return (
    <div style={styles.panel}>
      {/* Header */}
      <div style={styles.header}>
        <h3 style={styles.title}>🧠 AI Assist</h3>
        <button
          onClick={toggleAI}
          style={{
            ...styles.toggleButton,
            backgroundColor: aiEnabled ? "#10b981" : "#ef4444",
          }}
        >
          {aiEnabled ? "ON" : "OFF"}
        </button>
      </div>

      {/* Status */}
      {status && (
        <div style={styles.status}>
          <small style={{ color: "#94a3b8" }}>
            Conversations: {status.conversation_count}
          </small>
        </div>
      )}

      {/* Live output (text + optional snapshot image) */}
      {(liveText || liveImage) && (
        <div style={styles.liveBox}>
          <div style={styles.liveHeader}>Live response</div>
          {liveText && <div style={styles.liveText}>{liveText}</div>}
          {liveImage && (
            <img
              src={liveImage}
              alt="AI output snapshot"
              style={styles.liveImage}
            />
          )}
        </div>
      )}

      {/* Mode Selection */}
      {!selectedMode && (
        <div style={styles.modesGrid}>
          {modes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setSelectedMode(mode)}
              style={styles.modeButton}
              disabled={!aiEnabled}
            >
              {mode.label}
            </button>
          ))}
        </div>
      )}

      {/* Input Area */}
      {selectedMode && (
        <div style={styles.inputArea}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <button
              onClick={() => setSelectedMode(null)}
              style={styles.backButton}
            >
              ← Back
            </button>
            <button
              onClick={handleMicClick}
              style={{
                ...styles.modeButton,
                backgroundColor: isListening ? "#ef4444" : "#3b82f6",
                padding: "5px 10px",
                fontSize: "14px",
                width: "auto",
                margin: 0,
              }}
              title="Speak to AI"
            >
              {isListening ? "🛑 Listening..." : "🎤 Speak"}
            </button>
          </div>

          <h4 style={styles.modeTitle}>{selectedMode.label}</h4>

          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={selectedMode.placeholder}
            style={styles.textarea}
            rows={4}
          />

          {/* Position Controls */}
          <div style={styles.positionControls}>
            <label style={styles.label}>
              X:
              <input
                type="number"
                value={position.x}
                onChange={(e) =>
                  setPosition({ ...position, x: parseInt(e.target.value) || 0 })
                }
                style={styles.numberInput}
              />
            </label>
            <label style={styles.label}>
              Y:
              <input
                type="number"
                value={position.y}
                onChange={(e) =>
                  setPosition({ ...position, y: parseInt(e.target.value) || 0 })
                }
                style={styles.numberInput}
              />
            </label>
          </div>

          <button
            onClick={() => {
              // Execute based on current selectedMode.id and CURRENT inputText
              if (selectedMode.id === "discuss") handleDiscuss();
              else if (selectedMode.id === "draw") handleDraw();
              else if (selectedMode.id === "plan") handlePlan();
              else if (selectedMode.id === "design") handleDesign();
              else if (selectedMode.id === "brainstorm") handleBrainstorm();
              else if (selectedMode.id === "annotate") handleAnnotate();
              else if (selectedMode.id === "ask") handleAsk();
            }}
            style={styles.executeButton}
            disabled={loading || !aiEnabled}
          >
            {loading ? "⏳ Working..." : `✨ ${selectedMode.label}`}
          </button>
        </div>
      )}

      {/* Quick Actions */}
      {!selectedMode && (
        <div style={styles.quickActions}>
          <button onClick={showStartupNote} style={styles.quickButton}>
            Show Startup Note
          </button>
          <button onClick={loadStatus} style={styles.quickButton}>
            Refresh Status
          </button>
        </div>
      )}
    </div>
  );
};

const styles = {
  panel: {
    backgroundColor: "#1e293b",
    borderRadius: "8px",
    padding: "16px",
    color: "#e2e8f0",
    width: "300px",
    maxHeight: "600px",
    overflowY: "auto",
    boxShadow: "0 4px 6px rgba(0, 0, 0, 0.3)",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "12px",
  },
  title: {
    margin: 0,
    fontSize: "18px",
    fontWeight: "600",
  },
  toggleButton: {
    padding: "6px 12px",
    borderRadius: "4px",
    border: "none",
    color: "white",
    fontWeight: "600",
    cursor: "pointer",
    fontSize: "12px",
  },
  status: {
    marginBottom: "12px",
    padding: "8px",
    backgroundColor: "#334155",
    borderRadius: "4px",
  },
  modesGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "8px",
    marginBottom: "12px",
  },
  modeButton: {
    padding: "12px",
    backgroundColor: "#334155",
    border: "1px solid #475569",
    borderRadius: "6px",
    color: "#e2e8f0",
    cursor: "pointer",
    fontSize: "13px",
    transition: "all 0.2s",
  },
  inputArea: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  backButton: {
    alignSelf: "flex-start",
    padding: "6px 12px",
    backgroundColor: "#475569",
    border: "none",
    borderRadius: "4px",
    color: "#e2e8f0",
    cursor: "pointer",
    fontSize: "12px",
  },
  modeTitle: {
    margin: 0,
    fontSize: "16px",
    color: "#c4b5fd",
  },
  textarea: {
    width: "100%",
    padding: "10px",
    backgroundColor: "#334155",
    border: "1px solid #475569",
    borderRadius: "6px",
    color: "#e2e8f0",
    fontSize: "13px",
    resize: "vertical",
    fontFamily: "inherit",
  },
  positionControls: {
    display: "flex",
    gap: "12px",
  },
  label: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "13px",
    color: "#94a3b8",
  },
  numberInput: {
    width: "80px",
    padding: "6px",
    backgroundColor: "#334155",
    border: "1px solid #475569",
    borderRadius: "4px",
    color: "#e2e8f0",
    fontSize: "13px",
  },
  executeButton: {
    padding: "12px",
    backgroundColor: "#8b5cf6",
    border: "none",
    borderRadius: "6px",
    color: "white",
    fontWeight: "600",
    cursor: "pointer",
    fontSize: "14px",
    transition: "all 0.2s",
  },
  quickActions: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  quickButton: {
    padding: "8px",
    backgroundColor: "#334155",
    border: "1px solid #475569",
    borderRadius: "4px",
    color: "#94a3b8",
    cursor: "pointer",
    fontSize: "12px",
  },

  liveBox: {
    marginBottom: "12px",
    padding: "10px",
    backgroundColor: "rgba(2, 6, 23, 0.45)",
    border: "1px solid rgba(148, 163, 184, 0.2)",
    borderRadius: "8px",
  },
  liveHeader: {
    fontSize: "12px",
    fontWeight: 700,
    color: "#c4b5fd",
    marginBottom: "6px",
  },
  liveText: {
    fontSize: "12.5px",
    lineHeight: 1.35,
    color: "#e2e8f0",
    whiteSpace: "pre-wrap",
  },
  liveImage: {
    width: "100%",
    marginTop: "10px",
    borderRadius: "6px",
    border: "1px solid rgba(148, 163, 184, 0.2)",
    background: "rgba(15, 23, 42, 0.6)",
  },
};

export default CanvasAIPanel;
