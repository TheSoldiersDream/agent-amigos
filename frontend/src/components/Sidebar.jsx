/**
 * 🎛️ Agent Amigos - Left Sidebar
 * Collapsible navigation sidebar with all console/tool buttons
 */

import React, { useState } from "react";

const SIDEBAR_ITEMS = [
  { id: "company", icon: "🏛️", label: "Executive Suite", color: "#10b981" },
  { id: "chat", icon: "💬", label: "Executive Chat", color: "#6366f1" },
  { id: "openwork", icon: "🔧", label: "Governance & Ops", color: "#8b5cf6" },
  { id: "finance", icon: "📊", label: "P&L Dashboard", color: "#f59e0b" },
  { id: "scraper", icon: "🕷️", label: "Market Research", color: "#8b5cf6" },
  { id: "post", icon: "📝", label: "Revenue Content", color: "#a855f7" },
  { id: "internet", icon: "🌐", label: "Acquisition Bot", color: "#3b82f6" },
  { id: "macro", icon: "🤖", label: "Automations", color: "#f97316" },
  { id: "canvas", icon: "🎨", label: "Product Design", color: "#06b6d4" },
  { id: "media", icon: "🎬", label: "Media Assets", color: "#ec4899" },
  { id: "files", icon: "📁", label: "Corporate Assets", color: "#14b8a6" },
  { id: "comms", icon: "📡", label: "Outreach Bot", color: "#3b82f6" },
  { id: "avatar", icon: "👤", label: "AI Representative", color: "#f472b6" },
];

const Sidebar = ({
  collapsed = false,
  onToggle,
  activeItems = {},
  onItemClick,
  onItemDetach,
}) => {
  const [hoveredItem, setHoveredItem] = useState(null);
  const detachableItems = new Set([
    "canvas",
    "openwork",
    "scraper",
    "macro",
    "internet",
    "map",
    "weather",
    "finance",
    "media",
    "game",
    "files",
    "itinerary",
    "comms",
    "company",
    "post",
    "avatar",
  ]);

  return (
    <div
      style={{
        position: "fixed",
        left: 0,
        top: "72px",
        bottom: 0,
        width: collapsed ? "68px" : "220px",
        background: "var(--glass-bg)",
        backdropFilter: "blur(20px)",
        borderRight: "var(--glass-border)",
        display: "flex",
        flexDirection: "column",
        padding: "16px 12px",
        gap: "6px",
        transition: "width var(--anim-speed) var(--anim-curve)",
        zIndex: 500,
        overflowY: "auto",
        overflowX: "hidden",
      }}
    >
      {/* Collapse Toggle */}
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          padding: "10px",
          background: "rgba(255, 255, 255, 0.03)",
          border: "var(--glass-border)",
          borderRadius: "12px",
          color: "var(--text-secondary)",
          cursor: "pointer",
          fontSize: "0.75rem",
          fontWeight: "700",
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          marginBottom: "16px",
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "space-between",
          transition: "all 0.2s ease",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.borderColor = "var(--border-accent)";
          e.currentTarget.style.color = "var(--text-primary)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.borderColor = "rgba(255,255,255,0.08)";
          e.currentTarget.style.color = "var(--text-secondary)";
        }}
      >
        {!collapsed && <span>DEPARTMENTS</span>}
        <span style={{ fontSize: "1.2em" }}>{collapsed ? "»" : "«"}</span>
      </button>

      {/* Sidebar Items */}
      {SIDEBAR_ITEMS.map((item) => {
        const isActive = activeItems[item.id];
        const isHovered = hoveredItem === item.id;

        return (
          <button
            key={item.id}
            onClick={() => onItemClick(item.id)}
            onMouseEnter={() => setHoveredItem(item.id)}
            onMouseLeave={() => setHoveredItem(null)}
            style={{
              width: "100%",
              padding: collapsed ? "12px" : "12px 14px",
              background: isActive
                ? `linear-gradient(135deg, ${item.color}25, ${item.color}10)`
                : isHovered
                  ? "rgba(255, 255, 255, 0.05)"
                  : "transparent",
              border: isActive
                ? `1px solid ${item.color}50`
                : "1px solid transparent",
              borderRadius: "12px",
              color: isActive ? "#fff" : "var(--text-secondary)",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: isActive ? "700" : "500",
              display: "flex",
              alignItems: "center",
              justifyContent: collapsed ? "center" : "flex-start",
              gap: "12px",
              transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
              position: "relative",
              overflow: "hidden",
            }}
            title={collapsed ? item.label : undefined}
          >
            <span
              style={{
                fontSize: "1.2rem",
                filter: isActive
                  ? `drop-shadow(0 0 8px ${item.color}60)`
                  : "none",
              }}
            >
              {item.icon}
            </span>
            {!collapsed && (
              <span style={{ letterSpacing: "0.01em" }}>{item.label}</span>
            )}
            {!collapsed && onItemDetach && detachableItems.has(item.id) && (
              <span
                role="button"
                tabIndex={0}
                onClick={(e) => {
                  e.stopPropagation();
                  onItemDetach(item.id);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    e.stopPropagation();
                    onItemDetach(item.id);
                  }
                }}
                style={{
                  marginLeft: "auto",
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  color: "var(--text-muted)",
                  borderRadius: "6px",
                  width: "24px",
                  height: "24px",
                  cursor: "pointer",
                  fontSize: "0.7rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: isHovered ? 1 : 0,
                  transition: "opacity 0.2s ease",
                }}
                title={`Detach ${item.label}`}
                aria-label={`Detach ${item.label}`}
              >
                ↗
              </span>
            )}
            {isActive && (
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: "20%",
                  height: "60%",
                  width: "3px",
                  background: item.color,
                  borderRadius: "0 4px 4px 0",
                  boxShadow: `0 0 10px ${item.color}`,
                }}
              />
            )}
          </button>
        );
      })}

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Settings at bottom */}
      <button
        onClick={() => onItemClick("settings")}
        style={{
          width: "100%",
          padding: collapsed ? "12px" : "12px 14px",
          background: "rgba(255, 255, 255, 0.03)",
          border: "var(--glass-border)",
          borderRadius: "12px",
          color: "var(--text-secondary)",
          cursor: "pointer",
          fontSize: "0.85rem",
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "flex-start",
          gap: "12px",
          transition: "all 0.2s ease",
        }}
        title={collapsed ? "Settings" : undefined}
      >
        <span style={{ fontSize: "1.2rem" }}>⚙️</span>
        {!collapsed && <span style={{ fontWeight: "600" }}>Settings</span>}
      </button>
    </div>
  );
};

export default Sidebar;
