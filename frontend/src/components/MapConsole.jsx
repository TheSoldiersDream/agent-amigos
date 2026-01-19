import React, { useState, useEffect, useRef, useCallback } from "react";
import { FiMap, FiSend, FiNavigation, FiGlobe } from "react-icons/fi";

const buildMapsEmbedUrl = ({ place, from, to, mode, zoom, view }) => {
  // Use www.google.com for broader embed compatibility
  const base = "https://www.google.com/maps";
  const z = zoom || 15;
  const t = view === "satellite" ? "k" : view === "terrain" ? "p" : "m";
  const isStreetView = view === "streetview";

  if (from && to) {
    const params = new URLSearchParams({
      saddr: from,
      daddr: to,
      dirflg: mode ? mode[0] : "d",
      output: "embed",
      z: z,
      t: t,
    });
    return `${base}?${params.toString()}`;
  }
  if (place) {
    const params = new URLSearchParams({
      q: place,
      output: "embed",
      z: z,
      t: t,
    });
    if (isStreetView) {
      params.append("layer", "c");
    }
    return `${base}?${params.toString()}`;
  }
  return `${base}?output=embed&z=${z}&t=${t}${isStreetView ? "&layer=c" : ""}`;
};

const MapConsole = ({ isOpen, onToggle, externalCommand, onScreenUpdate }) => {
  const [place, setPlace] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [mode, setMode] = useState("driving");
  const [zoom, setZoom] = useState(15);
  const [view, setView] = useState("roadmap");
  const [iframeKey, setIframeKey] = useState(0);
  const [url, setUrl] = useState(
    "https://www.google.com/maps?output=embed&z=15"
  );

  // Handle external commands from Amigos AI
  useEffect(() => {
    if (externalCommand) {
      console.log("🗺️ MapConsole receiving command:", externalCommand);

      // Support both 'place' and 'location' as aliases
      const cmdPlace = externalCommand.place ?? externalCommand.location;

      const newPlace = cmdPlace !== undefined ? cmdPlace : place;
      const newFrom =
        externalCommand.from !== undefined ? externalCommand.from : from;
      const newTo = externalCommand.to !== undefined ? externalCommand.to : to;
      const newMode =
        externalCommand.mode !== undefined ? externalCommand.mode : mode;
      const newZoom =
        externalCommand.zoom !== undefined ? externalCommand.zoom : zoom;
      const newView =
        externalCommand.view !== undefined ? externalCommand.view : view;

      if (cmdPlace !== undefined) setPlace(String(cmdPlace || ""));
      if (externalCommand.from !== undefined)
        setFrom(String(externalCommand.from || ""));
      if (externalCommand.to !== undefined)
        setTo(String(externalCommand.to || ""));
      if (externalCommand.mode !== undefined) setMode(externalCommand.mode);
      if (externalCommand.zoom !== undefined)
        setZoom(Number(externalCommand.zoom) || 15);
      if (externalCommand.view !== undefined) setView(externalCommand.view);

      // Auto-trigger search if command arrives
      const nextUrl = buildMapsEmbedUrl({
        place: newPlace,
        from: newFrom,
        to: newTo,
        mode: newMode,
        zoom: newZoom,
        view: newView,
      });

      setUrl(nextUrl);
      setIframeKey((prev) => prev + 1); // Force iframe reload
    }
  }, [externalCommand]);

  // Report state to Amigos for screen awareness
  useEffect(() => {
    if (onScreenUpdate && isOpen) {
      onScreenUpdate({
        currentPlace: place,
        route: from && to ? { from, to, mode } : null,
        zoom: zoom,
        view: view,
        url: url,
      });
    }
  }, [place, from, to, mode, zoom, view, url, onScreenUpdate, isOpen]);

  // Draggable/Resizable state - Load from localStorage
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-map-console-pos");
      return saved ? JSON.parse(saved) : { x: window.innerWidth - 520, y: 80 };
    } catch {
      return { x: window.innerWidth - 520, y: 80 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-map-console-size");
      return saved ? JSON.parse(saved) : { width: 500, height: 650 };
    } catch {
      return { width: 500, height: 650 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Save position to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-map-console-pos", JSON.stringify(position));
  }, [position]);

  // Save size to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-map-console-size", JSON.stringify(size));
  }, [size]);

  const handleMouseDown = (e) => {
    if (
      e.target.closest(".resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("input") ||
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
          width: Math.max(400, e.clientX - rect.left + 10),
          height: Math.max(400, e.clientY - rect.top + 10),
        });
      }
    },
    [isDragging, isResizing, dragOffset]
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

  const handleSearch = () => {
    const nextUrl = buildMapsEmbedUrl({ place, from, to, mode, zoom, view });
    setUrl(nextUrl);
    setIframeKey((prev) => prev + 1);
  };

  const openEarth = () => {
    window.open(
      "https://earth.google.com/web",
      "_blank",
      "noopener,noreferrer"
    );
  };

  const openInBrowser = () => {
    window.open(
      url.replace("output=embed", "output=classic"),
      "_blank",
      "noopener,noreferrer"
    );
  };

  if (!isOpen) return null;

  const inputStyle = {
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(34, 197, 94, 0.3)",
    borderRadius: "10px",
    padding: "10px 12px",
    color: "#e5e7eb",
    outline: "none",
    fontSize: 13,
    width: "100%",
  };

  const btnStyle = {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    background: "linear-gradient(135deg, #22c55e, #16a34a)",
    border: "none",
    color: "white",
    padding: "10px 14px",
    borderRadius: "10px",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: "500",
    boxShadow: "0 4px 15px rgba(34, 197, 94, 0.3)",
  };

  const ghostBtn = {
    display: "inline-flex",
    alignItems: "center",
    gap: 6,
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(255,255,255,0.1)",
    color: "#d1d5db",
    padding: "10px 14px",
    borderRadius: "10px",
    cursor: "pointer",
    fontSize: 12,
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        left: position.x,
        top: position.y,
        width: size.width,
        height: size.height,
        backgroundColor: "rgba(15, 23, 42, 0.97)",
        color: "#e5e7eb",
        borderRadius: "16px",
        border: "1px solid rgba(34, 197, 94, 0.4)",
        boxShadow:
          "0 20px 60px rgba(0,0,0,0.5), 0 0 30px rgba(34, 197, 94, 0.1)",
        backdropFilter: "blur(20px)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        zIndex: 11000,
        cursor: isDragging ? "grabbing" : "default",
      }}
    >
      {/* Draggable Header */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          padding: "14px 18px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background:
            "linear-gradient(135deg, rgba(34,197,94,0.15), rgba(22,163,74,0.05))",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          cursor: "grab",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: 38,
              height: 38,
              borderRadius: "12px",
              background: "linear-gradient(135deg, #22c55e, #16a34a)",
              display: "grid",
              placeItems: "center",
              boxShadow: "0 8px 25px rgba(34,197,94,0.4)",
            }}
          >
            <FiMap color="#fff" size={20} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>Maps & Earth</div>
            <div style={{ fontSize: 11, color: "#94a3b8" }}>
              Search places • Get directions • (drag to move)
            </div>
          </div>
        </div>
        <button
          onClick={onToggle}
          style={{
            background: "#ff4757",
            border: "none",
            color: "white",
            width: "30px",
            height: "30px",
            borderRadius: "50%",
            cursor: "pointer",
            fontSize: "18px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          ×
        </button>
      </div>

      {/* Controls */}
      <div
        style={{
          padding: "14px 18px",
          display: "flex",
          flexDirection: "column",
          gap: 10,
        }}
      >
        <input
          value={place}
          onChange={(e) => setPlace(e.target.value)}
          placeholder="🔍 Search place or address (e.g., Eiffel Tower)"
          style={inputStyle}
          onKeyPress={(e) => e.key === "Enter" && handleSearch()}
        />
        <div
          style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}
        >
          <input
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            placeholder="📍 From (origin)"
            style={inputStyle}
          />
          <input
            value={to}
            onChange={(e) => setTo(e.target.value)}
            placeholder="🎯 To (destination)"
            style={inputStyle}
          />
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <label style={{ fontSize: 12, color: "#cbd5e1" }}>Mode:</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            style={{ ...inputStyle, flex: 1, backgroundColor: "#0f172a" }}
          >
            <option value="driving">🚗 Driving</option>
            <option value="walking">🚶 Walking</option>
            <option value="bicycling">🚴 Cycling</option>
            <option value="transit">🚌 Transit</option>
          </select>

          <label style={{ fontSize: 12, color: "#cbd5e1" }}>Zoom:</label>
          <select
            value={zoom}
            onChange={(e) => setZoom(parseInt(e.target.value))}
            style={{ ...inputStyle, width: 70, backgroundColor: "#0f172a" }}
          >
            {[1, 5, 10, 12, 15, 18, 20, 21].map((z) => (
              <option key={z} value={z}>
                {z}x
              </option>
            ))}
          </select>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <label style={{ fontSize: 12, color: "#cbd5e1" }}>View:</label>
          <select
            value={view}
            onChange={(e) => setView(e.target.value)}
            style={{ ...inputStyle, flex: 1, backgroundColor: "#0f172a" }}
          >
            <option value="roadmap">🗺️ Roadmap</option>
            <option value="satellite">🛰️ Satellite</option>
            <option value="terrain">⛰️ Terrain</option>
            <option value="streetview">🛣️ Street View</option>
          </select>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button style={btnStyle} onClick={handleSearch}>
            <FiSend size={14} /> Search / Route
          </button>
          <button style={ghostBtn} onClick={openEarth}>
            <FiGlobe size={14} /> Google Earth
          </button>
          <button style={ghostBtn} onClick={openInBrowser}>
            <FiNavigation size={14} /> Open in Browser
          </button>
        </div>
      </div>

      {/* Map View */}
      <div
        style={{
          flex: 1,
          borderTop: "1px solid rgba(255,255,255,0.06)",
          backgroundColor: "#0b1220",
        }}
      >
        <iframe
          key={iframeKey}
          title="Map viewer"
          src={url}
          style={{ width: "100%", height: "100%", border: "none" }}
          loading="lazy"
          allow="geolocation; microphone; camera; clipboard-read; clipboard-write"
          referrerPolicy="no-referrer-when-downgrade"
        />
      </div>

      {/* Resize Handle */}
      <div
        className="resize-handle"
        style={{
          position: "absolute",
          bottom: 0,
          right: 0,
          width: "20px",
          height: "20px",
          cursor: "se-resize",
          background: "linear-gradient(135deg, transparent 50%, #22c55e 50%)",
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

export default MapConsole;
