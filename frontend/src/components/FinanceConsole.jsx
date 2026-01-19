import React, { useState, useEffect, useRef, useCallback } from "react";

const FinanceConsole = ({
  isOpen,
  onToggle,
  apiUrl,
  backendPort = 8080,
  onScreenUpdate,
}) => {
  const [activeTab, setActiveTab] = useState("pnl");
  const [cryptoData, setCryptoData] = useState([]);
  const [stockData, setStockData] = useState([]);
  const [forexData, setForexData] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);

  // Crypto search state
  const [cryptoSearch, setCryptoSearch] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);

  // Stock search
  const [stockSearch, setStockSearch] = useState("");

  // Chart Modal state
  const [chartModal, setChartModal] = useState({
    open: false,
    asset: null,
    type: null,
  });

  // Draggable/Resizable state - Load from localStorage
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-finance-console-pos");
      return saved ? JSON.parse(saved) : { x: 100, y: 100 };
    } catch {
      return { x: 100, y: 100 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-finance-console-size");
      return saved ? JSON.parse(saved) : { width: 900, height: 700 };
    } catch {
      return { width: 900, height: 700 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Save position to localStorage when it changes
  useEffect(() => {
    localStorage.setItem(
      "amigos-finance-console-pos",
      JSON.stringify(position),
    );
  }, [position]);

  // Save size to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-finance-console-size", JSON.stringify(size));
  }, [size]);

  // 👀 SCREEN AWARENESS - Report data to Agent Amigos
  useEffect(() => {
    if (onScreenUpdate && isOpen) {
      onScreenUpdate({
        cryptoData,
        stockData,
        forexData,
        watchlist,
        analysis,
        activeTab,
      });
    }
  }, [
    cryptoData,
    stockData,
    forexData,
    watchlist,
    analysis,
    activeTab,
    isOpen,
    onScreenUpdate,
  ]);

  // Popular cryptos - includes meme coins
  const popularCrypto = [
    "bitcoin",
    "ethereum",
    "solana",
    "cardano",
    "dogecoin",
    "ripple",
    "shiba-inu",
    "pepe",
    "bonk",
    "floki",
  ];

  const popularStocks = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "TSLA",
    "AMZN",
    "NVDA",
    "META",
  ];

  const popularForex = [
    { symbol: "AUDUSD", name: "AUD / USD" },
    { symbol: "EURUSD", name: "EUR / USD" },
    { symbol: "GBPUSD", name: "GBP / USD" },
    { symbol: "USDJPY", name: "USD / JPY" },
    { symbol: "USDCAD", name: "USD / CAD" },
  ];

  // Load watchlist from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("finance_watchlist");
    if (saved) {
      try {
        setWatchlist(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to load watchlist:", e);
      }
    }
  }, []);

  // Auto-fetch data on mount and tab change
  useEffect(() => {
    if (!isOpen) return;
    if (activeTab === "crypto" && cryptoData.length === 0) {
      fetchCryptoData();
    } else if (activeTab === "stocks" && stockData.length === 0) {
      fetchStockData();
    } else if (activeTab === "forex" && forexData.length === 0) {
      fetchForexData();
    }
  }, [activeTab, isOpen]);

  const fetchForexData = async () => {
    setLoading(true);
    try {
      // Using a simple public API for forex or just mock data if not available
      // For now, we'll use the TradingView symbols which we can display in the table
      const data = popularForex.map((f) => ({
        ...f,
        price: "Live", // TradingView will show the real price in the chart
        change: 0,
        changePercent: 0,
      }));
      setForexData(data);
    } catch (err) {
      console.error("Forex fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Save watchlist to localStorage
  useEffect(() => {
    localStorage.setItem("finance_watchlist", JSON.stringify(watchlist));
  }, [watchlist]);

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
          width: Math.max(600, e.clientX - rect.left + 10),
          height: Math.max(400, e.clientY - rect.top + 10),
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

  // Search cryptos using CoinGecko API
  const searchCrypto = async (query) => {
    if (!query || query.length < 2) {
      setSearchResults([]);
      return;
    }

    setSearchLoading(true);
    try {
      const response = await fetch(
        `https://api.coingecko.com/api/v3/search?query=${encodeURIComponent(
          query,
        )}`,
      );
      if (response.ok) {
        const data = await response.json();
        // Return top 10 coins from search
        setSearchResults(data.coins?.slice(0, 10) || []);
      } else {
        setSearchResults([]);
      }
    } catch (err) {
      console.error("Crypto search error:", err);
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (cryptoSearch) {
        searchCrypto(cryptoSearch);
      } else {
        setSearchResults([]);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [cryptoSearch]);

  // Binance symbol mapping
  const binanceSymbolMap = {
    bitcoin: "BTCUSDT",
    ethereum: "ETHUSDT",
    solana: "SOLUSDT",
    cardano: "ADAUSDT",
    dogecoin: "DOGEUSDT",
    ripple: "XRPUSDT",
    "shiba-inu": "SHIBUSDT",
    pepe: "PEPEUSDT",
    bonk: "BONKUSDT",
    floki: "FLOKIUSDT",
  };

  // Fetch crypto data from Binance as primary, CoinGecko as fallback
  const fetchCryptoData = async (coins = popularCrypto) => {
    setLoading(true);
    setError(null);

    try {
      // Try Binance first for better reliability
      const binanceData = await Promise.all(
        coins.map(async (coinId) => {
          const symbol = binanceSymbolMap[coinId];
          if (!symbol) return null;

          try {
            // Get current price and 24h ticker
            const tickerRes = await fetch(
              `https://api.binance.com/api/v3/ticker/24hr?symbol=${symbol}`,
            );
            if (!tickerRes.ok) return null;
            const ticker = await tickerRes.json();

            // Get sparkline data (7d)
            const klinesRes = await fetch(
              `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=4h&limit=42`,
            );
            const klines = klinesRes.ok ? await klinesRes.json() : [];

            return {
              id: coinId,
              symbol: symbol.replace("USDT", ""),
              name:
                coinId.charAt(0).toUpperCase() +
                coinId.slice(1).replace("-", " "),
              current_price: parseFloat(ticker.lastPrice),
              price_change_percentage_24h: parseFloat(
                ticker.priceChangePercent,
              ),
              price_change_percentage_1h_in_currency: null,
              price_change_percentage_7d_in_currency: null,
              total_volume:
                parseFloat(ticker.volume) * parseFloat(ticker.lastPrice),
              market_cap: null,
              sparkline_in_7d: { price: klines.map((k) => parseFloat(k[4])) },
              image: `https://assets.coingecko.com/coins/images/1/small/${coinId}.png`,
            };
          } catch {
            return null;
          }
        }),
      );

      const validBinanceData = binanceData.filter(Boolean);

      if (validBinanceData.length >= coins.length / 2) {
        setCryptoData(validBinanceData);
        console.log("✅ Loaded crypto data from Binance");
        return validBinanceData;
      }

      // Fallback to CoinGecko
      throw new Error("Binance data insufficient, trying CoinGecko");
    } catch (binanceErr) {
      console.warn("Binance fetch failed:", binanceErr.message);

      // CoinGecko fallback
      try {
        const coinIds = coins.join(",");
        const response = await fetch(
          `https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=${coinIds}&order=market_cap_desc&sparkline=true&price_change_percentage=1h,24h,7d`,
        );
        if (!response.ok) throw new Error("CoinGecko: " + response.status);
        const data = await response.json();
        setCryptoData(data);
        console.log("✅ Loaded crypto data from CoinGecko");
        return data;
      } catch (geckoErr) {
        console.error("Both Binance and CoinGecko failed:", geckoErr.message);
        setError("Failed to fetch crypto data. Please try again.");
        return [];
      }
    } finally {
      setLoading(false);
    }
  };

  // Fetch stock data via Yahoo Finance API (via backend proxy or direct)
  const fetchStockData = async (symbols = popularStocks) => {
    setLoading(true);
    setError(null);
    const backendUrl = apiUrl || `http://localhost:${backendPort}`;

    try {
      // Using a free API for stock quotes
      const stockPromises = symbols.map(async (symbol) => {
        try {
          // Use backend scraper as proxy to avoid CORS
          const targetUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?interval=1d&range=5d`;
          const response = await fetch(`${backendUrl}/scrape/url`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              url: targetUrl,
              include_html: true, // Get raw response body
              include_text: false,
            }),
          });

          if (!response.ok) return null;

          const proxyData = await response.json();
          if (!proxyData.html) return null;

          const data = JSON.parse(proxyData.html);
          const quote = data.chart?.result?.[0];
          if (!quote) return null;

          const meta = quote.meta;
          const closes = quote.indicators?.quote?.[0]?.close || [];
          const prevClose = closes[closes.length - 2] || meta.previousClose;
          const currentPrice = meta.regularMarketPrice;
          const change = currentPrice - prevClose;
          const changePercent = (change / prevClose) * 100;

          return {
            symbol: meta.symbol,
            name: meta.shortName || meta.symbol,
            price: currentPrice,
            change: change,
            changePercent: changePercent,
            volume: meta.regularMarketVolume,
            sparkline: closes,
          };
        } catch (e) {
          console.error(`Error fetching stock ${symbol}:`, e);
          return null;
        }
      });

      const results = await Promise.all(stockPromises);
      const validResults = results.filter(Boolean);
      setStockData(validResults);
      return validResults;
    } catch (err) {
      setError(err.message);
      return [];
    } finally {
      setLoading(false);
    }
  };

  // Add to watchlist
  const addToWatchlist = (item, type) => {
    const id = type === "crypto" ? item.id : item.symbol;
    if (!watchlist.find((w) => w.id === id)) {
      setWatchlist([
        ...watchlist,
        {
          id,
          type,
          name: item.name || item.symbol,
          symbol: type === "crypto" ? item.symbol?.toUpperCase() : item.symbol,
        },
      ]);
    }
  };

  // Add from search results
  const addFromSearch = (coin) => {
    if (!watchlist.find((w) => w.id === coin.id)) {
      setWatchlist([
        ...watchlist,
        {
          id: coin.id,
          type: "crypto",
          name: coin.name,
          symbol: coin.symbol?.toUpperCase(),
        },
      ]);
    }
    setCryptoSearch("");
    setSearchResults([]);
  };

  // Remove from watchlist
  const removeFromWatchlist = (id) => {
    setWatchlist(watchlist.filter((w) => w.id !== id));
  };

  // Get AI analysis
  const getAIAnalysis = async () => {
    setAnalysisLoading(true);
    setAnalysis(null);
    try {
      // Ensure we have data for both
      let currentCrypto = cryptoData;
      let currentStocks = stockData;

      if (currentCrypto.length === 0) {
        currentCrypto = await fetchCryptoData(popularCrypto);
      }
      if (currentStocks.length === 0) {
        currentStocks = await fetchStockData(popularStocks);
      }

      const cryptoStrings = (currentCrypto || []).map(
        (c) =>
          `CRYPTO: ${
            c.name
          }: $${c.current_price?.toLocaleString()} (${c.price_change_percentage_24h?.toFixed(
            2,
          )}% 24h)`,
      );

      const stockStrings = (currentStocks || []).map(
        (s) =>
          `STOCK: ${s.symbol}: $${s.price?.toFixed(
            2,
          )} (${s.changePercent?.toFixed(2)}%)`,
      );

      const marketData = [...cryptoStrings, ...stockStrings];

      const prompt = `Analyze these market prices (Crypto & Stocks) and provide a brief market summary with key insights.
      
      DATA:
      ${marketData.join("\n")}
      
      INSTRUCTIONS:
      1. Summarize the overall sentiment for Crypto.
      2. Summarize the overall sentiment for Stocks.
      3. Highlight any major movers (gainers/losers).
      4. Keep it concise (3-4 sentences).`;

      const backendUrl = apiUrl || `http://localhost:${backendPort}`;
      const response = await fetch(`${backendUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: prompt }],
          require_approval: false,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        // Handle AgentResponse format (content is in .content)
        setAnalysis(
          data.content ||
            data.response ||
            data.message ||
            "Analysis not available",
        );
      } else {
        let errMsg = `Error ${response.status}`;
        try {
          const errData = await response.json();
          if (errData.detail) errMsg += `: ${JSON.stringify(errData.detail)}`;
        } catch (e) {
          errMsg += `: ${response.statusText}`;
        }
        setAnalysis(errMsg);
      }
    } catch (err) {
      setAnalysis("Error connecting to AI: " + err.message);
    } finally {
      setAnalysisLoading(false);
    }
  };

  // Initial fetch
  useEffect(() => {
    if (!isOpen) return;
    if (activeTab === "crypto") {
      const cryptoWatchlist = watchlist
        .filter((w) => w.type === "crypto")
        .map((w) => w.id);
      const allCryptos = [...new Set([...popularCrypto, ...cryptoWatchlist])];
      fetchCryptoData(allCryptos);
    } else if (activeTab === "stocks") {
      const stockWatchlist = watchlist
        .filter((w) => w.type === "stock")
        .map((w) => w.id);
      const allStocks = [...new Set([...popularStocks, ...stockWatchlist])];
      fetchStockData(allStocks);
    }
  }, [activeTab, watchlist, isOpen]);

  // Don't render if not open (must be after all hooks)
  if (!isOpen) return null;

  // Sparkline mini chart component
  const SparklineChart = ({ data, color }) => {
    if (!data || data.length === 0) return null;

    const validData = data.filter((d) => d != null);
    if (validData.length === 0) return null;

    const min = Math.min(...validData);
    const max = Math.max(...validData);
    const range = max - min || 1;

    const points = validData
      .map((value, i) => {
        const x = (i / (validData.length - 1)) * 80;
        const y = 30 - ((value - min) / range) * 25;
        return `${x},${y}`;
      })
      .join(" ");

    return (
      <svg width="80" height="30" style={{ display: "block" }}>
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="1.5"
          points={points}
        />
      </svg>
    );
  };

  // Format number with commas
  const formatNumber = (num) => {
    if (num >= 1e12) return (num / 1e12).toFixed(2) + "T";
    if (num >= 1e9) return (num / 1e9).toFixed(2) + "B";
    if (num >= 1e6) return (num / 1e6).toFixed(2) + "M";
    if (num >= 1e3) return (num / 1e3).toFixed(2) + "K";
    return num?.toLocaleString() || "0";
  };

  const styles = {
    container: {
      position: "fixed",
      left: position.x,
      top: position.y,
      width: size.width,
      height: size.height,
      backgroundColor: "rgba(11, 11, 21, 0.97)",
      backdropFilter: "blur(20px)",
      borderRadius: "16px",
      border: "1px solid rgba(99, 102, 241, 0.5)",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      boxShadow:
        "0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(99, 102, 241, 0.15)",
      zIndex: 1000,
      cursor: isDragging ? "grabbing" : "default",
    },
    header: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "14px 18px",
      background:
        "linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.1) 100%)",
      borderBottom: "1px solid rgba(99, 102, 241, 0.2)",
      cursor: "grab",
    },
    title: {
      color: "#a5b4fc",
      fontSize: "18px",
      fontWeight: "bold",
      display: "flex",
      alignItems: "center",
      gap: "12px",
    },
    closeBtn: {
      background: "linear-gradient(135deg, #ef4444 0%, #dc2626 100%)",
      border: "none",
      color: "white",
      width: "30px",
      height: "30px",
      borderRadius: "10px",
      cursor: "pointer",
      fontSize: "16px",
      boxShadow: "0 4px 15px rgba(239, 68, 68, 0.3)",
      transition: "all 0.2s ease",
    },
    tabs: {
      display: "flex",
      gap: "0",
      padding: "0 16px",
      backgroundColor: "rgba(18, 18, 31, 0.8)",
    },
    tab: {
      padding: "12px 24px",
      border: "none",
      cursor: "pointer",
      fontSize: "14px",
      fontWeight: "500",
      transition: "all 0.2s",
    },
    activeTab: {
      backgroundColor: "rgba(99, 102, 241, 0.1)",
      color: "#a5b4fc",
      borderBottom: "2px solid #6366f1",
    },
    inactiveTab: {
      backgroundColor: "transparent",
      color: "#6b7280",
    },
    content: {
      flex: 1,
      overflow: "auto",
      padding: "16px",
    },
    searchBar: {
      display: "flex",
      gap: "10px",
      marginBottom: "16px",
      position: "relative",
    },
    searchInput: {
      flex: 1,
      padding: "12px 18px",
      backgroundColor: "rgba(30, 30, 50, 0.8)",
      border: "1px solid rgba(99, 102, 241, 0.3)",
      borderRadius: "12px",
      color: "white",
      fontSize: "14px",
      outline: "none",
      transition: "all 0.2s ease",
    },
    searchResults: {
      position: "absolute",
      top: "100%",
      left: 0,
      right: 0,
      backgroundColor: "rgba(18, 18, 31, 0.98)",
      border: "1px solid rgba(99, 102, 241, 0.3)",
      borderRadius: "12px",
      maxHeight: "300px",
      overflow: "auto",
      zIndex: 100,
      marginTop: "4px",
      backdropFilter: "blur(10px)",
    },
    searchResultItem: {
      padding: "12px 16px",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      gap: "10px",
      borderBottom: "1px solid rgba(99, 102, 241, 0.1)",
      transition: "all 0.2s ease",
    },
    table: {
      width: "100%",
      borderCollapse: "collapse",
    },
    th: {
      textAlign: "left",
      padding: "14px",
      color: "#94a3b8",
      fontSize: "12px",
      fontWeight: "600",
      textTransform: "uppercase",
      borderBottom: "1px solid rgba(99, 102, 241, 0.2)",
    },
    td: {
      padding: "14px",
      borderBottom: "1px solid rgba(99, 102, 241, 0.1)",
      color: "white",
      fontSize: "14px",
    },
    coinCell: {
      display: "flex",
      alignItems: "center",
      gap: "10px",
    },
    coinIcon: {
      width: "32px",
      height: "32px",
      borderRadius: "50%",
      boxShadow: "0 2px 8px rgba(0, 0, 0, 0.3)",
    },
    positive: {
      color: "#10b981",
    },
    negative: {
      color: "#ef4444",
    },
    watchlistBtn: {
      padding: "6px 14px",
      background: "rgba(99, 102, 241, 0.15)",
      border: "1px solid rgba(99, 102, 241, 0.5)",
      borderRadius: "8px",
      color: "#a5b4fc",
      cursor: "pointer",
      fontSize: "12px",
      transition: "all 0.2s ease",
    },
    removeBtn: {
      padding: "6px 14px",
      background: "rgba(239, 68, 68, 0.15)",
      border: "1px solid rgba(239, 68, 68, 0.5)",
      borderRadius: "8px",
      color: "#fca5a5",
      cursor: "pointer",
      fontSize: "12px",
      transition: "all 0.2s ease",
    },
    analysisBox: {
      marginTop: "16px",
      padding: "16px",
      backgroundColor: "#16213e",
      borderRadius: "8px",
      border: "1px solid #333",
    },
    analysisBtn: {
      padding: "10px 20px",
      background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      border: "none",
      borderRadius: "8px",
      color: "white",
      cursor: "pointer",
      fontSize: "14px",
      fontWeight: "500",
    },
    refreshBtn: {
      padding: "8px 14px",
      background: "rgba(99, 102, 241, 0.15)",
      border: "1px solid rgba(99, 102, 241, 0.5)",
      borderRadius: "8px",
      color: "#a5b4fc",
      cursor: "pointer",
      fontSize: "12px",
      transition: "all 0.2s ease",
    },
    watchlistSection: {
      marginBottom: "20px",
      padding: "16px",
      backgroundColor: "#16213e",
      borderRadius: "8px",
      border: "1px solid #4a9eff33",
    },
    resizeHandle: {
      position: "absolute",
      bottom: 0,
      right: 0,
      width: "20px",
      height: "20px",
      cursor: "se-resize",
      background: "linear-gradient(135deg, transparent 50%, #4a9eff 50%)",
      borderRadius: "0 0 12px 0",
    },
  };

  return (
    <div ref={containerRef} style={styles.container}>
      {/* Draggable Header */}
      <div style={styles.header} onMouseDown={handleMouseDown}>
        <div style={styles.title}>
          📊 Finance Console
          <span
            style={{ fontSize: "12px", color: "#888", fontWeight: "normal" }}
          >
            (click on any row for detailed chart)
          </span>
        </div>
        <button style={styles.closeBtn} onClick={onToggle}>
          ×
        </button>
      </div>

      {/* Tabs */}
      <div style={styles.tabs}>
        <button
          style={{
            ...styles.tab,
            ...(activeTab === "crypto" ? styles.activeTab : styles.inactiveTab),
          }}
          onClick={() => setActiveTab("crypto")}
        >
          🪙 Crypto
        </button>
        <button
          style={{
            ...styles.tab,
            ...(activeTab === "stocks" ? styles.activeTab : styles.inactiveTab),
          }}
          onClick={() => setActiveTab("stocks")}
        >
          📈 Stocks
        </button>
        <button
          style={{
            ...styles.tab,
            ...(activeTab === "forex" ? styles.activeTab : styles.inactiveTab),
          }}
          onClick={() => setActiveTab("forex")}
        >
          💱 Forex
        </button>
        <button
          style={{
            ...styles.tab,
            ...(activeTab === "watchlist"
              ? styles.activeTab
              : styles.inactiveTab),
          }}
          onClick={() => setActiveTab("watchlist")}
        >
          ⭐ Watchlist ({watchlist.length})
        </button>
      </div>

      {/* Content */}
      <div style={styles.content}>
        {error && (
          <div
            style={{ color: "#ff4757", padding: "16px", textAlign: "center" }}
          >
            Error: {error}
          </div>
        )}

        {/* Crypto Tab */}
        {activeTab === "crypto" && (
          <>
            {/* Search Bar */}
            <div style={styles.searchBar}>
              <input
                style={styles.searchInput}
                type="text"
                placeholder="🔍 Search for any cryptocurrency (e.g., shib, pepe, bonk)..."
                value={cryptoSearch}
                onChange={(e) => setCryptoSearch(e.target.value)}
              />
              <button
                style={styles.analysisBtn}
                onClick={() => fetchCryptoData()}
              >
                🔄 Refresh
              </button>

              {/* Search Results Dropdown */}
              {(searchResults.length > 0 || searchLoading) && (
                <div style={styles.searchResults}>
                  {searchLoading ? (
                    <div
                      style={{
                        padding: "16px",
                        color: "#888",
                        textAlign: "center",
                      }}
                    >
                      Searching...
                    </div>
                  ) : (
                    searchResults.map((coin) => (
                      <div
                        key={coin.id}
                        style={styles.searchResultItem}
                        onClick={() => addFromSearch(coin)}
                        onMouseEnter={(e) =>
                          (e.target.style.backgroundColor = "#333")
                        }
                        onMouseLeave={(e) =>
                          (e.target.style.backgroundColor = "transparent")
                        }
                      >
                        {coin.thumb && (
                          <img
                            src={coin.thumb}
                            alt=""
                            style={{
                              width: "24px",
                              height: "24px",
                              borderRadius: "50%",
                            }}
                          />
                        )}
                        <div style={{ flex: 1 }}>
                          <div style={{ color: "white", fontWeight: "500" }}>
                            {coin.name}
                          </div>
                          <div style={{ color: "#888", fontSize: "12px" }}>
                            {coin.symbol?.toUpperCase()}
                          </div>
                        </div>
                        <span style={{ color: "#4a9eff", fontSize: "12px" }}>
                          + Add
                        </span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {loading ? (
              <div
                style={{ textAlign: "center", padding: "40px", color: "#888" }}
              >
                Loading crypto data...
              </div>
            ) : (
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>#</th>
                    <th style={styles.th}>Coin</th>
                    <th style={styles.th}>Price</th>
                    <th style={styles.th}>1h %</th>
                    <th style={styles.th}>24h %</th>
                    <th style={styles.th}>7d %</th>
                    <th style={styles.th}>Market Cap</th>
                    <th style={styles.th}>7d Chart</th>
                    <th style={styles.th}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {cryptoData.map((coin, index) => (
                    <tr
                      key={coin.id}
                      onClick={() =>
                        setChartModal({
                          open: true,
                          asset: coin,
                          type: "crypto",
                        })
                      }
                      style={{
                        cursor: "pointer",
                        transition: "background 0.2s",
                      }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background =
                          "rgba(74, 158, 255, 0.1)")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = "transparent")
                      }
                    >
                      <td style={styles.td}>{index + 1}</td>
                      <td style={styles.td}>
                        <div style={styles.coinCell}>
                          <img
                            src={coin.image}
                            alt={coin.name}
                            style={styles.coinIcon}
                          />
                          <div>
                            <div style={{ fontWeight: "500" }}>{coin.name}</div>
                            <div style={{ color: "#888", fontSize: "12px" }}>
                              {coin.symbol?.toUpperCase()}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td style={styles.td}>
                        ${coin.current_price?.toLocaleString()}
                      </td>
                      <td
                        style={{
                          ...styles.td,
                          ...(coin.price_change_percentage_1h_in_currency >= 0
                            ? styles.positive
                            : styles.negative),
                        }}
                      >
                        {coin.price_change_percentage_1h_in_currency?.toFixed(
                          2,
                        )}
                        %
                      </td>
                      <td
                        style={{
                          ...styles.td,
                          ...(coin.price_change_percentage_24h >= 0
                            ? styles.positive
                            : styles.negative),
                        }}
                      >
                        {coin.price_change_percentage_24h?.toFixed(2)}%
                      </td>
                      <td
                        style={{
                          ...styles.td,
                          ...(coin.price_change_percentage_7d_in_currency >= 0
                            ? styles.positive
                            : styles.negative),
                        }}
                      >
                        {coin.price_change_percentage_7d_in_currency?.toFixed(
                          2,
                        )}
                        %
                      </td>
                      <td style={styles.td}>
                        ${formatNumber(coin.market_cap)}
                      </td>
                      <td style={styles.td}>
                        <SparklineChart
                          data={coin.sparkline_in_7d?.price}
                          color={
                            coin.price_change_percentage_7d_in_currency >= 0
                              ? "#2ed573"
                              : "#ff4757"
                          }
                        />
                      </td>
                      <td style={styles.td}>
                        {watchlist.find((w) => w.id === coin.id) ? (
                          <button
                            style={styles.removeBtn}
                            onClick={(e) => {
                              e.stopPropagation();
                              removeFromWatchlist(coin.id);
                            }}
                          >
                            Remove
                          </button>
                        ) : (
                          <button
                            style={styles.watchlistBtn}
                            onClick={(e) => {
                              e.stopPropagation();
                              addToWatchlist(coin, "crypto");
                            }}
                          >
                            + Watch
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}

        {/* Stocks Tab */}
        {activeTab === "stocks" && (
          <>
            <div style={styles.searchBar}>
              <input
                style={styles.searchInput}
                type="text"
                placeholder="Enter stock symbol (e.g., AAPL, TSLA)..."
                value={stockSearch}
                onChange={(e) => setStockSearch(e.target.value.toUpperCase())}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && stockSearch) {
                    const newStocks = [...popularStocks];
                    if (!newStocks.includes(stockSearch)) {
                      newStocks.push(stockSearch);
                    }
                    fetchStockData(newStocks);
                    setStockSearch("");
                  }
                }}
              />
              <button
                style={styles.analysisBtn}
                onClick={() => {
                  if (stockSearch && !popularStocks.includes(stockSearch)) {
                    fetchStockData([...popularStocks, stockSearch]);
                  } else {
                    fetchStockData();
                  }
                  setStockSearch("");
                }}
              >
                {stockSearch ? "+ Add Stock" : "🔄 Refresh"}
              </button>
            </div>

            {loading ? (
              <div
                style={{ textAlign: "center", padding: "40px", color: "#888" }}
              >
                Loading stock data...
              </div>
            ) : (
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Symbol</th>
                    <th style={styles.th}>Name</th>
                    <th style={styles.th}>Price</th>
                    <th style={styles.th}>Change</th>
                    <th style={styles.th}>% Change</th>
                    <th style={styles.th}>5d Chart</th>
                    <th style={styles.th}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {stockData.map((stock) => (
                    <tr
                      key={stock.symbol}
                      onClick={() =>
                        setChartModal({
                          open: true,
                          asset: stock,
                          type: "stock",
                        })
                      }
                      style={{
                        cursor: "pointer",
                        transition: "background 0.2s",
                      }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background =
                          "rgba(74, 158, 255, 0.1)")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = "transparent")
                      }
                    >
                      <td style={{ ...styles.td, fontWeight: "bold" }}>
                        {stock.symbol}
                      </td>
                      <td style={styles.td}>{stock.name}</td>
                      <td style={styles.td}>${stock.price?.toFixed(2)}</td>
                      <td
                        style={{
                          ...styles.td,
                          ...(stock.change >= 0
                            ? styles.positive
                            : styles.negative),
                        }}
                      >
                        {stock.change >= 0 ? "+" : ""}
                        {stock.change?.toFixed(2)}
                      </td>
                      <td
                        style={{
                          ...styles.td,
                          ...(stock.changePercent >= 0
                            ? styles.positive
                            : styles.negative),
                        }}
                      >
                        {stock.changePercent >= 0 ? "+" : ""}
                        {stock.changePercent?.toFixed(2)}%
                      </td>
                      <td style={styles.td}>
                        <SparklineChart
                          data={stock.sparkline}
                          color={
                            stock.changePercent >= 0 ? "#2ed573" : "#ff4757"
                          }
                        />
                      </td>
                      <td style={styles.td}>
                        {watchlist.find((w) => w.id === stock.symbol) ? (
                          <button
                            style={styles.removeBtn}
                            onClick={(e) => {
                              e.stopPropagation();
                              removeFromWatchlist(stock.symbol);
                            }}
                          >
                            Remove
                          </button>
                        ) : (
                          <button
                            style={styles.watchlistBtn}
                            onClick={(e) => {
                              e.stopPropagation();
                              addToWatchlist(stock, "stock");
                            }}
                          >
                            + Watch
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}

        {/* Forex Tab */}
        {activeTab === "forex" && (
          <>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
              }}
            >
              <div style={{ color: "#888", fontSize: "14px" }}>
                Global Currency Exchange Rates (Forex)
              </div>
              <button
                onClick={fetchForexData}
                style={styles.refreshBtn}
                disabled={loading}
              >
                {loading ? "Refreshing..." : "↻ Refresh Rates"}
              </button>
            </div>

            {loading && forexData.length === 0 ? (
              <div
                style={{ textAlign: "center", padding: "40px", color: "#888" }}
              >
                Loading forex data...
              </div>
            ) : (
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Pair</th>
                    <th style={styles.th}>Name</th>
                    <th style={styles.th}>Status</th>
                    <th style={styles.th}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {forexData.map((pair) => (
                    <tr
                      key={pair.symbol}
                      onClick={() =>
                        setChartModal({
                          open: true,
                          asset: pair,
                          type: "forex",
                        })
                      }
                      style={{
                        cursor: "pointer",
                        transition: "background 0.2s",
                      }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background =
                          "rgba(74, 158, 255, 0.1)")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = "transparent")
                      }
                    >
                      <td style={{ ...styles.td, fontWeight: "bold" }}>
                        {pair.symbol}
                      </td>
                      <td style={styles.td}>{pair.name}</td>
                      <td style={styles.td}>
                        <span
                          style={{
                            padding: "4px 8px",
                            borderRadius: "4px",
                            background: "rgba(16, 185, 129, 0.1)",
                            color: "#10b981",
                            fontSize: "11px",
                          }}
                        >
                          Live Chart Available
                        </span>
                      </td>
                      <td style={styles.td}>
                        <button
                          style={styles.watchlistBtn}
                          onClick={(e) => {
                            e.stopPropagation();
                            setChartModal({
                              open: true,
                              asset: pair,
                              type: "forex",
                            });
                          }}
                        >
                          View Chart
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}

        {/* Watchlist Tab */}
        {activeTab === "watchlist" && (
          <div>
            {watchlist.length === 0 ? (
              <div
                style={{ textAlign: "center", padding: "40px", color: "#888" }}
              >
                Your watchlist is empty. Add coins or stocks from the other
                tabs!
              </div>
            ) : (
              <>
                <div style={{ marginBottom: "16px", color: "#888" }}>
                  Your personalized watchlist ({watchlist.length} items)
                </div>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Type</th>
                      <th style={styles.th}>Symbol</th>
                      <th style={styles.th}>Name</th>
                      <th style={styles.th}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {watchlist.map((item) => (
                      <tr key={item.id}>
                        <td style={styles.td}>
                          <span
                            style={{
                              padding: "4px 8px",
                              borderRadius: "4px",
                              backgroundColor:
                                item.type === "crypto"
                                  ? "#f0b90b22"
                                  : "#4a9eff22",
                              color:
                                item.type === "crypto" ? "#f0b90b" : "#4a9eff",
                              fontSize: "12px",
                            }}
                          >
                            {item.type === "crypto" ? "🪙 Crypto" : "📈 Stock"}
                          </span>
                        </td>
                        <td style={{ ...styles.td, fontWeight: "bold" }}>
                          {item.symbol}
                        </td>
                        <td style={styles.td}>{item.name}</td>
                        <td style={styles.td}>
                          <button
                            style={styles.removeBtn}
                            onClick={() => removeFromWatchlist(item.id)}
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>
        )}

        {/* AI Analysis Section */}
        <div style={styles.analysisBox}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "12px",
            }}
          >
            <span style={{ color: "#4a9eff", fontWeight: "500" }}>
              🤖 AI Market Analysis
            </span>
            <button
              style={styles.analysisBtn}
              onClick={getAIAnalysis}
              disabled={analysisLoading}
            >
              {analysisLoading ? "Analyzing..." : "Get AI Analysis"}
            </button>
          </div>
          {analysis && (
            <div style={{ color: "#ccc", lineHeight: "1.6", fontSize: "14px" }}>
              {analysis}
            </div>
          )}
        </div>
      </div>

      {/* Chart Modal */}
      {chartModal.open && chartModal.asset && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0, 0, 0, 0.85)",
            backdropFilter: "blur(10px)",
            zIndex: 10000,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
          onClick={() =>
            setChartModal({ open: false, asset: null, type: null })
          }
        >
          <div
            style={{
              width: "95%",
              maxWidth: "1400px",
              height: "85vh",
              backgroundColor: "#0f0f1a",
              borderRadius: "20px",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              boxShadow: "0 30px 100px rgba(0, 0, 0, 0.8)",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "20px 24px",
                background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
                borderBottom: "1px solid rgba(99, 102, 241, 0.2)",
              }}
            >
              <div
                style={{ display: "flex", alignItems: "center", gap: "16px" }}
              >
                {chartModal.type === "crypto" && chartModal.asset.image && (
                  <img
                    src={chartModal.asset.image}
                    alt=""
                    style={{
                      width: "40px",
                      height: "40px",
                      borderRadius: "50%",
                    }}
                  />
                )}
                <div>
                  <h2
                    style={{
                      margin: 0,
                      color: "#fff",
                      fontSize: "24px",
                      fontWeight: "600",
                    }}
                  >
                    {chartModal.type === "crypto"
                      ? chartModal.asset.name
                      : chartModal.asset.symbol}
                  </h2>
                  <span style={{ color: "#888", fontSize: "14px" }}>
                    {chartModal.type === "crypto"
                      ? chartModal.asset.symbol?.toUpperCase()
                      : chartModal.asset.name}
                    {" • "}
                    <span
                      style={{
                        color:
                          chartModal.type === "crypto"
                            ? chartModal.asset.price_change_percentage_24h >= 0
                              ? "#2ed573"
                              : "#ff4757"
                            : chartModal.type === "forex"
                              ? "#10b981"
                              : chartModal.asset.changePercent >= 0
                                ? "#2ed573"
                                : "#ff4757",
                      }}
                    >
                      {chartModal.type === "crypto"
                        ? `${chartModal.asset.price_change_percentage_24h?.toFixed(
                            2,
                          )}% (24h)`
                        : chartModal.type === "forex"
                          ? "Live Market"
                          : `${chartModal.asset.changePercent?.toFixed(2)}%`}
                    </span>
                  </span>
                </div>
              </div>
              <div
                style={{ display: "flex", alignItems: "center", gap: "16px" }}
              >
                <div style={{ textAlign: "right" }}>
                  <div
                    style={{
                      color: "#fff",
                      fontSize: "28px",
                      fontWeight: "700",
                    }}
                  >
                    {chartModal.type === "forex" ? "" : "$"}
                    {chartModal.type === "crypto"
                      ? chartModal.asset.current_price?.toLocaleString()
                      : chartModal.type === "forex"
                        ? "Live"
                        : chartModal.asset.price?.toFixed(2)}
                  </div>
                  {chartModal.type === "crypto" && (
                    <div style={{ color: "#888", fontSize: "12px" }}>
                      Market Cap: ${formatNumber(chartModal.asset.market_cap)}
                    </div>
                  )}
                </div>
                <button
                  onClick={() =>
                    setChartModal({ open: false, asset: null, type: null })
                  }
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "12px",
                    border: "none",
                    background: "rgba(255, 71, 87, 0.2)",
                    color: "#ff4757",
                    fontSize: "20px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "all 0.2s",
                  }}
                  onMouseEnter={(e) =>
                    (e.target.style.background = "rgba(255, 71, 87, 0.4)")
                  }
                  onMouseLeave={(e) =>
                    (e.target.style.background = "rgba(255, 71, 87, 0.2)")
                  }
                >
                  ✕
                </button>
              </div>
            </div>

            {/* TradingView Chart */}
            <div style={{ flex: 1, position: "relative" }}>
              <iframe
                src={
                  chartModal.type === "crypto"
                    ? `https://www.tradingview.com/widgetembed/?symbol=BINANCE:${chartModal.asset.symbol?.toUpperCase()}USDT&interval=D&theme=dark&style=1&locale=en&toolbar_bg=%231a1a2e&enable_publishing=false&hide_top_toolbar=false&hide_legend=false&save_image=false&container_id=tradingview_chart&hide_side_toolbar=0`
                    : chartModal.type === "forex"
                      ? `https://www.tradingview.com/widgetembed/?symbol=FX:${chartModal.asset.symbol}&interval=D&theme=dark&style=1&locale=en&toolbar_bg=%231a1a2e&enable_publishing=false&hide_top_toolbar=false&hide_legend=false&save_image=false&container_id=tradingview_chart&hide_side_toolbar=0`
                      : `https://www.tradingview.com/widgetembed/?symbol=${chartModal.asset.symbol}&interval=D&theme=dark&style=1&locale=en&toolbar_bg=%231a1a2e&enable_publishing=false&hide_top_toolbar=false&hide_legend=false&save_image=false&container_id=tradingview_chart&hide_side_toolbar=0`
                }
                style={{
                  width: "100%",
                  height: "100%",
                  border: "none",
                }}
                title="TradingView Chart"
              />

              {/* Fallback if iframe doesn't load */}
              <div
                style={{
                  position: "absolute",
                  bottom: "16px",
                  right: "16px",
                  background: "rgba(0, 0, 0, 0.8)",
                  backdropFilter: "blur(10px)",
                  padding: "10px 16px",
                  borderRadius: "10px",
                  color: "#888",
                  fontSize: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                }}
              >
                <span style={{ color: "#fbbf24" }}>📊</span>
                Powered by TradingView
              </div>
            </div>

            {/* Quick Stats Bar */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-around",
                padding: "16px 24px",
                background: "linear-gradient(135deg, #16213e 0%, #1a1a2e 100%)",
                borderTop: "1px solid rgba(99, 102, 241, 0.2)",
              }}
            >
              {chartModal.type === "crypto" ? (
                <>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#888",
                        fontSize: "11px",
                        marginBottom: "4px",
                      }}
                    >
                      1H CHANGE
                    </div>
                    <div
                      style={{
                        color:
                          chartModal.asset
                            .price_change_percentage_1h_in_currency >= 0
                            ? "#2ed573"
                            : "#ff4757",
                        fontWeight: "600",
                        fontSize: "14px",
                      }}
                    >
                      {chartModal.asset.price_change_percentage_1h_in_currency?.toFixed(
                        2,
                      )}
                      %
                    </div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#888",
                        fontSize: "11px",
                        marginBottom: "4px",
                      }}
                    >
                      24H CHANGE
                    </div>
                    <div
                      style={{
                        color:
                          chartModal.asset.price_change_percentage_24h >= 0
                            ? "#2ed573"
                            : "#ff4757",
                        fontWeight: "600",
                        fontSize: "14px",
                      }}
                    >
                      {chartModal.asset.price_change_percentage_24h?.toFixed(2)}
                      %
                    </div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#888",
                        fontSize: "11px",
                        marginBottom: "4px",
                      }}
                    >
                      7D CHANGE
                    </div>
                    <div
                      style={{
                        color:
                          chartModal.asset
                            .price_change_percentage_7d_in_currency >= 0
                            ? "#2ed573"
                            : "#ff4757",
                        fontWeight: "600",
                        fontSize: "14px",
                      }}
                    >
                      {chartModal.asset.price_change_percentage_7d_in_currency?.toFixed(
                        2,
                      )}
                      %
                    </div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#888",
                        fontSize: "11px",
                        marginBottom: "4px",
                      }}
                    >
                      MARKET CAP
                    </div>
                    <div
                      style={{
                        color: "#fff",
                        fontWeight: "600",
                        fontSize: "14px",
                      }}
                    >
                      ${formatNumber(chartModal.asset.market_cap)}
                    </div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#888",
                        fontSize: "11px",
                        marginBottom: "4px",
                      }}
                    >
                      24H VOLUME
                    </div>
                    <div
                      style={{
                        color: "#fff",
                        fontWeight: "600",
                        fontSize: "14px",
                      }}
                    >
                      ${formatNumber(chartModal.asset.total_volume)}
                    </div>
                  </div>
                </>
              ) : (
                <>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#888",
                        fontSize: "11px",
                        marginBottom: "4px",
                      }}
                    >
                      CHANGE
                    </div>
                    <div
                      style={{
                        color:
                          chartModal.asset.change >= 0 ? "#2ed573" : "#ff4757",
                        fontWeight: "600",
                        fontSize: "14px",
                      }}
                    >
                      {chartModal.asset.change >= 0 ? "+" : ""}
                      {chartModal.asset.change?.toFixed(2)}
                    </div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#888",
                        fontSize: "11px",
                        marginBottom: "4px",
                      }}
                    >
                      % CHANGE
                    </div>
                    <div
                      style={{
                        color:
                          chartModal.asset.changePercent >= 0
                            ? "#2ed573"
                            : "#ff4757",
                        fontWeight: "600",
                        fontSize: "14px",
                      }}
                    >
                      {chartModal.asset.changePercent >= 0 ? "+" : ""}
                      {chartModal.asset.changePercent?.toFixed(2)}%
                    </div>
                  </div>
                  <div style={{ textAlign: "center" }}>
                    <div
                      style={{
                        color: "#888",
                        fontSize: "11px",
                        marginBottom: "4px",
                      }}
                    >
                      VOLUME
                    </div>
                    <div
                      style={{
                        color: "#fff",
                        fontWeight: "600",
                        fontSize: "14px",
                      }}
                    >
                      {formatNumber(chartModal.asset.volume)}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Resize Handle */}
      <div
        className="resize-handle"
        style={styles.resizeHandle}
        onMouseDown={(e) => {
          e.stopPropagation();
          setIsResizing(true);
        }}
      />
    </div>
  );
};

export default FinanceConsole;
