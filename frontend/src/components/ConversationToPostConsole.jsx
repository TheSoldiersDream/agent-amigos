import React, { useState, useEffect, useRef } from "react";

// ═══════════════════════════════════════════════════════════════
// CONVERSATION TO POST CONSOLE
// Captures Agent Amigos' replies and converts them to SEO posts
// Perfect for live shows, interviews, and content creation!
// Now with DRAGGABLE and RESIZABLE functionality!
// ═══════════════════════════════════════════════════════════════

const ConversationToPostConsole = ({ isOpen, onClose, messages = [] }) => {
  const [capturedReplies, setCapturedReplies] = useState([]);
  const [selectedReplies, setSelectedReplies] = useState([]);
  const [generatedPost, setGeneratedPost] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [postStyle, setPostStyle] = useState("viral");
  const [includeEmojis, setIncludeEmojis] = useState(true);
  const [hashtagCount, setHashtagCount] = useState(10);
  const [targetAudience, setTargetAudience] = useState("general");
  const [customHashtags] = useState("#darrellbuttigieg #thesoldiersdream");
  const [region] = useState("Philippines");
  const [copySuccess, setCopySuccess] = useState(false);
  const [autoCapture, setAutoCapture] = useState(true);
  const lastMessageCountRef = useRef(0);

  // ═══════════════════════════════════════════════════════════════
  // DRAGGABLE & RESIZABLE STATE - Load from localStorage
  // ═══════════════════════════════════════════════════════════════
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-convpost-console-pos");
      return saved ? JSON.parse(saved) : { x: -1, y: -1 }; // -1 means center
    } catch {
      return { x: -1, y: -1 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-convpost-console-size");
      return saved ? JSON.parse(saved) : { width: 900, height: 700 };
    } catch {
      return { width: 900, height: 700 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Save position to localStorage when it changes (but not when centered)
  useEffect(() => {
    if (position.x !== -1 && position.y !== -1) {
      localStorage.setItem(
        "amigos-convpost-console-pos",
        JSON.stringify(position)
      );
    }
  }, [position]);

  // Save size to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-convpost-console-size", JSON.stringify(size));
  }, [size]);

  // Initialize position to center on first render (only if not loaded from localStorage)
  useEffect(() => {
    if (isOpen && position.x === -1) {
      setPosition({
        x: Math.max(0, (window.innerWidth - size.width) / 2),
        y: Math.max(0, (window.innerHeight - size.height) / 2),
      });
    }
  }, [isOpen]);

  // Handle drag start
  const handleDragStart = (e) => {
    if (
      e.target.closest(".resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("input") ||
      e.target.closest("select") ||
      e.target.closest("textarea")
    )
      return;
    setIsDragging(true);
    const rect = containerRef.current.getBoundingClientRect();
    setDragOffset({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    e.preventDefault();
  };

  // Handle drag
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

  // Handle resize start
  const handleResizeStart = (e) => {
    e.stopPropagation();
    setIsResizing(true);
  };

  // Handle resize
  useEffect(() => {
    if (!isResizing) return;
    const handleMouseMove = (e) => {
      const newWidth = Math.max(500, Math.min(1200, e.clientX - position.x));
      const newHeight = Math.max(400, Math.min(900, e.clientY - position.y));
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

  // Post style options
  const postStyles = [
    { value: "viral", label: "🔥 Viral/Trending", desc: "Maximum engagement" },
    { value: "professional", label: "💼 Professional", desc: "Business tone" },
    { value: "casual", label: "😊 Casual/Friendly", desc: "Conversational" },
    { value: "inspirational", label: "✨ Inspirational", desc: "Motivational" },
    { value: "educational", label: "📚 Educational", desc: "Informative" },
    { value: "humorous", label: "😂 Humorous", desc: "Fun & entertaining" },
    {
      value: "storytelling",
      label: "📖 Storytelling",
      desc: "Narrative format",
    },
  ];

  // Target audience options
  const audienceOptions = [
    { value: "general", label: "🌍 General Audience" },
    { value: "tech", label: "💻 Tech Enthusiasts" },
    { value: "business", label: "📈 Business/Entrepreneurs" },
    { value: "gamers", label: "🎮 Gamers" },
    { value: "filipino", label: "🇵🇭 Filipino Community" },
    { value: "creators", label: "🎨 Content Creators" },
    { value: "developers", label: "👨‍💻 Developers" },
  ];

  // Auto-capture new Amigos replies
  useEffect(() => {
    if (!autoCapture || !messages) return;

    const amigosReplies = messages.filter(
      (m) => m.role === "assistant" || m.role === "bot"
    );

    if (amigosReplies.length > lastMessageCountRef.current) {
      const newReplies = amigosReplies.slice(lastMessageCountRef.current);
      setCapturedReplies((prev) => [
        ...prev,
        ...newReplies.map((r, i) => ({
          id: Date.now() + i,
          content: r.content,
          timestamp: new Date().toLocaleTimeString(),
          selected: false,
        })),
      ]);
      lastMessageCountRef.current = amigosReplies.length;
    }
  }, [messages, autoCapture]);

  // Toggle reply selection
  const toggleReplySelection = (id) => {
    setCapturedReplies((prev) =>
      prev.map((r) => (r.id === id ? { ...r, selected: !r.selected } : r))
    );
  };

  // Select all replies
  const selectAllReplies = () => {
    setCapturedReplies((prev) => prev.map((r) => ({ ...r, selected: true })));
  };

  // Clear selection
  const clearSelection = () => {
    setCapturedReplies((prev) => prev.map((r) => ({ ...r, selected: false })));
  };

  // Clear all captured
  const clearAllCaptured = () => {
    setCapturedReplies([]);
    lastMessageCountRef.current = 0;
  };

  // Generate SEO Facebook Post from selected replies
  const generatePost = () => {
    const selected = capturedReplies.filter((r) => r.selected);
    if (selected.length === 0) {
      setGeneratedPost("⚠️ Please select at least one reply to convert!");
      return;
    }

    setIsGenerating(true);

    // Combine selected content
    const combinedContent = selected.map((r) => r.content).join("\n\n");

    // Generate post locally (no backend needed!)
    setTimeout(() => {
      const post = generateLocalSEOPost(combinedContent);
      setGeneratedPost(post);
      setIsGenerating(false);
    }, 800);
  };

  // Local SEO post generator
  const generateLocalSEOPost = (content) => {
    // Extract key phrases and topics
    const words = content.toLowerCase().split(/\s+/);
    const keyTopics = [];

    // Topic detection
    if (/ai|artificial|intelligence|robot|machine/i.test(content))
      keyTopics.push("AI", "technology", "future");
    if (/game|gaming|play|cheat|trainer/i.test(content))
      keyTopics.push("gaming", "gamers", "esports");
    if (/code|program|developer|software/i.test(content))
      keyTopics.push("coding", "developers", "tech");
    if (/social|media|facebook|instagram|viral/i.test(content))
      keyTopics.push("socialmedia", "digital", "marketing");
    if (/philippines|filipino|pinoy/i.test(content))
      keyTopics.push("Philippines", "Pinoy", "Filipino");
    if (/business|entrepreneur|success/i.test(content))
      keyTopics.push("business", "entrepreneur", "success");
    if (/help|support|assist/i.test(content))
      keyTopics.push("productivity", "helpful", "tips");
    if (/dream|goal|future|plan/i.test(content))
      keyTopics.push("motivation", "dreams", "goals");
    if (/fun|funny|joke|laugh/i.test(content))
      keyTopics.push("funny", "humor", "entertainment");

    // Style-specific openers
    const openers = {
      viral: [
        "🔥 THIS IS HUGE! 🔥",
        "⚡ You WON'T believe this! ⚡",
        "🚀 BREAKING: Something amazing just happened!",
        "💥 STOP SCROLLING! You need to see this!",
        "🎯 This changes EVERYTHING!",
      ],
      professional: [
        "📊 Key Insight:",
        "💼 Professional Update:",
        "🎯 Important Announcement:",
        "📈 Here's what you need to know:",
      ],
      casual: [
        "Hey everyone! 👋",
        "So here's what happened... 😊",
        "Guys, you have to hear this! 🎉",
        "Quick update for you all! ✨",
      ],
      inspirational: [
        "✨ Let this inspire you today...",
        "🌟 Here's something powerful:",
        "💫 Remember this:",
        "🦋 Words to live by:",
      ],
      educational: [
        "📚 Did you know?",
        "💡 Here's something interesting:",
        "🎓 Learn something new today:",
        "🔍 Fun fact:",
      ],
      humorous: [
        "😂 LMAO you guys...",
        "🤣 I can't even...",
        "😆 This is too good!",
        "🎭 Comedy gold right here:",
      ],
      storytelling: [
        "📖 Let me tell you a story...",
        "🎬 Picture this:",
        "✍️ Here's what happened:",
        "🌅 Once upon a time in tech...",
      ],
    };

    // Audience-specific touches
    const audienceTouches = {
      general: "Share if you agree! 👇",
      tech: "Fellow tech enthusiasts, what do you think? 💻",
      business: "Entrepreneurs, take note! 📈",
      gamers: "Gamers, you feel me? 🎮",
      filipino: "Mga kabayan, ano sa tingin niyo? 🇵🇭",
      creators: "Creators, this is for you! 🎨",
      developers: "Devs, drop your thoughts below! 👨‍💻",
    };

    // Generate trending hashtags based on topics
    const baseHashtags = [
      "viral",
      "trending",
      "foryou",
      "fyp",
      "share",
      "follow",
      "like",
      "comment",
      "engagement",
      "growth",
    ];

    const topicHashtags = keyTopics.map((t) =>
      t.toLowerCase().replace(/\s/g, "")
    );
    const allHashtags = [...new Set([...topicHashtags, ...baseHashtags])];

    // Select random opener based on style
    const styleOpeners = openers[postStyle] || openers.viral;
    const opener =
      styleOpeners[Math.floor(Math.random() * styleOpeners.length)];

    // Clean and format the content
    let formattedContent = content
      .replace(/[\r\n]+/g, "\n")
      .split("\n")
      .filter((line) => line.trim())
      .join("\n\n");

    // Add emojis throughout if enabled
    if (includeEmojis) {
      const emojiInserts = [
        "✨",
        "💯",
        "🔥",
        "⚡",
        "🎯",
        "💪",
        "🌟",
        "🚀",
        "💫",
        "👏",
      ];
      const sentences = formattedContent.split(/(?<=[.!?])\s+/);
      formattedContent = sentences
        .map((s, i) => {
          if (i % 2 === 0 && Math.random() > 0.5) {
            return (
              s +
              " " +
              emojiInserts[Math.floor(Math.random() * emojiInserts.length)]
            );
          }
          return s;
        })
        .join(" ");
    }

    // Build the post
    let post = `${opener}\n\n`;
    post += `${formattedContent}\n\n`;

    // Add audience touch
    post += `${audienceTouches[targetAudience]}\n\n`;

    // Add call to action
    const ctas = [
      "💬 Drop a comment below!",
      "👍 Like if you agree!",
      "🔄 Share to spread the word!",
      "📲 Save this for later!",
      "👥 Tag someone who needs to see this!",
    ];
    post += `${ctas[Math.floor(Math.random() * ctas.length)]}\n\n`;

    // Add region mention
    post += `📍 ${region} 🇵🇭\n\n`;

    // Add hashtags
    const selectedHashtags = allHashtags.slice(0, hashtagCount - 2); // Reserve 2 for custom
    post += `${customHashtags} #${selectedHashtags.join(" #")}\n`;

    // Add AI attribution
    post += `\n🤖 Powered by Agent Amigos AI`;

    return post;
  };

  // Copy to clipboard
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(generatedPost);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  // Manual capture current message
  const captureManually = (text) => {
    if (!text.trim()) return;
    setCapturedReplies((prev) => [
      ...prev,
      {
        id: Date.now(),
        content: text,
        timestamp: new Date().toLocaleTimeString(),
        selected: false,
      },
    ]);
  };

  if (!isOpen) return null;

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        left: position.x === -1 ? "50%" : `${position.x}px`,
        top: position.y === -1 ? "50%" : `${position.y}px`,
        transform: position.x === -1 ? "translate(-50%, -50%)" : "none",
        width: `${size.width}px`,
        height: `${size.height}px`,
        backgroundColor: "#0a0a1a",
        borderRadius: "20px",
        border: "2px solid #8b5cf6",
        boxShadow: "0 0 60px rgba(139, 92, 246, 0.4)",
        zIndex: 10000,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        transition: isDragging || isResizing ? "none" : "box-shadow 0.3s ease",
      }}
    >
      {/* Draggable Header */}
      <div
        onMouseDown={handleDragStart}
        style={{
          padding: "16px 20px",
          background: "linear-gradient(135deg, #8b5cf6, #6366f1)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: isDragging ? "grabbing" : "grab",
          userSelect: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "1.5em" }}>📱</span>
          <div>
            <h2 style={{ margin: 0, color: "white", fontSize: "1.2em" }}>
              Conversation → SEO Post Generator
            </h2>
            <p
              style={{
                margin: 0,
                color: "rgba(255,255,255,0.8)",
                fontSize: "0.85em",
              }}
            >
              {isDragging
                ? "🔄 Moving..."
                : "Turn Agent Amigos replies into viral posts! (Drag to move)"}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "rgba(255,255,255,0.2)",
            border: "none",
            color: "white",
            width: "36px",
            height: "36px",
            borderRadius: "50%",
            cursor: "pointer",
            fontSize: "1.2em",
          }}
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          overflow: "auto",
          padding: "20px",
          display: "flex",
          gap: "20px",
        }}
      >
        {/* Left Panel - Captured Replies */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "12px",
            }}
          >
            <h3 style={{ margin: 0, color: "#8b5cf6" }}>
              🎤 Captured Replies ({capturedReplies.length})
            </h3>
            <div style={{ display: "flex", gap: "8px" }}>
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  color: "#a0a0a0",
                  fontSize: "0.85em",
                }}
              >
                <input
                  type="checkbox"
                  checked={autoCapture}
                  onChange={(e) => setAutoCapture(e.target.checked)}
                  style={{ accentColor: "#8b5cf6" }}
                />
                Auto-capture
              </label>
            </div>
          </div>

          {/* Quick Actions */}
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "6px",
              marginBottom: "12px",
            }}
          >
            <button
              onClick={selectAllReplies}
              style={{
                padding: "6px 10px",
                backgroundColor: "#1a1a2e",
                border: "1px solid #8b5cf6",
                borderRadius: "6px",
                color: "#8b5cf6",
                cursor: "pointer",
                fontSize: "0.75em",
                flexShrink: 0,
              }}
            >
              ✅ All
            </button>
            <button
              onClick={clearSelection}
              style={{
                padding: "6px 10px",
                backgroundColor: "#1a1a2e",
                border: "1px solid #6b7280",
                borderRadius: "6px",
                color: "#9ca3af",
                cursor: "pointer",
                fontSize: "0.75em",
                flexShrink: 0,
              }}
            >
              ⬜ Clear
            </button>
            <button
              onClick={clearAllCaptured}
              style={{
                padding: "6px 10px",
                backgroundColor: "#1a1a2e",
                border: "1px solid #ef4444",
                borderRadius: "6px",
                color: "#ef4444",
                cursor: "pointer",
                fontSize: "0.8em",
              }}
            >
              🗑️ Clear All
            </button>
          </div>

          {/* Replies List */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              backgroundColor: "#111827",
              borderRadius: "12px",
              padding: "12px",
              minHeight: "200px",
            }}
          >
            {capturedReplies.length === 0 ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  color: "#6b7280",
                  textAlign: "center",
                  padding: "20px",
                }}
              >
                <span style={{ fontSize: "3em", marginBottom: "12px" }}>
                  🎙️
                </span>
                <p>No replies captured yet!</p>
                <p style={{ fontSize: "0.85em" }}>
                  Chat with Agent Amigos and her replies will appear here.
                </p>
              </div>
            ) : (
              capturedReplies.map((reply) => (
                <div
                  key={reply.id}
                  onClick={() => toggleReplySelection(reply.id)}
                  style={{
                    padding: "12px",
                    marginBottom: "8px",
                    backgroundColor: reply.selected ? "#2d1f5e" : "#1f2937",
                    borderRadius: "8px",
                    border: reply.selected
                      ? "2px solid #8b5cf6"
                      : "2px solid transparent",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: "6px",
                    }}
                  >
                    <span style={{ color: "#8b5cf6", fontSize: "0.8em" }}>
                      {reply.selected ? "✅" : "⬜"} {reply.timestamp}
                    </span>
                    <span style={{ color: "#6b7280", fontSize: "0.75em" }}>
                      Click to {reply.selected ? "deselect" : "select"}
                    </span>
                  </div>
                  <p
                    style={{
                      margin: 0,
                      color: "#e5e7eb",
                      fontSize: "0.9em",
                      lineHeight: 1.5,
                      maxHeight: "80px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {reply.content.slice(0, 200)}
                    {reply.content.length > 200 ? "..." : ""}
                  </p>
                </div>
              ))
            )}
          </div>

          {/* Manual Input */}
          <div style={{ marginTop: "12px" }}>
            <textarea
              placeholder="Or paste text manually here..."
              style={{
                width: "100%",
                padding: "10px",
                backgroundColor: "#1f2937",
                border: "1px solid #374151",
                borderRadius: "8px",
                color: "white",
                fontSize: "0.9em",
                resize: "vertical",
                minHeight: "60px",
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && e.ctrlKey) {
                  captureManually(e.target.value);
                  e.target.value = "";
                }
              }}
            />
            <p
              style={{
                margin: "4px 0 0",
                color: "#6b7280",
                fontSize: "0.75em",
              }}
            >
              Press Ctrl+Enter to add manually
            </p>
          </div>
        </div>

        {/* Right Panel - Post Generator */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <h3 style={{ margin: "0 0 12px", color: "#10b981" }}>
            ⚙️ Post Settings
          </h3>

          {/* Settings Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
              marginBottom: "16px",
            }}
          >
            {/* Post Style */}
            <div>
              <label
                style={{
                  color: "#9ca3af",
                  fontSize: "0.85em",
                  display: "block",
                  marginBottom: "6px",
                }}
              >
                Post Style
              </label>
              <select
                value={postStyle}
                onChange={(e) => setPostStyle(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px",
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  color: "white",
                  fontSize: "0.9em",
                }}
              >
                {postStyles.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Target Audience */}
            <div>
              <label
                style={{
                  color: "#9ca3af",
                  fontSize: "0.85em",
                  display: "block",
                  marginBottom: "6px",
                }}
              >
                Target Audience
              </label>
              <select
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px",
                  backgroundColor: "#1f2937",
                  border: "1px solid #374151",
                  borderRadius: "8px",
                  color: "white",
                  fontSize: "0.9em",
                }}
              >
                {audienceOptions.map((a) => (
                  <option key={a.value} value={a.value}>
                    {a.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Hashtag Count */}
            <div>
              <label
                style={{
                  color: "#9ca3af",
                  fontSize: "0.85em",
                  display: "block",
                  marginBottom: "6px",
                }}
              >
                Hashtags: {hashtagCount}
              </label>
              <input
                type="range"
                min="5"
                max="20"
                value={hashtagCount}
                onChange={(e) => setHashtagCount(parseInt(e.target.value))}
                style={{ width: "100%", accentColor: "#10b981" }}
              />
            </div>

            {/* Emojis Toggle */}
            <div>
              <label
                style={{
                  color: "#9ca3af",
                  fontSize: "0.85em",
                  display: "block",
                  marginBottom: "6px",
                }}
              >
                Include Emojis
              </label>
              <button
                onClick={() => setIncludeEmojis(!includeEmojis)}
                style={{
                  width: "100%",
                  padding: "10px",
                  backgroundColor: includeEmojis ? "#065f46" : "#1f2937",
                  border: `1px solid ${includeEmojis ? "#10b981" : "#374151"}`,
                  borderRadius: "8px",
                  color: includeEmojis ? "#10b981" : "#9ca3af",
                  cursor: "pointer",
                }}
              >
                {includeEmojis ? "✅ Yes - Add Emojis" : "❌ No - Plain Text"}
              </button>
            </div>
          </div>

          {/* Custom Hashtags Display */}
          <div
            style={{
              padding: "10px",
              backgroundColor: "#1a1a2e",
              borderRadius: "8px",
              marginBottom: "12px",
            }}
          >
            <span style={{ color: "#8b5cf6", fontSize: "0.85em" }}>
              🏷️ Permanent Tags: {customHashtags}
            </span>
          </div>

          {/* Generate Button */}
          <button
            onClick={generatePost}
            disabled={
              isGenerating ||
              capturedReplies.filter((r) => r.selected).length === 0
            }
            style={{
              padding: "14px",
              background: isGenerating
                ? "#4b5563"
                : "linear-gradient(135deg, #10b981, #059669)",
              border: "none",
              borderRadius: "10px",
              color: "white",
              fontSize: "1em",
              fontWeight: "bold",
              cursor: isGenerating ? "not-allowed" : "pointer",
              marginBottom: "16px",
            }}
          >
            {isGenerating
              ? "🔄 Generating..."
              : `🚀 Generate SEO Post (${
                  capturedReplies.filter((r) => r.selected).length
                } selected)`}
          </button>

          {/* Generated Post Output */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "8px",
              }}
            >
              <h3 style={{ margin: 0, color: "#f59e0b" }}>📱 Generated Post</h3>
              {generatedPost && (
                <button
                  onClick={copyToClipboard}
                  style={{
                    padding: "6px 14px",
                    backgroundColor: copySuccess ? "#065f46" : "#1f2937",
                    border: `1px solid ${copySuccess ? "#10b981" : "#f59e0b"}`,
                    borderRadius: "6px",
                    color: copySuccess ? "#10b981" : "#f59e0b",
                    cursor: "pointer",
                    fontSize: "0.85em",
                  }}
                >
                  {copySuccess ? "✅ Copied!" : "📋 Copy to Clipboard"}
                </button>
              )}
            </div>
            <textarea
              value={generatedPost}
              onChange={(e) => setGeneratedPost(e.target.value)}
              placeholder="Your SEO-optimized Facebook post will appear here..."
              style={{
                flex: 1,
                width: "100%",
                padding: "14px",
                backgroundColor: "#111827",
                border: "1px solid #374151",
                borderRadius: "12px",
                color: "#e5e7eb",
                fontSize: "0.95em",
                lineHeight: 1.6,
                resize: "none",
                minHeight: "200px",
              }}
            />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          padding: "12px 20px",
          backgroundColor: "#111827",
          borderTop: "1px solid #374151",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span style={{ color: "#6b7280", fontSize: "0.85em" }}>
          💡 Tip: Interview Agent Amigos, then convert her best replies to
          posts!
        </span>
        <div style={{ display: "flex", gap: "8px" }}>
          <span style={{ color: "#8b5cf6", fontSize: "0.85em" }}>
            🤖 Powered by Agent Amigos
          </span>
        </div>
      </div>

      {/* Resize Handle */}
      <div
        className="resize-handle"
        onMouseDown={handleResizeStart}
        style={{
          position: "absolute",
          bottom: "0",
          right: "0",
          width: "24px",
          height: "24px",
          cursor: "se-resize",
          background:
            "linear-gradient(135deg, transparent 50%, rgba(139, 92, 246, 0.6) 50%)",
          borderBottomRightRadius: "18px",
        }}
        title="Drag to resize"
      />
    </div>
  );
};

export default ConversationToPostConsole;
