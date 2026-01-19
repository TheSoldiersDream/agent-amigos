import React, { useEffect, useState, useRef } from "react";
import axios from "axios";

const EmailItineraryConsole = ({ isOpen, onToggle, apiUrl }) => {
  const [rawEmail, setRawEmail] = useState("");
  const [autosave, setAutosave] = useState(true);
  const [itineraries, setItineraries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [lastParse, setLastParse] = useState(null);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [combinedSummary, setCombinedSummary] = useState("");

  // Draggable & Resizable State
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-itinerary-console-pos");
      return saved ? JSON.parse(saved) : { x: -1, y: -1 };
    } catch {
      return { x: -1, y: -1 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-itinerary-console-size");
      return saved ? JSON.parse(saved) : { width: 560, height: 520 };
    } catch {
      return { width: 560, height: 520 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  useEffect(() => {
    if (position.x !== -1 && position.y !== -1) {
      localStorage.setItem(
        "amigos-itinerary-console-pos",
        JSON.stringify(position)
      );
    }
  }, [position]);

  useEffect(() => {
    localStorage.setItem("amigos-itinerary-console-size", JSON.stringify(size));
  }, [size]);

  useEffect(() => {
    if (isOpen && position.x === -1) {
      setPosition({
        x: window.innerWidth - size.width - 24,
        y: window.innerHeight - size.height - 24,
      });
    }
  }, [isOpen]);

  const handleDragStart = (e) => {
    if (
      e.target.closest(".resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("input") ||
      e.target.closest("textarea")
    )
      return;
    setIsDragging(true);
    const rect = containerRef.current.getBoundingClientRect();
    setDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
  };

  useEffect(() => {
    if (!isDragging) return;
    const handleMouseMove = (e) => {
      const newX = Math.max(
        0,
        Math.min(window.innerWidth - size.width, e.clientX - dragOffset.x)
      );
      const newY = Math.max(
        0,
        Math.min(window.innerHeight - size.height, e.clientY - dragOffset.y)
      );
      setPosition({ x: newX, y: newY });
    };
    const handleMouseUp = () => setIsDragging(false);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, dragOffset, size]);

  const handleResizeStart = (e) => {
    e.stopPropagation();
    setIsResizing(true);
  };

  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e) => {
      const newWidth = Math.max(400, Math.min(1000, e.clientX - position.x));
      const newHeight = Math.max(300, Math.min(800, e.clientY - position.y));
      setSize({ width: newWidth, height: newHeight });
    };
    const handleMouseUp = () => setIsResizing(false);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing, position]);

  const fetchItineraries = async () => {
    const computeAndSetDateRange = (list) => {
      if (!Array.isArray(list) || list.length === 0) return;
      let minDate = null;
      let maxDate = null;
      list.forEach((it) => {
        if (it.start_date) {
          const d = it.start_date.split("T")[0];
          if (!minDate || d < minDate) minDate = d;
        }
        if (it.end_date) {
          const d = it.end_date.split("T")[0];
          if (!maxDate || d > maxDate) maxDate = d;
        }
        // Also check segments just in case
        it.segments?.forEach((seg) => {
          if (seg.start_date) {
            const d = seg.start_date.split("T")[0];
            if (!minDate || d < minDate) minDate = d;
          }
          if (seg.end_date) {
            const d = seg.end_date.split("T")[0];
            if (!maxDate || d > maxDate) maxDate = d;
          }
        });
      });
      if (minDate) setFromDate(minDate);
      if (maxDate) setToDate(maxDate);
    };

    try {
      // Primary endpoint
      const res = await axios.get(`${apiUrl}/itineraries`);
      let list = res.data?.itineraries || res.data || [];
      // Handle case where server returned a single itinerary
      if (!Array.isArray(list) && list?.itinerary) list = [list.itinerary];
      setItineraries(list);
      computeAndSetDateRange(list);
    } catch (primaryErr) {
      // Fallback endpoint for older/alternate servers
      try {
        const res2 = await axios.get(`${apiUrl}/agent/itineraries`);
        let list2 = res2.data?.itineraries || res2.data || [];
        if (!Array.isArray(list2) && list2?.itinerary)
          list2 = [list2.itinerary];
        setItineraries(list2);
        computeAndSetDateRange(list2);
      } catch (fallbackErr) {
        console.error("Itinerary fetch error", primaryErr, fallbackErr);
      }
    }
  };

  useEffect(() => {
    if (isOpen) fetchItineraries();
  }, [isOpen]);

  // Auto-generate summary when itineraries or dates change
  useEffect(() => {
    if (itineraries.length > 0 && fromDate && toDate) {
      handleGenerateSummary();
    }
  }, [itineraries, fromDate, toDate]);

  const handleParse = async () => {
    if (!rawEmail.trim()) return;
    setLoading(true);
    try {
      const res = await axios.post(`${apiUrl}/email_monitor/parse_sample`, {
        raw_email: rawEmail,
        autosave,
      });
      setLastParse(res.data.itinerary);
      if (res.data.status === "saved") {
        setRawEmail("");
        await fetchItineraries();
      }
    } catch (err) {
      console.error("Parse error", err);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = (trip_id) => {
    window.open(`${apiUrl}/itineraries/${trip_id}/export.ics`, "_blank");
  };

  const handleDelete = async (trip_id) => {
    try {
      await axios.post(`${apiUrl}/itineraries/${trip_id}/delete`);
      await fetchItineraries();
    } catch (err) {
      console.error("Delete failed", err);
    }
  };

  const handleGenerateSummary = async () => {
    try {
      const res = await axios.get(`${apiUrl}/itineraries/summary`, {
        params: { from_date: fromDate, to_date: toDate },
      });
      setCombinedSummary(res.data.summary);
    } catch (err) {
      console.error("Summary error", err);
    }
  };

  const handleDownloadCombined = () => {
    const url = `${apiUrl}/itineraries/combined.ics?from_date=${fromDate}&to_date=${toDate}`;
    window.open(url, "_blank");
  };

  if (!isOpen)
    return (
      <button
        onClick={onToggle}
        style={{
          position: "fixed",
          right: "20px",
          bottom: "140px",
          zIndex: 1200,
        }}
      >
        ✈️ Itineraries
      </button>
    );

  return (
    <div
      ref={containerRef}
      onMouseDown={handleDragStart}
      style={{
        position: "fixed",
        left: position.x,
        top: position.y,
        width: size.width,
        height: size.height,
        zIndex: 2000,
        cursor: isDragging ? "grabbing" : "default",
      }}
    >
      <div
        style={{
          padding: 12,
          background: "#0b0b16",
          borderRadius: 12,
          boxShadow: "0 10px 40px rgba(0,0,0,0.6)",
          border: "1px solid rgba(99,102,241,0.12)",
          display: "flex",
          flexDirection: "column",
          height: "100%",
          position: "relative",
        }}
      >
        {/* Resize Handle */}
        <div
          className="resize-handle"
          onMouseDown={handleResizeStart}
          style={{
            position: "absolute",
            right: 0,
            bottom: 0,
            width: 20,
            height: 20,
            cursor: "nwse-resize",
            zIndex: 10,
            background:
              "linear-gradient(135deg, transparent 50%, rgba(99,102,241,0.4) 50%)",
            borderRadius: "0 0 12px 0",
          }}
        />

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 10,
            cursor: "grab",
          }}
        >
          <h3 style={{ margin: 0 }}>✈️ Email Itineraries</h3>
          <div>
            <label style={{ marginRight: 8 }}>
              <input
                type="checkbox"
                checked={autosave}
                onChange={(e) => setAutosave(e.target.checked)}
              />{" "}
              Auto-save
            </label>
            <button onClick={onToggle} style={{ marginLeft: 8 }}>
              Close
            </button>
          </div>
        </div>

        <textarea
          value={rawEmail}
          onChange={(e) => setRawEmail(e.target.value)}
          placeholder="Paste full email text here"
          style={{
            height: 80,
            minHeight: 80,
            marginBottom: 8,
            padding: 8,
            borderRadius: 8,
            background: "#0f1724",
            color: "#e5e7eb",
            border: "1px solid #2b3446",
            resize: "none",
          }}
        />
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <button
            onClick={handleParse}
            disabled={loading}
            style={{
              padding: "8px 16px",
              background: "#6366f1",
              color: "white",
              border: "none",
              borderRadius: 6,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {loading ? "Parsing..." : "Parse & Save"}
          </button>
          <button
            onClick={() => {
              setRawEmail("");
              setLastParse(null);
            }}
            style={{
              padding: "8px 12px",
              background: "transparent",
              border: "1px solid #334155",
              color: "#94a3b8",
              borderRadius: 6,
            }}
          >
            Clear
          </button>
          {lastParse && (
            <div
              style={{ marginLeft: 12, color: "#10b981", fontSize: "0.9em" }}
            >
              ✅ Saved: {lastParse?.summary || "Itinerary"}
            </div>
          )}
        </div>

        <div
          style={{
            overflow: "auto",
            flex: 1,
            padding: "0 4px",
            background: "#05050a",
            borderRadius: 8,
            marginBottom: 12,
            border: "1px solid rgba(255,255,255,0.05)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "8px 4px",
              position: "sticky",
              top: 0,
              background: "#05050a",
              zIndex: 5,
            }}
          >
            <h4 style={{ margin: 0, fontSize: "0.9em", color: "#94a3b8" }}>
              Saved Itineraries ({itineraries.length})
            </h4>
            <button
              onClick={fetchItineraries}
              style={{ fontSize: "0.7em", padding: "2px 6px" }}
            >
              Refresh
            </button>
          </div>
          {itineraries.length === 0 && (
            <div style={{ color: "#475569", padding: 10, textAlign: "center" }}>
              No itineraries saved yet.
            </div>
          )}
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: "0.8em",
              color: "#e5e7eb",
            }}
          >
            <thead>
              <tr
                style={{
                  borderBottom: "1px solid #1e293b",
                  textAlign: "left",
                  color: "#64748b",
                }}
              >
                <th style={{ padding: "4px" }}>Date</th>
                <th style={{ padding: "4px" }}>Summary</th>
                <th style={{ padding: "4px" }}>Tools</th>
              </tr>
            </thead>
            <tbody>
              {itineraries.map((it) => (
                <React.Fragment key={it.trip_id}>
                  <tr
                    style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}
                  >
                    <td
                      style={{
                        padding: "6px 4px",
                        verticalAlign: "top",
                        whiteSpace: "nowrap",
                        color: "#60a5fa",
                      }}
                    >
                      {it.start_date
                        ? new Date(it.start_date).toLocaleDateString(
                            undefined,
                            { month: "short", day: "numeric" }
                          )
                        : "N/A"}
                    </td>
                    <td style={{ padding: "6px 4px", verticalAlign: "top" }}>
                      <div style={{ fontWeight: 500, color: "#f1f5f9" }}>
                        {it.segments?.some((s) => s.type === "stay")
                          ? "🏨 "
                          : it.segments?.some((s) => s.type === "activity")
                          ? "🎟️ "
                          : "✈️ "}
                        {it.summary || "Trip"}
                      </div>
                    </td>
                    <td style={{ padding: "6px 4px", verticalAlign: "top" }}>
                      <div style={{ display: "flex", gap: 4 }}>
                        <button
                          onClick={() => handleExport(it.trip_id)}
                          title="Export .ics"
                          style={{ padding: "1px 4px", fontSize: "1em" }}
                        >
                          📅
                        </button>
                        <button
                          onClick={() => handleDelete(it.trip_id)}
                          title="Delete"
                          style={{
                            padding: "1px 4px",
                            fontSize: "1em",
                            color: "#ef4444",
                          }}
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>

        <div
          style={{
            borderTop: "1px solid #1e293b",
            paddingTop: 10,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <h4 style={{ margin: 0, fontSize: "0.9em" }}>
              📅 Combined Summary
            </h4>
            <div style={{ display: "flex", gap: 4 }}>
              <button
                onClick={handleDownloadCombined}
                style={{ padding: "2px 8px", fontSize: "0.8em" }}
              >
                Download .ics
              </button>
            </div>
          </div>
          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              style={{
                background: "#0f1724",
                color: "#fff",
                border: "1px solid #2b3446",
                padding: "2px 4px",
                borderRadius: 4,
                fontSize: "0.85em",
              }}
            />
            <span style={{ color: "#475569" }}>to</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              style={{
                background: "#0f1724",
                color: "#fff",
                border: "1px solid #2b3446",
                padding: "2px 4px",
                borderRadius: 4,
                fontSize: "0.85em",
              }}
            />
          </div>
          {combinedSummary && (
            <div
              style={{
                background: "#0f172a",
                padding: 8,
                borderRadius: 6,
                fontSize: "0.8em",
                maxHeight: 120,
                overflow: "auto",
                border: "1px solid rgba(99,102,241,0.1)",
              }}
            >
              <pre
                style={{ whiteSpace: "pre-wrap", margin: 0, color: "#cbd5e1" }}
              >
                {combinedSummary}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EmailItineraryConsole;
