import React, { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";

// ═══════════════════════════════════════════════════════════════════════════════
// 🕷️ SCRAPER WORKBENCH v2.0 - "Social Media Post Factory"
// Redesigned with Mini Bot Agent "Scrapey" for guided UX
// Flow: URL → Scrape → AI Enhance → Facebook-Ready Post
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// 📌 PLATFORM PRESETS
// ═══════════════════════════════════════════════════════════════════════════════
const PLATFORM_PRESETS = {
  auto: {
    name: "🤖 Auto-Detect",
    icon: "🤖",
    selectors: "article, .post, .content, p, h1, h2, h3",
  },
  facebook: {
    name: "📘 Facebook",
    icon: "📘",
    selectors:
      "div[dir='auto'], span[dir='auto'], div[role='article'], [data-ad-preview='message']",
  },
  twitter: {
    name: "🐦 Twitter/X",
    icon: "🐦",
    selectors: "article[data-testid='tweet'], div[data-testid='tweetText']",
  },
  instagram: {
    name: "📸 Instagram",
    icon: "📸",
    selectors: "article, span._ap3a, h1._ap3a",
  },
  youtube: {
    name: "🎬 YouTube",
    icon: "🎬",
    selectors: "#title h1, #description-text, #content-text",
  },
  news: {
    name: "📰 News Article",
    icon: "📰",
    selectors: "article, .article-body, .story-body, p",
  },
  blog: {
    name: "📝 Blog Post",
    icon: "📝",
    selectors: "article, .post-content, .entry-content, p",
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// 🤖 SCRAPEY BOT - Mini Agent Messages
// ═══════════════════════════════════════════════════════════════════════════════
const SCRAPEY_MESSAGES = {
  idle: [
    "Ready to scrape! 🕷️",
    "Paste a URL to get started!",
    "What shall we scrape today?",
  ],
  thinking: [
    "Hmm, analyzing that URL...",
    "Let me figure this out...",
    "Processing...",
  ],
  scraping: [
    "Fetching content... 🔍",
    "Crawling the web... 🕸️",
    "Grabbing that data...",
  ],
  success: [
    "Got it! Content extracted! ✨",
    "Success! Ready to enhance!",
    "Nailed it! 🎯",
  ],
  enhancing: [
    "AI magic in progress... ✨",
    "Making it viral-worthy...",
    "SEO optimization...",
  ],
  done: [
    "Your post is ready! 📱",
    "Copy and paste to Facebook!",
    "Go viral! 🚀",
  ],
  error: [
    "Oops! Something went wrong 😅",
    "Let me try again...",
    "That didn't work...",
  ],
  tip_facebook: [
    "💡 For Facebook, use Dynamic mode with your logged-in browser!",
  ],
  tip_seo: ["💡 Tip: Add trending hashtags for more reach!"],
};

const getRandomMessage = (category) => {
  const messages = SCRAPEY_MESSAGES[category] || SCRAPEY_MESSAGES.idle;
  return messages[Math.floor(Math.random() * messages.length)];
};

// ═══════════════════════════════════════════════════════════════════════════════
// 🎨 SCRAPEY BOT COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════
const ScrapeyBot = ({ mood, message, isAnimating }) => {
  const moodEmojis = {
    idle: "🕷️",
    thinking: "🤔",
    working: "⚙️",
    happy: "😊",
    success: "🎉",
    error: "😅",
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "10px",
        padding: "10px 12px",
        background:
          "linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(245, 158, 11, 0.08))",
        borderRadius: "12px",
        border: "1px solid rgba(251, 191, 36, 0.3)",
        marginBottom: "10px",
      }}
    >
      {/* Bot Avatar */}
      <div
        style={{
          width: "40px",
          height: "40px",
          borderRadius: "50%",
          background: "linear-gradient(135deg, #fbbf24, #f59e0b)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "1.3em",
          boxShadow: "0 4px 15px rgba(251, 191, 36, 0.4)",
          animation: isAnimating ? "pulse 1s infinite" : "none",
          flexShrink: 0,
        }}
      >
        {moodEmojis[mood] || "🕷️"}
      </div>

      {/* Speech Bubble */}
      <div
        style={{
          flex: 1,
          background: "rgba(15, 23, 42, 0.6)",
          borderRadius: "12px",
          padding: "8px 12px",
          position: "relative",
          fontSize: "0.8em",
          color: "#e2e8f0",
          lineHeight: "1.4",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "-6px",
            top: "12px",
            width: 0,
            height: 0,
            borderTop: "6px solid transparent",
            borderBottom: "6px solid transparent",
            borderRight: "6px solid rgba(15, 23, 42, 0.6)",
          }}
        />
        <div
          style={{
            fontWeight: "bold",
            fontSize: "0.75em",
            color: "#fbbf24",
            marginBottom: "2px",
          }}
        >
          Scrapey 🕷️
        </div>
        {message}
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// 📱 FACEBOOK POST PREVIEW COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════
const FacebookPostPreview = ({ content, onCopy, copied }) => {
  if (!content) return null;

  // Highlight hashtags
  const formatContent = (text) => {
    return text.split(/(#\w+)/g).map((part, i) =>
      part.startsWith("#") ? (
        <span key={i} style={{ color: "#1877f2", fontWeight: "500" }}>
          {part}
        </span>
      ) : (
        part
      )
    );
  };

  return (
    <div
      style={{
        background: "#fff",
        borderRadius: "8px",
        overflow: "hidden",
        boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
        border: "1px solid #dddfe2",
      }}
    >
      {/* FB Header */}
      <div
        style={{
          padding: "12px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          borderBottom: "1px solid #eff2f5",
        }}
      >
        <div
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "50%",
            background: "linear-gradient(135deg, #fbbf24, #f59e0b)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "1.2em",
          }}
        >
          🤖
        </div>
        <div style={{ flex: 1 }}>
          <div
            style={{ fontWeight: "600", fontSize: "0.9em", color: "#050505" }}
          >
            Your Page
          </div>
          <div
            style={{
              fontSize: "0.75em",
              color: "#65676b",
              display: "flex",
              alignItems: "center",
              gap: "4px",
            }}
          >
            Just now · <span style={{ fontSize: "0.9em" }}>🌍</span>
          </div>
        </div>
        <button
          onClick={onCopy}
          style={{
            background: copied ? "#42b72a" : "#1877f2",
            color: "#fff",
            border: "none",
            padding: "6px 16px",
            borderRadius: "6px",
            fontWeight: "600",
            fontSize: "0.8em",
            cursor: "pointer",
            transition: "all 0.2s",
          }}
        >
          {copied ? "✓ Copied!" : "📋 Copy"}
        </button>
      </div>

      {/* FB Content */}
      <div
        style={{
          padding: "12px",
          fontSize: "0.9em",
          color: "#050505",
          lineHeight: "1.5",
          maxHeight: "200px",
          overflow: "auto",
          whiteSpace: "pre-wrap",
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        }}
      >
        {formatContent(content)}
      </div>

      {/* FB Reactions Bar */}
      <div
        style={{
          padding: "8px 12px",
          borderTop: "1px solid #eff2f5",
          display: "flex",
          justifyContent: "space-around",
          color: "#65676b",
          fontSize: "0.85em",
          fontWeight: "600",
        }}
      >
        <span style={{ cursor: "pointer" }}>👍 Like</span>
        <span style={{ cursor: "pointer" }}>💬 Comment</span>
        <span style={{ cursor: "pointer" }}>↗️ Share</span>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════════
// 🎯 MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════
const ScraperWorkbench = ({
  isOpen,
  onToggle,
  backendUrl = "http://127.0.0.1:65252",
  onScreenUpdate,
}) => {
  // Position & Size State
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-scraper-pos");
      return saved ? JSON.parse(saved) : { x: 50, y: 80 };
    } catch {
      return { x: 50, y: 80 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-scraper-size");
      return saved ? JSON.parse(saved) : { width: 420, height: 650 };
    } catch {
      return { width: 420, height: 650 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Save to localStorage
  useEffect(() => {
    localStorage.setItem("amigos-scraper-pos", JSON.stringify(position));
  }, [position]);
  useEffect(() => {
    localStorage.setItem("amigos-scraper-size", JSON.stringify(size));
  }, [size]);

  // ═══════════════════════════════════════════════════════════════════════════
  // 🕷️ SCRAPEY BOT STATE
  // ═══════════════════════════════════════════════════════════════════════════
  const [botMood, setBotMood] = useState("idle");
  const [botMessage, setBotMessage] = useState(getRandomMessage("idle"));
  const [botAnimating, setBotAnimating] = useState(false);

  // ═══════════════════════════════════════════════════════════════════════════
  // 📝 FORM STATE - Single unified state for the wizard flow
  // ═══════════════════════════════════════════════════════════════════════════
  const [currentStep, setCurrentStep] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);

  const [formData, setFormData] = useState({
    // Step 1: Source
    url: "",
    platform: "auto",
    useDynamic: true,

    // Step 2: Extracted Content
    rawContent: "",
    cleanedContent: "",

    // Step 3: Enhancement Options
    postStyle: "viral",
    audience: "general",
    region: "Philippines",
    hashtagCount: 25,
    customHashtags: "#darrellbuttigieg #thesoldiersdream",
    includeEmojis: true,
    includeCTA: true,

    // Step 4: Output
    finalPost: "",
  });

  const [copySuccess, setCopySuccess] = useState(false);

  // ═══════════════════════════════════════════════════════════════════════════
  // 🎬 DRAG & RESIZE HANDLERS
  // ═══════════════════════════════════════════════════════════════════════════
  const handleMouseDown = (e) => {
    if (
      e.target.closest(".resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("input") ||
      e.target.closest("textarea") ||
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
        // Clamp position to keep window visible within viewport
        const maxX = window.innerWidth - 100; // Keep at least 100px visible on right
        const maxY = window.innerHeight - 60; // Keep at least 60px visible on bottom (header)
        const minX = -size.width + 100; // Keep at least 100px visible on left
        const minY = 0; // Don't allow going above viewport

        setPosition({
          x: Math.min(maxX, Math.max(minX, e.clientX - dragOffset.x)),
          y: Math.min(maxY, Math.max(minY, e.clientY - dragOffset.y)),
        });
      }
      if (isResizing) {
        const rect = containerRef.current.getBoundingClientRect();
        // Limit resize to viewport bounds
        const maxWidth = window.innerWidth - position.x - 20;
        const maxHeight = window.innerHeight - position.y - 20;
        setSize({
          width: Math.min(maxWidth, Math.max(380, e.clientX - rect.left + 10)),
          height: Math.min(maxHeight, Math.max(450, e.clientY - rect.top + 10)),
        });
      }
    },
    [isDragging, isResizing, dragOffset, size.width, position.x, position.y]
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setIsResizing(false);
  }, []);

  // Auto-correct window position if it goes off-screen (on open or window resize)
  useEffect(() => {
    const checkAndCorrectPosition = () => {
      if (!isOpen) return;

      const maxX = window.innerWidth - 100;
      const maxY = window.innerHeight - 60;
      const minX = -size.width + 100;

      let needsCorrection = false;
      let newX = position.x;
      let newY = position.y;

      if (position.x > maxX) {
        newX = Math.max(50, maxX - 50);
        needsCorrection = true;
      }
      if (position.x < minX) {
        newX = 50;
        needsCorrection = true;
      }
      if (position.y > maxY) {
        newY = 80;
        needsCorrection = true;
      }
      if (position.y < 0) {
        newY = 80;
        needsCorrection = true;
      }

      if (needsCorrection) {
        setPosition({ x: newX, y: newY });
      }
    };

    checkAndCorrectPosition();
    window.addEventListener("resize", checkAndCorrectPosition);
    return () => window.removeEventListener("resize", checkAndCorrectPosition);
  }, [isOpen, position.x, position.y, size.width]);

  // Reset position helper function
  const resetWindowPosition = useCallback(() => {
    setPosition({ x: 50, y: 80 });
    setSize({ width: 420, height: 650 });
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

  // ═══════════════════════════════════════════════════════════════════════════
  // 🔍 STEP 1: SCRAPE CONTENT
  // ═══════════════════════════════════════════════════════════════════════════
  const handleScrape = async () => {
    if (!formData.url.trim()) {
      setBotMood("error");
      setBotMessage("Please enter a URL first! 🔗");
      return;
    }

    setIsProcessing(true);
    setBotMood("working");
    setBotMessage(getRandomMessage("scraping"));
    setBotAnimating(true);

    try {
      const preset =
        PLATFORM_PRESETS[formData.platform] || PLATFORM_PRESETS.auto;

      const endpoint = formData.useDynamic
        ? "/scrape/dynamic"
        : "/scrape/static";
      const payload = formData.useDynamic
        ? {
            url: formData.url,
            wait_for_selector: "body",
            wait_timeout: 15,
            headless: true,
            selectors: preset.selectors,
          }
        : {
            url: formData.url,
            selectors: preset.selectors,
          };

      const response = await axios.post(`${backendUrl}${endpoint}`, payload);
      const data = response.data;

      // Extract content from various possible locations
      let extracted = "";
      if (data.matches && typeof data.matches === "object") {
        const texts = [];
        for (const vals of Object.values(data.matches)) {
          if (Array.isArray(vals)) {
            texts.push(
              ...vals.filter(
                (v) => typeof v === "string" && v.trim().length > 15
              )
            );
          }
        }
        extracted = [...new Set(texts)].join("\n\n");
      }
      if (!extracted || extracted.length < 50) {
        extracted =
          data.text ||
          data.content ||
          data.fallback ||
          JSON.stringify(data, null, 2);
      }

      // Clean up the content
      const cleaned = extracted
        .substring(0, 8000)
        .replace(/\\n/g, "\n")
        .replace(/\\"/g, '"')
        .replace(/\s+/g, " ")
        .trim();

      setFormData((prev) => ({
        ...prev,
        rawContent: extracted,
        cleanedContent: cleaned,
      }));
      setCurrentStep(2);
      setBotMood("success");
      setBotMessage(getRandomMessage("success"));
    } catch (err) {
      setBotMood("error");
      setBotMessage(
        `Error: ${err.message}. Try Dynamic mode if it's Facebook!`
      );
    }

    setBotAnimating(false);
    setIsProcessing(false);
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // ⚡ STEP 3: AI ENHANCE & GENERATE POST
  // ═══════════════════════════════════════════════════════════════════════════
  const handleEnhanceAndGenerate = async () => {
    if (!formData.cleanedContent.trim()) {
      setBotMood("error");
      setBotMessage("No content to enhance! Go back and scrape first.");
      return;
    }

    setIsProcessing(true);
    setBotMood("working");
    setBotMessage(getRandomMessage("enhancing"));
    setBotAnimating(true);

    const styleGuides = {
      viral:
        "engaging, shareable with curiosity gaps and emotional hooks that make people STOP scrolling",
      professional:
        "professional yet personable, suitable for business audiences while remaining engaging",
      casual: "friendly, conversational like you're talking to a close friend",
      promotional:
        "compelling promotional angle highlighting benefits with subtle urgency",
      educational:
        "educational and valuable, teaching readers something they didn't know",
      inspirational:
        "inspirational and uplifting, motivating readers to take positive action",
    };

    const audienceContext = {
      general: "everyday social media users who enjoy engaging content",
      filipino:
        "Filipino audience who appreciate relatable local content and Taglish occasionally",
      business: "professionals, entrepreneurs, and business-minded individuals",
      tech: "tech enthusiasts, developers, and early adopters",
      youth:
        "Gen Z and younger millennials who love trendy, meme-worthy content",
    };

    // ═══════════════════════════════════════════════════════════════════════════
    // 🚀 ENHANCED AI PROMPT - Deep storytelling, engaging facts, viral formula
    // ═══════════════════════════════════════════════════════════════════════════
    const prompt = `You are a WORLD-CLASS STORYTELLER and VIRAL CONTENT STRATEGIST who has created posts that reached MILLIONS.

## 🎯 YOUR MISSION:
Transform the scraped content into a CAPTIVATING, SHAREABLE Facebook post that makes readers feel something, learn something, and WANT to engage.

## 📊 RAW CONTENT TO TRANSFORM (from: ${formData.url}):
"""
${formData.cleanedContent.substring(0, 5000)}
"""

## 🧠 DEEP CONTENT ANALYSIS (perform these steps):

### STEP 1: EXTRACT KEY FACTS
- What are the SPECIFIC numbers, dates, names, or statistics?
- What is the SURPRISING or unexpected element?
- What is the HUMAN element or emotional core?
- What makes this TIMELY or relevant NOW?

### STEP 2: FIND THE STORY ANGLE
Choose the most powerful angle:
- **The Underdog Story**: Someone overcoming odds
- **The Revelation**: "What most people don't know is..."
- **The Transformation**: Before vs. After
- **The Warning**: "If you're not paying attention to this..."
- **The Celebration**: Good news worth sharing
- **The Debate**: "Here's why people are divided on this..."
- **The Insider Scoop**: Behind-the-scenes truth

### STEP 3: IDENTIFY EMOTIONAL HOOKS
What emotion will drive engagement?
- 🔥 Outrage/Passion (for controversial topics)
- 😲 Surprise/Shock (for unexpected facts)
- 💪 Inspiration/Hope (for uplifting stories)
- 🤔 Curiosity (for mysteries or questions)
- ❤️ Connection (for relatable experiences)
- 😂 Humor (if appropriate)

## 📝 VIRAL POST REQUIREMENTS:
- **LANGUAGE**: ENGLISH only (mandatory!)
- **STYLE**: ${styleGuides[formData.postStyle] || styleGuides.viral}
- **AUDIENCE**: ${audienceContext[formData.audience] || audienceContext.general}
- **REGION**: ${formData.region}
${
  formData.includeEmojis
    ? "- **EMOJIS**: Strategic use to enhance key points and readability"
    : "- **EMOJIS**: None"
}
${
  formData.includeCTA
    ? "- **CTA**: Compelling call-to-action driving comments/shares"
    : ""
}

## 📱 WINNING POST STRUCTURE:

### 🪝 THE HOOK (First 2 lines - CRITICAL!)
The hook must create an "open loop" that DEMANDS readers continue. Use ONE of these proven formulas:
- **Pattern Interrupt**: "Wait... did this just actually happen?"
- **Specific Curiosity**: "3 things about [topic] that changed my perspective..."
- **Bold Statement**: "Unpopular opinion: [surprising take]"
- **Personal Revelation**: "I've been thinking about this all day..."
- **Numbers Hook**: "[Specific number] just dropped and it means [impact]"
- **Question Hook**: "Has anyone else noticed [observation]?"

### 📖 THE STORY (Body - 2-4 SHORT paragraphs)
Structure it like a mini-story:
1. **Set the Scene**: Quick context (1-2 sentences)
2. **Build Tension**: What's at stake or interesting?
3. **Key Facts**: Include SPECIFIC details from the content (numbers, names, dates)
4. **The Insight**: Your unique perspective or takeaway
5. **Bridge to Reader**: Make it relevant to THEIR life

Writing tips:
- Each paragraph: MAX 3 sentences
- Use line breaks for mobile scrolling
- Include at least ONE specific fact/statistic
- Make abstract concepts CONCRETE with examples
- Use "you" to speak directly to reader

### 🎯 THE CLOSE (Engagement trigger)
${
  formData.includeCTA
    ? `End with ONE of these engagement drivers:
- **Opinion Poll**: "What's your take? A or B?"
- **Personal Experience**: "Has this happened to you?"
- **Prediction Request**: "Where do you think this is heading?"
- **Tag Request**: "Tag someone who needs to see this"
- **Controversial Question**: "Am I wrong for thinking...?"`
    : "End with a memorable closing thought or insight"
}

### #️⃣ HASHTAGS (New line)
Include ${formData.hashtagCount} hashtags:
- MUST include: ${formData.customHashtags}
- Mix: trending + niche + topic-specific
- Think SEO: what would someone search for?

## ⚠️ ABSOLUTE RULES (FOLLOW OR FAIL):
1. ENGLISH ONLY - no exceptions
2. NO AI-sounding phrases ("I'd be happy to...", "Here's your post...")
3. SPECIFIC > GENERIC (use actual facts from content)
4. SHORT PARAGRAPHS (max 3 sentences each)
5. AUTHENTIC VOICE (sound like a real person)
6. ACCURACY (don't invent facts not in the source)
7. MOBILE-FIRST (visual line breaks matter)
8. EMOTION > INFORMATION (make them FEEL something)

## 🎬 OUTPUT:
Write ONLY the final Facebook post. Start directly with the hook. No introductions, no explanations, just the post ready to copy-paste:
Write ONLY the final Facebook post (ready to copy-paste). Start directly with the hook, no introductions:`;

    try {
      const response = await axios.post(`${backendUrl}/chat`, {
        message: prompt,
        conversation_history: [],
        require_approval: false,
      });

      let aiPost =
        response.data?.response || response.data?.message || response.data;
      if (typeof aiPost === "object") {
        aiPost = aiPost.response || aiPost.message || aiPost.text || "";
      }

      // Clean up AI response
      if (aiPost && aiPost.length > 50) {
        let cleaned = aiPost
          // Remove common AI prefixes
          .replace(
            /^(Here's|Here is|I've created|Below is|Sure!|Certainly!|Of course!)[\s\S]*?:\s*/gi,
            ""
          )
          .replace(
            /^(Here's your|Your post|The post|Final post)[\s\S]*?:\s*/gi,
            ""
          )
          // Remove code blocks
          .replace(/```[\s\S]*?```/g, "")
          // Remove markdown headers
          .replace(/^#{1,3}\s+/gm, "")
          // Clean up extra whitespace
          .replace(/\n{3,}/g, "\n\n")
          .trim();

        // Ensure custom hashtags are included
        const firstHashtag = formData.customHashtags.split(" ")[0];
        if (firstHashtag && !cleaned.includes(firstHashtag)) {
          cleaned += "\n\n" + formData.customHashtags;
        }

        setFormData((prev) => ({ ...prev, finalPost: cleaned }));
        setCurrentStep(4);
        setBotMood("success");
        setBotMessage(getRandomMessage("done"));
      } else {
        // Fallback to local generation
        generateLocalPost();
      }
    } catch (err) {
      console.log("AI failed, using local generation:", err.message);
      generateLocalPost();
    }

    setBotAnimating(false);
    setIsProcessing(false);
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // 📝 ENHANCED LOCAL POST GENERATOR (Fallback with smart content extraction)
  // ═══════════════════════════════════════════════════════════════════════════
  const generateLocalPost = () => {
    const content = formData.cleanedContent;
    const url = formData.url;

    // ═══════════════════════════════════════════════════════════════════════════
    // STEP 1: INTELLIGENT SENTENCE EXTRACTION
    // ═══════════════════════════════════════════════════════════════════════════
    const sentences = content
      .replace(/\s+/g, " ")
      .split(/[.!?]+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 20 && s.length < 400)
      .filter(
        (s) =>
          !s.includes("<!DOCTYPE") &&
          !s.includes("<html") &&
          !s.includes("javascript") &&
          !s.includes("cookie") &&
          !s.includes("privacy policy")
      )
      .filter((s) => /[a-zA-Z]{3,}/.test(s)); // Must contain real words

    // ═══════════════════════════════════════════════════════════════════════════
    // STEP 2: EXTRACT KEY ENGAGEMENT ELEMENTS
    // ═══════════════════════════════════════════════════════════════════════════

    // Find sentences with NUMBERS (statistics are engaging!)
    const numbersPattern =
      /(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(%|percent|million|billion|thousand|K|M|B)?/i;
    const sentenceWithNumber = sentences.find((s) => numbersPattern.test(s));

    // Find sentences with PROPER NAMES (people, places, companies)
    const namesPattern = /[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+/;
    const sentenceWithName = sentences.find((s) => namesPattern.test(s));

    // Find EMOTIONAL/ACTION words
    const emotionalPattern =
      /(amazing|incredible|shocking|breaking|exclusive|revealed|finally|secret|truth|warning|must|urgent|confirmed|official|announces?|launched?|releases?)/i;
    const emotionalSentence = sentences.find((s) => emotionalPattern.test(s));

    // Find sentences with QUOTES
    const quoteSentence = sentences.find(
      (s) => /[""].*[""]/.test(s) || /".*"/.test(s)
    );

    // Find the most INFORMATIVE sentence (balance length with content)
    const scoredSentences = sentences
      .map((s) => {
        let score = 0;
        if (numbersPattern.test(s)) score += 3;
        if (namesPattern.test(s)) score += 2;
        if (emotionalPattern.test(s)) score += 2;
        if (s.length > 50 && s.length < 200) score += 1;
        return { sentence: s, score };
      })
      .sort((a, b) => b.score - a.score);

    const topSentences = scoredSentences.slice(0, 5);

    // ═══════════════════════════════════════════════════════════════════════════
    // STEP 3: DETERMINE CONTENT TYPE FROM URL
    // ═══════════════════════════════════════════════════════════════════════════
    let contentType = "news";
    let emoji = "📰";

    if (url.includes("facebook.com")) {
      contentType = "social";
      emoji = "📱";
    } else if (url.includes("twitter.com") || url.includes("x.com")) {
      contentType = "viral";
      emoji = "🔥";
    } else if (url.includes("instagram.com")) {
      contentType = "trending";
      emoji = "✨";
    } else if (url.includes("youtube.com")) {
      contentType = "video";
      emoji = "🎬";
    } else if (
      url.includes("news") ||
      url.includes("bbc") ||
      url.includes("cnn")
    ) {
      contentType = "breaking";
      emoji = "🚨";
    } else if (url.includes("tech") || url.includes("gadget")) {
      contentType = "tech";
      emoji = "💻";
    } else if (url.includes("sport")) {
      contentType = "sports";
      emoji = "🏆";
    } else if (url.includes("entertainment") || url.includes("celebrity")) {
      contentType = "entertainment";
      emoji = "🌟";
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // STEP 4: SELECT BEST HOOK BASED ON CONTENT
    // ═══════════════════════════════════════════════════════════════════════════
    const hookTemplates = {
      // Number-based hooks (most engaging!)
      withNumber: [
        `${emoji} This number just dropped and it changes everything...`,
        `Wait... ${emoji} Did you see this stat? I had to double-check...`,
        `${emoji} The numbers are in, and they're shocking...`,
      ],
      // Name-based hooks (adds credibility)
      withName: [
        `${emoji} This is making headlines right now...`,
        `Everyone's talking about this ${emoji} Here's what's happening...`,
        `${emoji} JUST IN: Big news you need to know about...`,
      ],
      // Emotional hooks (drives engagement)
      emotional: [
        `${emoji} I can't stop thinking about this...`,
        `This changes everything ${emoji} Let me explain...`,
        `${emoji} If you haven't seen this yet, you need to...`,
      ],
      // Quote hooks
      withQuote: [
        `"${
          quoteSentence
            ? quoteSentence.match(/[""](.*)[""]|"(.*)"/)?.[1] || ""
            : ""
        }" ${emoji}`,
        `${emoji} This quote is going viral for a reason...`,
      ],
      // Generic engaging hooks
      generic: [
        `${emoji} This caught my attention and I think you need to see it...`,
        `${emoji} Something interesting is happening and I wanted to share...`,
        `Here's something worth talking about ${emoji}`,
        `${emoji} I've been seeing this everywhere - here's the scoop...`,
        `Can we talk about this? ${emoji}`,
      ],
    };

    // Select hook based on what content we found
    let hookArray;
    if (sentenceWithNumber) hookArray = hookTemplates.withNumber;
    else if (sentenceWithName) hookArray = hookTemplates.withName;
    else if (emotionalSentence) hookArray = hookTemplates.emotional;
    else if (quoteSentence) hookArray = hookTemplates.withQuote;
    else hookArray = hookTemplates.generic;

    const hook = hookArray[Math.floor(Math.random() * hookArray.length)];

    // ═══════════════════════════════════════════════════════════════════════════
    // STEP 5: BUILD COMPELLING BODY WITH BEST CONTENT
    // ═══════════════════════════════════════════════════════════════════════════

    // Priority: Number fact > Named entity > Emotional > Length-scored
    const mainSentence =
      sentenceWithNumber ||
      sentenceWithName ||
      emotionalSentence ||
      topSentences[0]?.sentence ||
      sentences[0];
    const supportSentence1 = topSentences[1]?.sentence || sentences[1] || "";
    const supportSentence2 = topSentences[2]?.sentence || sentences[2] || "";

    // Format body with strategic line breaks
    let body = "";
    if (mainSentence) {
      body += `${formData.includeEmojis ? "📌 " : ""}${mainSentence}`;
    }
    if (supportSentence1 && supportSentence1 !== mainSentence) {
      body += `\n\n${formData.includeEmojis ? "➡️ " : ""}${supportSentence1}`;
    }
    if (
      supportSentence2 &&
      supportSentence2 !== mainSentence &&
      supportSentence2 !== supportSentence1
    ) {
      body += `\n\n${formData.includeEmojis ? "💡 " : ""}${supportSentence2}`;
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // STEP 6: ENGAGEMENT-DRIVING CALL TO ACTION
    // ═══════════════════════════════════════════════════════════════════════════
    const ctaTemplates = [
      "\n\n💬 What do you think about this? I'm curious to hear your take!",
      "\n\n👇 Has anyone else noticed this? Drop your thoughts below!",
      "\n\n🤔 Agree or disagree? Let's discuss in the comments!",
      "\n\n💭 This got me thinking... what's your opinion?",
      "\n\n🔄 Share this if you think more people should know!",
      "\n\n👀 Am I the only one who finds this interesting? Comment below!",
      "\n\n📢 Tag someone who needs to see this!",
    ];

    const cta = formData.includeCTA
      ? ctaTemplates[Math.floor(Math.random() * ctaTemplates.length)]
      : "";

    // ═══════════════════════════════════════════════════════════════════════════
    // STEP 7: SMART HASHTAG GENERATION
    // ═══════════════════════════════════════════════════════════════════════════
    const baseHashtags = formData.customHashtags;

    // Extract potential hashtag words from content
    const words = content.toLowerCase().match(/\b[a-z]{4,15}\b/g) || [];
    const wordFreq = {};
    words.forEach((w) => {
      if (
        ![
          "this",
          "that",
          "with",
          "from",
          "have",
          "been",
          "were",
          "they",
          "their",
          "about",
          "would",
          "could",
          "should",
        ].includes(w)
      ) {
        wordFreq[w] = (wordFreq[w] || 0) + 1;
      }
    });

    const topWords = Object.entries(wordFreq)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([word]) => `#${word}`);

    // Content-type hashtags
    const typeHashtags = {
      news: ["#breakingnews", "#news", "#update", "#headlines"],
      social: ["#trending", "#viral", "#socialmedia", "#share"],
      tech: ["#tech", "#innovation", "#digital", "#future"],
      sports: ["#sports", "#win", "#gameday", "#highlights"],
      entertainment: ["#entertainment", "#celebrity", "#showbiz"],
      breaking: ["#breaking", "#justnow", "#alert", "#important"],
      video: ["#video", "#watch", "#content", "#creator"],
      trending: ["#trending", "#explore", "#fyp", "#mustwatch"],
    };

    const additionalTags = typeHashtags[contentType] || typeHashtags.social;
    const genericTags = [
      "#fyp",
      "#explore",
      "#viral",
      "#share",
      "#community",
      "#mustread",
      "#engagement",
    ];

    // Build final hashtags (avoid duplicates)
    const allTags = new Set([
      ...baseHashtags.split(" ").filter(Boolean),
      ...topWords,
      ...additionalTags,
      ...genericTags,
    ]);

    const finalHashtags = Array.from(allTags)
      .slice(0, formData.hashtagCount)
      .join(" ");

    // ═══════════════════════════════════════════════════════════════════════════
    // STEP 8: ASSEMBLE FINAL POST
    // ═══════════════════════════════════════════════════════════════════════════
    const post = `${hook}

${body}
${cta}

${finalHashtags}`;

    setFormData((prev) => ({ ...prev, finalPost: post.trim() }));
    setCurrentStep(4);
    setBotMood("success");
    setBotMessage(
      "📱 Created an engaging post with smart extraction! Ready to go viral!"
    );
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // 📋 COPY TO CLIPBOARD
  // ═══════════════════════════════════════════════════════════════════════════
  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(formData.finalPost);
      setCopySuccess(true);
      setBotMood("happy");
      setBotMessage("Copied! Now paste it on Facebook! 🚀");
      setTimeout(() => setCopySuccess(false), 3000);
    } catch {
      // Fallback
      const ta = document.createElement("textarea");
      ta.value = formData.finalPost;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      if (ta) {
        try {
          if (typeof ta.remove === "function") {
            ta.remove();
          } else if (ta.parentNode && ta.parentNode.contains(ta)) {
            ta.parentNode.removeChild(ta);
          }
        } catch (e) {
          console.warn("Failed to remove fallback textarea", e);
        }
      }
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 3000);
    }
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // 🔄 RESET FLOW
  // ═══════════════════════════════════════════════════════════════════════════
  const resetFlow = () => {
    setFormData({
      url: "",
      platform: "auto",
      useDynamic: true,
      rawContent: "",
      cleanedContent: "",
      postStyle: "viral",
      audience: "general",
      region: "Philippines",
      hashtagCount: 25,
      customHashtags: "#darrellbuttigieg #thesoldiersdream",
      includeEmojis: true,
      includeCTA: true,
      finalPost: "",
    });
    setCurrentStep(1);
    setBotMood("idle");
    setBotMessage(getRandomMessage("idle"));
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // 🎨 STYLES
  // ═══════════════════════════════════════════════════════════════════════════
  const inputStyle = {
    background: "rgba(15, 23, 42, 0.8)",
    border: "1px solid rgba(251, 191, 36, 0.3)",
    borderRadius: "8px",
    padding: "10px 12px",
    color: "#f8fafc",
    fontSize: "0.85em",
    width: "100%",
    outline: "none",
  };

  const stepIndicator = (num, label, isActive, isComplete) => (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
        opacity: isActive ? 1 : isComplete ? 0.8 : 0.4,
      }}
    >
      <div
        style={{
          width: "22px",
          height: "22px",
          borderRadius: "50%",
          background: isComplete
            ? "#10b981"
            : isActive
            ? "#fbbf24"
            : "rgba(255,255,255,0.2)",
          color: isComplete || isActive ? "#111" : "#888",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "0.7em",
          fontWeight: "bold",
        }}
      >
        {isComplete ? "✓" : num}
      </div>
      <span
        style={{ fontSize: "0.7em", color: isActive ? "#fbbf24" : "#94a3b8" }}
      >
        {label}
      </span>
    </div>
  );

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
        background: "rgba(11, 15, 25, 0.97)",
        color: "#f8fafc",
        borderRadius: "16px",
        border: "1px solid rgba(251, 191, 36, 0.4)",
        display: "flex",
        flexDirection: "column",
        zIndex: 999,
        boxShadow:
          "0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(251, 191, 36, 0.1)",
        backdropFilter: "blur(20px)",
        cursor: isDragging ? "grabbing" : "default",
      }}
    >
      {/* ═══════════════════════════════════════════════════════════════════
          HEADER
      ═══════════════════════════════════════════════════════════════════ */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          background:
            "linear-gradient(135deg, rgba(24, 119, 242, 0.2), rgba(66, 183, 42, 0.1))",
          borderRadius: "16px 16px 0 0",
          cursor: "grab",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #1877f2, #42b72a)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.1em",
            }}
          >
            📱
          </div>
          <div>
            <div style={{ fontWeight: "bold", fontSize: "0.9em" }}>
              Social Post Factory
            </div>
            <div style={{ fontSize: "0.65em", color: "#94a3b8" }}>
              URL → Scrape → AI → Facebook
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          {/* Reset Position Button */}
          <button
            onClick={resetWindowPosition}
            title="Reset window position"
            style={{
              background: "rgba(255,255,255,0.1)",
              border: "1px solid rgba(255,255,255,0.2)",
              width: "28px",
              height: "28px",
              borderRadius: "50%",
              color: "#94a3b8",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.8em",
            }}
          >
            ⟲
          </button>
          {/* Close Button */}
          <button
            onClick={onToggle}
            style={{
              background: "#ff4757",
              border: "none",
              width: "28px",
              height: "28px",
              borderRadius: "50%",
              color: "white",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.9em",
            }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          STEP INDICATOR BAR
      ═══════════════════════════════════════════════════════════════════ */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          padding: "10px 16px",
          borderBottom: "1px solid rgba(255,255,255,0.05)",
          background: "rgba(0,0,0,0.2)",
        }}
      >
        {stepIndicator(1, "Source", currentStep === 1, currentStep > 1)}
        {stepIndicator(2, "Content", currentStep === 2, currentStep > 2)}
        {stepIndicator(3, "Enhance", currentStep === 3, currentStep > 3)}
        {stepIndicator(4, "Post", currentStep === 4, false)}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          CONTENT AREA
      ═══════════════════════════════════════════════════════════════════ */}
      <div style={{ flex: 1, overflow: "auto", padding: "12px 16px" }}>
        {/* 🕷️ SCRAPEY BOT */}
        <ScrapeyBot
          mood={botMood}
          message={botMessage}
          isAnimating={botAnimating}
        />

        {/* ═══════════════════════════════════════════════════════════════════
            STEP 1: SOURCE URL
        ═══════════════════════════════════════════════════════════════════ */}
        {currentStep === 1 && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            {/* URL Input */}
            <div>
              <label
                style={{
                  fontSize: "0.75em",
                  color: "#94a3b8",
                  marginBottom: "4px",
                  display: "block",
                }}
              >
                🔗 Paste URL to Scrape
              </label>
              <input
                style={inputStyle}
                value={formData.url}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, url: e.target.value }))
                }
                placeholder="https://facebook.com/groups/.../posts/..."
              />
            </div>

            {/* Platform Selector */}
            <div>
              <label
                style={{
                  fontSize: "0.75em",
                  color: "#94a3b8",
                  marginBottom: "4px",
                  display: "block",
                }}
              >
                📌 Platform
              </label>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {Object.entries(PLATFORM_PRESETS).map(([key, preset]) => (
                  <button
                    key={key}
                    onClick={() =>
                      setFormData((prev) => ({ ...prev, platform: key }))
                    }
                    style={{
                      background:
                        formData.platform === key
                          ? "linear-gradient(135deg, #fbbf24, #f59e0b)"
                          : "rgba(255,255,255,0.05)",
                      border:
                        formData.platform === key
                          ? "none"
                          : "1px solid rgba(255,255,255,0.1)",
                      padding: "6px 10px",
                      borderRadius: "6px",
                      color: formData.platform === key ? "#111" : "#94a3b8",
                      fontSize: "0.75em",
                      cursor: "pointer",
                      fontWeight: formData.platform === key ? "bold" : "normal",
                    }}
                  >
                    {preset.icon} {preset.name.split(" ")[1] || preset.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Dynamic Mode Toggle */}
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "0.8em",
                color: "#94a3b8",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={formData.useDynamic}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    useDynamic: e.target.checked,
                  }))
                }
              />
              ⚡ Dynamic Mode (recommended for Facebook)
            </label>

            {/* Scrape Button */}
            <button
              onClick={handleScrape}
              disabled={isProcessing || !formData.url.trim()}
              style={{
                background: isProcessing
                  ? "linear-gradient(135deg, #64748b, #475569)"
                  : "linear-gradient(135deg, #1877f2, #42b72a)",
                border: "none",
                padding: "14px",
                borderRadius: "10px",
                color: "#fff",
                fontWeight: "bold",
                fontSize: "0.95em",
                cursor: isProcessing ? "wait" : "pointer",
                boxShadow: "0 4px 15px rgba(24, 119, 242, 0.3)",
              }}
            >
              {isProcessing ? "🔄 Scraping..." : "🔍 Fetch Content"}
            </button>

            {/* Tips */}
            <div
              style={{
                background: "rgba(24, 119, 242, 0.1)",
                border: "1px solid rgba(24, 119, 242, 0.2)",
                borderRadius: "8px",
                padding: "10px",
                fontSize: "0.7em",
                color: "#93c5fd",
              }}
            >
              <strong>💡 Tips:</strong>
              <ul
                style={{
                  margin: "4px 0 0 0",
                  paddingLeft: "16px",
                  lineHeight: "1.6",
                }}
              >
                <li>For Facebook: Make sure you're logged in to Chrome</li>
                <li>Dynamic mode works best for social media sites</li>
                <li>Group posts require membership to scrape</li>
              </ul>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            STEP 2: REVIEW CONTENT
        ═══════════════════════════════════════════════════════════════════ */}
        {currentStep === 2 && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            <div>
              <label
                style={{
                  fontSize: "0.75em",
                  color: "#94a3b8",
                  marginBottom: "4px",
                  display: "block",
                }}
              >
                📄 Extracted Content (
                {formData.cleanedContent.length.toLocaleString()} chars)
              </label>
              <textarea
                value={formData.cleanedContent}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    cleanedContent: e.target.value,
                  }))
                }
                style={{
                  ...inputStyle,
                  minHeight: "150px",
                  resize: "vertical",
                  fontFamily: "monospace",
                  fontSize: "0.75em",
                }}
              />
            </div>

            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => setCurrentStep(1)}
                style={{
                  flex: 1,
                  background: "rgba(255,255,255,0.1)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  padding: "10px",
                  borderRadius: "8px",
                  color: "#94a3b8",
                  cursor: "pointer",
                  fontSize: "0.85em",
                }}
              >
                ← Back
              </button>
              <button
                onClick={() => {
                  setCurrentStep(3);
                  setBotMessage("Now let's make it viral! 🔥");
                }}
                style={{
                  flex: 2,
                  background: "linear-gradient(135deg, #8b5cf6, #ec4899)",
                  border: "none",
                  padding: "10px",
                  borderRadius: "8px",
                  color: "#fff",
                  fontWeight: "bold",
                  cursor: "pointer",
                  fontSize: "0.85em",
                }}
              >
                Continue to AI Enhancement →
              </button>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            STEP 3: ENHANCEMENT OPTIONS
        ═══════════════════════════════════════════════════════════════════ */}
        {currentStep === 3 && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            {/* Style & Audience */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
              }}
            >
              <div>
                <label
                  style={{
                    fontSize: "0.7em",
                    color: "#94a3b8",
                    marginBottom: "3px",
                    display: "block",
                  }}
                >
                  🎨 Style
                </label>
                <select
                  value={formData.postStyle}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      postStyle: e.target.value,
                    }))
                  }
                  style={{ ...inputStyle, fontSize: "0.8em", padding: "8px" }}
                >
                  <option value="viral">🔥 Viral</option>
                  <option value="professional">💼 Professional</option>
                  <option value="casual">😊 Casual</option>
                  <option value="promotional">📢 Promotional</option>
                  <option value="educational">📚 Educational</option>
                  <option value="inspirational">✨ Inspirational</option>
                </select>
              </div>
              <div>
                <label
                  style={{
                    fontSize: "0.7em",
                    color: "#94a3b8",
                    marginBottom: "3px",
                    display: "block",
                  }}
                >
                  👥 Audience
                </label>
                <select
                  value={formData.audience}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      audience: e.target.value,
                    }))
                  }
                  style={{ ...inputStyle, fontSize: "0.8em", padding: "8px" }}
                >
                  <option value="general">🌍 General</option>
                  <option value="filipino">🇵🇭 Filipino</option>
                  <option value="business">💼 Business</option>
                  <option value="tech">💻 Tech</option>
                  <option value="youth">🎮 Gen Z</option>
                </select>
              </div>
            </div>

            {/* Region & Hashtags */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
              }}
            >
              <div>
                <label
                  style={{
                    fontSize: "0.7em",
                    color: "#94a3b8",
                    marginBottom: "3px",
                    display: "block",
                  }}
                >
                  🌏 Region
                </label>
                <input
                  value={formData.region}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, region: e.target.value }))
                  }
                  style={{ ...inputStyle, fontSize: "0.8em", padding: "8px" }}
                />
              </div>
              <div>
                <label
                  style={{
                    fontSize: "0.7em",
                    color: "#94a3b8",
                    marginBottom: "3px",
                    display: "block",
                  }}
                >
                  # Tags
                </label>
                <input
                  type="number"
                  min="10"
                  max="35"
                  value={formData.hashtagCount}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      hashtagCount: Number(e.target.value),
                    }))
                  }
                  style={{ ...inputStyle, fontSize: "0.8em", padding: "8px" }}
                />
              </div>
            </div>

            {/* Custom Hashtags */}
            <div>
              <label
                style={{
                  fontSize: "0.7em",
                  color: "#94a3b8",
                  marginBottom: "3px",
                  display: "block",
                }}
              >
                🏷️ Always Include
              </label>
              <input
                value={formData.customHashtags}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    customHashtags: e.target.value,
                  }))
                }
                style={{ ...inputStyle, fontSize: "0.8em", padding: "8px" }}
              />
            </div>

            {/* Toggles */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-around",
                fontSize: "0.8em",
                color: "#94a3b8",
              }}
            >
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={formData.includeEmojis}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      includeEmojis: e.target.checked,
                    }))
                  }
                />
                😀 Emojis
              </label>
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  cursor: "pointer",
                }}
              >
                <input
                  type="checkbox"
                  checked={formData.includeCTA}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      includeCTA: e.target.checked,
                    }))
                  }
                />
                📣 CTA
              </label>
            </div>

            {/* Buttons */}
            <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
              <button
                onClick={() => setCurrentStep(2)}
                style={{
                  flex: 1,
                  background: "rgba(255,255,255,0.1)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  padding: "10px",
                  borderRadius: "8px",
                  color: "#94a3b8",
                  cursor: "pointer",
                  fontSize: "0.85em",
                }}
              >
                ← Back
              </button>
              <button
                onClick={handleEnhanceAndGenerate}
                disabled={isProcessing}
                style={{
                  flex: 2,
                  background: isProcessing
                    ? "linear-gradient(135deg, #64748b, #475569)"
                    : "linear-gradient(135deg, #10b981, #059669)",
                  border: "none",
                  padding: "12px",
                  borderRadius: "8px",
                  color: "#fff",
                  fontWeight: "bold",
                  cursor: isProcessing ? "wait" : "pointer",
                  fontSize: "0.9em",
                  boxShadow: "0 4px 15px rgba(16, 185, 129, 0.3)",
                }}
              >
                {isProcessing
                  ? "🔄 AI Processing..."
                  : "🚀 Generate Viral Post"}
              </button>
            </div>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════════════
            STEP 4: FINAL POST (Facebook Preview)
        ═══════════════════════════════════════════════════════════════════ */}
        {currentStep === 4 && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            {/* Facebook Post Preview */}
            <FacebookPostPreview
              content={formData.finalPost}
              onCopy={copyToClipboard}
              copied={copySuccess}
            />

            {/* Action Buttons */}
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => setCurrentStep(3)}
                style={{
                  flex: 1,
                  background: "rgba(255,255,255,0.1)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  padding: "10px",
                  borderRadius: "8px",
                  color: "#94a3b8",
                  cursor: "pointer",
                  fontSize: "0.85em",
                }}
              >
                ← Edit Options
              </button>
              <button
                onClick={resetFlow}
                style={{
                  flex: 1,
                  background: "linear-gradient(135deg, #1877f2, #42b72a)",
                  border: "none",
                  padding: "10px",
                  borderRadius: "8px",
                  color: "#fff",
                  fontWeight: "bold",
                  cursor: "pointer",
                  fontSize: "0.85em",
                }}
              >
                🔄 New Post
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════
          RESIZE HANDLE
      ═══════════════════════════════════════════════════════════════════ */}
      <div
        className="resize-handle"
        style={{
          position: "absolute",
          bottom: 0,
          right: 0,
          width: "20px",
          height: "20px",
          cursor: "se-resize",
          background: "linear-gradient(135deg, transparent 50%, #fbbf24 50%)",
          borderRadius: "0 0 16px 0",
        }}
        onMouseDown={(e) => {
          e.stopPropagation();
          setIsResizing(true);
        }}
      />

      {/* Pulse Animation Style */}
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }
      `}</style>
    </div>
  );
};

export default ScraperWorkbench;
