import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import axios from "axios";

const CommunicationsConsole = ({ isOpen, onToggle, apiUrl }) => {
  const backendUrl = apiUrl || "http://127.0.0.1:65252";

  const companyBoard = useMemo(
    () => ({
      mission:
        "Build long-term online income by shipping tools and automations that convert web opportunities into measurable revenue.",
      vision:
        "A disciplined, agent-led online company that compounds audience growth into sustainable wealth.",
      leadership: [
        {
          title: "Chairman & Owner",
          name: "Darrell Buttigieg",
          focus: "Overall ownership, governance, and long-term direction.",
        },
        {
          title: "CEO",
          name: "Amigos CEO Agent",
          focus:
            "Profitability, clear mission/vision, identifying current Facebook + YouTube opportunities for Darrell Buttigieg, and ensuring agent upkeep + performance tracking.",
        },
        {
          title: "AI Strategy",
          name: "Amigos AI Core",
          focus:
            "Ensure CEO meetings with agents; convert insights into objectives and execution plans.",
        },
        {
          title: "Workflow Operations",
          name: "OpenWork Agent",
          focus:
            "Runs structured workflows, tracks execution, and escalates blockers.",
        },
      ],
      topPriorities: [
        "Darrell Buttigieg Facebook growth opportunities",
        "Darrell Buttigieg YouTube growth opportunities",
        "Social media growth & consistency (Top 5 priority)",
        "Revenue systems: offers, funnels, and conversion tracking",
        "Agent-built tools that produce long-term online income",
      ],
    }),
    [],
  );

  const [activeTab, setActiveTab] = useState("timeline");
  const [filterMode, setFilterMode] = useState("amigos");
  const [events, setEvents] = useState([]);
  const [topContacts, setTopContacts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null);

  // Draggable/Resizable state
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-comms-console-pos");
      return saved ? JSON.parse(saved) : { x: 260, y: 120 };
    } catch {
      return { x: 260, y: 120 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-comms-console-size");
      return saved ? JSON.parse(saved) : { width: 520, height: 560 };
    } catch {
      return { width: 520, height: 560 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("amigos-comms-console-pos", JSON.stringify(position));
  }, [position]);

  useEffect(() => {
    localStorage.setItem("amigos-comms-console-size", JSON.stringify(size));
  }, [size]);

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
          width: Math.max(420, e.clientX - rect.left + 10),
          height: Math.max(380, e.clientY - rect.top + 10),
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

  const fetchComms = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await axios.get(`${backendUrl}/agents/communications`, {
        params: {
          limit: 60,
          top_agent: "amigos",
          top_limit: 5,
        },
      });
      const data = response.data?.data || {};
      setEvents(data.events || []);
      setTopContacts(data.top_contacts || []);
      setLastUpdatedAt(new Date());
    } catch (err) {
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Failed to load communications.",
      );
    } finally {
      setLoading(false);
    }
  }, [backendUrl]);

  useEffect(() => {
    if (!isOpen) return;
    fetchComms();
    const interval = setInterval(fetchComms, 6000);
    return () => clearInterval(interval);
  }, [isOpen, fetchComms]);

  const filteredEvents = useMemo(() => {
    if (filterMode === "all") return events;
    return events.filter((e) => e.from === "amigos" || e.to === "amigos");
  }, [events, filterMode]);

  const formatTime = (isoString) => {
    if (!isoString) return "—";
    const date = new Date(isoString);
    return date.toLocaleTimeString("en-AU", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  };

  const tabBtn = (key) => ({
    flex: 1,
    padding: "10px 8px",
    background: activeTab === key ? "rgba(59, 130, 246, 0.2)" : "transparent",
    border: "none",
    borderBottom:
      activeTab === key
        ? "2px solid rgba(59, 130, 246, 0.9)"
        : "2px solid transparent",
    color: activeTab === key ? "#93c5fd" : "#94a3b8",
    cursor: "pointer",
    fontSize: "0.8em",
    fontWeight: activeTab === key ? 600 : 400,
  });

  const card = {
    padding: "14px",
    borderRadius: "12px",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    background: "rgba(15, 23, 42, 0.6)",
    backdropFilter: "blur(10px)",
    marginBottom: "12px",
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
        backgroundColor: "rgba(11, 11, 21, 0.97)",
        backdropFilter: "blur(20px)",
        borderRadius: "16px",
        border: "1px solid rgba(59, 130, 246, 0.5)",
        boxShadow:
          "0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(59, 130, 246, 0.15)",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        color: "#e5e7eb",
        fontFamily: "'Inter', sans-serif",
        cursor: isDragging ? "grabbing" : "default",
      }}
    >
      <div
        onMouseDown={handleMouseDown}
        style={{
          padding: "14px 18px",
          borderBottom: "1px solid rgba(59, 130, 246, 0.2)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background:
            "linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.15))",
          cursor: "grab",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              borderRadius: "12px",
              background: "linear-gradient(135deg, #60a5fa, #3b82f6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.3em",
              boxShadow: "0 8px 25px rgba(59, 130, 246, 0.4)",
            }}
          >
            📡
          </div>
          <div>
            <div style={{ fontWeight: "700", fontSize: "1em", color: "#fff" }}>
              Communications
            </div>
            <div style={{ fontSize: "0.7em", color: "#94a3b8" }}>
              Who is talking to who • Top 5 for Amigos
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
        }}
      >
        <button
          style={tabBtn("timeline")}
          onClick={() => setActiveTab("timeline")}
        >
          💬 Timeline
        </button>
        <button style={tabBtn("top5")} onClick={() => setActiveTab("top5")}>
          ⭐ Top 5
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
        {error && (
          <div
            style={{
              ...card,
              borderColor: "rgba(239, 68, 68, 0.5)",
              color: "#fca5a5",
              fontSize: "0.85em",
            }}
          >
            {error}
          </div>
        )}

        {loading && (
          <div style={{ ...card, textAlign: "center", color: "#94a3b8" }}>
            Loading communications...
          </div>
        )}

        <div
          style={{
            ...card,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "12px",
            flexWrap: "wrap",
          }}
        >
          <div>
            <div style={{ fontWeight: 600, color: "#93c5fd" }}>
              Live Signal Stream
            </div>
            <div style={{ fontSize: "0.75em", color: "#94a3b8" }}>
              {lastUpdatedAt
                ? `Updated ${lastUpdatedAt.toLocaleTimeString()}`
                : "Awaiting first refresh"}
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <select
              value={filterMode}
              onChange={(e) => setFilterMode(e.target.value)}
              style={{
                padding: "6px 10px",
                borderRadius: "8px",
                border: "1px solid rgba(148, 163, 184, 0.4)",
                background: "rgba(15, 23, 42, 0.8)",
                color: "#e2e8f0",
                fontSize: "0.75em",
              }}
            >
              <option value="amigos">Amigos only</option>
              <option value="all">All agents</option>
            </select>
            <button
              onClick={fetchComms}
              style={{
                padding: "6px 12px",
                borderRadius: "8px",
                border: "1px solid rgba(59, 130, 246, 0.5)",
                background: "rgba(59, 130, 246, 0.15)",
                color: "#93c5fd",
                cursor: "pointer",
                fontSize: "0.75em",
              }}
            >
              Refresh
            </button>
          </div>
        </div>

        {activeTab === "timeline" && (
          <>
            {filteredEvents.length === 0 ? (
              <div style={{ ...card, textAlign: "center", color: "#94a3b8" }}>
                No communications logged yet.
              </div>
            ) : (
              filteredEvents
                .slice()
                .reverse()
                .map((event, idx) => (
                  <div key={`${event.timestamp || idx}-${idx}`} style={card}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "8px",
                      }}
                    >
                      <div style={{ fontWeight: 600, color: "#fff" }}>
                        {String(event.from || "?").toUpperCase()} →{" "}
                        {String(event.to || "?").toUpperCase()}
                      </div>
                      <div style={{ fontSize: "0.7em", color: "#94a3b8" }}>
                        {formatTime(event.timestamp)}
                      </div>
                    </div>
                    <div
                      style={{
                        display: "flex",
                        gap: "8px",
                        flexWrap: "wrap",
                        alignItems: "center",
                        marginBottom: "6px",
                      }}
                    >
                      <span
                        style={{
                          padding: "2px 8px",
                          borderRadius: "999px",
                          background: "rgba(59, 130, 246, 0.15)",
                          border: "1px solid rgba(59, 130, 246, 0.4)",
                          fontSize: "0.7em",
                          color: "#93c5fd",
                          textTransform: "uppercase",
                          letterSpacing: "0.04em",
                        }}
                      >
                        {event.channel || "message"}
                      </span>
                      {event.payload?.collab_id && (
                        <span
                          style={{
                            padding: "2px 8px",
                            borderRadius: "999px",
                            background: "rgba(148, 163, 184, 0.1)",
                            border: "1px solid rgba(148, 163, 184, 0.3)",
                            fontSize: "0.7em",
                            color: "#cbd5e1",
                          }}
                        >
                          {event.payload.collab_id}
                        </span>
                      )}
                    </div>
                    {event.summary && (
                      <div style={{ fontSize: "0.85em", color: "#e2e8f0" }}>
                        {event.summary}
                      </div>
                    )}
                  </div>
                ))
            )}
          </>
        )}

        {activeTab === "top5" && (
          <>
            <div style={card}>
              <div style={{ fontWeight: 700, color: "#fff" }}>
                Company Communication Board
              </div>
              <div style={{ fontSize: "0.75em", color: "#94a3b8" }}>
                Mission, vision, and top 5 priorities
              </div>
              <div style={{ marginTop: "12px", fontSize: "0.85em" }}>
                <div style={{ color: "#93c5fd", fontWeight: 600 }}>Mission</div>
                <div style={{ color: "#e2e8f0", marginBottom: "10px" }}>
                  {companyBoard.mission}
                </div>
                <div style={{ color: "#93c5fd", fontWeight: 600 }}>Vision</div>
                <div style={{ color: "#e2e8f0", marginBottom: "10px" }}>
                  {companyBoard.vision}
                </div>
                <div style={{ color: "#93c5fd", fontWeight: 600 }}>
                  Top 5 Priorities
                </div>
                <ol style={{ margin: "8px 0 12px 18px", color: "#e2e8f0" }}>
                  {companyBoard.topPriorities.map((item) => (
                    <li key={item} style={{ marginBottom: "6px" }}>
                      {item}
                    </li>
                  ))}
                </ol>
                <div style={{ color: "#93c5fd", fontWeight: 600 }}>
                  Leadership Focus
                </div>
                <div style={{ display: "grid", gap: "8px", marginTop: "8px" }}>
                  {companyBoard.leadership.map((leader) => (
                    <div
                      key={leader.title}
                      style={{
                        padding: "8px 10px",
                        borderRadius: "10px",
                        background: "rgba(15, 23, 42, 0.8)",
                        border: "1px solid rgba(148, 163, 184, 0.2)",
                      }}
                    >
                      <div style={{ fontWeight: 600, color: "#fff" }}>
                        {leader.title}: {leader.name}
                      </div>
                      <div style={{ fontSize: "0.75em", color: "#cbd5e1" }}>
                        {leader.focus}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            {topContacts.length === 0 ? (
              <div style={{ ...card, textAlign: "center", color: "#94a3b8" }}>
                No top contacts yet.
              </div>
            ) : (
              topContacts.map((item, idx) => (
                <div key={`${item.agent}-${idx}`} style={card}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div style={{ fontWeight: 600, color: "#fff" }}>
                      {String(item.agent || "?").toUpperCase()}
                    </div>
                    <div style={{ fontSize: "0.8em", color: "#93c5fd" }}>
                      {item.count} interactions
                    </div>
                  </div>
                  <div
                    style={{
                      marginTop: "8px",
                      height: "6px",
                      background: "rgba(255,255,255,0.08)",
                      borderRadius: "999px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        height: "100%",
                        width: `${Math.min(100, (item.count || 0) * 10)}%`,
                        background: "linear-gradient(90deg, #60a5fa, #3b82f6)",
                        borderRadius: "999px",
                      }}
                    />
                  </div>
                </div>
              ))
            )}
          </>
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
          background: "linear-gradient(135deg, transparent 50%, #60a5fa 50%)",
          borderRadius: "0 0 16px 0",
        }}
        onMouseDown={(e) => {
          e.stopPropagation();
          setIsResizing(true);
        }}
      />
    </div>
  );
};

export default CommunicationsConsole;
