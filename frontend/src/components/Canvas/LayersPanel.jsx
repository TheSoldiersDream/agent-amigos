/**
 * 🧠🎨 Agent Amigos Canvas - Layers Panel
 *
 * Layer management for organizing drawing elements.
 * Supports visibility toggle, reordering, and layer-specific operations.
 *
 * Created by Darrell Buttigieg (@darrellbuttigieg) #thesoldiersdream
 */

import React, { useState } from "react";

const DEFAULT_LAYERS = [
  {
    id: "background",
    name: "🖼️ Background",
    visible: true,
    locked: false,
    color: "#64748b",
  },
  {
    id: "sketch",
    name: "✏️ Sketch",
    visible: true,
    locked: false,
    color: "#ec4899",
  },
  {
    id: "diagram",
    name: "📊 Diagram",
    visible: true,
    locked: false,
    color: "#8b5cf6",
  },
  { id: "cad", name: "📐 CAD", visible: true, locked: false, color: "#06b6d4" },
  {
    id: "text",
    name: "📝 Text",
    visible: true,
    locked: false,
    color: "#22c55e",
  },
  {
    id: "media",
    name: "🎬 Media",
    visible: true,
    locked: false,
    color: "#f59e0b",
  },
  {
    id: "annotations",
    name: "💬 Annotations",
    visible: true,
    locked: false,
    color: "#f97316",
  },
  {
    id: "ai_assist_layer",
    name: "🧠 AI Assist",
    visible: true,
    locked: false,
    color: "#a78bfa",
  },
];

const LayersPanel = ({
  layers = DEFAULT_LAYERS,
  activeLayerId = "sketch",
  onLayerSelect,
  onLayerVisibilityToggle,
  onLayerLockToggle,
  onLayerAdd,
  onLayerDelete,
  onLayerRename,
  onLayerReorder,
  onLayersChange,
  collapsed = false,
  onToggleCollapse,
}) => {
  const [editingLayerId, setEditingLayerId] = useState(null);
  const [editName, setEditName] = useState("");
  const [draggedLayerId, setDraggedLayerId] = useState(null);

  const handleStartRename = (layer) => {
    setEditingLayerId(layer.id);
    setEditName(layer.name);
  };

  const handleFinishRename = (layerId) => {
    if (editName.trim()) {
      onLayerRename?.(layerId, editName.trim());
    }
    setEditingLayerId(null);
    setEditName("");
  };

  const handleAddLayer = () => {
    const newLayer = {
      id: `layer_${Date.now()}`,
      name: `🎨 Layer ${layers.length + 1}`,
      visible: true,
      locked: false,
      color: "#94a3b8",
    };
    onLayerAdd?.(newLayer);
  };

  const handleDragStart = (e, layerId) => {
    setDraggedLayerId(layerId);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e, layerId) => {
    e.preventDefault();
    if (draggedLayerId && draggedLayerId !== layerId) {
      const dragIndex = layers.findIndex((l) => l.id === draggedLayerId);
      const hoverIndex = layers.findIndex((l) => l.id === layerId);

      if (dragIndex !== hoverIndex) {
        const newLayers = [...layers];
        const [removed] = newLayers.splice(dragIndex, 1);
        newLayers.splice(hoverIndex, 0, removed);
        onLayersChange?.(newLayers);
      }
    }
  };

  const handleDragEnd = () => {
    setDraggedLayerId(null);
  };

  if (collapsed) {
    return (
      <button
        onClick={onToggleCollapse}
        style={{
          position: "absolute",
          right: "10px",
          top: "50%",
          transform: "translateY(-50%)",
          padding: "12px 8px",
          background: "rgba(15, 23, 42, 0.95)",
          border: "1px solid rgba(99, 102, 241, 0.3)",
          borderRadius: "8px 0 0 8px",
          color: "#a5b4fc",
          cursor: "pointer",
          fontSize: "1.2em",
          backdropFilter: "blur(10px)",
        }}
        title="Show Layers"
      >
        📑
      </button>
    );
  }

  return (
    <div
      style={{
        width: "200px",
        height: "100%",
        background: "rgba(15, 23, 42, 0.95)",
        backdropFilter: "blur(20px)",
        borderLeft: "1px solid rgba(99, 102, 241, 0.2)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid rgba(99, 102, 241, 0.2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span
          style={{ color: "#e2e8f0", fontWeight: "600", fontSize: "0.9em" }}
        >
          📑 Layers
        </span>
        <div style={{ display: "flex", gap: "6px" }}>
          <button
            onClick={handleAddLayer}
            title="Add Layer"
            style={{
              padding: "4px 8px",
              borderRadius: "4px",
              border: "none",
              background: "rgba(34, 197, 94, 0.2)",
              color: "#22c55e",
              cursor: "pointer",
              fontSize: "0.8em",
            }}
          >
            +
          </button>
          <button
            onClick={onToggleCollapse}
            title="Hide Layers Panel"
            style={{
              padding: "4px 8px",
              borderRadius: "4px",
              border: "none",
              background: "rgba(99, 102, 241, 0.2)",
              color: "#a5b4fc",
              cursor: "pointer",
              fontSize: "0.8em",
            }}
          >
            ◀
          </button>
        </div>
      </div>

      {/* Layers List */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px",
        }}
      >
        {layers.map((layer, index) => (
          <div
            key={layer.id}
            draggable
            onDragStart={(e) => handleDragStart(e, layer.id)}
            onDragOver={(e) => handleDragOver(e, layer.id)}
            onDragEnd={handleDragEnd}
            onClick={() => onLayerSelect?.(layer.id)}
            style={{
              padding: "10px 12px",
              marginBottom: "6px",
              borderRadius: "8px",
              background:
                activeLayerId === layer.id
                  ? `linear-gradient(135deg, ${layer.color}30, ${layer.color}15)`
                  : "rgba(30, 41, 59, 0.5)",
              border:
                activeLayerId === layer.id
                  ? `1px solid ${layer.color}50`
                  : "1px solid transparent",
              cursor: "pointer",
              opacity: layer.visible ? 1 : 0.5,
              transition: "all 0.2s ease",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {/* Drag Handle */}
            <span
              style={{
                color: "#475569",
                fontSize: "0.8em",
                cursor: "grab",
              }}
            >
              ⋮⋮
            </span>

            {/* Layer Color Indicator */}
            <div
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "3px",
                background: layer.color,
                flexShrink: 0,
              }}
            />

            {/* Layer Name */}
            {editingLayerId === layer.id ? (
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onBlur={() => handleFinishRename(layer.id)}
                onKeyDown={(e) =>
                  e.key === "Enter" && handleFinishRename(layer.id)
                }
                autoFocus
                style={{
                  flex: 1,
                  padding: "4px 6px",
                  background: "rgba(0, 0, 0, 0.3)",
                  border: "1px solid rgba(99, 102, 241, 0.5)",
                  borderRadius: "4px",
                  color: "#e2e8f0",
                  fontSize: "0.8em",
                  outline: "none",
                }}
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <span
                onDoubleClick={(e) => {
                  e.stopPropagation();
                  handleStartRename(layer);
                }}
                style={{
                  flex: 1,
                  color: activeLayerId === layer.id ? "#e2e8f0" : "#94a3b8",
                  fontSize: "0.8em",
                  fontWeight: activeLayerId === layer.id ? "600" : "400",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {layer.name}
              </span>
            )}

            {/* Layer Actions */}
            <div style={{ display: "flex", gap: "4px", flexShrink: 0 }}>
              {/* Visibility Toggle */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onLayerVisibilityToggle?.(layer.id);
                }}
                title={layer.visible ? "Hide Layer" : "Show Layer"}
                style={{
                  padding: "4px",
                  borderRadius: "4px",
                  border: "none",
                  background: "transparent",
                  color: layer.visible ? "#22c55e" : "#64748b",
                  cursor: "pointer",
                  fontSize: "0.85em",
                }}
              >
                {layer.visible ? "👁️" : "👁️‍🗨️"}
              </button>

              {/* Lock Toggle */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onLayerLockToggle?.(layer.id);
                }}
                title={layer.locked ? "Unlock Layer" : "Lock Layer"}
                style={{
                  padding: "4px",
                  borderRadius: "4px",
                  border: "none",
                  background: "transparent",
                  color: layer.locked ? "#f59e0b" : "#64748b",
                  cursor: "pointer",
                  fontSize: "0.85em",
                }}
              >
                {layer.locked ? "🔒" : "🔓"}
              </button>

              {/* Delete (not for default layers) */}
              {![
                "background",
                "sketch",
                "diagram",
                "cad",
                "text",
                "media",
                "annotations",
              ].includes(layer.id) && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onLayerDelete?.(layer.id);
                  }}
                  title="Delete Layer"
                  style={{
                    padding: "4px",
                    borderRadius: "4px",
                    border: "none",
                    background: "transparent",
                    color: "#ef4444",
                    cursor: "pointer",
                    fontSize: "0.85em",
                  }}
                >
                  🗑️
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Footer Info */}
      <div
        style={{
          padding: "10px 12px",
          borderTop: "1px solid rgba(99, 102, 241, 0.2)",
          fontSize: "0.7em",
          color: "#64748b",
          textAlign: "center",
        }}
      >
        {layers.length} layers • Double-click to rename
      </div>
    </div>
  );
};

export { DEFAULT_LAYERS };
export default LayersPanel;
