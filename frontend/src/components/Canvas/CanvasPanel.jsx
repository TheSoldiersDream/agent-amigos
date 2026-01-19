/**
 * 🧠🎨 Agent Amigos Canvas - Main Panel
 *
 * Full-featured visual thinking and creation surface for Agent Amigos.
 * Supports sketching, diagrams, CAD, media, and text with agent integration.
 *
 * Created by Darrell Buttigieg (@darrellbuttigieg) #thesoldiersdream
 */

import React, { useState, useRef, useCallback, useEffect } from "react";
import CanvasSurface, { TOOLS, DEFAULT_STYLES } from "./CanvasSurface";
import ToolsToolbar, { MODES } from "./ToolsToolbar";
import LayersPanel, { DEFAULT_LAYERS } from "./LayersPanel";
import CanvasAIPanel from "./CanvasAIPanel";
import {
  getVoiceEnabled,
  setVoiceEnabled as persistVoiceEnabled,
  primeVoices,
  speak,
  unlockSpeechSynthesisOnFirstGesture,
} from "../../utils/tts";

const CanvasPanel = ({
  isOpen = false,
  onClose,
  apiUrl = "http://127.0.0.1:65252",
  agentCommands: incomingAgentCommands = [], // Commands from agents (prop)
  onAgentResponse,
  onSessionReady,
  isDocked = false,
  initialPosition = { x: 100, y: 100 },
  initialSize = { width: 1200, height: 800 },
}) => {
  // Canvas ref for imperative methods
  const canvasRef = useRef(null);

  // State
  const [mode, setMode] = useState(MODES.SKETCH);
  const [tool, setTool] = useState(TOOLS.PEN);
  const [styles, setStyles] = useState(DEFAULT_STYLES);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [activeLayerId, setActiveLayerId] = useState("sketch");
  const [gridEnabled, setGridEnabled] = useState(false);
  const [snapToGrid, setSnapToGrid] = useState(false);
  const [layersPanelCollapsed, setLayersPanelCollapsed] = useState(false);
  const [aiPanelVisible, setAiPanelVisible] = useState(false);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);
  const [selectedObjects, setSelectedObjects] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [agentThoughts, setAgentThoughts] = useState([]);
  const [showThoughts, setShowThoughts] = useState(false);
  const [agentStatusMessage, setAgentStatusMessage] = useState(null);
  const [agentCommands, setAgentCommands] = useState([]);

  // ⚡ AI realtime feedback: text + voice + image snapshot
  const [aiLiveText, setAiLiveText] = useState(null);
  const [aiLiveImage, setAiLiveImage] = useState(null);
  const [lastAiSpeakText, setLastAiSpeakText] = useState(null);

  // Helper to get canvas snapshot
  const getCanvasSnapshot = useCallback(() => {
    return canvasRef.current?.exportPNG?.();
  }, []);

  // 🔊 Voice replies (shared global setting with the rest of Agent Amigos)
  const [voiceEnabled, setVoiceEnabled] = useState(() => {
    try {
      return typeof window !== "undefined" ? getVoiceEnabled(true) : true;
    } catch {
      return true;
    }
  });

  useEffect(() => {
    try {
      persistVoiceEnabled(voiceEnabled);
    } catch {
      // ignore
    }
  }, [voiceEnabled]);

  useEffect(() => {
    primeVoices();
    const cleanup = unlockSpeechSynthesisOnFirstGesture();
    return cleanup;
  }, []);

  const toast = useCallback((text, { autoHideMs = 3500 } = {}) => {
    setAgentStatusMessage(text);
    if (autoHideMs > 0) {
      setTimeout(() => setAgentStatusMessage(null), autoHideMs);
    }
  }, []);

  const speakIfEnabled = useCallback(
    (text, { interrupt = true } = {}) => {
      if (!text) return;
      setLastAiSpeakText(text);
      try {
        speak(text, { enabled: !!voiceEnabled, interrupt });
      } catch {
        // ignore
      }
    },
    [voiceEnabled]
  );

  // Dragging & Resizing state (for floating mode)
  const [position, setPosition] = useState(initialPosition);
  const [size, setSize] = useState(initialSize);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  // Initialize session
  useEffect(() => {
    if (isOpen && !sessionId) {
      initSession();
    }
  }, [isOpen]);

  // Process agent commands
  useEffect(() => {
    if (agentCommands.length > 0) {
      processAgentCommands(agentCommands);
    }
  }, [agentCommands]);

  // Sync commands passed from parent into local processing pipeline
  useEffect(() => {
    if (
      Array.isArray(incomingAgentCommands) &&
      incomingAgentCommands.length > 0
    ) {
      setAgentCommands(incomingAgentCommands);
    }
  }, [incomingAgentCommands]);
  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;

      // Check for modifier keys
      const ctrl = e.ctrlKey || e.metaKey;

      if (ctrl && e.key === "z") {
        e.preventDefault();
        handleUndo();
      } else if (ctrl && e.key === "y") {
        e.preventDefault();
        handleRedo();
      } else if (!ctrl) {
        // Tool shortcuts
        const shortcuts = {
          v: TOOLS.SELECT,
          p: TOOLS.PEN,
          b: TOOLS.BRUSH,
          e: TOOLS.ERASER,
          l: TOOLS.LINE,
          r: TOOLS.RECTANGLE,
          o: TOOLS.ELLIPSE,
          a: TOOLS.ARROW,
          t: TOOLS.TEXT,
          w: TOOLS.WALL,
          d: TOOLS.DOOR,
          n: TOOLS.WINDOW,
          m: TOOLS.DIMENSION,
        };
        if (shortcuts[e.key.toLowerCase()]) {
          setTool(shortcuts[e.key.toLowerCase()]);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Initialize backend session
  const initSession = async () => {
    try {
      const response = await fetch(`${apiUrl}/canvas/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "create" }),
      });
      const data = await response.json();
      setSessionId(data.session_id);
      onSessionReady?.(data.session_id);
    } catch (error) {
      console.error("Failed to create canvas session:", error);
      // Generate local session ID if backend unavailable
      setSessionId(`local_${Date.now()}`);
      onSessionReady?.(`local_${Date.now()}`);
    }
  };

  // Process commands from agents (handles backend command_type format)
  const processAgentCommands = async (commands) => {
    console.log("🎨 Processing agent commands:", commands.length);

    const showAgentStatus = (text) => {
      toast(text, { autoHideMs: 2500 });
    };

    // If these commands are mostly targeted at the AI assist layer, make sure
    // the user actually *sees* something by unhiding the layer and resetting view.
    try {
      const list = Array.isArray(commands) ? commands : [];
      const aiHits = list.filter(
        (c) => (c?.parameters?.layer_id || c?.layer_id) === "ai_assist_layer"
      ).length;
      if (list.length > 0 && aiHits / list.length >= 0.6) {
        setLayers((prev) =>
          prev.map((l) =>
            l.id === "ai_assist_layer" ? { ...l, visible: true } : l
          )
        );
        canvasRef.current?.resetView?.();
      }
    } catch {
      // ignore
    }

    const objectsToAdd = [];

    for (const cmd of commands) {
      try {
        const params = cmd.parameters || {};
        const cmdType = cmd.command_type || cmd.action;
        const layerId = params.layer_id || cmd.layer_id || "ai_assist_layer";

        console.log(`🖌️ Executing: ${cmdType}`, params);

        const strokeColor =
          params.strokeColor ||
          params.stroke_color ||
          params.color ||
          "#6366f1";
        const fillColor =
          params.fillColor || params.fill_color || "transparent";
        const strokeWidth = params.strokeWidth || params.stroke_width || 2;

        switch (cmdType) {
          // Drawing shapes
          case "draw_rectangle":
            objectsToAdd.push({
              type: "rectangle",
              x: params.x || 100,
              y: params.y || 100,
              width: params.width || 100,
              height: params.height || 100,
              strokeColor,
              fillColor,
              strokeWidth,
              layerId,
            });
            break;

          case "draw_ellipse":
            objectsToAdd.push({
              type: "ellipse",
              x: params.cx - (params.rx || 50),
              y: params.cy - (params.ry || 50),
              width: (params.rx || 50) * 2,
              height: (params.ry || 50) * 2,
              strokeColor,
              fillColor,
              strokeWidth,
              layerId,
            });
            break;

          case "draw_line":
            objectsToAdd.push({
              type: "line",
              x1: params.x1 || 0,
              y1: params.y1 || 0,
              x2: params.x2 || 100,
              y2: params.y2 || 100,
              strokeColor,
              strokeWidth,
              layerId,
            });
            break;

          case "draw_arrow":
            objectsToAdd.push({
              type: "arrow",
              x1: params.x1 || 0,
              y1: params.y1 || 0,
              x2: params.x2 || 100,
              y2: params.y2 || 100,
              strokeColor,
              strokeWidth: params.width || strokeWidth,
              layerId,
            });
            break;

          case "draw_text":
            objectsToAdd.push({
              type: "text",
              text: params.text || "Text",
              x: params.x || 100,
              y: params.y || 100,
              fontSize: params.fontSize || params.font_size || 16,
              fontFamily: params.fontFamily || params.font_family || "Arial",
              strokeColor: params.color || "#ffffff",
              layerId,
            });
            break;

          // Legacy action-based commands
          case "draw":
            await executeDrawCommand(cmd);
            break;
          case "add_text":
            objectsToAdd.push({
              type: "text",
              text: cmd.text,
              x: cmd.x || 100,
              y: cmd.y || 100,
              fontSize: cmd.fontSize || 16,
              strokeColor: cmd.color || "#ffffff",
              layerId: activeLayerId,
            });
            break;
          case "add_shape":
            objectsToAdd.push({
              type: cmd.shapeType,
              ...cmd.props,
              layerId: activeLayerId,
            });
            break;
          case "clear":
            canvasRef.current?.clear();
            break;
          case "set_mode":
            setMode(cmd.mode || params.mode);
            break;
          case "thought":
            setAgentThoughts((prev) => [
              ...prev,
              {
                agent: cmd.agent || "Amigos",
                text: cmd.thought || params.thought || cmd.text,
                timestamp: Date.now(),
              },
            ]);
            break;
          default:
            console.log("Unknown agent command:", cmdType, cmd);
        }

        // Add thought if present
        if (cmd.thought) {
          setAgentThoughts((prev) => [
            ...prev,
            { agent: "Amigos", text: cmd.thought, timestamp: Date.now() },
          ]);
        }
      } catch (error) {
        console.error("Error processing command:", cmd, error);
      }
    }

    if (objectsToAdd.length > 0) {
      canvasRef.current?.addObjects(objectsToAdd);
      showAgentStatus(`Agent executed ${objectsToAdd.length} drawing commands`);
    }

    // Snapshot the canvas after executing the batch ("image" feedback)
    try {
      canvasRef.current?.redraw?.();
      const png = canvasRef.current?.exportPNG?.();
      if (png) setAiLiveImage(png);
    } catch {
      // ignore
    }
  };

  // Realtime text/voice feedback emitted by CanvasAIPanel
  const handleAiRealtimeEvent = useCallback(
    (evt) => {
      if (!evt || !evt.type) return;

      if (evt.type === "start") {
        const text = evt.text || "Working...";
        setAiLiveText(text);
        setAiLiveImage(null);
        toast(text, { autoHideMs: 1500 });
        setAiPanelVisible(true);
        setLayers((prev) =>
          prev.map((l) =>
            l.id === "ai_assist_layer" ? { ...l, visible: true } : l
          )
        );
        return;
      }

      if (evt.type === "success") {
        const text = evt.text || "Done.";
        setAiLiveText(text);
        toast(text, { autoHideMs: 3500 });
        speakIfEnabled(text);
        setAiPanelVisible(true);
        return;
      }

      if (evt.type === "error") {
        const text = evt.text || "Error.";
        setAiLiveText(text);
        toast(text, { autoHideMs: 4500 });
        speakIfEnabled(text);
        setAiPanelVisible(true);
      }
    },
    [speakIfEnabled, toast]
  );

  // Execute complex draw commands (e.g., floor plans, diagrams)
  const executeDrawCommand = async (cmd) => {
    if (cmd.type === "floor_plan") {
      // Draw a floor plan from specifications
      const { rooms, scale = 1 } = cmd;
      let offsetX = 100;
      let offsetY = 100;

      for (const room of rooms) {
        // Draw room walls
        const w = room.width * scale * 50;
        const h = room.height * scale * 50;

        canvasRef.current?.addObject({
          type: "rectangle",
          x: offsetX,
          y: offsetY,
          width: w,
          height: h,
          strokeColor: "#64748b",
          strokeWidth: 6,
          fillColor: "transparent",
        });

        // Add room label
        canvasRef.current?.addObject({
          type: "text",
          text: room.name,
          x: offsetX + w / 2 - 30,
          y: offsetY + h / 2,
          fontSize: 14,
          strokeColor: "#94a3b8",
        });

        // Add dimensions
        canvasRef.current?.addObject({
          type: "dimension",
          x1: offsetX,
          y1: offsetY + h + 20,
          x2: offsetX + w,
          y2: offsetY + h + 20,
          unit: "mm",
        });

        // Add doors if specified
        if (room.doors) {
          for (const door of room.doors) {
            canvasRef.current?.addObject({
              type: "door",
              x: offsetX + (door.position === "left" ? 0 : w - 40),
              y: offsetY + h / 2 - 20,
              width: 40,
            });
          }
        }

        offsetX += w + 50;
      }
    } else if (cmd.type === "flowchart") {
      // Draw a flowchart from nodes and connections
      const { nodes, connections } = cmd;
      const nodePositions = {};

      // Draw nodes
      for (const node of nodes) {
        nodePositions[node.id] = { x: node.x, y: node.y };

        if (node.shape === "diamond") {
          // Decision node - draw as rotated rectangle
          canvasRef.current?.addObject({
            type: "rectangle",
            x: node.x - 40,
            y: node.y - 25,
            width: 80,
            height: 50,
            strokeColor: "#f59e0b",
            strokeWidth: 2,
          });
        } else {
          // Regular node
          canvasRef.current?.addObject({
            type: node.shape === "ellipse" ? "ellipse" : "rectangle",
            x: node.x - 50,
            y: node.y - 20,
            width: 100,
            height: 40,
            strokeColor: "#8b5cf6",
            strokeWidth: 2,
          });
        }

        // Add label
        canvasRef.current?.addObject({
          type: "text",
          text: node.label,
          x: node.x - 40,
          y: node.y + 5,
          fontSize: 12,
          strokeColor: "#e2e8f0",
        });
      }

      // Draw connections
      for (const conn of connections) {
        const from = nodePositions[conn.from];
        const to = nodePositions[conn.to];
        if (from && to) {
          canvasRef.current?.addObject({
            type: "arrow",
            x1: from.x,
            y1: from.y + 25,
            x2: to.x,
            y2: to.y - 25,
            strokeColor: "#6366f1",
            strokeWidth: 2,
          });
        }
      }
    } else if (cmd.type === "poem" || cmd.type === "text_block") {
      // Render formatted text (poem, story, etc.)
      const lines = cmd.text.split("\n");
      let y = cmd.y || 100;

      for (const line of lines) {
        canvasRef.current?.addObject({
          type: "text",
          text: line,
          x: cmd.x || 100,
          y: y,
          fontSize: cmd.fontSize || 18,
          strokeColor: cmd.color || "#e2e8f0",
          fontFamily: cmd.font || "Georgia, serif",
        });
        y += cmd.lineHeight || 28;
      }
    }
  };

  // Tool handlers
  const handleModeChange = (newMode) => {
    setMode(newMode);
    // Set default tool for mode
    const modeTools = {
      [MODES.SKETCH]: TOOLS.PEN,
      [MODES.DIAGRAM]: TOOLS.RECTANGLE,
      [MODES.CAD]: TOOLS.WALL,
      [MODES.MEDIA]: TOOLS.IMAGE,
      [MODES.TEXT]: TOOLS.TEXT,
    };
    setTool(modeTools[newMode] || TOOLS.SELECT);

    // Enable grid for CAD mode
    if (newMode === MODES.CAD) {
      setGridEnabled(true);
      setSnapToGrid(true);
      setActiveLayerId("cad");
    } else {
      setGridEnabled(false);
      setSnapToGrid(false);
    }
  };

  const handleUndo = () => canvasRef.current?.undo();
  const handleRedo = () => canvasRef.current?.redo();
  const handleClear = () => {
    if (confirm("Clear all content? This cannot be undone.")) {
      canvasRef.current?.clear();
    }
  };

  const handleExport = async (format) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    let data, filename, type;

    switch (format) {
      case "png":
        data = canvas.exportPNG();
        filename = `canvas_${Date.now()}.png`;
        // Download
        const linkPng = document.createElement("a");
        linkPng.download = filename;
        linkPng.href = data;
        linkPng.click();
        break;

      case "svg":
        data = canvas.exportSVG();
        filename = `canvas_${Date.now()}.svg`;
        const blobSvg = new Blob([data], { type: "image/svg+xml" });
        const urlSvg = URL.createObjectURL(blobSvg);
        const linkSvg = document.createElement("a");
        linkSvg.download = filename;
        linkSvg.href = urlSvg;
        linkSvg.click();
        URL.revokeObjectURL(urlSvg);
        break;

      case "json":
        data = JSON.stringify(
          {
            objects: canvas.getObjects(),
            layers,
            mode,
            timestamp: Date.now(),
          },
          null,
          2
        );
        filename = `canvas_${Date.now()}.json`;
        const blobJson = new Blob([data], { type: "application/json" });
        const urlJson = URL.createObjectURL(blobJson);
        const linkJson = document.createElement("a");
        linkJson.download = filename;
        linkJson.href = urlJson;
        linkJson.click();
        URL.revokeObjectURL(urlJson);
        break;

      case "pdf":
      case "dxf":
        // These would require backend processing
        try {
          const response = await fetch(`${apiUrl}/canvas/export`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              format,
              objects: canvas.getObjects(),
              layers,
            }),
          });
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.download = `canvas_${Date.now()}.${format}`;
          link.href = url;
          link.click();
          URL.revokeObjectURL(url);
        } catch (error) {
          console.error(`Export to ${format} failed:`, error);
          alert(`Export to ${format.toUpperCase()} requires backend support.`);
        }
        break;
    }
  };

  const handleImport = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*,.json";
    input.onchange = async (e) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (file.type === "application/json") {
        // Import JSON state
        const text = await file.text();
        const data = JSON.parse(text);
        if (data.objects) {
          canvasRef.current?.setObjects(data.objects);
        }
        if (data.layers) {
          setLayers(data.layers);
        }
        if (data.mode) {
          setMode(data.mode);
        }
      } else {
        // Import image
        const reader = new FileReader();
        reader.onload = (event) => {
          const img = new Image();
          img.onload = () => {
            canvasRef.current?.addObject({
              type: "image",
              imageData: event.target.result,
              x: 100,
              y: 100,
              width: img.width,
              height: img.height,
            });
          };
          img.src = event.target.result;
        };
        reader.readAsDataURL(file);
      }
    };
    input.click();
  };

  // Layer handlers
  const handleLayerVisibilityToggle = (layerId) => {
    setLayers(
      layers.map((l) => (l.id === layerId ? { ...l, visible: !l.visible } : l))
    );
  };

  const handleLayerLockToggle = (layerId) => {
    setLayers(
      layers.map((l) => (l.id === layerId ? { ...l, locked: !l.locked } : l))
    );
  };

  const handleLayerAdd = (newLayer) => {
    setLayers([...layers, newLayer]);
  };

  const handleLayerDelete = (layerId) => {
    setLayers(layers.filter((l) => l.id !== layerId));
    if (activeLayerId === layerId) {
      setActiveLayerId(layers[0]?.id || "sketch");
    }
  };

  const handleLayerRename = (layerId, newName) => {
    setLayers(
      layers.map((l) => (l.id === layerId ? { ...l, name: newName } : l))
    );
  };

  // Drag handlers (floating mode)
  const handleDragStart = (e) => {
    if (isDocked) return;
    setIsDragging(true);
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y,
    });
  };

  const handleDrag = useCallback(
    (e) => {
      if (!isDragging) return;
      setPosition({
        x: e.clientX - dragOffset.x,
        y: e.clientY - dragOffset.y,
      });
    },
    [isDragging, dragOffset]
  );

  const handleDragEnd = () => {
    setIsDragging(false);
  };

  // Resize handlers
  const handleResizeStart = (e) => {
    if (isDocked) return;
    e.stopPropagation();
    setIsResizing(true);
  };

  const handleResize = useCallback(
    (e) => {
      if (!isResizing) return;
      setSize({
        width: Math.max(600, e.clientX - position.x),
        height: Math.max(400, e.clientY - position.y),
      });
    },
    [isResizing, position]
  );

  const handleResizeEnd = () => {
    setIsResizing(false);
  };

  useEffect(() => {
    if (isDragging) {
      window.addEventListener("mousemove", handleDrag);
      window.addEventListener("mouseup", handleDragEnd);
    }
    return () => {
      window.removeEventListener("mousemove", handleDrag);
      window.removeEventListener("mouseup", handleDragEnd);
    };
  }, [isDragging, handleDrag]);

  useEffect(() => {
    if (isResizing) {
      window.addEventListener("mousemove", handleResize);
      window.addEventListener("mouseup", handleResizeEnd);
    }
    return () => {
      window.removeEventListener("mousemove", handleResize);
      window.removeEventListener("mouseup", handleResizeEnd);
    };
  }, [isResizing, handleResize]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: isDocked ? "relative" : "fixed",
        left: isDocked ? 0 : position.x,
        top: isDocked ? 0 : position.y,
        width: isDocked ? "100%" : size.width,
        height: isDocked ? "100%" : size.height,
        background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)",
        borderRadius: isDocked ? 0 : "16px",
        border: "1px solid rgba(99, 102, 241, 0.3)",
        boxShadow: isDocked ? "none" : "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
        zIndex: 1000,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        onMouseDown={handleDragStart}
        style={{
          padding: "12px 16px",
          background:
            "linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.1))",
          borderBottom: "1px solid rgba(99, 102, 241, 0.2)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: isDocked ? "default" : isDragging ? "grabbing" : "grab",
          userSelect: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "1.3em" }}>🧠🎨</span>
          <div>
            <div
              style={{ color: "#e2e8f0", fontWeight: "700", fontSize: "1em" }}
            >
              Agent Amigos Canvas
            </div>
            <div style={{ color: "#64748b", fontSize: "0.7em" }}>
              Visual Thinking & Creation Surface • Session:{" "}
              {sessionId?.slice(0, 8) || "Initializing..."}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* AI Assist Toggle */}
          <button
            onClick={() => setAiPanelVisible(!aiPanelVisible)}
            title="Toggle AI Assist Panel"
            style={{
              padding: "6px 12px",
              borderRadius: "8px",
              border: "none",
              background: aiPanelVisible
                ? "rgba(167, 139, 250, 0.3)"
                : "rgba(30, 41, 59, 0.5)",
              color: aiPanelVisible ? "#a78bfa" : "#94a3b8",
              cursor: "pointer",
              fontSize: "0.75em",
              fontWeight: "600",
            }}
          >
            🧠 AI Assist
          </button>

          {/* Agent Thoughts Toggle */}
          <button
            onClick={() => setShowThoughts(!showThoughts)}
            title="Toggle Agent Thoughts"
            style={{
              padding: "6px 12px",
              borderRadius: "8px",
              border: "none",
              background: showThoughts
                ? "rgba(139, 92, 246, 0.3)"
                : "rgba(30, 41, 59, 0.5)",
              color: showThoughts ? "#c4b5fd" : "#94a3b8",
              cursor: "pointer",
              fontSize: "0.75em",
              fontWeight: "600",
            }}
          >
            💭 Thoughts{" "}
            {agentThoughts.length > 0 && `(${agentThoughts.length})`}
          </button>

          {/* Voice toggle */}
          <button
            onClick={() => {
              setVoiceEnabled((prev) => {
                const next = !prev;
                // If we're turning voice ON, confirm audibly.
                if (!prev) {
                  try {
                    speak("Voice replies enabled.", {
                      enabled: true,
                      interrupt: true,
                    });
                  } catch {
                    // ignore
                  }
                }
                return next;
              });
            }}
            title={voiceEnabled ? "Voice replies ON" : "Voice replies OFF"}
            style={{
              padding: "6px 10px",
              borderRadius: "8px",
              border: "none",
              background: voiceEnabled
                ? "rgba(16, 185, 129, 0.22)"
                : "rgba(30, 41, 59, 0.5)",
              color: voiceEnabled ? "#34d399" : "#94a3b8",
              cursor: "pointer",
              fontSize: "0.8em",
            }}
          >
            🔊
          </button>

          {/* Replay last AI voice line */}
          {lastAiSpeakText && (
            <button
              onClick={() =>
                speakIfEnabled(lastAiSpeakText, { interrupt: true })
              }
              title="Replay last AI response"
              style={{
                padding: "6px 10px",
                borderRadius: "8px",
                border: "none",
                background: "rgba(30, 41, 59, 0.5)",
                color: "#94a3b8",
                cursor: "pointer",
                fontSize: "0.8em",
              }}
            >
              🔁
            </button>
          )}

          {/* Zoom Controls */}
          <button
            onClick={() => canvasRef.current?.setZoom(1)}
            title="Reset Zoom"
            style={{
              padding: "6px 10px",
              borderRadius: "8px",
              border: "none",
              background: "rgba(30, 41, 59, 0.5)",
              color: "#94a3b8",
              cursor: "pointer",
              fontSize: "0.8em",
            }}
          >
            🔍 100%
          </button>

          {/* Close Button */}
          <button
            onClick={onClose}
            style={{
              padding: "6px 12px",
              borderRadius: "8px",
              border: "none",
              background: "rgba(239, 68, 68, 0.2)",
              color: "#ef4444",
              cursor: "pointer",
              fontSize: "0.9em",
              fontWeight: "700",
            }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Tools Toolbar */}
        <ToolsToolbar
          mode={mode}
          tool={tool}
          styles={styles}
          gridEnabled={gridEnabled}
          snapToGrid={snapToGrid}
          onModeChange={handleModeChange}
          onToolChange={setTool}
          onStylesChange={setStyles}
          onGridToggle={() => setGridEnabled(!gridEnabled)}
          onSnapToggle={() => setSnapToGrid(!snapToGrid)}
          onUndo={handleUndo}
          onRedo={handleRedo}
          onClear={handleClear}
          onExport={handleExport}
          onImport={handleImport}
          canUndo={canUndo}
          canRedo={canRedo}
        />

        {/* Canvas Area */}
        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          <CanvasSurface
            ref={canvasRef}
            width={size.width - 70 - (layersPanelCollapsed ? 0 : 200)}
            height={size.height - 60}
            tool={tool}
            styles={styles}
            gridEnabled={gridEnabled}
            gridSize={20}
            snapToGrid={snapToGrid}
            layers={layers}
            activeLayerId={activeLayerId}
            mode={mode}
            onObjectAdd={(obj) => console.log("Object added:", obj)}
            onObjectDelete={(id) => console.log("Object deleted:", id)}
            onSelectionChange={setSelectedObjects}
          />

          {/* Agent Thoughts Overlay */}
          {showThoughts && agentThoughts.length > 0 && (
            <div
              style={{
                position: "absolute",
                top: "10px",
                left: "10px",
                maxWidth: "300px",
                maxHeight: "200px",
                overflowY: "auto",
                padding: "12px",
                background: "rgba(15, 23, 42, 0.9)",
                backdropFilter: "blur(10px)",
                borderRadius: "12px",
                border: "1px solid rgba(139, 92, 246, 0.3)",
              }}
            >
              <div
                style={{
                  fontSize: "0.75em",
                  color: "#c4b5fd",
                  marginBottom: "8px",
                  fontWeight: "600",
                }}
              >
                💭 Agent Thoughts
              </div>
              {agentThoughts.slice(-5).map((thought, i) => (
                <div
                  key={i}
                  style={{
                    padding: "6px 8px",
                    marginBottom: "4px",
                    background: "rgba(139, 92, 246, 0.1)",
                    borderRadius: "6px",
                    fontSize: "0.7em",
                    color: "#e2e8f0",
                  }}
                >
                  <span style={{ color: "#a78bfa", fontWeight: "600" }}>
                    {thought.agent}:
                  </span>{" "}
                  {thought.text}
                </div>
              ))}
            </div>
          )}

          {/* Mode Indicator */}
          <div
            style={{
              position: "absolute",
              bottom: "10px",
              left: "10px",
              padding: "8px 16px",
              background: "rgba(15, 23, 42, 0.9)",
              borderRadius: "20px",
              fontSize: "0.75em",
              color: "#94a3b8",
            }}
          >
            Mode:{" "}
            <span style={{ color: "#a5b4fc", fontWeight: "600" }}>
              {mode.toUpperCase()}
            </span>
            {" • "}Tool:{" "}
            <span style={{ color: "#6ee7b7", fontWeight: "600" }}>{tool}</span>
          </div>
        </div>

        {/* Layers Panel */}
        <LayersPanel
          layers={layers}
          activeLayerId={activeLayerId}
          onLayerSelect={setActiveLayerId}
          onLayerVisibilityToggle={handleLayerVisibilityToggle}
          onLayerLockToggle={handleLayerLockToggle}
          onLayerAdd={handleLayerAdd}
          onLayerDelete={handleLayerDelete}
          onLayerRename={handleLayerRename}
          onLayersChange={setLayers}
          collapsed={layersPanelCollapsed}
          onToggleCollapse={() =>
            setLayersPanelCollapsed(!layersPanelCollapsed)
          }
        />

        {/* AI Assist Panel */}
        {aiPanelVisible && (
          <div
            style={{
              position: "absolute",
              top: "80px",
              right: layersPanelCollapsed ? "20px" : "220px",
              zIndex: 1000,
            }}
          >
            <CanvasAIPanel
              onRealtimeEvent={handleAiRealtimeEvent}
              liveText={aiLiveText}
              liveImage={aiLiveImage}
              getCanvasSnapshot={getCanvasSnapshot}
              apiUrl={apiUrl}
              layers={layers}
              onCommandIssued={(commands) => {
                console.log(
                  "AI command executed, processing commands:",
                  commands
                );
                // commands is an array of DrawCommand objects
                if (Array.isArray(commands) && commands.length > 0) {
                  setAiPanelVisible(true);
                  setAiLiveText(
                    `Drawing ${commands.length} item${
                      commands.length === 1 ? "" : "s"
                    }...`
                  );
                  // Process the commands through the normal flow
                  setAgentCommands(commands);
                  toast(
                    `AI executed ${commands.length} command(s) on layer ai_assist_layer`,
                    { autoHideMs: 2500 }
                  );
                }
              }}
            />
          </div>
        )}
      </div>

      {/* Resize Handle (floating mode) */}
      {!isDocked && (
        <div
          onMouseDown={handleResizeStart}
          style={{
            position: "absolute",
            bottom: 0,
            right: 0,
            width: "20px",
            height: "20px",
            cursor: "se-resize",
            background:
              "linear-gradient(135deg, transparent 50%, rgba(99, 102, 241, 0.5) 50%)",
            borderRadius: "0 0 16px 0",
          }}
        />
      )}

      {/* Agent status toast */}
      {agentStatusMessage && (
        <div
          style={{
            position: "absolute",
            right: 16,
            bottom: 16,
            background: "rgba(30,41,59,0.9)",
            color: "#e2e8f0",
            padding: "10px 12px",
            borderRadius: "8px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
            border: "1px solid rgba(99,102,241,0.4)",
            fontSize: "0.9em",
            zIndex: 2000,
          }}
        >
          {agentStatusMessage}
        </div>
      )}
    </div>
  );
};

export default CanvasPanel;
