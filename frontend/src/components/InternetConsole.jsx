import React, { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import {
  FiGlobe,
  FiSearch,
  FiExternalLink,
  FiClock,
  FiActivity,
  FiTrendingUp,
  FiBriefcase,
  FiDollarSign,
  FiShoppingCart,
  FiHome,
  FiMapPin,
  FiRefreshCw,
} from "react-icons/fi";

const InternetConsole = ({
  isOpen,
  onToggle,
  apiUrl,
  externalResults,
  onScreenUpdate,
  onSendMessage,
}) => {
  const backendUrl = apiUrl || "http://127.0.0.1:65252";
  const companyRegistry = "Agent Amigos AI Corp";
  const roleOwner = "Acquisition & Research Dept";
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchType, setSearchType] = useState("web");

  // Draggable/Resizable state - Load from localStorage
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-internet-console-pos");
      return saved ? JSON.parse(saved) : { x: window.innerWidth - 500, y: 80 };
    } catch {
      return { x: window.innerWidth - 500, y: 80 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-internet-console-size");
      return saved ? JSON.parse(saved) : { width: 450, height: 600 };
    } catch {
      return { width: 450, height: 600 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Save position to localStorage when it changes
  useEffect(() => {
    localStorage.setItem(
      "amigos-internet-console-pos",
      JSON.stringify(position),
    );
  }, [position]);

  // Save size to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-internet-console-size", JSON.stringify(size));
  }, [size]);

  useEffect(() => {
    if (externalResults && externalResults.length > 0) {
      setResults(externalResults);
      setError("");
    }
  }, [externalResults]);

  // Report results to screen context for agent awareness
  useEffect(() => {
    if (onScreenUpdate && isOpen) {
      onScreenUpdate({
        results: results.slice(0, 10), // Send top 10 results
        searchType,
        lastQuery: query,
        financeData:
          searchType === "finance"
            ? { symbol: "AUDUSD", status: "Live Chart Visible" }
            : null,
        jobData:
          searchType === "jobs"
            ? { type: "Job Search", query: query || "Latest Jobs" }
            : null,
        hustleData:
          searchType === "hustle"
            ? { type: "Side Hustle", query: query || "Passive Income" }
            : null,
        productData:
          searchType === "products"
            ? { type: "Product Search", query: query || "Top Products" }
            : null,
        propertyData:
          searchType === "property"
            ? { type: "Property & Rentals", query: query || "Real Estate" }
            : null,
        accommodationData:
          searchType === "accommodation"
            ? { type: "Accommodation", query: query || "Hotels & Stays" }
            : null,
      });
    }
  }, [results, searchType, query, onScreenUpdate, isOpen]);

  // Auto-fetch news/finance when switching tabs if empty
  useEffect(() => {
    if (!isOpen) return;
    if (results.length === 0 && !loading) {
      if (searchType === "finance") {
        handleSearch("latest finance market news");
      } else if (searchType === "news") {
        handleSearch("latest world news");
      } else if (searchType === "jobs") {
        handleSearch("latest remote jobs hiring");
      } else if (searchType === "hustle") {
        handleSearch("best side hustles 2025");
      } else if (searchType === "products") {
        handleSearch("best selling products on amazon 2025");
      } else if (searchType === "property") {
        handleSearch("latest property for sale and rent");
      } else if (searchType === "accommodation") {
        handleSearch("best accommodation and hotels deals");
      }
    }
  }, [searchType, isOpen]);

  // Dragging handlers
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
      if (isDragging) {
        setPosition({
          x: Math.max(0, e.clientX - dragOffset.x),
          y: Math.max(0, e.clientY - dragOffset.y),
        });
      }
      if (isResizing) {
        const rect = containerRef.current.getBoundingClientRect();
        setSize({
          width: Math.max(350, e.clientX - rect.left + 10),
          height: Math.max(300, e.clientY - rect.top + 10),
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

  const quickTopics = [
    { label: "🌍 World", query: "latest world news" },
    { label: "🇦🇺 ABC News", query: "ABC News Australia latest news" },
    {
      label: "🇵🇭 Filipino News",
      query: "latest news Philippines GMA ABS-CBN TV5",
    },
    { label: "💻 Tech", query: "latest technology news" },
    { label: "💹 Finance", query: "latest finance market news" },
    { label: "🪙 Crypto", query: "latest cryptocurrency news" },
    { label: "🤖 AI", query: "artificial intelligence news" },
    { label: "💼 Jobs", query: "remote software engineer jobs" },
    { label: "💰 Hustle", query: "best side hustles 2025" },
    { label: "🛒 Shop", query: "best deals on amazon today" },
    { label: "🏠 Home", query: "apartments for rent near me" },
    { label: "🏨 Stay", query: "best hotels in London" },
  ];

  // Function to merge news stories into a cohesive narrative
  const mergeNewsStories = async (stories) => {
    if (!stories || stories.length === 0) return null;

    try {
      const formattedStories = stories.map((s) => ({
        title: s.title || "No Title",
        snippet: s.body || s.snippet || "No snippet",
        source: s.source || "Web",
      }));

      const response = await fetch("http://127.0.0.1:65252/scrape/merge-news", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stories: formattedStories }),
      });

      if (!response.ok) throw new Error("Failed to merge stories");

      const data = await response.json();
      if (data.success) {
        // Parse the LLM output (assuming TITLE: ..., STORY: ..., SOURCES: ...)
        const content = data.summary;
        const titleMatch = content.match(/TITLE:\s*(.*)/i);
        const storyMatch = content.match(/STORY:\s*([\s\S]*?)(?=SOURCES:|$)/i);
        const sourceMatch = content.match(/SOURCES:\s*([\s\S]*)/i);

        return {
          title: titleMatch ? titleMatch[1].trim() : "Merged News Digest",
          mainStory: storyMatch ? storyMatch[1].trim() : content,
          sources: sourceMatch ? sourceMatch[1].trim() : "Various",
          timestamp: new Date().toLocaleString(),
          isAI: true,
        };
      }
    } catch (err) {
      console.error("Narrative merge failed:", err);
    }

    // Fallback to basic merge if AI fails or isn't reachable
    const titles = stories.map((s) => s.title || "").filter(Boolean);
    const snippets = stories
      .map((s) => s.body || s.snippet || "")
      .filter(Boolean);
    const sources = [
      ...new Set(stories.map((s) => s.source || "").filter(Boolean)),
    ];

    return {
      title: "Today's Top Stories: " + titles.slice(0, 3).join(" | "),
      introduction: `Here's a comprehensive update on the latest news:`,
      mainStory: snippets.slice(0, 5).join("\n\n"),
      sources: sources.join(", "),
      timestamp: new Date().toLocaleString(),
      isAI: false,
    };
  };

  const handleSearch = async (searchQuery) => {
    const q = (searchQuery || query || "").trim();
    if (!q) {
      setError("Please enter a search query first.");
      return;
    }

    setLoading(true);
    setError("");
    setResults([]);

    try {
      let toolName = "web_search";
      let finalQuery = q;

      if (searchType === "news") {
        toolName = "web_search_news";
      } else if (searchType === "finance") {
        toolName = "web_search_news";
        // If it's a generic search in finance tab, add context
        if (
          !q.toLowerCase().includes("finance") &&
          !q.toLowerCase().includes("market")
        ) {
          finalQuery = `${q} finance market news`;
        }
      } else if (searchType === "jobs") {
        toolName = "web_search";
        if (
          !q.toLowerCase().includes("job") &&
          !q.toLowerCase().includes("hiring")
        ) {
          finalQuery = `${q} jobs hiring remote`;
        }
      } else if (searchType === "hustle") {
        toolName = "web_search";
        if (
          !q.toLowerCase().includes("hustle") &&
          !q.toLowerCase().includes("income")
        ) {
          finalQuery = `${q} side hustle passive income ideas`;
        }
      } else if (searchType === "products") {
        toolName = "web_search";
        if (
          !q.toLowerCase().includes("amazon") &&
          !q.toLowerCase().includes("buy") &&
          !q.toLowerCase().includes("price")
        ) {
          finalQuery = `${q} price amazon buy online`;
        }
      } else if (searchType === "property") {
        toolName = "web_search";
        if (
          !q.toLowerCase().includes("rent") &&
          !q.toLowerCase().includes("sale") &&
          !q.toLowerCase().includes("property")
        ) {
          finalQuery = `${q} property for sale or rent real estate`;
        }
      } else if (searchType === "accommodation") {
        toolName = "web_search";
        if (
          !q.toLowerCase().includes("hotel") &&
          !q.toLowerCase().includes("stay") &&
          !q.toLowerCase().includes("airbnb")
        ) {
          finalQuery = `${q} hotels accommodation airbnb stays`;
        }
      }

      const response = await axios.post(`${backendUrl}/execute_tool`, {
        tool_name: toolName,
        arguments: {
          query: finalQuery,
          max_results: 10,
        },
      });

      if (response.data.status === "success" && response.data.result.success) {
        const rawResults = response.data.result.results;
        setResults(rawResults);

        // Create merged narrative for news stories
        if (searchType === "news" && rawResults.length > 0) {
          const narrative = await mergeNewsStories(rawResults);
          // Store the narrative in the results for the agent to access
          if (narrative && onScreenUpdate) {
            onScreenUpdate({
              results: rawResults.slice(0, 10),
              searchType,
              lastQuery: query,
              mergedNarrative: narrative,
            });
          }
        }
      } else {
        setError(response.data.result.error || "Failed to fetch results");
      }
    } catch (err) {
      const isAxios = !!err?.isAxiosError;
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;

      if (isAxios && status) {
        let detailText = "";
        if (detail && typeof detail === "object") {
          const code = detail.error || detail.code;
          const action = detail.action ? ` (${detail.action})` : "";
          detailText = code ? `${code}${action}` : JSON.stringify(detail);
        } else if (typeof detail === "string") {
          detailText = detail;
        }
        setError(
          `Request failed (${status})${detailText ? `: ${detailText}` : ""}`,
        );
      } else {
        // Axios 'Network Error' usually means: backend not running, wrong URL, blocked by firewall/proxy.
        const baseMsg = err?.message || "Network error";
        setError(
          `${baseMsg}. Unable to reach Agent Amigos backend at ${backendUrl}. ` +
            `Make sure the backend is running on ${backendUrl} (default 127.0.0.1:65252).`,
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = useCallback(() => {
    if (loading) return;
    
    // Explicitly clear results to show loading state
    setResults([]);
    
    let refreshQuery = query;
    
    if (!refreshQuery) {
      if (searchType === "news") {
        const newsQueries = [
          "latest world news", 
          "top breaking stories today", 
          "major global events",
          "world news headlines",
          "ABC News latest",
          "BBC News world"
        ];
        refreshQuery = newsQueries[Math.floor(Math.random() * newsQueries.length)];
      } else if (searchType === "finance") {
        refreshQuery = "latest finance market news";
      } else if (searchType === "tech") {
        refreshQuery = "latest technology news";
      } else {
        refreshQuery = "latest " + searchType;
      }
    }
    
    handleSearch(refreshQuery);
  }, [loading, query, searchType, handleSearch]);

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
        backgroundColor: "var(--glass-bg)",
        backdropFilter: "blur(20px)",
        borderRadius: "20px",
        border: "var(--glass-border)",
        boxShadow: "var(--shadow-lg)",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        color: "var(--text-primary)",
        fontFamily: "var(--font-main)",
        cursor: isDragging ? "grabbing" : "default",
      }}
    >
      {/* Draggable Header */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          padding: "16px 20px",
          borderBottom: "var(--glass-border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%)",
          cursor: "grab",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            className="brand-mark"
            style={{
              background: "var(--gradient-executive)",
              width: "40px",
              height: "40px",
            }}
          >
            <FiGlobe size={20} color="white" />
          </div>
          <div>
            <h2
              style={{
                margin: 0,
                fontSize: "1rem",
                fontWeight: "800",
                color: "white",
                letterSpacing: "-0.01em",
              }}
            >
              Acquisition <span className="revenue-text">BOT</span>
            </h2>
            <div
              style={{
                fontSize: "0.65rem",
                color: "var(--text-muted)",
                fontWeight: "700",
                textTransform: "uppercase",
                letterSpacing: "0.05em",
              }}
            >
              Autonomous Market Intel
            </div>
          </div>
        </div>
        <button
          onClick={onToggle}
          style={{
            background: "rgba(255, 255, 255, 0.05)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            color: "var(--text-secondary)",
            width: "32px",
            height: "32px",
            borderRadius: "10px",
            cursor: "pointer",
            fontSize: "18px",
            transition: "all 0.2s ease",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(239, 68, 68, 0.2)";
            e.currentTarget.style.color = "#fff";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
            e.currentTarget.style.color = "var(--text-secondary)";
          }}
        >
          ×
        </button>
      </div>

      {/* Control Bar (Search & Refresh) */}
      <div style={{ 
        padding: "10px 16px", 
        borderBottom: "var(--glass-border)",
        display: "flex",
        gap: "10px",
        alignItems: "center",
        background: "rgba(0,0,0,0.2)"
      }}>
        <div style={{ position: "relative", flex: 1 }}>
          <FiSearch 
            size={14} 
            style={{ 
              position: "absolute", 
              left: "12px", 
              top: "50%", 
              transform: "translateY(-50%)",
              color: "var(--text-muted)"
            }} 
          />
          <input
            type="text"
            placeholder={`Search ${searchType}...`}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            style={{
              width: "100%",
              padding: "10px 12px 10px 36px",
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "10px",
              color: "white",
              fontSize: "0.85rem",
              outline: "none",
            }}
          />
        </div>
        <button
          onClick={() => handleRefresh()}
          disabled={loading}
          title="Refresh Content"
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            padding: "10px",
            borderRadius: "10px",
            color: "var(--text-secondary)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all 0.2s"
          }}
          onMouseEnter={(e) => {
            if(!loading) e.currentTarget.style.background = "rgba(59, 130, 246, 0.2)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "rgba(255, 255, 255, 0.05)";
          }}
        >
          <FiRefreshCw size={14} className={loading ? "spin-animation" : ""} />
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: "16px", overflowY: "auto", flex: 1 }}>
        {/* Search Type Toggle */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "8px",
            marginBottom: "20px",
          }}
        >
          {[
            {
              id: "web",
              icon: <FiSearch size={14} />,
              label: "Web",
              color: "var(--accent-primary)",
            },
            {
              id: "news",
              icon: <FiGlobe size={14} />,
              label: "News",
              color: "var(--accent-primary)",
            },
            {
              id: "finance",
              icon: <FiTrendingUp size={14} />,
              label: "Finance",
              color: "var(--accent-primary)",
            },
            {
              id: "jobs",
              icon: <FiBriefcase size={14} />,
              label: "Jobs",
              color: "var(--accent-success)",
            },
            {
              id: "hustle",
              icon: <FiDollarSign size={14} />,
              label: "Hustle",
              color: "var(--accent-revenue)",
            },
            {
              id: "products",
              icon: <FiShoppingCart size={14} />,
              label: "Shop",
              color: "#ec4899",
            },
            {
              id: "property",
              icon: <FiHome size={14} />,
              label: "Home",
              color: "var(--accent-tertiary)",
            },
            {
              id: "accommodation",
              icon: <FiMapPin size={14} />,
              label: "Stay",
              color: "var(--accent-secondary)",
            },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSearchType(tab.id)}
              style={{
                padding: "10px 8px",
                borderRadius: "12px",
                border: "1px solid",
                borderColor:
                  searchType === tab.id ? tab.color : "rgba(255,255,255,0.06)",
                background:
                  searchType === tab.id
                    ? `${tab.color}15`
                    : "rgba(255,255,255,0.03)",
                color: searchType === tab.id ? "#fff" : "var(--text-secondary)",
                cursor: "pointer",
                fontSize: "0.75rem",
                fontWeight: searchType === tab.id ? "700" : "500",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "6px",
                transition: "all 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
              }}
            >
              <span
                style={{
                  fontSize: "1.1rem",
                  opacity: searchType === tab.id ? 1 : 0.6,
                }}
              >
                {tab.icon}
              </span>
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Quick Topics Intel */}
        <div style={{ marginBottom: "20px" }}>
          <div style={{ 
            fontSize: "0.7rem", 
            fontWeight: "700", 
            textTransform: "uppercase", 
            color: "var(--text-muted)",
            marginBottom: "10px",
            letterSpacing: "0.05em",
            display: "flex",
            alignItems: "center",
            gap: "6px"
          }}>
            <FiActivity size={10} /> Quick Intel Topics
          </div>
          <div style={{ 
            display: "flex", 
            flexWrap: "wrap", 
            gap: "8px" 
          }}>
            {quickTopics.map((topic, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuery(topic.query);
                  handleSearch(topic.query);
                }}
                style={{
                  padding: "6px 10px",
                  background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  borderRadius: "8px",
                  fontSize: "0.7rem",
                  color: "var(--text-secondary)",
                  cursor: "pointer",
                  transition: "all 0.2s"
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.08)";
                  e.currentTarget.style.color = "#fff";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "rgba(255,255,255,0.03)";
                  e.currentTarget.style.color = "var(--text-secondary)";
                }}
              >
                {topic.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {results.length > 0 && !loading && (
            <button
              onClick={async () => {
                const type =
                  searchType === "jobs"
                    ? "Job Search"
                    : searchType === "hustle"
                      ? "Side Hustle"
                      : searchType === "finance"
                        ? "Finance"
                        : searchType === "products"
                          ? "Product Search"
                          : searchType === "property"
                            ? "Property & Rentals"
                            : searchType === "accommodation"
                              ? "Accommodation"
                              : searchType === "news"
                                ? "News"
                                : "Web Search";

                let summaryPrompt = `Please summarize these ${type} results from the internet console and generate a professional report for me.`;

                if (searchType === "news") {
                  const narrative = await mergeNewsStories(results);
                  if (narrative) {
                    if (narrative.isAI) {
                      summaryPrompt = `Please review this AI-generated news story derived from the search results and present it nicely:\n\n${narrative.title}\n\n${narrative.mainStory}\n\nSources: ${narrative.sources}`;
                    } else {
                      summaryPrompt = `Please create a flowing, cohesive news story that merges these headlines into an interesting narrative. Use this structure as a starting point:\n\n${narrative.title}\n\n${narrative.mainStory}\n\nSources: ${narrative.sources}`;
                    }
                  } else if (query.toLowerCase().includes("abc news")) {
                    summaryPrompt = `Please summarize the latest news from ABC Australia based on these results and provide a concise briefing.`;
                  } else if (
                    query.toLowerCase().includes("philippines") ||
                    query.toLowerCase().includes("filipino")
                  ) {
                    summaryPrompt = `Please summarize the latest Filipino news from these results (GMA, ABS-CBN, TV5) and provide a concise briefing.`;
                  } else {
                    summaryPrompt = `Please create a flowing, cohesive news story that merges these headlines into an interesting narrative. Make it read like a professional news broadcast.`;
                  }
                }

                if (typeof onSendMessage === "function") {
                  onSendMessage(summaryPrompt);
                }
              }}
              style={{
                background: "linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)",
                border: "none",
                borderRadius: "10px",
                padding: "10px",
                color: "white",
                fontSize: "13px",
                fontWeight: "600",
                cursor: "pointer",
                marginBottom: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                boxShadow: "0 4px 15px rgba(139, 92, 246, 0.3)",
              }}
            >
              {searchType === "news"
                ? "🤖 Generate Flowing News Story"
                : "🤖 Generate AI Summary Report"}
            </button>
          )}

          {searchType === "finance" && !loading && (
            <div
              style={{
                background: "rgba(59, 130, 246, 0.1)",
                border: "1px solid rgba(59, 130, 246, 0.2)",
                borderRadius: "12px",
                padding: "12px",
                marginBottom: "8px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "10px",
                }}
              >
                <h3
                  style={{
                    margin: 0,
                    fontSize: "13px",
                    fontWeight: "600",
                    color: "#93c5fd",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <FiTrendingUp size={14} /> AUD Value Chart
                </h3>
                <span style={{ fontSize: "10px", color: "#60a5fa" }}>
                  Live AUD/USD
                </span>
              </div>
              <div
                style={{
                  height: "180px",
                  width: "100%",
                  borderRadius: "8px",
                  overflow: "hidden",
                  background: "#000",
                }}
              >
                <iframe
                  src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_76d4d&symbol=FX%3AAUDUSD&interval=D&hidesidetoolbar=1&hidetoptoolbar=1&symboledit=1&saveimage=1&toolbarbg=f1f3f6&studies=%5B%5D&theme=dark&style=1&timezone=Etc%2FUTC&studies_overrides=%7B%7D&overrides=%7B%7D&enabled_features=%5B%5D&disabled_features=%5B%5D&locale=en&utm_source=localhost&utm_medium=widget&utm_campaign=chart&utm_term=FX%3AAUDUSD"
                  style={{
                    width: "100%",
                    height: "100%",
                    border: "none",
                  }}
                  title="AUD/USD Chart"
                />
              </div>
            </div>
          )}

          {results.map((item, index) => (
            <div
              key={index}
              style={{
                background: "rgba(255, 255, 255, 0.03)",
                border: "1px solid rgba(255, 255, 255, 0.05)",
                borderRadius: "12px",
                padding: "12px",
              }}
            >
              <a
                href={item.url || item.href}
                target="_blank"
                rel="noopener noreferrer"
                style={{ textDecoration: "none" }}
              >
                <h3
                  style={{
                    margin: "0 0 8px 0",
                    fontSize: "14px",
                    fontWeight: "600",
                    color: "#60a5fa",
                    lineHeight: "1.4",
                  }}
                >
                  {item.title}
                </h3>
              </a>
              <p
                style={{
                  margin: "0 0 8px 0",
                  fontSize: "12px",
                  color: "#9ca3af",
                  lineHeight: "1.5",
                }}
              >
                {item.body || item.snippet || "No description available."}
              </p>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  fontSize: "11px",
                  color: "#6b7280",
                }}
              >
                <span
                  style={{ display: "flex", alignItems: "center", gap: "4px" }}
                >
                  <FiClock size={10} /> {item.date || "Recent"}
                </span>
                <span
                  style={{ display: "flex", alignItems: "center", gap: "4px" }}
                >
                  {item.source || "Web"} <FiExternalLink size={10} />
                </span>
              </div>
            </div>
          ))}

          {!loading && results.length === 0 && !error && (
            <div
              style={{
                textAlign: "center",
                padding: "40px 0",
                color: "#6b7280",
              }}
            >
              <FiGlobe
                size={32}
                style={{ marginBottom: "12px", opacity: 0.5 }}
              />
              <p>Search the web to see results here</p>
            </div>
          )}
        </div>
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
          background: "linear-gradient(135deg, transparent 50%, #3b82f6 50%)",
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

export default InternetConsole;
