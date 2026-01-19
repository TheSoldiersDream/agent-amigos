/**
 * 🧠🎨 Agent Amigos Canvas - Tools Toolbar
 *
 * Tool selection panel with mode switching (Text/Sketch/Diagram/Media/CAD)
 * and comprehensive drawing tools for each mode.
 *
 * Created by Darrell Buttigieg (@darrellbuttigieg) #thesoldiersdream
 */

import React, { useState } from "react";
import { TOOLS, DEFAULT_STYLES } from "./CanvasSurface";

// Mode configurations
const MODES = {
  SKETCH: "sketch",
  DIAGRAM: "diagram",
  CAD: "cad",
  MEDIA: "media",
  TEXT: "text",
};

const MODE_CONFIG = {
  [MODES.SKETCH]: {
    label: "✏️ Sketch",
    description: "Freehand drawing & illustrations",
    color: "#ec4899",
    tools: [
      TOOLS.SELECT,
      TOOLS.PEN,
      TOOLS.BRUSH,
      TOOLS.ERASER,
      TOOLS.LINE,
      TOOLS.RECTANGLE,
      TOOLS.ELLIPSE,
      TOOLS.TEXT,
    ],
  },
  [MODES.DIAGRAM]: {
    label: "📊 Diagram",
    description: "Flowcharts, boxes & arrows",
    color: "#8b5cf6",
    tools: [
      TOOLS.SELECT,
      TOOLS.RECTANGLE,
      TOOLS.ELLIPSE,
      TOOLS.LINE,
      TOOLS.ARROW,
      TOOLS.TEXT,
      TOOLS.ERASER,
    ],
  },
  [MODES.CAD]: {
    label: "📐 CAD",
    description: "Floor plans & technical drawings",
    color: "#06b6d4",
    tools: [
      TOOLS.SELECT,
      TOOLS.WALL,
      TOOLS.DOOR,
      TOOLS.WINDOW,
      TOOLS.DIMENSION,
      TOOLS.LINE,
      TOOLS.RECTANGLE,
      TOOLS.TEXT,
      TOOLS.ERASER,
    ],
  },
  [MODES.MEDIA]: {
    label: "🎬 Media",
    description: "Images, videos & animations",
    color: "#f59e0b",
    tools: [TOOLS.SELECT, TOOLS.IMAGE, TOOLS.RECTANGLE, TOOLS.TEXT],
  },
  [MODES.TEXT]: {
    label: "📝 Text",
    description: "Poetry, stories & notes",
    color: "#22c55e",
    tools: [TOOLS.SELECT, TOOLS.TEXT, TOOLS.ERASER],
  },
};

const TOOL_CONFIG = {
  [TOOLS.SELECT]: { icon: "👆", label: "Select", shortcut: "V" },
  [TOOLS.PEN]: { icon: "✏️", label: "Pen", shortcut: "P" },
  [TOOLS.BRUSH]: { icon: "🖌️", label: "Brush", shortcut: "B" },
  [TOOLS.ERASER]: { icon: "🧹", label: "Eraser", shortcut: "E" },
  [TOOLS.LINE]: { icon: "📏", label: "Line", shortcut: "L" },
  [TOOLS.RECTANGLE]: { icon: "⬜", label: "Rectangle", shortcut: "R" },
  [TOOLS.ELLIPSE]: { icon: "⭕", label: "Ellipse", shortcut: "O" },
  [TOOLS.ARROW]: { icon: "➡️", label: "Arrow", shortcut: "A" },
  [TOOLS.TEXT]: { icon: "🔤", label: "Text", shortcut: "T" },
  [TOOLS.IMAGE]: { icon: "🖼️", label: "Image", shortcut: "I" },
  [TOOLS.WALL]: { icon: "🧱", label: "Wall", shortcut: "W" },
  [TOOLS.DOOR]: { icon: "🚪", label: "Door", shortcut: "D" },
  [TOOLS.WINDOW]: { icon: "🪟", label: "Window", shortcut: "N" },
  [TOOLS.DIMENSION]: { icon: "📐", label: "Dimension", shortcut: "M" },
};

// Color presets
const COLOR_PRESETS = [
  "#ffffff",
  "#ef4444",
  "#f97316",
  "#f59e0b",
  "#eab308",
  "#22c55e",
  "#14b8a6",
  "#06b6d4",
  "#3b82f6",
  "#6366f1",
  "#8b5cf6",
  "#a855f7",
  "#d946ef",
  "#ec4899",
  "#64748b",
];

const ToolsToolbar = ({
  mode = MODES.SKETCH,
  tool = TOOLS.PEN,
  styles = DEFAULT_STYLES,
  gridEnabled = false,
  snapToGrid = false,
  onModeChange,
  onToolChange,
  onStylesChange,
  onGridToggle,
  onSnapToggle,
  onUndo,
  onRedo,
  onClear,
  onExport,
  onImport,
  canUndo = false,
  canRedo = false,
}) => {
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [colorPickerType, setColorPickerType] = useState("stroke"); // 'stroke' or 'fill'

  const currentModeConfig = MODE_CONFIG[mode];
  const availableTools = currentModeConfig?.tools || [];

  const handleColorSelect = (color) => {
    onStylesChange?.({
      ...styles,
      [colorPickerType === "stroke" ? "strokeColor" : "fillColor"]: color,
    });
    setShowColorPicker(false);
  };

  const handleStrokeWidthChange = (e) => {
    onStylesChange?.({
      ...styles,
      strokeWidth: parseInt(e.target.value, 10),
    });
  };

  const handleFontSizeChange = (e) => {
    onStylesChange?.({
      ...styles,
      fontSize: parseInt(e.target.value, 10),
    });
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        padding: "12px",
        background: "rgba(15, 23, 42, 0.95)",
        backdropFilter: "blur(20px)",
        borderRight: "1px solid rgba(99, 102, 241, 0.2)",
        height: "100%",
        width: "70px",
        overflowY: "auto",
      }}
    >
      {/* Mode Selector */}
      <div style={{ marginBottom: "8px" }}>
        <div
          style={{
            fontSize: "0.65em",
            color: "#64748b",
            marginBottom: "6px",
            textAlign: "center",
          }}
        >
          MODE
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {Object.entries(MODE_CONFIG).map(([key, config]) => (
            <button
              key={key}
              onClick={() => onModeChange?.(key)}
              title={config.description}
              style={{
                padding: "8px 4px",
                borderRadius: "8px",
                border: "none",
                background:
                  mode === key
                    ? `linear-gradient(135deg, ${config.color}40, ${config.color}20)`
                    : "rgba(30, 41, 59, 0.5)",
                color: mode === key ? config.color : "#94a3b8",
                cursor: "pointer",
                fontSize: "0.7em",
                fontWeight: "600",
                transition: "all 0.2s ease",
                boxShadow: mode === key ? `0 0 15px ${config.color}30` : "none",
              }}
            >
              {config.label.split(" ")[0]}
              <div style={{ fontSize: "0.85em", marginTop: "2px" }}>
                {config.label.split(" ")[1]}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div
        style={{
          height: "1px",
          background: "rgba(99, 102, 241, 0.2)",
          margin: "4px 0",
        }}
      />

      {/* Tools */}
      <div>
        <div
          style={{
            fontSize: "0.65em",
            color: "#64748b",
            marginBottom: "6px",
            textAlign: "center",
          }}
        >
          TOOLS
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {availableTools.map((toolKey) => {
            const config = TOOL_CONFIG[toolKey];
            return (
              <button
                key={toolKey}
                onClick={() => onToolChange?.(toolKey)}
                title={`${config.label} (${config.shortcut})`}
                style={{
                  padding: "10px 6px",
                  borderRadius: "8px",
                  border: "none",
                  background:
                    tool === toolKey
                      ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
                      : "rgba(30, 41, 59, 0.5)",
                  color: tool === toolKey ? "#fff" : "#94a3b8",
                  cursor: "pointer",
                  fontSize: "1.1em",
                  transition: "all 0.2s ease",
                  boxShadow:
                    tool === toolKey
                      ? "0 4px 15px rgba(99, 102, 241, 0.3)"
                      : "none",
                }}
              >
                {config.icon}
              </button>
            );
          })}
        </div>
      </div>

      {/* Divider */}
      <div
        style={{
          height: "1px",
          background: "rgba(99, 102, 241, 0.2)",
          margin: "4px 0",
        }}
      />

      {/* Color Pickers */}
      <div>
        <div
          style={{
            fontSize: "0.65em",
            color: "#64748b",
            marginBottom: "6px",
            textAlign: "center",
          }}
        >
          COLORS
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {/* Stroke Color */}
          <button
            onClick={() => {
              setColorPickerType("stroke");
              setShowColorPicker(!showColorPicker);
            }}
            title="Stroke Color"
            style={{
              width: "100%",
              height: "28px",
              borderRadius: "6px",
              border: "2px solid rgba(255,255,255,0.2)",
              background: styles.strokeColor,
              cursor: "pointer",
              position: "relative",
            }}
          >
            <span
              style={{
                position: "absolute",
                bottom: "-2px",
                right: "-2px",
                fontSize: "0.6em",
                background: "#1e293b",
                padding: "1px 3px",
                borderRadius: "3px",
              }}
            >
              ✏️
            </span>
          </button>

          {/* Fill Color */}
          <button
            onClick={() => {
              setColorPickerType("fill");
              setShowColorPicker(!showColorPicker);
            }}
            title="Fill Color"
            style={{
              width: "100%",
              height: "28px",
              borderRadius: "6px",
              border: "2px solid rgba(255,255,255,0.2)",
              background:
                styles.fillColor === "transparent"
                  ? "repeating-linear-gradient(45deg, #374151, #374151 5px, #1f2937 5px, #1f2937 10px)"
                  : styles.fillColor,
              cursor: "pointer",
              position: "relative",
            }}
          >
            <span
              style={{
                position: "absolute",
                bottom: "-2px",
                right: "-2px",
                fontSize: "0.6em",
                background: "#1e293b",
                padding: "1px 3px",
                borderRadius: "3px",
              }}
            >
              🪣
            </span>
          </button>
        </div>

        {/* Color Picker Popup */}
        {showColorPicker && (
          <div
            style={{
              position: "absolute",
              left: "80px",
              top: "50%",
              transform: "translateY(-50%)",
              padding: "12px",
              background: "rgba(15, 23, 42, 0.98)",
              borderRadius: "12px",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
              zIndex: 1000,
              display: "grid",
              gridTemplateColumns: "repeat(5, 1fr)",
              gap: "6px",
            }}
          >
            {COLOR_PRESETS.map((color) => (
              <button
                key={color}
                onClick={() => handleColorSelect(color)}
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "6px",
                  border:
                    styles[
                      colorPickerType === "stroke" ? "strokeColor" : "fillColor"
                    ] === color
                      ? "2px solid #fff"
                      : "2px solid transparent",
                  background: color,
                  cursor: "pointer",
                }}
              />
            ))}
            {colorPickerType === "fill" && (
              <button
                onClick={() => handleColorSelect("transparent")}
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "6px",
                  border: "2px solid #ef4444",
                  background:
                    "repeating-linear-gradient(45deg, #374151, #374151 3px, #ef4444 3px, #ef4444 6px)",
                  cursor: "pointer",
                }}
                title="Transparent"
              />
            )}
          </div>
        )}
      </div>

      {/* Stroke Width */}
      <div>
        <div
          style={{
            fontSize: "0.65em",
            color: "#64748b",
            marginBottom: "4px",
            textAlign: "center",
          }}
        >
          SIZE: {styles.strokeWidth}px
        </div>
        <input
          type="range"
          min="1"
          max="20"
          value={styles.strokeWidth}
          onChange={handleStrokeWidthChange}
          style={{
            width: "100%",
            accentColor: "#6366f1",
          }}
        />
      </div>

      {/* Font Size (for Text mode) */}
      {mode === MODES.TEXT && (
        <div>
          <div
            style={{
              fontSize: "0.65em",
              color: "#64748b",
              marginBottom: "4px",
              textAlign: "center",
            }}
          >
            FONT: {styles.fontSize}px
          </div>
          <input
            type="range"
            min="12"
            max="72"
            value={styles.fontSize}
            onChange={handleFontSizeChange}
            style={{
              width: "100%",
              accentColor: "#22c55e",
            }}
          />
        </div>
      )}

      {/* Divider */}
      <div
        style={{
          height: "1px",
          background: "rgba(99, 102, 241, 0.2)",
          margin: "4px 0",
        }}
      />

      {/* Grid & Snap Options (CAD mode) */}
      {mode === MODES.CAD && (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <button
            onClick={onGridToggle}
            title="Toggle Grid"
            style={{
              padding: "8px",
              borderRadius: "8px",
              border: "none",
              background: gridEnabled
                ? "rgba(6, 182, 212, 0.3)"
                : "rgba(30, 41, 59, 0.5)",
              color: gridEnabled ? "#06b6d4" : "#64748b",
              cursor: "pointer",
              fontSize: "0.75em",
              fontWeight: "600",
            }}
          >
            🔲 Grid
          </button>
          <button
            onClick={onSnapToggle}
            title="Snap to Grid"
            style={{
              padding: "8px",
              borderRadius: "8px",
              border: "none",
              background: snapToGrid
                ? "rgba(6, 182, 212, 0.3)"
                : "rgba(30, 41, 59, 0.5)",
              color: snapToGrid ? "#06b6d4" : "#64748b",
              cursor: "pointer",
              fontSize: "0.75em",
              fontWeight: "600",
            }}
          >
            🧲 Snap
          </button>
        </div>
      )}

      {/* Divider */}
      <div
        style={{
          height: "1px",
          background: "rgba(99, 102, 241, 0.2)",
          margin: "4px 0",
        }}
      />

      {/* Actions */}
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <button
          onClick={onUndo}
          disabled={!canUndo}
          title="Undo (Ctrl+Z)"
          style={{
            padding: "8px",
            borderRadius: "8px",
            border: "none",
            background: canUndo
              ? "rgba(30, 41, 59, 0.5)"
              : "rgba(30, 41, 59, 0.2)",
            color: canUndo ? "#94a3b8" : "#475569",
            cursor: canUndo ? "pointer" : "not-allowed",
            fontSize: "1em",
          }}
        >
          ↩️
        </button>
        <button
          onClick={onRedo}
          disabled={!canRedo}
          title="Redo (Ctrl+Y)"
          style={{
            padding: "8px",
            borderRadius: "8px",
            border: "none",
            background: canRedo
              ? "rgba(30, 41, 59, 0.5)"
              : "rgba(30, 41, 59, 0.2)",
            color: canRedo ? "#94a3b8" : "#475569",
            cursor: canRedo ? "pointer" : "not-allowed",
            fontSize: "1em",
          }}
        >
          ↪️
        </button>
        <button
          onClick={onClear}
          title="Clear Canvas"
          style={{
            padding: "8px",
            borderRadius: "8px",
            border: "none",
            background: "rgba(239, 68, 68, 0.2)",
            color: "#ef4444",
            cursor: "pointer",
            fontSize: "1em",
          }}
        >
          🗑️
        </button>
      </div>

      {/* Divider */}
      <div
        style={{
          height: "1px",
          background: "rgba(99, 102, 241, 0.2)",
          margin: "4px 0",
        }}
      />

      {/* Export */}
      <div style={{ position: "relative" }}>
        <button
          onClick={() => setShowExportMenu(!showExportMenu)}
          title="Export"
          style={{
            width: "100%",
            padding: "10px 8px",
            borderRadius: "8px",
            border: "none",
            background: "linear-gradient(135deg, #22c55e, #16a34a)",
            color: "#fff",
            cursor: "pointer",
            fontSize: "0.75em",
            fontWeight: "600",
          }}
        >
          💾 Export
        </button>

        {showExportMenu && (
          <div
            style={{
              position: "absolute",
              left: "80px",
              bottom: "0",
              padding: "8px",
              background: "rgba(15, 23, 42, 0.98)",
              borderRadius: "12px",
              border: "1px solid rgba(34, 197, 94, 0.3)",
              boxShadow: "0 8px 32px rgba(0, 0, 0, 0.5)",
              zIndex: 1000,
              display: "flex",
              flexDirection: "column",
              gap: "4px",
              minWidth: "100px",
            }}
          >
            {["PNG", "SVG", "PDF", "DXF", "JSON"].map((format) => (
              <button
                key={format}
                onClick={() => {
                  onExport?.(format.toLowerCase());
                  setShowExportMenu(false);
                }}
                style={{
                  padding: "8px 12px",
                  borderRadius: "6px",
                  border: "none",
                  background: "rgba(30, 41, 59, 0.5)",
                  color: "#e2e8f0",
                  cursor: "pointer",
                  fontSize: "0.8em",
                  textAlign: "left",
                }}
              >
                📄 {format}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Import */}
      <button
        onClick={onImport}
        title="Import Image"
        style={{
          width: "100%",
          padding: "10px 8px",
          borderRadius: "8px",
          border: "none",
          background: "rgba(99, 102, 241, 0.2)",
          color: "#a5b4fc",
          cursor: "pointer",
          fontSize: "0.75em",
          fontWeight: "600",
        }}
      >
        📥 Import
      </button>
    </div>
  );
};

export { MODES };
export default ToolsToolbar;
