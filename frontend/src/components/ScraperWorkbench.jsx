import React, { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";

const defaultResult = {
  success: false,
  message: "Run a scrape to see results",
};

const tabs = [
  { key: "static", label: "🕸️ Static", desc: "HTTP scraping" },
  { key: "dynamic", label: "⚡ Dynamic", desc: "Browser automation" },
  { key: "batch", label: "📚 Batch", desc: "Multiple URLs" },
  { key: "monitor", label: "⏱️ Monitor", desc: "Track changes" },
  { key: "summarize", label: "🧠 AI Extract", desc: "AI summary" },
  { key: "facebook", label: "📱 FB Post", desc: "Generate viral post" },
  { key: "report", label: "📊 Report", desc: "SEO Data Report" },
];

// ═══════════════════════════════════════════════════════════════════════════
// 📌 SCRAPER PRESETS - Platform-specific CSS selectors for optimal scraping
// ═══════════════════════════════════════════════════════════════════════════
const SCRAPER_PRESETS = {
  general: {
    name: "🌐 General (Default)",
    selectors: "h1, h2, h3, p, article, .content, .post, .entry",
    description: "Generic selectors for most websites",
  },
  facebookPost: {
    name: "📘 Facebook Post (Full)",
    selectors: [
      // Post content and text
      "[data-ad-preview='message']",
      "[data-ad-comet-preview='message']",
      "div[dir='auto']",
      "span[dir='auto']",
      // User names and profile info
      "a[role='link'] span",
      "h2 a span",
      "strong a",
      "a.x1i10hfl span",
      // Comments section
      "ul[role='list'] li",
      "div[aria-label*='Comment']",
      "div[aria-label*='comment']",
      // Reactions and engagement
      "span[aria-label*='reaction']",
      "span[aria-label*='like']",
      "div[aria-label*='reactions']",
      // Timestamps
      "abbr[data-utime]",
      "span[id*='jsc'] a",
      // Images and media captions
      "img[alt]",
      "div[data-visualcompletion='media-vc-image']",
      // Shared content
      "div[role='article']",
      // See more expanded text
      "div[data-ad-preview]",
    ].join(", "),
    description:
      "Comprehensive Facebook post scraping including comments & usernames",
  },
  facebookGroup: {
    name: "👥 Facebook Group Post",
    selectors: [
      // Group post specific
      "div[role='article']",
      "div[data-pagelet*='FeedUnit']",
      // Author info
      "h2 a[role='link']",
      "h3 a[role='link']",
      "a[role='link'][tabindex='0'] span",
      "strong span",
      // Post text content
      "[data-ad-comet-preview='message']",
      "[data-ad-preview='message']",
      "div[dir='auto'][style*='text-align']",
      "div[data-ad-rendering-role='story_message']",
      // Comments
      "ul li div[dir='auto']",
      "div[aria-label*='Comment by']",
      "div[aria-label*='Reply from']",
      // Commenter names
      "span.x3nfvp2",
      "span[dir='auto'] a span",
      // Time stamps
      "a[role='link'] span[id]",
      "abbr",
      // Engagement metrics
      "span[role='toolbar'] span",
      "div[aria-label*='reactions']",
    ].join(", "),
    description: "Facebook group posts with comments and member names",
  },
  facebookComments: {
    name: "💬 Facebook Comments Only",
    selectors: [
      // Comment containers
      "ul[role='list']",
      "li div[role='article']",
      // Comment text
      "div[dir='auto'] span[dir='auto']",
      "span.x193iq5w",
      // Commenter names
      "span.x3nfvp2 a",
      "a[role='link'] span[class*='xt0psk2']",
      "strong a span",
      // Reply threads
      "div[aria-label*='Replies']",
      "div[aria-label*='reply']",
      // Timestamps on comments
      "a[role='link'] span[class*='x4k7w5x']",
    ].join(", "),
    description: "Focus on comment text and commenter names",
  },
  twitter: {
    name: "🐦 Twitter/X Post",
    selectors: [
      "article[data-testid='tweet']",
      "div[data-testid='tweetText']",
      "a[role='link'][href*='/status/']",
      "span[data-testid='app-text-transition-container']",
      "div[data-testid='User-Name']",
      "time",
    ].join(", "),
    description: "Twitter/X posts and replies",
  },
  instagram: {
    name: "📸 Instagram Post",
    selectors: [
      "article[role='presentation']",
      "h1._ap3a",
      "span._ap3a",
      "a._ap3a",
      "div._a9zs",
      "span._aacl",
      "time",
    ].join(", "),
    description: "Instagram posts and captions",
  },
  youtube: {
    name: "🎬 YouTube Video",
    selectors: [
      "#title h1",
      "h1.ytd-video-primary-info-renderer",
      "#description-text",
      "#content-text",
      "#author-text",
      "ytd-comment-renderer #content-text",
      "#count yt-formatted-string",
    ].join(", "),
    description: "YouTube video info and comments",
  },
  news: {
    name: "📰 News Article",
    selectors: [
      "article",
      "h1",
      "h2.headline",
      ".article-body p",
      ".story-body p",
      ".author-name",
      "time",
      ".byline",
      "figcaption",
    ].join(", "),
    description: "News articles and author info",
  },
  reddit: {
    name: "🔥 Reddit Post",
    selectors: [
      "shreddit-post h1",
      "div[slot='text-body']",
      "p[id*='post-rtjson-content']",
      "shreddit-comment div[slot='comment']",
      "a[data-testid='comment_author_link']",
      "time",
      "span[data-testid='karma']",
    ].join(", "),
    description: "Reddit posts and comments",
  },
};

const ScraperWorkbench = ({
  apiUrl,
  isOpen,
  onToggle,
  onScreenUpdate,
  isStandalone = false,
}) => {
  const backendUrl = apiUrl || "http://127.0.0.1:65252";
  const [activeTab, setActiveTab] = useState("static");
  const [result, setResult] = useState(defaultResult);
  const [isRunning, setIsRunning] = useState(false);

  // Draggable/Resizable state - Load from localStorage
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-scraper-pos");
      return saved ? JSON.parse(saved) : { x: window.innerWidth - 480, y: 100 };
    } catch {
      return { x: window.innerWidth - 480, y: 100 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-scraper-size");
      return saved ? JSON.parse(saved) : { width: 450, height: 620 };
    } catch {
      return { width: 450, height: 620 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Save position to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-scraper-pos", JSON.stringify(position));
  }, [position]);

  // Save size to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-scraper-size", JSON.stringify(size));
  }, [size]);

  // Scraper preset selection
  const [selectedPreset, setSelectedPreset] = useState("general");

  // Form states
  const [staticForm, setStaticForm] = useState({
    url: "https://example.org",
    selectors: SCRAPER_PRESETS.general.selectors,
    includeLinks: false,
    includeHtml: false,
  });

  // Quick SEO scrape (simple mode)
  const [quickUrl, setQuickUrl] = useState("");
  const [quickDynamic, setQuickDynamic] = useState(false);
  const [quickLoading, setQuickLoading] = useState(false);
  const [quickResult, setQuickResult] = useState(null);

  const handleQuickScrape = async () => {
    if (!quickUrl || quickUrl.length < 5) return;
    setQuickLoading(true);
    setQuickResult(null);
    try {
      const res = await axios.post(`${backendUrl}/scrape/simple`, {
        url: quickUrl,
        dynamic: quickDynamic,
        max_words: 400,
      });
      setQuickResult(res.data);
      if (typeof onScreenUpdate === "function") {
        onScreenUpdate({ lastUrl: quickUrl, lastResult: res.data.summary });
      }
    } catch (err) {
      setQuickResult({
        success: false,
        error: err?.response?.data || err.message,
      });
    } finally {
      setQuickLoading(false);
    }
  };

  // Comments summarization UI state
  const [commentsText, setCommentsText] = useState("");
  const [commentsLoading, setCommentsLoading] = useState(false);
  const [commentsResult, setCommentsResult] = useState(null);

  const handleSummarizeComments = async () => {
    const lines = (commentsText || "")
      .split("\n")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!lines.length) return;
    setCommentsLoading(true);
    setCommentsResult(null);
    try {
      const res = await axios.post(`${backendUrl}/scrape/comments-summary`, {
        comments: lines,
        max_words: 150,
      });
      setCommentsResult(res.data.result || res.data);
    } catch (err) {
      setCommentsResult({
        success: false,
        error: err?.response?.data || err.message,
      });
    } finally {
      setCommentsLoading(false);
    }
  };

  const [dynamicForm, setDynamicForm] = useState({
    url: "https://example.org",
    waitForSelector: "body",
    waitTimeout: 10,
    headless: true,
    screenshot: false,
    actionsJson: "[]",
  });

  const [batchForm, setBatchForm] = useState({
    urls: "https://example.org\nhttps://news.ycombinator.com",
    selectors: SCRAPER_PRESETS.general.selectors,
  });

  const [monitorForm, setMonitorForm] = useState({
    url: "https://example.org",
    selectors: SCRAPER_PRESETS.general.selectors,
  });

  const [summaryForm, setSummaryForm] = useState({
    content: "Paste scraped text here...",
    instructions: "Summarize the core insights as bullet points.",
    maxWords: 200,
  });

  // Facebook Post Generator state
  const [facebookForm, setFacebookForm] = useState({
    content: "",
    postStyle: "viral",
    includeEmojis: true,
    hashtagCount: 25,
    targetAudience: "general",
    callToAction: true,
    customHashtags: "#darrellbuttigieg #thesoldiersdream",
    region: "Philippines",
  });
  const [generatedPost, setGeneratedPost] = useState("");
  const [copySuccess, setCopySuccess] = useState(false);

  // SEO Report state
  const [reportForm, setReportForm] = useState({
    rawData: "",
    reportType: "trends",
    includeAnalysis: true,
  });
  const [generatedReport, setGeneratedReport] = useState("");

  // 👀 SCREEN AWARENESS - Report data to Agent Amigos
  useEffect(() => {
    if (onScreenUpdate && isOpen) {
      onScreenUpdate({
        lastUrl: staticForm.url || dynamicForm.url,
        lastResult: result.success
          ? result.text || result.content || JSON.stringify(result)
          : "",
        generatedPost,
        generatedReport,
        activeTab,
      });
    }
  }, [
    staticForm.url,
    dynamicForm.url,
    result,
    generatedPost,
    generatedReport,
    activeTab,
    isOpen,
    onScreenUpdate,
  ]);

  // Drag handlers
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
        const maxY = window.innerHeight - 60; // Keep at least 60px visible on bottom
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
          height: Math.min(maxHeight, Math.max(400, e.clientY - rect.top + 10)),
        });
      }
    },
    [isDragging, isResizing, dragOffset, size.width, position.x, position.y],
  );

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    setIsResizing(false);
  }, []);

  // Auto-correct window position if it goes off-screen
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
        newX = Math.max(50, window.innerWidth - 500);
        needsCorrection = true;
      }
      if (position.x < minX) {
        newX = 50;
        needsCorrection = true;
      }
      if (position.y > maxY) {
        newY = 100;
        needsCorrection = true;
      }
      if (position.y < 0) {
        newY = 100;
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
    setPosition({ x: window.innerWidth - 480, y: 100 });
    setSize({ width: 450, height: 620 });
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

  const runRequest = async (fn) => {
    setIsRunning(true);
    setResult({ success: false, message: "Working..." });
    try {
      const payload = await fn();
      setResult(payload.data || payload);
    } catch (error) {
      setResult({
        success: false,
        error: error.response?.data?.detail || error.message,
      });
    }
    setIsRunning(false);
  };

  const runStaticScrape = () =>
    runRequest(() =>
      axios.post(`${backendUrl}/scrape/url`, {
        url: staticForm.url,
        selectors: staticForm.selectors
          ?.split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        include_links: staticForm.includeLinks,
        include_html: staticForm.includeHtml,
      }),
    );

  const runDynamicScrape = () =>
    runRequest(() => {
      let actions;
      if (dynamicForm.actionsJson.trim()) {
        try {
          actions = JSON.parse(dynamicForm.actionsJson);
        } catch {
          throw new Error("Invalid actions JSON");
        }
      }
      return axios.post(`${backendUrl}/scrape/dynamic`, {
        url: dynamicForm.url,
        wait_for_selector: dynamicForm.waitForSelector || undefined,
        wait_timeout: Number(dynamicForm.waitTimeout) || 10,
        headless: dynamicForm.headless,
        screenshot: dynamicForm.screenshot,
        actions,
      });
    });

  const runBatchScrape = () =>
    runRequest(() =>
      axios.post(`${backendUrl}/scrape/batch`, {
        urls: batchForm.urls
          .split(/\r?\n/)
          .map((l) => l.trim())
          .filter(Boolean),
        selectors: batchForm.selectors
          ?.split(",")
          .map((s) => s.trim())
          .filter(Boolean),
      }),
    );

  const runMonitor = () =>
    runRequest(() =>
      axios.post(`${backendUrl}/scrape/monitor`, {
        url: monitorForm.url,
        selectors: monitorForm.selectors
          ?.split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        include_html: true,
      }),
    );

  const runSummary = () =>
    runRequest(() =>
      axios.post(`${backendUrl}/scrape/extract`, {
        content: summaryForm.content,
        instructions: summaryForm.instructions || undefined,
        max_words: Number(summaryForm.maxWords) || 200,
      }),
    );

  // Facebook Post Generator - AI-powered viral post creation with SEO
  const generateFacebookPost = async () => {
    if (!facebookForm.content.trim()) {
      setResult({
        success: false,
        error: "Please paste or enter content to convert",
      });
      return;
    }

    setIsRunning(true);
    setResult({
      success: false,
      message: "🔄 Generating SEO-optimized Facebook post...",
    });
    setCopySuccess(false);

    const customTags = facebookForm.customHashtags.trim();

    // ═══════════════════════════════════════════════════════════════════════
    // CONTENT QUALITY DETECTION - Check if we actually got meaningful content
    // ═══════════════════════════════════════════════════════════════════════
    const detectContentQuality = (rawContent) => {
      const lowQualityIndicators = [
        "__fb-light-mode",
        "Grupo • Facebook",
        "Facebook><meta",
        "Log into Facebook",
        "Create new account",
        "See more on Facebook",
        "You must log in",
        "content is not available",
        "This page isn't available",
        "Sorry, this content isn't available",
        "<html",
        "<!DOCTYPE",
        "LLM_API_BASE not configured",
        "Connection aborted",
        "Remote end closed",
      ];

      const contentStr =
        typeof rawContent === "string"
          ? rawContent
          : JSON.stringify(rawContent);
      const hasLowQuality = lowQualityIndicators.some((indicator) =>
        contentStr.toLowerCase().includes(indicator.toLowerCase()),
      );

      // Check for meaningful content length (excluding JSON structure)
      const cleanedForLength = contentStr
        .replace(/[{}\[\]"':,]/g, " ")
        .replace(/\\n|\\r|\\t/g, " ")
        .replace(/https?:\/\/[^\s]+/g, "")
        .replace(/\s+/g, " ")
        .trim();

      const meaningfulWords = cleanedForLength
        .split(" ")
        .filter(
          (w) =>
            w.length > 3 &&
            !/^(null|true|false|undefined|error|success|elapsed|status|code)$/i.test(
              w,
            ),
        );

      return {
        isLowQuality: hasLowQuality || meaningfulWords.length < 10,
        meaningfulWordCount: meaningfulWords.length,
        detectedIssue: hasLowQuality
          ? "Facebook login wall or metadata only"
          : meaningfulWords.length < 10
            ? "Insufficient content scraped"
            : null,
      };
    };

    // Check content quality first
    const qualityCheck = detectContentQuality(facebookForm.content);

    if (qualityCheck.isLowQuality) {
      setResult({
        success: false,
        error: `⚠️ LOW QUALITY SCRAPE DETECTED: ${qualityCheck.detectedIssue}

📋 SOLUTIONS:
1. Use DYNAMIC mode (⚡ tab) for Facebook - it uses your logged-in browser
2. Make sure you're logged into Facebook in Chrome first
3. For group posts, you must be a member of the group
4. Try scrolling down in Dynamic mode to load comments

💡 Static scraping can't bypass Facebook's login requirements.`,
      });
      setIsRunning(false);
      return;
    }

    // LOCAL FALLBACK: Extract and format content when AI is unavailable
    const generateLocalPost = (rawContent) => {
      // ═══════════════════════════════════════════════════════════════════════
      // IMPROVED CONTENT EXTRACTION - Better parsing of scraped data
      // ═══════════════════════════════════════════════════════════════════════
      let textContent = rawContent;

      // Try to parse if it's JSON and extract meaningful content
      try {
        const parsed = JSON.parse(rawContent);

        // Look for actual text content in various possible locations
        const possibleTextFields = [
          parsed.text,
          parsed.content,
          parsed.data?.text,
          parsed.data?.content,
          parsed.extracted,
          parsed.data?.extracted,
          parsed.fallback,
        ];

        // Also extract from matches object (CSS selector results)
        if (parsed.matches && typeof parsed.matches === "object") {
          const matchTexts = [];
          for (const [selector, values] of Object.entries(parsed.matches)) {
            if (Array.isArray(values)) {
              matchTexts.push(
                ...values.filter((v) => typeof v === "string" && v.length > 5),
              );
            }
          }
          if (matchTexts.length > 0) {
            possibleTextFields.push(matchTexts.join("\n"));
          }
        }

        textContent =
          possibleTextFields.find(
            (f) => f && typeof f === "string" && f.length > 20,
          ) || JSON.stringify(parsed);
      } catch (e) {
        // Not JSON, use as-is
      }

      // Clean up the text - remove JSON artifacts and noise
      const cleanedText = textContent
        .replace(/\\n/g, "\n")
        .replace(/\\"/g, '"')
        .replace(/\\t/g, " ")
        .replace(/\{|\}|\[|\]/g, " ")
        .replace(
          /"url":|"status_code":|"success":|"elapsed":|"error":|"fallback":|"matches":|"text":|"content":/g,
          "",
        )
        .replace(/https?:\/\/[^\s]+/g, "") // Remove URLs
        .replace(/null|true|false/g, "")
        .replace(/\d+\.\d+/g, "") // Remove decimals
        .replace(/['"]/g, " ")
        .replace(/\s+/g, " ")
        .trim();

      // Extract meaningful phrases and sentences (not just single words)
      const sentences = cleanedText
        .split(/[.!?\n]+/)
        .map((s) => s.trim())
        .filter((s) => s.length > 15 && s.length < 200)
        .filter((s) => !s.match(/^(error|null|undefined|connection|remote)/i));

      // Extract names (capitalized sequences) that look like real names
      const namePattern = /\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b/g;
      const potentialNames = [...cleanedText.matchAll(namePattern)]
        .map((m) => m[1])
        .filter(
          (name) =>
            name.length > 4 &&
            name.length < 40 &&
            ![
              "Connection Error",
              "Remote End",
              "Status Code",
              "Light Mode",
            ].includes(name),
        );

      // Extract hashtags that were already in the content
      const existingHashtags = [...cleanedText.matchAll(/#\w+/g)].map(
        (m) => m[0],
      );

      // Extract quoted text (often post content)
      const quotedText = [...cleanedText.matchAll(/"([^"]{20,})"/g)].map(
        (m) => m[1],
      );

      // Generate trending hashtags based on region and content
      const trendingHashtags = {
        Philippines: [
          "#Philippines",
          "#Pinoy",
          "#PinoyPride",
          "#Pilipinas",
          "#Manila",
          "#PHtrending",
          "#PinoyViral",
          "#FilipinoPride",
          "#PHnews",
          "#KapamilyaForever",
          "#PBB",
          "#ABSCBN",
          "#GMANetwork",
          "#trending",
          "#viral",
          "#fyp",
          "#foryou",
          "#explorepage",
          "#reels",
          "#facebookreels",
        ],
        Global: [
          "#trending",
          "#viral",
          "#fyp",
          "#foryou",
          "#explorepage",
          "#reels",
          "#facebookreels",
          "#instagood",
          "#love",
          "#follow",
          "#like",
          "#photooftheday",
          "#beautiful",
          "#happy",
          "#cute",
          "#tbt",
          "#fashion",
          "#followme",
          "#picoftheday",
          "#selfie",
        ],
      };

      const regionTags =
        trendingHashtags[facebookForm.region] || trendingHashtags.Global;
      const hashtagCount = facebookForm.hashtagCount || 25;

      // Combine existing hashtags with region tags
      const allTags = [...new Set([...existingHashtags, ...regionTags])];
      const selectedTags = allTags.slice(0, Math.max(hashtagCount - 2, 10));

      // Build the post with actual extracted content
      const emojis = facebookForm.includeEmojis
        ? ["🔥", "✨", "💫", "🎉", "📣", "💪", "🙌", "❤️", "👀", "🚀"]
        : [""];
      const randomEmoji = () =>
        emojis[Math.floor(Math.random() * emojis.length)];

      let post = "";

      // If we have actual sentences/content, use them
      if (sentences.length > 0 || quotedText.length > 0) {
        const mainContent =
          quotedText.length > 0
            ? quotedText.slice(0, 3).join("\n\n")
            : sentences.slice(0, 4).join("\n\n");

        const namesMention =
          potentialNames.length > 0
            ? `\n\n${
                facebookForm.includeEmojis ? "👤 " : ""
              }Featuring: ${potentialNames.slice(0, 5).join(", ")}`
            : "";

        post = `${randomEmoji()} Check this out! ${randomEmoji()}

${mainContent}${namesMention}

${
  facebookForm.callToAction
    ? `${
        facebookForm.includeEmojis ? "💬" : ""
      } What do you think? Drop a comment below! ${
        facebookForm.includeEmojis ? "👇" : ""
      }`
    : ""
}

${customTags} ${selectedTags.join(" ")}`;
      } else {
        // Truly minimal content - ask user to try Dynamic mode
        post = `${randomEmoji()} Content extraction was limited ${randomEmoji()}

${
  facebookForm.includeEmojis ? "⚠️" : ""
} The scraper didn't capture enough content from this page.

${
  facebookForm.includeEmojis ? "💡" : ""
} TIP: For Facebook posts, try using the DYNAMIC (⚡) scraper mode with your logged-in Chrome browser for better results!

${
  facebookForm.callToAction
    ? `${
        facebookForm.includeEmojis ? "💬" : ""
      } Have content to share? Paste it directly in the content box! ${
        facebookForm.includeEmojis ? "👇" : ""
      }`
    : ""
}

${customTags} ${selectedTags.join(" ")}`;
      }

      return post;
    };

    // ═══════════════════════════════════════════════════════════════════════
    // 🤖 AGENTIC AI POST GENERATOR - Uses main chat endpoint for smart analysis
    // ═══════════════════════════════════════════════════════════════════════
    const generateWithAgenticAI = async (rawContent) => {
      const styleGuides = {
        viral:
          "Create a highly engaging, shareable post that hooks readers immediately. Use curiosity gaps, emotional triggers, and a strong call-to-action.",
        professional:
          "Create a professional, informative post suitable for business audiences. Maintain credibility while being engaging.",
        casual:
          "Create a friendly, conversational post that feels authentic and relatable.",
        promotional:
          "Create a promotional post that highlights benefits, creates urgency, and drives action.",
        educational:
          "Create an educational post that teaches something valuable while being easy to understand.",
        inspirational:
          "Create an inspirational, motivational post that uplifts and encourages the audience.",
      };

      const audienceGuides = {
        general: "general social media audience",
        business: "business professionals and entrepreneurs",
        tech: "tech enthusiasts and developers",
        lifestyle: "lifestyle and wellness focused readers",
        youth: "younger generation (Gen Z/Millennials)",
        parents: "parents and families",
        filipino: "Filipino social media users and culture enthusiasts",
      };

      const emojiInstruction = facebookForm.includeEmojis
        ? "Include relevant emojis throughout to make it visually engaging."
        : "Do NOT include any emojis.";

      const ctaInstruction = facebookForm.callToAction
        ? "End with a compelling call-to-action that encourages engagement (comments, shares, reactions)."
        : "";

      // Agentic analysis prompt - AI analyzes intent and creates meaningful content
      const agenticPrompt = `You are an EXPERT Social Media Content Strategist and SEO Specialist for Agent Amigos.

## 🎯 YOUR MISSION:
Analyze the following scraped/raw data and CREATE a highly engaging, SEO-optimized Facebook post.

## 📊 AGENTIC ANALYSIS STEPS:
1. **UNDERSTAND THE CONTEXT**: What is this content about? (news, trending topic, personal story, product, event, discussion thread, etc.)
2. **IDENTIFY KEY ELEMENTS**: 
   - Main topic/theme
   - Key people mentioned (if any)
   - Important facts, dates, numbers
   - Emotional hooks or interesting angles
   - What makes this share-worthy?
3. **DETERMINE USER INTENT**: What is the user trying to share or promote?
4. **CRAFT THE MESSAGE**: Transform raw data into compelling narrative

## 📝 RAW CONTENT TO ANALYZE:
\`\`\`
${rawContent.substring(0, 4000)}
\`\`\`

## 🎨 POST REQUIREMENTS:
- **Style**: ${styleGuides[facebookForm.postStyle] || styleGuides.viral}
- **Target Audience**: ${
        audienceGuides[facebookForm.targetAudience] || audienceGuides.general
      }
- **Region Focus**: ${facebookForm.region || "Global"}
- ${emojiInstruction}
- ${ctaInstruction}

## 📱 OUTPUT FORMAT (COPY-PASTE READY):
Create a Facebook post with:
1. **Hook** (first line grabs attention)
2. **Body** (2-3 short paragraphs, mobile-friendly with line breaks)
3. **CTA** (engagement driver)
4. **Hashtags** (exactly ${facebookForm.hashtagCount} hashtags)

MANDATORY HASHTAGS TO INCLUDE: ${customTags}

## ⚠️ RULES:
- NO JSON, technical jargon, or system messages in output
- NO explaining what you're doing - just output the final post
- Keep paragraphs SHORT (2-3 sentences max)
- Make it SHAREABLE and ENGAGING
- Sound HUMAN and AUTHENTIC, not like AI
- Focus on what makes this content INTERESTING to readers

## OUTPUT:
Write ONLY the final Facebook post below (ready to copy-paste):`;

      // Try the main /chat endpoint for agentic AI analysis
      try {
        const response = await axios.post(`${backendUrl}/chat`, {
          message: agenticPrompt,
          conversation_history: [],
          require_approval: false,
        });

        // Extract the AI response
        let aiResponse =
          response.data?.response || response.data?.message || response.data;

        if (typeof aiResponse === "object") {
          aiResponse =
            aiResponse.response ||
            aiResponse.message ||
            aiResponse.text ||
            JSON.stringify(aiResponse);
        }

        // Check if we got a valid response
        if (
          aiResponse &&
          typeof aiResponse === "string" &&
          aiResponse.length > 50 &&
          !aiResponse.includes("LLM_API_BASE not configured") &&
          !aiResponse.includes("Connection aborted")
        ) {
          // Clean up the response
          let cleanedPost = aiResponse
            .replace(
              /^(Here's|Here is|I've created|Below is|The post:?)[\s\S]*?:/gi,
              "",
            )
            .replace(/```[\s\S]*?```/g, "")
            .replace(/^\s*[-*]\s*/gm, "")
            .trim();

          // Ensure custom hashtags are included
          if (customTags && !cleanedPost.includes(customTags.split(" ")[0])) {
            cleanedPost = cleanedPost + "\n\n" + customTags;
          }

          return { success: true, post: cleanedPost, method: "agentic-ai" };
        }
      } catch (chatError) {
        console.log(
          "Chat endpoint failed, trying extract endpoint:",
          chatError.message,
        );
      }

      // Fallback to /scrape/extract endpoint
      try {
        const extractResponse = await axios.post(
          `${backendUrl}/scrape/extract`,
          {
            content: rawContent,
            instructions: agenticPrompt,
            max_words: 600,
          },
        );

        let postContent =
          extractResponse.data?.data?.extracted ||
          extractResponse.data?.extracted ||
          extractResponse.data?.data ||
          "";

        if (
          postContent &&
          typeof postContent === "string" &&
          postContent.length > 50 &&
          !postContent.includes("LLM_API_BASE")
        ) {
          let cleanedPost = postContent.replace(/```[\s\S]*?```/g, "").trim();

          if (customTags && !cleanedPost.includes(customTags.split(" ")[0])) {
            cleanedPost = cleanedPost + "\n\n" + customTags;
          }

          return { success: true, post: cleanedPost, method: "extract-ai" };
        }
      } catch (extractError) {
        console.log("Extract endpoint also failed:", extractError.message);
      }

      // All AI methods failed
      return { success: false, method: "none" };
    };

    try {
      // First try agentic AI generation
      setResult({
        success: false,
        message:
          "🤖 AI is analyzing your content and crafting an engaging post...",
      });

      const aiResult = await generateWithAgenticAI(facebookForm.content);

      if (aiResult.success) {
        setGeneratedPost(aiResult.post);
        setResult({
          success: true,
          message: `✅ AI-powered post generated! (${
            aiResult.method === "agentic-ai"
              ? "🧠 Agentic Analysis"
              : "📝 AI Extract"
          })`,
        });
        setIsRunning(false);
        return;
      }

      // AI unavailable - use improved local fallback
      console.log("AI unavailable, using enhanced local fallback");
      const localPost = generateLocalPost(facebookForm.content);
      setGeneratedPost(localPost);
      setResult({
        success: true,
        message:
          "✅ Post generated (offline mode - AI unavailable). For better results, ensure your LLM is configured.",
      });
    } catch (error) {
      console.log("Post generation error:", error.message);
      const localPost = generateLocalPost(facebookForm.content);
      setGeneratedPost(localPost);
      setResult({
        success: true,
        message: "✅ Post generated (fallback mode)",
      });
    }
    setIsRunning(false);
  };

  // SEO Data Report Generator - Creates comprehensive trend analysis
  const generateSEOReport = async () => {
    if (!reportForm.rawData.trim()) {
      setResult({
        success: false,
        error: "Please paste raw data to analyze",
      });
      return;
    }

    setIsRunning(true);
    setResult({
      success: false,
      message: "📊 Generating SEO Data Report...",
    });

    // Local fallback for report generation
    const generateLocalReport = (rawData) => {
      const today = new Date().toLocaleDateString();

      // Extract text content
      let textContent = rawData;
      try {
        const parsed = JSON.parse(rawData);
        textContent =
          parsed.fallback ||
          parsed.text ||
          parsed.content ||
          parsed.data?.text ||
          JSON.stringify(parsed);
      } catch (e) {}

      // Clean and extract topics
      const cleanText = textContent
        .replace(/\\n/g, " ")
        .replace(/\\"/g, '"')
        .replace(/[{}\[\]]/g, " ")
        .replace(/"[a-z_]+"\s*:/gi, " ")
        .replace(/https?:\/\/[^\s]+/g, "")
        .replace(/null|true|false|\d+\.\d+/g, "")
        .replace(/['"]/g, " ")
        .trim();

      // Find capitalized phrases (potential trends)
      const words = cleanText.split(/\s+/);
      const potentialTopics = [];
      const skipWords = [
        "Connection",
        "Remote",
        "Error",
        "LLM",
        "API",
        "BASE",
        "aborted",
        "closed",
        "response",
        "without",
        "configured",
        "status",
        "code",
        "success",
        "elapsed",
        "content",
        "length",
        "null",
      ];

      for (let i = 0; i < words.length; i++) {
        const word = words[i];
        if (
          word.length > 2 &&
          word[0] === word[0].toUpperCase() &&
          !skipWords.includes(word)
        ) {
          potentialTopics.push(word);
        }
      }

      // Extract any hashtags
      const hashtags = cleanText.match(/#\w+/g) || [];

      // Default Filipino trending hashtags
      const defaultHashtags =
        "#darrellbuttigieg #thesoldiersdream #Philippines #Pinoy #trending #viral #fyp #PH #Manila #Pilipinas #PinoyPride #PHtrending #facebookreels #reels #explorepage #foryou #love #follow #like #instagood #photooftheday #beautiful #happy #fashion #followme";

      return `═══════════════════════════════════════════════════════════
📊 SEO TREND ANALYSIS REPORT
Generated: ${today}
═══════════════════════════════════════════════════════════

📈 TOP TRENDING TOPICS
━━━━━━━━━━━━━━━━━━━━━━
${
  potentialTopics.length > 0
    ? potentialTopics
        .slice(0, 10)
        .map((t, i) => `${i + 1}. ${t}`)
        .join("\n")
    : "• Data extraction in progress\n• Check back for trending updates"
}

🎭 TREND CATEGORIES
━━━━━━━━━━━━━━━━━━━━━━
• Entertainment: ${potentialTopics.slice(0, 3).join(", ") || "Updating..."}
• Fandoms: ${potentialTopics.slice(3, 6).join(", ") || "Updating..."}
• Events: ${potentialTopics.slice(6, 8).join(", ") || "Updating..."}
• Culture: Philippine trends, local content
• News: Current events, breaking stories

#️⃣ EXTRACTED HASHTAGS
━━━━━━━━━━━━━━━━━━━━━━
${hashtags.length > 0 ? hashtags.join(" ") : "No hashtags found in source data"}

💡 KEY INSIGHTS
━━━━━━━━━━━━━━━━━━━━━━
• Filipino audience highly engaged with entertainment content
• Fandom culture drives significant social media traffic
• Local events and shows generate viral moments
• Emotional and relatable content performs best
• Timing posts with trending topics increases reach

🎯 RECOMMENDED CONTENT ANGLES
━━━━━━━━━━━━━━━━━━━━━━
1. React to trending entertainment topics
2. Create relatable content for Filipino audience
3. Jump on viral hashtags early
4. Use local references and humor
5. Post during peak hours (7-9 PM PHT)

📱 READY-TO-USE HASHTAG PACK (25 tags)
━━━━━━━━━━━━━━━━━━━━━━
${defaultHashtags}

═══════════════════════════════════════════════════════════`;
    };

    try {
      const reportInstructions = `
You are the SEO Social Media Engine for Agent Amigos.
Analyze this raw trending data and create a comprehensive SEO Data Report.

### TASK:
1. **Extract ALL trending topics** from the raw text (ignore JSON errors, system messages).
2. **Categorize trends** by type: Entertainment, Events, Fandoms, Culture, News, etc.
3. **Rank trends by engagement** (note any view/engagement numbers like "188K", "797K").
4. **Identify key hashtags** already present in the data.
5. **Generate insights** about what's driving these trends.

### OUTPUT FORMAT:
═══════════════════════════════════════════════════════════
📊 SEO TREND ANALYSIS REPORT
Generated: ${new Date().toLocaleDateString()}
═══════════════════════════════════════════════════════════

📈 TOP TRENDING TOPICS
━━━━━━━━━━━━━━━━━━━━━━
[List the top 10 trends with engagement numbers if available]

🎭 TREND CATEGORIES
━━━━━━━━━━━━━━━━━━━━━━
• Entertainment: [list]
• Fandoms: [list]
• Events: [list]
• Culture: [list]
• News: [list]

#️⃣ EXTRACTED HASHTAGS
━━━━━━━━━━━━━━━━━━━━━━
[List all hashtags found in the data]

💡 KEY INSIGHTS
━━━━━━━━━━━━━━━━━━━━━━
[3-5 bullet points about what's driving engagement]

🎯 RECOMMENDED CONTENT ANGLES
━━━━━━━━━━━━━━━━━━━━━━
[Suggest 3-5 content ideas based on these trends]

📱 READY-TO-USE HASHTAG PACK (25 tags)
━━━━━━━━━━━━━━━━━━━━━━
#darrellbuttigieg #thesoldiersdream [+ 23 more relevant hashtags]

═══════════════════════════════════════════════════════════
`;

      const response = await axios.post(`${backendUrl}/scrape/extract`, {
        content: reportForm.rawData,
        instructions: reportInstructions,
        max_words: 800,
      });

      let reportContent =
        response.data?.data?.extracted ||
        response.data?.extracted ||
        response.data?.data ||
        JSON.stringify(response.data);

      // Check if AI failed
      const responseStr = JSON.stringify(response.data);
      if (
        responseStr.includes("LLM_API_BASE not configured") ||
        responseStr.includes("error") ||
        !reportContent
      ) {
        const localReport = generateLocalReport(reportForm.rawData);
        setGeneratedReport(localReport);
        setResult({
          success: true,
          message: "✅ SEO Report generated (local mode)",
        });
        setIsRunning(false);
        return;
      }

      let cleanedReport =
        typeof reportContent === "string"
          ? reportContent
          : JSON.stringify(reportContent, null, 2);

      cleanedReport = cleanedReport.replace(/```[\s\S]*?```/g, "").trim();

      setGeneratedReport(cleanedReport);
      setResult({
        success: true,
        message: "✅ SEO Report generated successfully!",
      });
    } catch (error) {
      // Use local fallback
      const localReport = generateLocalReport(reportForm.rawData);
      setGeneratedReport(localReport);
      setResult({
        success: true,
        message: "✅ SEO Report generated (offline mode)",
      });
    }
    setIsRunning(false);
  };

  // Copy report to clipboard
  const copyReportToClipboard = async () => {
    if (!generatedReport) return;
    try {
      await navigator.clipboard.writeText(generatedReport);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      const textArea = document.createElement("textarea");
      textArea.value = generatedReport;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      if (textArea) {
        try {
          if (typeof textArea.remove === "function") {
            textArea.remove();
          } else if (
            textArea.parentNode &&
            textArea.parentNode.contains(textArea)
          ) {
            textArea.parentNode.removeChild(textArea);
          }
        } catch (e) {
          console.warn("Failed to remove fallback textarea", e);
        }
      }
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  // Copy post to clipboard
  const copyToClipboard = async () => {
    if (!generatedPost) return;
    try {
      await navigator.clipboard.writeText(generatedPost);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement("textarea");
      textArea.value = generatedPost;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand("copy");
      if (textArea) {
        try {
          if (typeof textArea.remove === "function") {
            textArea.remove();
          } else if (
            textArea.parentNode &&
            textArea.parentNode.contains(textArea)
          ) {
            textArea.parentNode.removeChild(textArea);
          }
        } catch (e) {
          console.warn("Failed to remove fallback textarea", e);
        }
      }
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  // ═══════════════════════════════════════════════════════════════════════════
  // ⚡ AUTO FB POST - One-click AI conversion from scraped data to viral post
  // ═══════════════════════════════════════════════════════════════════════════
  const [autoFbGenerating, setAutoFbGenerating] = useState(false);
  const [quickPostResult, setQuickPostResult] = useState(null);

  const autoGenerateFacebookPost = async () => {
    // Extract content from result
    if (
      !result ||
      (!result.data && !result.text && !result.content && !result.matches)
    ) {
      setResult({
        success: false,
        error: "⚠️ No scraped content available. Run a scrape first!",
      });
      return;
    }

    setAutoFbGenerating(true);
    setQuickPostResult(null);

    // Extract content from various possible locations
    let extractedContent = "";
    const resultData = result.data || result;

    // Check for matches object (CSS selector results)
    if (resultData.matches && typeof resultData.matches === "object") {
      const matchTexts = [];
      for (const [selector, values] of Object.entries(resultData.matches)) {
        if (Array.isArray(values)) {
          const validTexts = values
            .filter((v) => typeof v === "string" && v.trim().length > 10)
            .filter((v) => !v.includes("<!DOCTYPE") && !v.includes("<html"))
            .map((v) => v.trim());
          matchTexts.push(...validTexts);
        }
      }
      const uniqueTexts = [...new Set(matchTexts)];
      if (uniqueTexts.length > 0) {
        extractedContent = uniqueTexts.join("\n\n");
      }
    }

    // Fallback to direct text content
    if (!extractedContent || extractedContent.length < 50) {
      const textContent =
        resultData.text ||
        resultData.content ||
        resultData.extracted ||
        resultData.fallback ||
        "";
      if (textContent && textContent.length > extractedContent.length) {
        extractedContent = textContent;
      }
    }

    // Last resort - stringify
    if (!extractedContent || extractedContent.length < 30) {
      extractedContent = JSON.stringify(resultData, null, 2);
    }

    const cleanedContent = extractedContent
      .substring(0, 8000)
      .replace(/\\n/g, "\n")
      .replace(/\\"/g, '"');

    // Quality check
    const lowQualityIndicators = [
      "__fb-light-mode",
      "Grupo • Facebook",
      "Facebook><meta",
      "Log into Facebook",
      "content is not available",
    ];
    const isLowQuality = lowQualityIndicators.some((ind) =>
      cleanedContent.toLowerCase().includes(ind.toLowerCase()),
    );

    if (isLowQuality) {
      setAutoFbGenerating(false);
      setQuickPostResult({
        success: false,
        error:
          "⚠️ Low quality scrape detected. Use DYNAMIC mode with logged-in browser.",
      });
      return;
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 🚀 VIRAL SEO FACEBOOK POST GENERATION
    // ═══════════════════════════════════════════════════════════════════════
    const viralSeoPrompt = `You are a VIRAL SOCIAL MEDIA EXPERT and SEO STRATEGIST for Agent Amigos.

## 🎯 MISSION: Create a VIRAL, SEO-optimized Facebook post from this scraped data.

## 📊 SCRAPED CONTENT TO TRANSFORM:
\`\`\`
${cleanedContent.substring(0, 4000)}
\`\`\`

## 🔥 VIRAL POST FORMULA:
1. **HOOK** (First line) - Create CURIOSITY, use pattern interrupts, make them STOP scrolling
   - Use numbers, questions, or bold statements
   - Example: "90% of people don't know this..." or "This changed EVERYTHING for me..."

2. **STORY/VALUE** (Body) - Transform the scraped content into:
   - Relatable narrative OR shocking revelation OR useful insight
   - Use short paragraphs (2-3 sentences max)
   - Add LINE BREAKS for mobile readability
   - Include relevant emojis strategically

3. **ENGAGEMENT CTA** (End) - Drive comments/shares:
   - Ask a question that's easy to answer
   - Create friendly debate ("Agree or disagree?")
   - Invite sharing ("Tag someone who needs this!")

4. **HASHTAGS** - Include 25-30 strategic hashtags:
   - Mix trending + niche + location-specific
   - MUST include: #darrellbuttigieg #thesoldiersdream
   - Add viral tags: #viral #trending #fyp #foryou #explore

## 📱 SEO OPTIMIZATION:
- Front-load keywords in first 2 sentences
- Use power words: FREE, SECRET, REVEALED, AMAZING, SHOCKING
- Include numbers and statistics when possible
- Create curiosity gaps

## ⚠️ RULES:
- Output ONLY the final post (ready to copy-paste)
- Sound HUMAN and AUTHENTIC (not robotic AI)
- Keep ACCURATE to the original content's meaning
- NO explaining what you're doing
- NO JSON or technical formatting

## 📱 FINAL POST (copy-paste ready):`;

    try {
      // Try AI generation first
      const response = await axios.post(`${backendUrl}/chat`, {
        message: viralSeoPrompt,
        conversation_history: [],
        require_approval: false,
      });

      let aiResponse =
        response.data?.response || response.data?.message || response.data;
      if (typeof aiResponse === "object") {
        aiResponse =
          aiResponse.response ||
          aiResponse.message ||
          aiResponse.text ||
          JSON.stringify(aiResponse);
      }

      if (
        aiResponse &&
        typeof aiResponse === "string" &&
        aiResponse.length > 50 &&
        !aiResponse.includes("LLM_API_BASE not configured") &&
        !aiResponse.includes("Connection aborted")
      ) {
        // Clean up response
        let cleanedPost = aiResponse
          .replace(
            /^(Here's|Here is|I've created|Below is|The post:?)[\s\S]*?:/gi,
            "",
          )
          .replace(/```[\s\S]*?```/g, "")
          .replace(/^\s*[-*]\s*/gm, "")
          .trim();

        // Ensure mandatory hashtags
        if (!cleanedPost.includes("#darrellbuttigieg")) {
          cleanedPost += "\n\n#darrellbuttigieg #thesoldiersdream";
        }

        setGeneratedPost(cleanedPost);
        setQuickPostResult({
          success: true,
          post: cleanedPost,
          method: "AI Generated",
        });
        setActiveTab("facebook");
        setFacebookForm({ ...facebookForm, content: cleanedContent });
      } else {
        throw new Error("AI response insufficient");
      }
    } catch (err) {
      console.log("AI generation failed, using local fallback:", err.message);

      // Local fallback with viral formatting
      const localPost = generateLocalViralPost(cleanedContent);
      setGeneratedPost(localPost);
      setQuickPostResult({
        success: true,
        post: localPost,
        method: "Local SEO",
      });
      setActiveTab("facebook");
      setFacebookForm({ ...facebookForm, content: cleanedContent });
    }

    setAutoFbGenerating(false);
  };

  // Local viral post generator (fallback when AI unavailable)
  const generateLocalViralPost = (content) => {
    // Extract key phrases and sentences
    const sentences = content
      .replace(/\n+/g, " ")
      .replace(/\s+/g, " ")
      .split(/[.!?]+/)
      .map((s) => s.trim())
      .filter((s) => s.length > 20 && s.length < 200);

    const keyPhrase = sentences[0] || content.substring(0, 100);
    const bodyContent = sentences.slice(1, 4).join(". ");

    // Viral hooks
    const hooks = [
      "🔥 This is HUGE...",
      "⚠️ You need to see this...",
      "😱 I can't believe what I just found...",
      "💡 Game-changer alert!",
      "🚨 Breaking news everyone should know...",
    ];
    const randomHook = hooks[Math.floor(Math.random() * hooks.length)];

    // CTAs
    const ctas = [
      "👇 What do you think? Drop a comment!",
      "💬 Agree or disagree? Let me know!",
      "🔁 Share this if it resonated with you!",
      "❤️ Like if this hit different!",
      "👥 Tag someone who needs to see this!",
    ];
    const randomCta = ctas[Math.floor(Math.random() * ctas.length)];

    // Build post
    const post = `${randomHook}

${keyPhrase}

${bodyContent ? bodyContent + "." : ""}

${randomCta}

#darrellbuttigieg #thesoldiersdream #viral #trending #fyp #foryou #explore #motivation #inspiration #success #mindset #growth #philippines #pinoy #news #update #breaking #share #like #follow #community #socialmedia #facebook #engagement #2024 #lifestyle`;

    return post;
  };

  // Use scraped result as input for Facebook post - IMPROVED EXTRACTION
  const useScrapedContent = () => {
    if (
      !result ||
      (!result.data && !result.text && !result.content && !result.matches)
    ) {
      setResult({
        success: false,
        error: "No scraped content available. Run a scrape first!",
      });
      return;
    }

    // Extract content from various possible locations in the result
    let extractedContent = "";
    const resultData = result.data || result;

    // 1. Check for matches object (CSS selector results) - BEST SOURCE
    if (resultData.matches && typeof resultData.matches === "object") {
      const matchTexts = [];
      for (const [selector, values] of Object.entries(resultData.matches)) {
        if (Array.isArray(values)) {
          // Filter out very short strings and duplicates
          const validTexts = values
            .filter((v) => typeof v === "string" && v.trim().length > 10)
            .filter((v) => !v.includes("<!DOCTYPE") && !v.includes("<html"))
            .map((v) => v.trim());
          matchTexts.push(...validTexts);
        }
      }
      // Remove duplicates and join
      const uniqueTexts = [...new Set(matchTexts)];
      if (uniqueTexts.length > 0) {
        extractedContent = uniqueTexts.join("\n\n");
      }
    }

    // 2. Check for direct text content
    if (!extractedContent || extractedContent.length < 50) {
      const textContent =
        resultData.text ||
        resultData.content ||
        resultData.extracted ||
        resultData.fallback ||
        "";

      if (textContent && textContent.length > extractedContent.length) {
        extractedContent = textContent;
      }
    }

    // 3. Fallback to JSON stringify (last resort)
    if (!extractedContent || extractedContent.length < 30) {
      extractedContent = JSON.stringify(resultData, null, 2);
    }

    // Clean up and set
    const cleanedContent = extractedContent
      .substring(0, 8000) // Limit size
      .replace(/\\n/g, "\n")
      .replace(/\\"/g, '"');

    // Check quality before switching tabs
    const lowQualityIndicators = [
      "__fb-light-mode",
      "Grupo • Facebook",
      "Facebook><meta",
      "Log into Facebook",
      "content is not available",
    ];

    const isLowQuality = lowQualityIndicators.some((ind) =>
      cleanedContent.toLowerCase().includes(ind.toLowerCase()),
    );

    if (isLowQuality) {
      setResult({
        success: false,
        error: `⚠️ The scraped content appears to be Facebook metadata only, not actual post content.

💡 TIP: For Facebook posts, use DYNAMIC mode (⚡ tab) with your logged-in Chrome browser.`,
      });
      return;
    }

    setFacebookForm({ ...facebookForm, content: cleanedContent });
    setActiveTab("facebook");
    setResult({
      success: true,
      message: `✅ Loaded ${cleanedContent.length} characters of scraped content. Ready to generate!`,
    });
  };

  // Use scraped result for report
  const useScrapedForReport = () => {
    if (result) {
      const content = JSON.stringify(result, null, 2);
      setReportForm({ ...reportForm, rawData: content.substring(0, 10000) });
      setActiveTab("report");
    }
  };

  if (!isOpen) return null;

  const inputStyle = {
    background: "rgba(15, 23, 42, 0.8)",
    border: "1px solid rgba(251, 191, 36, 0.3)",
    borderRadius: "10px",
    padding: "10px 12px",
    color: "#f8fafc",
    fontSize: "0.9em",
    width: "100%",
    outline: "none",
  };

  const textareaStyle = {
    ...inputStyle,
    minHeight: "70px",
    resize: "vertical",
  };

  const labelStyle = {
    fontSize: "0.75em",
    color: "#94a3b8",
    marginBottom: "4px",
    display: "block",
  };

  const btnPrimary = {
    background: "linear-gradient(135deg, #fbbf24, #f59e0b)",
    border: "none",
    padding: "12px 18px",
    borderRadius: "10px",
    color: "#111",
    fontWeight: "bold",
    cursor: "pointer",
    fontSize: "0.9em",
    boxShadow: "0 4px 15px rgba(251, 191, 36, 0.3)",
    width: "100%",
    marginTop: "10px",
  };

  const checkboxRow = {
    display: "flex",
    justifyContent: "space-between",
    fontSize: "0.8em",
    color: "#cbd5e1",
    padding: "8px 0",
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case "static":
        return (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            {/* Platform Preset Selector */}
            <div>
              <label style={labelStyle}>📌 Platform Preset</label>
              <select
                style={{
                  ...inputStyle,
                  cursor: "pointer",
                  appearance: "none",
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23fbbf24'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`,
                  backgroundRepeat: "no-repeat",
                  backgroundPosition: "right 10px center",
                  backgroundSize: "16px",
                  paddingRight: "35px",
                }}
                value={selectedPreset}
                onChange={(e) => {
                  const preset = e.target.value;
                  setSelectedPreset(preset);
                  if (SCRAPER_PRESETS[preset]) {
                    setStaticForm({
                      ...staticForm,
                      selectors: SCRAPER_PRESETS[preset].selectors,
                    });
                  }
                }}
              >
                {Object.entries(SCRAPER_PRESETS).map(([key, preset]) => (
                  <option key={key} value={key}>
                    {preset.name}
                  </option>
                ))}
              </select>
              {SCRAPER_PRESETS[selectedPreset] && (
                <span
                  style={{
                    fontSize: "0.7em",
                    color: "#64748b",
                    marginTop: "4px",
                    display: "block",
                  }}
                >
                  {SCRAPER_PRESETS[selectedPreset].description}
                </span>
              )}
            </div>

            <div>
              <label style={labelStyle}>Target URL</label>
              <input
                style={inputStyle}
                value={staticForm.url}
                onChange={(e) => {
                  const url = e.target.value;
                  setStaticForm({ ...staticForm, url });
                  // Auto-detect platform and suggest preset
                  if (url.includes("facebook.com/groups/")) {
                    setSelectedPreset("facebookGroup");
                    setStaticForm((prev) => ({
                      ...prev,
                      url,
                      selectors: SCRAPER_PRESETS.facebookGroup.selectors,
                    }));
                  } else if (url.includes("facebook.com")) {
                    setSelectedPreset("facebookPost");
                    setStaticForm((prev) => ({
                      ...prev,
                      url,
                      selectors: SCRAPER_PRESETS.facebookPost.selectors,
                    }));
                  } else if (
                    url.includes("twitter.com") ||
                    url.includes("x.com")
                  ) {
                    setSelectedPreset("twitter");
                    setStaticForm((prev) => ({
                      ...prev,
                      url,
                      selectors: SCRAPER_PRESETS.twitter.selectors,
                    }));
                  } else if (url.includes("instagram.com")) {
                    setSelectedPreset("instagram");
                    setStaticForm((prev) => ({
                      ...prev,
                      url,
                      selectors: SCRAPER_PRESETS.instagram.selectors,
                    }));
                  } else if (
                    url.includes("youtube.com") ||
                    url.includes("youtu.be")
                  ) {
                    setSelectedPreset("youtube");
                    setStaticForm((prev) => ({
                      ...prev,
                      url,
                      selectors: SCRAPER_PRESETS.youtube.selectors,
                    }));
                  } else if (url.includes("reddit.com")) {
                    setSelectedPreset("reddit");
                    setStaticForm((prev) => ({
                      ...prev,
                      url,
                      selectors: SCRAPER_PRESETS.reddit.selectors,
                    }));
                  }
                }}
                placeholder="https://facebook.com/groups/..."
              />
            </div>

            <div>
              <label style={labelStyle}>CSS Selectors (comma separated)</label>
              <textarea
                style={{
                  ...inputStyle,
                  minHeight: "80px",
                  resize: "vertical",
                  fontFamily: "monospace",
                  fontSize: "0.75em",
                  lineHeight: "1.4",
                }}
                value={staticForm.selectors}
                onChange={(e) =>
                  setStaticForm({ ...staticForm, selectors: e.target.value })
                }
                placeholder="div[role='article'], span[dir='auto'], a[role='link'] span"
              />
              <span style={{ fontSize: "0.65em", color: "#64748b" }}>
                💡 Tip: For Facebook posts, use the preset above or paste group
                post URL for auto-detection
              </span>
            </div>

            <div style={checkboxRow}>
              <label>
                <input
                  type="checkbox"
                  checked={staticForm.includeLinks}
                  onChange={(e) =>
                    setStaticForm({
                      ...staticForm,
                      includeLinks: e.target.checked,
                    })
                  }
                />{" "}
                Include Links
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={staticForm.includeHtml}
                  onChange={(e) =>
                    setStaticForm({
                      ...staticForm,
                      includeHtml: e.target.checked,
                    })
                  }
                />{" "}
                Include HTML
              </label>
            </div>

            <button
              style={btnPrimary}
              onClick={runStaticScrape}
              disabled={isRunning}
            >
              {isRunning ? "Scraping..." : "🕸️ Run Static Scrape"}
            </button>

            {/* Quick Tips for Facebook Scraping */}
            <div
              style={{
                background: "rgba(59, 130, 246, 0.1)",
                border: "1px solid rgba(59, 130, 246, 0.3)",
                borderRadius: "8px",
                padding: "10px",
                fontSize: "0.7em",
                color: "#93c5fd",
              }}
            >
              <strong>📘 Facebook Scraping Tips:</strong>
              <ul
                style={{
                  margin: "6px 0 0 0",
                  paddingLeft: "18px",
                  lineHeight: "1.6",
                }}
              >
                <li>
                  Use <strong>Dynamic</strong> tab for logged-in Facebook (needs
                  browser)
                </li>
                <li>Static scrape works for public posts only</li>
                <li>Comments require scrolling (use Dynamic mode)</li>
                <li>
                  For full conversations, try the "FB Comments Only" preset
                </li>
              </ul>
            </div>
          </div>
        );
      case "dynamic":
        return (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            <div>
              <label style={labelStyle}>Target URL</label>
              <input
                style={inputStyle}
                value={dynamicForm.url}
                onChange={(e) =>
                  setDynamicForm({ ...dynamicForm, url: e.target.value })
                }
              />
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "10px",
              }}
            >
              <div>
                <label style={labelStyle}>Wait For Selector</label>
                <input
                  style={inputStyle}
                  value={dynamicForm.waitForSelector}
                  onChange={(e) =>
                    setDynamicForm({
                      ...dynamicForm,
                      waitForSelector: e.target.value,
                    })
                  }
                />
              </div>
              <div>
                <label style={labelStyle}>Timeout (s)</label>
                <input
                  style={inputStyle}
                  type="number"
                  value={dynamicForm.waitTimeout}
                  onChange={(e) =>
                    setDynamicForm({
                      ...dynamicForm,
                      waitTimeout: e.target.value,
                    })
                  }
                />
              </div>
            </div>
            <div style={checkboxRow}>
              <label>
                <input
                  type="checkbox"
                  checked={dynamicForm.headless}
                  onChange={(e) =>
                    setDynamicForm({
                      ...dynamicForm,
                      headless: e.target.checked,
                    })
                  }
                />{" "}
                Headless
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={dynamicForm.screenshot}
                  onChange={(e) =>
                    setDynamicForm({
                      ...dynamicForm,
                      screenshot: e.target.checked,
                    })
                  }
                />{" "}
                Screenshot
              </label>
            </div>
            <button
              style={btnPrimary}
              onClick={runDynamicScrape}
              disabled={isRunning}
            >
              {isRunning ? "Running..." : "⚡ Run Dynamic Scrape"}
            </button>
          </div>
        );
      case "batch":
        return (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            {/* Platform Preset for Batch */}
            <div>
              <label style={labelStyle}>📌 Platform Preset</label>
              <select
                style={{
                  ...inputStyle,
                  cursor: "pointer",
                  appearance: "none",
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%23fbbf24'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`,
                  backgroundRepeat: "no-repeat",
                  backgroundPosition: "right 10px center",
                  backgroundSize: "16px",
                  paddingRight: "35px",
                }}
                value={selectedPreset}
                onChange={(e) => {
                  const preset = e.target.value;
                  setSelectedPreset(preset);
                  if (SCRAPER_PRESETS[preset]) {
                    setBatchForm({
                      ...batchForm,
                      selectors: SCRAPER_PRESETS[preset].selectors,
                    });
                  }
                }}
              >
                {Object.entries(SCRAPER_PRESETS).map(([key, preset]) => (
                  <option key={key} value={key}>
                    {preset.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={labelStyle}>URLs (one per line)</label>
              <textarea
                style={textareaStyle}
                value={batchForm.urls}
                onChange={(e) =>
                  setBatchForm({ ...batchForm, urls: e.target.value })
                }
                placeholder="https://facebook.com/groups/12345/posts/67890&#10;https://facebook.com/groups/12345/posts/11111"
              />
            </div>
            <div>
              <label style={labelStyle}>CSS Selectors</label>
              <textarea
                style={{
                  ...inputStyle,
                  minHeight: "60px",
                  resize: "vertical",
                  fontFamily: "monospace",
                  fontSize: "0.75em",
                }}
                value={batchForm.selectors}
                onChange={(e) =>
                  setBatchForm({ ...batchForm, selectors: e.target.value })
                }
              />
            </div>
            <button
              style={btnPrimary}
              onClick={runBatchScrape}
              disabled={isRunning}
            >
              {isRunning ? "Running..." : "📚 Run Batch Scrape"}
            </button>
          </div>
        );
      case "monitor":
        return (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            <div>
              <label style={labelStyle}>URL to Monitor</label>
              <input
                style={inputStyle}
                value={monitorForm.url}
                onChange={(e) =>
                  setMonitorForm({ ...monitorForm, url: e.target.value })
                }
              />
            </div>
            <div>
              <label style={labelStyle}>Selectors to Watch</label>
              <input
                style={inputStyle}
                value={monitorForm.selectors}
                onChange={(e) =>
                  setMonitorForm({ ...monitorForm, selectors: e.target.value })
                }
              />
            </div>
            <button
              style={btnPrimary}
              onClick={runMonitor}
              disabled={isRunning}
            >
              {isRunning ? "Monitoring..." : "⏱️ Take Snapshot"}
            </button>
          </div>
        );
      case "summarize":
        return (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            <div>
              <label style={labelStyle}>Content to Analyze</label>
              <textarea
                style={{ ...textareaStyle, minHeight: "100px" }}
                value={summaryForm.content}
                onChange={(e) =>
                  setSummaryForm({ ...summaryForm, content: e.target.value })
                }
              />
            </div>
            <div>
              <label style={labelStyle}>AI Instructions</label>
              <input
                style={inputStyle}
                value={summaryForm.instructions}
                onChange={(e) =>
                  setSummaryForm({
                    ...summaryForm,
                    instructions: e.target.value,
                  })
                }
              />
            </div>
            <div>
              <label style={labelStyle}>Max Words</label>
              <input
                style={inputStyle}
                type="number"
                value={summaryForm.maxWords}
                onChange={(e) =>
                  setSummaryForm({ ...summaryForm, maxWords: e.target.value })
                }
              />
            </div>
            <button
              style={btnPrimary}
              onClick={runSummary}
              disabled={isRunning}
            >
              {isRunning ? "Analyzing..." : "🧠 AI Extract"}
            </button>
          </div>
        );

      case "facebook":
        return (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            {/* Content Input */}
            <div>
              <label style={labelStyle}>📝 Raw Data / Content to Convert</label>
              <textarea
                style={{ ...textareaStyle, minHeight: "70px" }}
                value={facebookForm.content}
                onChange={(e) =>
                  setFacebookForm({ ...facebookForm, content: e.target.value })
                }
                placeholder='Paste scraped data, trending topics, or any content to convert into SEO Facebook post...\n\nExample: {"trending": "DUSTBIA PALAVAN TOUR 188K ... PBB GIRLS..."}'
              />
              {result && (
                <button
                  style={{
                    ...btnPrimary,
                    background: "linear-gradient(135deg, #3b82f6, #1d4ed8)",
                    marginTop: "6px",
                    fontSize: "0.75em",
                    padding: "6px 10px",
                  }}
                  onClick={useScrapedContent}
                >
                  📋 Use Last Scraped Result
                </button>
              )}
            </div>

            {/* Two column layout */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
              }}
            >
              <div>
                <label style={labelStyle}>🎨 Post Style</label>
                <select
                  style={{
                    ...inputStyle,
                    cursor: "pointer",
                    fontSize: "0.8em",
                  }}
                  value={facebookForm.postStyle}
                  onChange={(e) =>
                    setFacebookForm({
                      ...facebookForm,
                      postStyle: e.target.value,
                    })
                  }
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
                <label style={labelStyle}>👥 Audience</label>
                <select
                  style={{
                    ...inputStyle,
                    cursor: "pointer",
                    fontSize: "0.8em",
                  }}
                  value={facebookForm.targetAudience}
                  onChange={(e) =>
                    setFacebookForm({
                      ...facebookForm,
                      targetAudience: e.target.value,
                    })
                  }
                >
                  <option value="general">🌍 General</option>
                  <option value="filipino">🇵🇭 Filipino</option>
                  <option value="business">💼 Business</option>
                  <option value="tech">💻 Tech</option>
                  <option value="youth">🎮 Gen Z</option>
                </select>
              </div>
            </div>

            {/* Region and Hashtag count */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "8px",
              }}
            >
              <div>
                <label style={labelStyle}>🌏 Region Focus</label>
                <input
                  style={{ ...inputStyle, fontSize: "0.8em" }}
                  value={facebookForm.region}
                  onChange={(e) =>
                    setFacebookForm({ ...facebookForm, region: e.target.value })
                  }
                  placeholder="Philippines"
                />
              </div>
              <div>
                <label style={labelStyle}># Hashtags (20-35)</label>
                <input
                  style={{ ...inputStyle, fontSize: "0.8em" }}
                  type="number"
                  min="10"
                  max="35"
                  value={facebookForm.hashtagCount}
                  onChange={(e) =>
                    setFacebookForm({
                      ...facebookForm,
                      hashtagCount: Number(e.target.value),
                    })
                  }
                />
              </div>
            </div>

            {/* Custom Hashtags */}
            <div>
              <label style={labelStyle}>
                🏷️ Permanent Hashtags (always included)
              </label>
              <input
                style={{ ...inputStyle, fontSize: "0.8em" }}
                value={facebookForm.customHashtags}
                onChange={(e) =>
                  setFacebookForm({
                    ...facebookForm,
                    customHashtags: e.target.value,
                  })
                }
                placeholder="#darrellbuttigieg #thesoldiersdream"
              />
            </div>

            {/* Options Row */}
            <div style={checkboxRow}>
              <label>
                <input
                  type="checkbox"
                  checked={facebookForm.includeEmojis}
                  onChange={(e) =>
                    setFacebookForm({
                      ...facebookForm,
                      includeEmojis: e.target.checked,
                    })
                  }
                />{" "}
                😀 Emojis
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={facebookForm.callToAction}
                  onChange={(e) =>
                    setFacebookForm({
                      ...facebookForm,
                      callToAction: e.target.checked,
                    })
                  }
                />{" "}
                📣 CTA
              </label>
            </div>

            {/* Generate Button */}
            <button
              style={btnPrimary}
              onClick={generateFacebookPost}
              disabled={isRunning || !facebookForm.content.trim()}
            >
              {isRunning
                ? "🔄 Generating SEO Post..."
                : "📱 Generate SEO Facebook Post"}
            </button>

            {/* Generated Post Output */}
            {generatedPost && (
              <div style={{ marginTop: "4px" }}>
                <label style={labelStyle}>
                  📱 FINAL FACEBOOK POST (Ready to Paste)
                </label>
                <div
                  style={{
                    background:
                      "linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1))",
                    border: "1px solid rgba(59, 130, 246, 0.3)",
                    borderRadius: "10px",
                    padding: "10px",
                    maxHeight: "150px",
                    overflow: "auto",
                  }}
                >
                  <pre
                    style={{
                      margin: 0,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontSize: "0.8em",
                      color: "#e2e8f0",
                      fontFamily: "inherit",
                      lineHeight: "1.4",
                    }}
                  >
                    {generatedPost}
                  </pre>
                </div>
                <button
                  style={{
                    ...btnPrimary,
                    background: copySuccess
                      ? "linear-gradient(135deg, #10b981, #059669)"
                      : "linear-gradient(135deg, #8b5cf6, #7c3aed)",
                    marginTop: "8px",
                  }}
                  onClick={copyToClipboard}
                >
                  {copySuccess ? "✅ Copied!" : "📋 Copy to Clipboard"}
                </button>
              </div>
            )}
          </div>
        );
      case "report":
        return (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            {/* Raw Data Input */}
            <div>
              <label style={labelStyle}>
                📊 Raw Trending Data (paste JSON, scraped data, or any raw
                input)
              </label>
              <textarea
                style={{
                  ...textareaStyle,
                  minHeight: "100px",
                  fontSize: "0.8em",
                }}
                value={reportForm.rawData}
                onChange={(e) =>
                  setReportForm({ ...reportForm, rawData: e.target.value })
                }
                placeholder={
                  '{"success":false,"error":"LLM_API_BASE not configured","fallback":"Philippines … trending topics for last 24 hours ... DUSTBIA PALAVAN TOUR 188K ... PBB GIRLS DESERVE BETTER ... "}'
                }
              />
              {result && (
                <button
                  style={{
                    ...btnPrimary,
                    background: "linear-gradient(135deg, #10b981, #059669)",
                    marginTop: "6px",
                    fontSize: "0.75em",
                    padding: "6px 10px",
                  }}
                  onClick={useScrapedForReport}
                >
                  📋 Use Last Scraped Result
                </button>
              )}
            </div>

            {/* Report Type */}
            <div>
              <label style={labelStyle}>📈 Report Type</label>
              <select
                style={{ ...inputStyle, cursor: "pointer", fontSize: "0.85em" }}
                value={reportForm.reportType}
                onChange={(e) =>
                  setReportForm({ ...reportForm, reportType: e.target.value })
                }
              >
                <option value="trends">📈 Trending Topics Analysis</option>
                <option value="hashtags">🏷️ Hashtag Extraction</option>
                <option value="content">📝 Content Ideas</option>
                <option value="full">📊 Full SEO Report</option>
              </select>
            </div>

            {/* Generate Button */}
            <button
              style={{
                ...btnPrimary,
                background: "linear-gradient(135deg, #10b981, #059669)",
              }}
              onClick={generateSEOReport}
              disabled={isRunning || !reportForm.rawData.trim()}
            >
              {isRunning
                ? "📊 Generating Report..."
                : "📊 Generate SEO Data Report"}
            </button>

            {/* Generated Report Output */}
            {generatedReport && (
              <div style={{ marginTop: "4px" }}>
                <label style={labelStyle}>📊 SEO TREND ANALYSIS REPORT</label>
                <div
                  style={{
                    background:
                      "linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(5, 150, 105, 0.1))",
                    border: "1px solid rgba(16, 185, 129, 0.3)",
                    borderRadius: "10px",
                    padding: "10px",
                    maxHeight: "200px",
                    overflow: "auto",
                  }}
                >
                  <pre
                    style={{
                      margin: 0,
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      fontSize: "0.75em",
                      color: "#e2e8f0",
                      fontFamily: "monospace",
                      lineHeight: "1.3",
                    }}
                  >
                    {generatedReport}
                  </pre>
                </div>
                <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                  <button
                    style={{
                      ...btnPrimary,
                      flex: 1,
                      background: copySuccess
                        ? "linear-gradient(135deg, #10b981, #059669)"
                        : "linear-gradient(135deg, #8b5cf6, #7c3aed)",
                    }}
                    onClick={copyReportToClipboard}
                  >
                    {copySuccess ? "✅ Copied!" : "📋 Copy Report"}
                  </button>
                  <button
                    style={{
                      ...btnPrimary,
                      flex: 1,
                      background: "linear-gradient(135deg, #3b82f6, #1d4ed8)",
                    }}
                    onClick={() => {
                      setFacebookForm({
                        ...facebookForm,
                        content: reportForm.rawData,
                      });
                      setActiveTab("facebook");
                    }}
                  >
                    📱 Make FB Post
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: isStandalone ? "relative" : "fixed",
        left: isStandalone ? 0 : position.x,
        top: isStandalone ? 0 : position.y,
        width: isStandalone ? "100%" : size.width,
        height: isStandalone ? "100vh" : size.height,
        background: "rgba(11, 15, 25, 0.97)",
        color: "#f8fafc",
        borderRadius: isStandalone ? "0" : "16px",
        border: isStandalone ? "none" : "1px solid rgba(251, 191, 36, 0.4)",
        display: "flex",
        flexDirection: "column",
        zIndex: 999,
        boxShadow: isStandalone
          ? "none"
          : "0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(251, 191, 36, 0.1)",
        backdropFilter: isStandalone ? "none" : "blur(20px)",
        cursor: isDragging ? "grabbing" : "default",
      }}
    >
      {/* Draggable Header */}
      <div
        onMouseDown={isStandalone ? undefined : handleMouseDown}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "14px 18px",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
          background:
            "linear-gradient(135deg, rgba(251, 191, 36, 0.15), rgba(245, 158, 11, 0.05))",
          borderRadius: isStandalone ? "0" : "16px 16px 0 0",
          cursor: isStandalone ? "default" : "grab",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "12px",
              background: "linear-gradient(135deg, #fbbf24, #f59e0b)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.2em",
              boxShadow: "0 8px 25px rgba(251, 191, 36, 0.4)",
            }}
          >
            🕷️
          </div>
          <div>
            <div style={{ fontWeight: "bold", fontSize: "0.95em" }}>
              Amigos Scraper
            </div>
            <div style={{ fontSize: "0.7em", color: "#94a3b8" }}>
              AI Web Scraping •{" "}
              {isStandalone ? "Standalone Window" : "drag to move"}
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
          {!isStandalone && (
            <button
              onClick={() => {
                const url = window.location.origin + "?standalone=Scraper";
                window.open(url, "_blank", "width=800,height=900,popup");
              }}
              title="Popout to new window"
              style={{
                background: "rgba(255,255,255,0.1)",
                border: "none",
                color: "#94a3b8",
                cursor: "pointer",
                padding: "4px 8px",
                borderRadius: "4px",
                fontSize: "10px",
                display: "flex",
                alignItems: "center",
                gap: "4px",
              }}
            >
              <span>↗</span> Detach
            </button>
          )}
          {/* Reset Position Button */}
          {!isStandalone && (
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
          )}
          {/* Close Button */}
          <button
            onClick={onToggle}
            style={{
              background: "#ff4757",
              border: "none",
              fontSize: "1em",
              cursor: "pointer",
              color: "white",
              width: "30px",
              height: "30px",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Quick SEO - Simple URL input (hidden complexity) */}
      <div
        style={{
          padding: 12,
          borderBottom: "1px solid rgba(255,255,255,0.03)",
          background: "linear-gradient(90deg,#021022,#071430)",
        }}
      >
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            value={quickUrl}
            onChange={(e) => setQuickUrl(e.target.value)}
            placeholder="Enter a URL and click 'Scrape & SEO'"
            style={{
              flex: 1,
              padding: 10,
              borderRadius: 8,
              border: "1px solid #1f2a38",
              background: "#081322",
              color: "#e6eef8",
            }}
          />
          <button
            onClick={() => setQuickDynamic(!quickDynamic)}
            style={{
              padding: "8px 10px",
              borderRadius: 8,
              border: "1px solid #233042",
              background: quickDynamic ? "#0ea5a5" : "#13232b",
              color: "#fff",
            }}
            title="Toggle dynamic render scraping (requires Playwright setup)"
          >
            {quickDynamic ? "Dynamic" : "Static"}
          </button>
          <button
            onClick={handleQuickScrape}
            disabled={quickLoading || !quickUrl}
            style={{
              padding: "8px 12px",
              borderRadius: 8,
              border: "none",
              background: "linear-gradient(90deg,#8b5cf6,#6366f1)",
              color: "white",
              fontWeight: "700",
            }}
          >
            {quickLoading ? "Working…" : "Scrape & SEO"}
          </button>
        </div>
        {quickResult && (
          <div style={{ marginTop: 10 }}>
            {quickResult?.success === false ? (
              <div style={{ color: "#f87171" }}>
                Error:{" "}
                {quickResult?.error?.detail ||
                  quickResult?.error ||
                  JSON.stringify(quickResult)}
              </div>
            ) : (
              <div
                style={{
                  marginTop: 6,
                  color: "#cbd5e1",
                  fontSize: "0.9em",
                  whiteSpace: "pre-wrap",
                }}
              >
                {typeof quickResult?.summary === "string"
                  ? quickResult.summary
                  : JSON.stringify(quickResult.summary, null, 2)}
              </div>
            )}
          </div>
        )}

        {/* Comments quick-summarizer (paste comments, get summary) */}
        <div
          style={{
            marginTop: 10,
            borderTop: "1px solid rgba(255,255,255,0.02)",
            paddingTop: 10,
          }}
        >
          <div
            style={{ fontSize: "0.85em", color: "#94a3b8", marginBottom: 6 }}
          >
            💬 Summarize comments (paste one comment per line)
          </div>
          <textarea
            value={commentsText}
            onChange={(e) => setCommentsText(e.target.value)}
            placeholder="Paste comments here, one per line..."
            rows={4}
            style={{
              width: "100%",
              borderRadius: 8,
              padding: 8,
              background: "#031926",
              color: "#e6eef8",
              border: "1px solid #0f1724",
            }}
          />
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button
              onClick={handleSummarizeComments}
              disabled={commentsLoading || !commentsText}
              style={{
                padding: "8px 12px",
                borderRadius: 8,
                border: "none",
                background: "linear-gradient(90deg,#06b6d4,#0ea5a5)",
                color: "white",
                fontWeight: 700,
              }}
            >
              {commentsLoading ? "Summarizing…" : "Summarize Comments"}
            </button>
            <button
              onClick={() => {
                setCommentsText("");
                setCommentsResult(null);
              }}
              style={{
                padding: "8px 10px",
                borderRadius: 8,
                border: "1px solid #233042",
                background: "#0b1220",
                color: "#cbd5e1",
              }}
            >
              Clear
            </button>
          </div>
          {commentsResult && (
            <div
              style={{
                marginTop: 8,
                background: "#071426",
                padding: 10,
                borderRadius: 8,
                color: "#e6eef8",
              }}
            >
              {commentsResult?.success === false ? (
                <div style={{ color: "#f87171" }}>
                  Error:{" "}
                  {commentsResult?.error || JSON.stringify(commentsResult)}
                </div>
              ) : (
                <div style={{ whiteSpace: "pre-wrap", fontSize: "0.92em" }}>
                  {typeof commentsResult === "string"
                    ? commentsResult
                    : JSON.stringify(commentsResult, null, 2)}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              flex: 1,
              padding: "12px 8px",
              background:
                tab.key === activeTab
                  ? "rgba(251, 191, 36, 0.1)"
                  : "transparent",
              border: "none",
              borderBottom:
                tab.key === activeTab
                  ? "2px solid #fbbf24"
                  : "2px solid transparent",
              color: tab.key === activeTab ? "#fbbf24" : "#94a3b8",
              cursor: "pointer",
              fontSize: "0.75em",
              fontWeight: tab.key === activeTab ? 600 : 400,
              transition: "all 0.2s",
            }}
            title={tab.desc}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: "auto", padding: "16px" }}>
        {renderTabContent()}
      </div>

      {/* Result */}
      <div
        style={{
          borderTop: "1px solid rgba(255,255,255,0.08)",
          padding: "10px 14px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "6px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <div
              style={{
                fontSize: "0.75em",
                color: "#fbbf24",
                fontWeight: "500",
              }}
            >
              📋 Result
            </div>
            {(result.success || result.data || result.error) && (
              <button
                onClick={() => setResult({ success: false, message: "Ready." })}
                style={{
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  fontSize: "0.6em",
                  color: "#94a3b8",
                  cursor: "pointer",
                }}
              >
                Clear
              </button>
            )}
          </div>
          {/* Convert buttons - show when there's any result data */}
          {(result.success ||
            result.data ||
            result.text ||
            result.error ||
            result.fallback) &&
            activeTab !== "facebook" &&
            activeTab !== "report" && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: "4px" }}>
                {/* ⚡ AUTO FB POST - One-click AI viral post generator */}
                <button
                  onClick={autoGenerateFacebookPost}
                  disabled={autoFbGenerating}
                  style={{
                    background: autoFbGenerating
                      ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
                      : "linear-gradient(135deg, #f59e0b, #ef4444)",
                    border: "none",
                    padding: "4px 8px",
                    borderRadius: "6px",
                    color: "white",
                    fontSize: "0.6em",
                    fontWeight: "bold",
                    cursor: autoFbGenerating ? "wait" : "pointer",
                    flexShrink: 0,
                    boxShadow: "0 2px 8px rgba(245, 158, 11, 0.4)",
                    animation: autoFbGenerating ? "pulse 1s infinite" : "none",
                  }}
                  title="Auto-generate viral SEO Facebook post from scraped data"
                >
                  {autoFbGenerating ? "⏳ AI..." : "⚡ Auto FB"}
                </button>
                <button
                  onClick={useScrapedContent}
                  style={{
                    background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                    border: "none",
                    padding: "4px 6px",
                    borderRadius: "6px",
                    color: "white",
                    fontSize: "0.6em",
                    fontWeight: "bold",
                    cursor: "pointer",
                    flexShrink: 0,
                  }}
                  title="Load content into FB Post tab for manual editing"
                >
                  📱 FB
                </button>
                <button
                  onClick={useScrapedForReport}
                  style={{
                    background: "linear-gradient(135deg, #10b981, #059669)",
                    border: "none",
                    padding: "4px 6px",
                    borderRadius: "6px",
                    color: "white",
                    fontSize: "0.6em",
                    fontWeight: "bold",
                    cursor: "pointer",
                    flexShrink: 0,
                  }}
                >
                  📊 Rpt
                </button>
              </div>
            )}
        </div>
        {/* Quick Post Result notification */}
        {quickPostResult && (
          <div
            style={{
              background: quickPostResult.success
                ? "linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.1))"
                : "linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.1))",
              border: quickPostResult.success
                ? "1px solid rgba(16, 185, 129, 0.4)"
                : "1px solid rgba(239, 68, 68, 0.4)",
              borderRadius: "8px",
              padding: "8px 10px",
              marginBottom: "8px",
              fontSize: "0.7em",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span
                style={{
                  color: quickPostResult.success ? "#34d399" : "#f87171",
                }}
              >
                {quickPostResult.success
                  ? `✅ Viral post generated! (${quickPostResult.method})`
                  : quickPostResult.error}
              </span>
              {quickPostResult.success && (
                <button
                  onClick={async () => {
                    await navigator.clipboard.writeText(quickPostResult.post);
                    setCopySuccess(true);
                    setTimeout(() => setCopySuccess(false), 2000);
                  }}
                  style={{
                    background: copySuccess
                      ? "linear-gradient(135deg, #10b981, #059669)"
                      : "linear-gradient(135deg, #8b5cf6, #7c3aed)",
                    border: "none",
                    padding: "3px 8px",
                    borderRadius: "4px",
                    color: "white",
                    fontSize: "0.9em",
                    fontWeight: "bold",
                    cursor: "pointer",
                  }}
                >
                  {copySuccess ? "✅ Copied!" : "📋 Copy"}
                </button>
              )}
            </div>
          </div>
        )}
        <pre
          style={{
            height: "180px",
            overflowY: "auto",
            overflowX: "hidden",
            background: "rgba(5, 5, 10, 0.8)",
            padding: "10px",
            borderRadius: "8px",
            fontSize: "0.75em",
            color:
              result.success || result.data
                ? "#34d399"
                : result.error
                  ? "#f87171"
                  : "#94a3b8",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            margin: 0,
            border: "1px solid rgba(255,255,255,0.05)",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {isRunning && (
            <div style={{ marginBottom: "10px" }}>
              <div
                style={{
                  fontSize: "0.8em",
                  color: "#fbbf24",
                  marginBottom: "4px",
                }}
              >
                {result.message || "Processing..."}
              </div>
              <div
                style={{
                  width: "100%",
                  height: "4px",
                  background: "rgba(255,255,255,0.1)",
                  borderRadius: "2px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    width: "100%",
                    height: "100%",
                    background: "linear-gradient(90deg, #fbbf24, #f59e0b)",
                    animation: "loading-bar 2s linear infinite",
                    transformOrigin: "left",
                  }}
                />
              </div>
              <style>{`
                @keyframes loading-bar {
                  0% { transform: scaleX(0); }
                  50% { transform: scaleX(0.7); }
                  100% { transform: scaleX(1); opacity: 0; }
                }
              `}</style>
            </div>
          )}
          {JSON.stringify(result, null, 2)}
        </pre>
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
          background: "linear-gradient(135deg, transparent 50%, #fbbf24 50%)",
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

export default ScraperWorkbench;
