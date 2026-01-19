import React, { useState, useEffect, useRef, useCallback } from "react";

const MiniBrowser = ({ isOpen, onToggle }) => {
  // Default to a search page that usually allows embedding
  const defaultHome = "https://duckduckgo.com";
  const [url, setUrl] = useState(defaultHome);
  const [inputUrl, setInputUrl] = useState(defaultHome);
  const [history, setHistory] = useState([defaultHome]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [bookmarks, setBookmarks] = useState([
    { name: "Google", url: "https://www.google.com", icon: "🔍" },
    { name: "YouTube", url: "https://www.youtube.com", icon: "▶️" },
    { name: "GitHub", url: "https://www.github.com", icon: "💻" },
    { name: "Reddit", url: "https://www.reddit.com", icon: "🔶" },
    { name: "Twitter/X", url: "https://www.x.com", icon: "🐦" },
    { name: "ChatGPT", url: "https://chat.openai.com", icon: "🤖" },
  ]);
  const [showBookmarks, setShowBookmarks] = useState(false);
  const iframeRef = useRef(null);

  // Draggable/Resizable state
  const [position, setPosition] = useState({ x: 150, y: 80 });
  const [size, setSize] = useState({ width: 1000, height: 700 });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Don't render if not open
  if (!isOpen) return null;

  // Keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isExpanded) {
        setIsExpanded(false);
      }
      if (e.ctrlKey && e.key === "l") {
        document.getElementById("browser-url-input")?.focus();
        e.preventDefault();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isExpanded]);

  // Drag handlers
  const handleMouseDown = (e) => {
    if (
      e.target.closest(".resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("input")
    )
      return;
    setIsDragging(true);
    const rect = containerRef.current.getBoundingClientRect();
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  const handleMouseMove = useCallback(
    (e) => {
      if (isDragging && !isExpanded) {
        setPosition({
          x: Math.max(0, e.clientX - dragOffset.x),
          y: Math.max(0, e.clientY - dragOffset.y),
        });
      }
      if (isResizing && !isExpanded) {
        const rect = containerRef.current.getBoundingClientRect();
        setSize({
          width: Math.max(500, e.clientX - rect.left + 10),
          height: Math.max(400, e.clientY - rect.top + 10),
        });
      }
    },
    [isDragging, isResizing, dragOffset, isExpanded]
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

  const navigateTo = (newUrl) => {
    let processedUrl = newUrl.trim();

    // Add protocol if missing
    if (
      !processedUrl.startsWith("http://") &&
      !processedUrl.startsWith("https://")
    ) {
      // Check if it looks like a URL
      if (processedUrl.includes(".") && !processedUrl.includes(" ")) {
        processedUrl = "https://" + processedUrl;
      } else {
        // Treat as search query
        processedUrl = `https://www.google.com/search?q=${encodeURIComponent(
          processedUrl
        )}`;
      }
    }

    setIsLoading(true);
    setUrl(processedUrl);
    setInputUrl(processedUrl);

    // Update history
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push(processedUrl);
    setHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
  };

  const goBack = () => {
    if (historyIndex > 0) {
      const newIndex = historyIndex - 1;
      setHistoryIndex(newIndex);
      setUrl(history[newIndex]);
      setInputUrl(history[newIndex]);
      setIsLoading(true);
    }
  };

  const goForward = () => {
    if (historyIndex < history.length - 1) {
      const newIndex = historyIndex + 1;
      setHistoryIndex(newIndex);
      setUrl(history[newIndex]);
      setInputUrl(history[newIndex]);
      setIsLoading(true);
    }
  };

  const refresh = () => {
    setIsLoading(true);
    if (iframeRef.current) {
      iframeRef.current.src = url;
    }
  };

  const addBookmark = () => {
    const name = prompt("Bookmark name:", url.split("/")[2]);
    if (name) {
      setBookmarks([...bookmarks, { name, url, icon: "⭐" }]);
    }
  };

  const containerStyle = isExpanded
    ? {
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 9999,
        borderRadius: 0,
      }
    : {
        position: "fixed",
        left: `${position.x}px`,
        top: `${position.y}px`,
        width: `${size.width}px`,
        height: `${size.height}px`,
        zIndex: 1000,
        borderRadius: "16px",
      };

  return (
    <div
      ref={containerRef}
      style={{
        ...containerStyle,
        background: "linear-gradient(145deg, #0a0a14 0%, #12121f 100%)",
        border: isExpanded ? "none" : "1px solid rgba(99, 102, 241, 0.3)",
        boxShadow: isExpanded
          ? "none"
          : "0 25px 80px rgba(0, 0, 0, 0.8), 0 0 40px rgba(99, 102, 241, 0.15)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      }}
    >
      {/* Premium Header */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
          padding: "12px 16px",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
          cursor: isDragging ? "grabbing" : isExpanded ? "default" : "grab",
          borderBottom: "1px solid rgba(99, 102, 241, 0.2)",
        }}
      >
        {/* Top row - Controls */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {/* Window controls */}
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button
              onClick={onToggle}
              style={{
                width: "14px",
                height: "14px",
                borderRadius: "50%",
                border: "none",
                background: "linear-gradient(135deg, #ff5f57, #ff3b30)",
                cursor: "pointer",
                transition: "transform 0.2s",
              }}
              onMouseEnter={(e) => (e.target.style.transform = "scale(1.2)")}
              onMouseLeave={(e) => (e.target.style.transform = "scale(1)")}
              title="Close"
            />
            <button
              onClick={() => setIsExpanded(false)}
              style={{
                width: "14px",
                height: "14px",
                borderRadius: "50%",
                border: "none",
                background: "linear-gradient(135deg, #ffbd2e, #ff9500)",
                cursor: "pointer",
                transition: "transform 0.2s",
              }}
              onMouseEnter={(e) => (e.target.style.transform = "scale(1.2)")}
              onMouseLeave={(e) => (e.target.style.transform = "scale(1)")}
              title="Minimize"
            />
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              style={{
                width: "14px",
                height: "14px",
                borderRadius: "50%",
                border: "none",
                background: "linear-gradient(135deg, #27c93f, #32d74b)",
                cursor: "pointer",
                transition: "transform 0.2s",
              }}
              onMouseEnter={(e) => (e.target.style.transform = "scale(1.2)")}
              onMouseLeave={(e) => (e.target.style.transform = "scale(1)")}
              title={isExpanded ? "Restore" : "Maximize"}
            />
            <span
              style={{
                marginLeft: "12px",
                color: "#a5b4fc",
                fontSize: "13px",
                fontWeight: "600",
                letterSpacing: "0.5px",
              }}
            >
              🌐 Mini Browser
            </span>
          </div>

          {/* Right controls */}
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              onClick={() => setShowBookmarks(!showBookmarks)}
              style={{
                background: showBookmarks
                  ? "rgba(99, 102, 241, 0.3)"
                  : "rgba(255, 255, 255, 0.05)",
                border: "1px solid rgba(99, 102, 241, 0.3)",
                color: "#a5b4fc",
                padding: "6px 12px",
                borderRadius: "8px",
                cursor: "pointer",
                fontSize: "12px",
                display: "flex",
                alignItems: "center",
                gap: "4px",
                transition: "all 0.2s",
              }}
            >
              ⭐ Bookmarks
            </button>
          </div>
        </div>

        {/* URL Bar */}
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {/* Navigation buttons */}
          <div
            style={{ display: "flex", gap: "4px", flexShrink: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={goBack}
              disabled={historyIndex <= 0}
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                border: "none",
                background:
                  historyIndex > 0
                    ? "rgba(99, 102, 241, 0.2)"
                    : "rgba(255, 255, 255, 0.05)",
                color: historyIndex > 0 ? "#a5b4fc" : "#4b5563",
                cursor: historyIndex > 0 ? "pointer" : "not-allowed",
                fontSize: "16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.2s",
              }}
            >
              ←
            </button>
            <button
              onClick={goForward}
              disabled={historyIndex >= history.length - 1}
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                border: "none",
                background:
                  historyIndex < history.length - 1
                    ? "rgba(99, 102, 241, 0.2)"
                    : "rgba(255, 255, 255, 0.05)",
                color:
                  historyIndex < history.length - 1 ? "#a5b4fc" : "#4b5563",
                cursor:
                  historyIndex < history.length - 1 ? "pointer" : "not-allowed",
                fontSize: "16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.2s",
              }}
            >
              →
            </button>
            <button
              onClick={refresh}
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                border: "none",
                background: "rgba(99, 102, 241, 0.2)",
                color: "#a5b4fc",
                cursor: "pointer",
                fontSize: "14px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "all 0.2s",
              }}
            >
              {isLoading ? "⏳" : "🔄"}
            </button>
          </div>

          {/* URL input */}
          <div
            style={{
              flex: 1,
              position: "relative",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                position: "absolute",
                left: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                color: url.startsWith("https") ? "#10b981" : "#f59e0b",
                fontSize: "12px",
              }}
            >
              {url.startsWith("https") ? "🔒" : "⚠️"}
            </div>
            <input
              id="browser-url-input"
              type="text"
              value={inputUrl}
              onChange={(e) => setInputUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && navigateTo(inputUrl)}
              placeholder="Search or enter URL..."
              style={{
                width: "100%",
                padding: "10px 12px 10px 36px",
                borderRadius: "12px",
                border: "1px solid rgba(99, 102, 241, 0.3)",
                background: "rgba(0, 0, 0, 0.4)",
                color: "#e5e7eb",
                fontSize: "13px",
                outline: "none",
                boxSizing: "border-box",
                transition: "all 0.2s",
              }}
              onFocus={(e) => {
                e.target.style.borderColor = "#6366f1";
                e.target.style.boxShadow = "0 0 0 3px rgba(99, 102, 241, 0.2)";
              }}
              onBlur={(e) => {
                e.target.style.borderColor = "rgba(99, 102, 241, 0.3)";
                e.target.style.boxShadow = "none";
              }}
            />
          </div>

          <button
            onClick={addBookmark}
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              border: "none",
              background: "rgba(251, 191, 36, 0.2)",
              color: "#fbbf24",
              cursor: "pointer",
              fontSize: "14px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
              transition: "all 0.2s",
            }}
            title="Add Bookmark"
          >
            ⭐
          </button>
        </div>

        {/* Bookmarks bar */}
        {showBookmarks && (
          <div
            style={{
              display: "flex",
              gap: "8px",
              padding: "8px 0 0 0",
              borderTop: "1px solid rgba(99, 102, 241, 0.1)",
              flexWrap: "wrap",
            }}
          >
            {bookmarks.map((bm, idx) => (
              <button
                key={idx}
                onClick={(e) => {
                  e.stopPropagation();
                  navigateTo(bm.url);
                }}
                style={{
                  background: "rgba(99, 102, 241, 0.15)",
                  border: "1px solid rgba(99, 102, 241, 0.25)",
                  color: "#a5b4fc",
                  padding: "6px 12px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.target.style.background = "rgba(99, 102, 241, 0.3)";
                }}
                onMouseLeave={(e) => {
                  e.target.style.background = "rgba(99, 102, 241, 0.15)";
                }}
              >
                <span>{bm.icon}</span>
                {bm.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Browser Content */}
      <div
        style={{
          flex: 1,
          position: "relative",
          background: "#0f0f1a",
        }}
      >
        {/* Loading indicator */}
        {isLoading && (
          <div
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: "3px",
              background: "rgba(99, 102, 241, 0.2)",
              zIndex: 10,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: "30%",
                background: "linear-gradient(90deg, #6366f1, #8b5cf6, #6366f1)",
                animation: "loadingBar 1.5s ease-in-out infinite",
              }}
            />
          </div>
        )}

        {/* iframe - Note: Some sites may block embedding */}
        <iframe
          ref={iframeRef}
          src={url}
          style={{
            width: "100%",
            height: "100%",
            border: "none",
            background: "#fff",
          }}
          sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-modals allow-downloads"
          onLoad={() => setIsLoading(false)}
          onError={() => setIsLoading(false)}
          title="Mini Browser"
        />

        {/* Overlay message for blocked sites */}
        <div
          style={{
            position: "absolute",
            bottom: "16px",
            right: "16px",
            background: "rgba(0, 0, 0, 0.8)",
            backdropFilter: "blur(10px)",
            padding: "8px 14px",
            borderRadius: "8px",
            color: "#9ca3af",
            fontSize: "11px",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            border: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <span style={{ color: "#fbbf24" }}>💡</span>
          Some sites may block embedding. Try opening in new tab if needed.
        </div>
      </div>

      {/* Resize Handle */}
      {!isExpanded && (
        <div
          className="resize-handle"
          onMouseDown={(e) => {
            e.stopPropagation();
            setIsResizing(true);
          }}
          style={{
            position: "absolute",
            bottom: 0,
            right: 0,
            width: "20px",
            height: "20px",
            cursor: "se-resize",
            background:
              "linear-gradient(135deg, transparent 50%, rgba(99, 102, 241, 0.4) 50%)",
            borderRadius: "0 0 16px 0",
          }}
        />
      )}

      {/* CSS Animation */}
      <style>{`
        @keyframes loadingBar {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(400%); }
        }
      `}</style>
    </div>
  );
};

export default MiniBrowser;
