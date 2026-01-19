import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import axios from "axios";

const STORAGE = {
  pos: "amigos-weather-console-pos",
  size: "amigos-weather-console-size",
  prefs: "amigos-weather-console-prefs",
};

const clampInt = (value, min, max, fallback) => {
  const n = Number.parseInt(String(value), 10);
  if (Number.isFinite(n)) return Math.min(max, Math.max(min, n));
  return fallback;
};

const formatNumber = (value, decimals = 1) => {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(decimals);
};

const weatherCodeLabel = (code) => {
  const c = Number(code);
  const map = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
  };
  return map[c] || (Number.isFinite(c) ? `Weather code ${c}` : "—");
};

const pickBackendUrl = (apiUrl) => apiUrl || "http://127.0.0.1:65252";

const WeatherConsole = ({ isOpen, onToggle, apiUrl, onScreenUpdate }) => {
  const backendUrl = pickBackendUrl(apiUrl);

  // Preferences
  const [location, setLocation] = useState("");
  const [units, setUnits] = useState("metric");
  const [forecastDays, setForecastDays] = useState(7);
  const [includeHourly, setIncludeHourly] = useState(false);
  const [includeSolar, setIncludeSolar] = useState(true);
  const [pvKw, setPvKw] = useState("5");
  const [pvPerformanceRatio, setPvPerformanceRatio] = useState("0.80");

  // Data
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  // Draggable/Resizable
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE.pos);
      return saved ? JSON.parse(saved) : { x: window.innerWidth - 540, y: 90 };
    } catch {
      return { x: window.innerWidth - 540, y: 90 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE.size);
      return saved ? JSON.parse(saved) : { width: 520, height: 660 };
    } catch {
      return { width: 520, height: 660 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Load prefs
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE.prefs);
      if (!raw) return;
      const p = JSON.parse(raw);
      if (typeof p.location === "string") setLocation(p.location);
      if (p.units === "metric" || p.units === "imperial") setUnits(p.units);
      if (typeof p.forecastDays === "number")
        setForecastDays(clampInt(p.forecastDays, 1, 7, 7));
      if (typeof p.includeHourly === "boolean")
        setIncludeHourly(p.includeHourly);
      if (typeof p.includeSolar === "boolean") setIncludeSolar(p.includeSolar);
      if (typeof p.pvKw === "string") setPvKw(p.pvKw);
      if (typeof p.pvPerformanceRatio === "string")
        setPvPerformanceRatio(p.pvPerformanceRatio);
    } catch {
      // ignore
    }
  }, []);

  // Save prefs
  useEffect(() => {
    localStorage.setItem(
      STORAGE.prefs,
      JSON.stringify({
        location,
        units,
        forecastDays,
        includeHourly,
        includeSolar,
        pvKw,
        pvPerformanceRatio,
      })
    );
  }, [
    location,
    units,
    forecastDays,
    includeHourly,
    includeSolar,
    pvKw,
    pvPerformanceRatio,
  ]);

  // Save pos/size
  useEffect(() => {
    localStorage.setItem(STORAGE.pos, JSON.stringify(position));
  }, [position]);
  useEffect(() => {
    localStorage.setItem(STORAGE.size, JSON.stringify(size));
  }, [size]);

  const handleMouseDown = (e) => {
    if (
      e.target.closest(".resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("input") ||
      e.target.closest("select") ||
      e.target.closest("textarea")
    ) {
      return;
    }
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
          width: Math.max(480, e.clientX - rect.left + 10),
          height: Math.max(460, e.clientY - rect.top + 10),
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
    if (!isDragging && !isResizing) return;
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, isResizing, handleMouseMove, handleMouseUp]);

  const fetchWeather = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const fd = clampInt(forecastDays, 1, 7, 7);

      const pvKwNum = Number.parseFloat(String(pvKw));
      const pvPrNum = Number.parseFloat(String(pvPerformanceRatio));
      const pvKwValue =
        Number.isFinite(pvKwNum) && pvKwNum > 0 ? pvKwNum : undefined;
      const pvPrValue = Number.isFinite(pvPrNum)
        ? Math.max(0.1, Math.min(1.0, pvPrNum))
        : 0.8;

      const parameters = {
        location: location?.trim() ? location.trim() : undefined,
        units,
        forecast_days: fd,
        include_hourly: !!includeHourly,
        include_solar: !!includeSolar,
        pv_kw: pvKwValue,
        pv_performance_ratio: pvPrValue,
      };

      const res = await axios.post(
        `${backendUrl}/execute_tool`,
        { tool_name: "get_weather", parameters },
        { timeout: 20000 }
      );

      const toolResult = res?.data?.result;
      if (!toolResult || toolResult.success !== true) {
        const msg = toolResult?.error || "Weather lookup failed.";
        setResult(null);
        setError(String(msg));
        return;
      }

      setResult(toolResult);
    } catch (err) {
      const isAxios = !!err?.isAxiosError;
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;

      if (isAxios && status) {
        const detailStr = detail ? JSON.stringify(detail) : "";
        if (status === 403 && detailStr.includes("autonomy_blocked")) {
          setError(
            "⚠️ Action blocked by Autonomy Settings. Please disable the Kill Switch or enable 'network-local' actions in settings."
          );
        } else {
          setError(`Request failed (${status}): ${detailStr}`);
        }
      } else {
        const baseMsg = err?.message || "Network error";
        setError(
          `${baseMsg}. Unable to reach Agent Amigos backend at ${backendUrl}. ` +
            `Make sure the backend is running (default 127.0.0.1:65252).`
        );
      }
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [
    backendUrl,
    forecastDays,
    includeHourly,
    includeSolar,
    location,
    pvKw,
    pvPerformanceRatio,
    units,
  ]);

  // Auto-refresh every 5 minutes when open and we already have a result
  useEffect(() => {
    if (!isOpen) return;
    if (!result?.success) return;
    const interval = setInterval(() => {
      fetchWeather().catch(() => {});
    }, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [isOpen, result?.success, fetchWeather]);

  // Screen awareness
  useEffect(() => {
    if (!onScreenUpdate || !isOpen) return;
    onScreenUpdate({
      location: location || null,
      units,
      forecastDays,
      includeHourly,
      includeSolar,
      pvKw,
      pvPerformanceRatio,
      loading,
      error: error || null,
      result,
      fetchedAt: result?.fetched_at_unix || null,
    });
  }, [
    onScreenUpdate,
    isOpen,
    location,
    units,
    forecastDays,
    includeHourly,
    includeSolar,
    pvKw,
    pvPerformanceRatio,
    loading,
    error,
    result,
  ]);

  const resolvedPlace = result?.resolved_location?.place || "";
  const geocodingProvider = result?.resolved_location?.geocoding_provider || "";
  const current = result?.current || null;
  const daily = result?.daily || null;
  const derived = result?.derived || null;
  const unitsLabel = result?.units || {};

  const dailyRows = useMemo(() => {
    const times = daily?.time || [];
    const tmax = daily?.temperature_2m_max || [];
    const tmin = daily?.temperature_2m_min || [];
    const pr = daily?.precipitation_sum || [];
    const prProb = daily?.precipitation_probability_max || [];
    const windMax = daily?.wind_speed_10m_max || [];

    const dTimes = derived?.daily?.time || [];
    const cloudMean = derived?.daily?.cloud_cover_mean || [];
    const solarKwhM2 = derived?.daily?.shortwave_radiation_sum_kwh_m2 || [];
    const pvKwh = derived?.daily?.pv_estimated_kwh || [];

    const n = Math.max(
      times.length,
      tmax.length,
      tmin.length,
      pr.length,
      prProb.length,
      windMax.length
    );
    const rows = [];

    for (let i = 0; i < n; i += 1) {
      const date = times[i] || "";
      if (!date) continue;
      const dIdx = dTimes.indexOf(date);
      rows.push({
        date,
        tmax: tmax[i],
        tmin: tmin[i],
        precip: pr[i],
        precipProbMax: prProb[i],
        windMax: windMax[i],
        cloudCoverMean: dIdx >= 0 ? cloudMean[dIdx] : undefined,
        solarKwhM2: dIdx >= 0 ? solarKwhM2[dIdx] : undefined,
        pvKwh: dIdx >= 0 ? pvKwh[dIdx] : undefined,
      });
    }

    return rows;
  }, [daily, derived]);

  if (!isOpen) return null;

  const inputStyle = {
    background: "rgba(255,255,255,0.05)",
    border: "1px solid rgba(56, 189, 248, 0.30)",
    borderRadius: "10px",
    padding: "10px 12px",
    color: "#e5e7eb",
    outline: "none",
    fontSize: 13,
    width: "100%",
  };

  const labelStyle = {
    fontSize: 11,
    color: "#94a3b8",
    marginBottom: 6,
  };

  const primaryBtn = {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    background: "linear-gradient(135deg, #38bdf8, #6366f1)",
    border: "none",
    color: "white",
    padding: "10px 14px",
    borderRadius: "10px",
    cursor: "pointer",
    fontSize: 12,
    fontWeight: 600,
    boxShadow: "0 4px 15px rgba(99, 102, 241, 0.30)",
    whiteSpace: "nowrap",
  };

  const secondaryBtn = {
    display: "inline-flex",
    alignItems: "center",
    gap: 8,
    background: "rgba(255,255,255,0.06)",
    border: "1px solid rgba(255,255,255,0.10)",
    color: "#d1d5db",
    padding: "10px 14px",
    borderRadius: "10px",
    cursor: "pointer",
    fontSize: 12,
    whiteSpace: "nowrap",
  };

  const tableMinWidth = 820;

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
        border: "1px solid rgba(56, 189, 248, 0.35)",
        boxShadow:
          "0 20px 60px rgba(0,0,0,0.5), 0 0 30px rgba(56, 189, 248, 0.12)",
        backdropFilter: "blur(20px)",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        zIndex: 11000,
        cursor: isDragging ? "grabbing" : "default",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Header */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          padding: "14px 18px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background:
            "linear-gradient(135deg, rgba(56,189,248,0.16), rgba(99,102,241,0.06))",
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
              background: "linear-gradient(135deg, #38bdf8, #6366f1)",
              display: "grid",
              placeItems: "center",
              boxShadow: "0 8px 25px rgba(56,189,248,0.35)",
              fontSize: 18,
            }}
          >
            🌦️
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: 15 }}>Weather Console</div>
            <div style={{ fontSize: 11, color: "#94a3b8" }}>
              Live conditions • 1–7 day forecast • Solar/PV view
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
          aria-label="Close"
          title="Close"
        >
          ×
        </button>
      </div>

      {/* Controls */}
      <div
        style={{
          padding: "14px 18px",
          display: "grid",
          gridTemplateColumns: "1fr 170px",
          gap: 12,
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <div>
          <div style={labelStyle}>Location (leave blank = default)</div>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g., Panlaitan, PH or London"
            style={inputStyle}
          />
          <div
            style={{
              marginTop: 10,
              display: "flex",
              gap: 10,
              flexWrap: "wrap",
            }}
          >
            <button
              style={primaryBtn}
              onClick={fetchWeather}
              disabled={loading}
            >
              {loading ? "Fetching…" : "Get forecast"}
            </button>
            <button
              style={secondaryBtn}
              onClick={() => {
                setLocation("");
                setTimeout(() => fetchWeather(), 0);
              }}
              disabled={loading}
              title="Use backend default location"
            >
              Use default
            </button>
          </div>
        </div>

        <div style={{ display: "grid", gap: 10 }}>
          <div>
            <div style={labelStyle}>Units</div>
            <select
              value={units}
              onChange={(e) => setUnits(e.target.value)}
              style={{ ...inputStyle, padding: "10px 10px" }}
            >
              <option value="metric">Metric (°C, km/h)</option>
              <option value="imperial">Imperial (°F, mph)</option>
            </select>
          </div>

          <div>
            <div style={labelStyle}>Days</div>
            <select
              value={forecastDays}
              onChange={(e) =>
                setForecastDays(clampInt(e.target.value, 1, 7, 7))
              }
              style={{ ...inputStyle, padding: "10px 10px" }}
            >
              {[1, 2, 3, 4, 5, 6, 7].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 12,
              color: "#cbd5e1",
            }}
          >
            <input
              type="checkbox"
              checked={includeHourly}
              onChange={(e) => setIncludeHourly(e.target.checked)}
            />
            Include hourly
          </label>

          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 12,
              color: "#cbd5e1",
            }}
          >
            <input
              type="checkbox"
              checked={includeSolar}
              onChange={(e) => setIncludeSolar(e.target.checked)}
            />
            Include solar/PV
          </label>
        </div>
      </div>

      {/* PV config */}
      <div
        style={{
          padding: "0 18px 14px 18px",
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 12,
          borderBottom: "1px solid rgba(255,255,255,0.06)",
        }}
      >
        <div>
          <div style={labelStyle}>PV system size (kW)</div>
          <input
            value={pvKw}
            onChange={(e) => setPvKw(e.target.value)}
            placeholder="e.g., 5"
            style={inputStyle}
          />
        </div>
        <div>
          <div style={labelStyle}>PV performance ratio (0.1–1.0)</div>
          <input
            value={pvPerformanceRatio}
            onChange={(e) => setPvPerformanceRatio(e.target.value)}
            placeholder="0.80"
            style={inputStyle}
          />
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: "14px 18px", overflow: "auto", flex: 1 }}>
        {error && (
          <div
            style={{
              padding: "12px 14px",
              borderRadius: 12,
              border: "1px solid rgba(239, 68, 68, 0.35)",
              background: "rgba(239, 68, 68, 0.10)",
              color: "#fecaca",
              marginBottom: 12,
              fontSize: 13,
              lineHeight: 1.4,
            }}
          >
            {String(error)}
          </div>
        )}

        {!result && !error && (
          <div style={{ color: "#94a3b8", fontSize: 13, lineHeight: 1.5 }}>
            Enter a location and request a 1–7 day forecast. Leave blank to use
            the backend default (Panlaitan, Busuanga).
          </div>
        )}

        {result?.success && (
          <>
            <div
              style={{
                padding: "12px 14px",
                borderRadius: 14,
                border: "1px solid rgba(99, 102, 241, 0.22)",
                background: "rgba(15, 15, 35, 0.55)",
                marginBottom: 12,
              }}
            >
              <div style={{ fontWeight: 800, fontSize: 14 }}>
                {resolvedPlace || "Resolved location"}
              </div>
              <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                {formatNumber(result?.resolved_location?.latitude, 4)} ,{" "}
                {formatNumber(result?.resolved_location?.longitude, 4)} •
                Timezone: {result?.resolved_location?.timezone || "—"}
              </div>
            </div>

            {current && (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 10,
                  marginBottom: 12,
                }}
              >
                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: 14,
                    border: "1px solid rgba(56, 189, 248, 0.20)",
                    background: "rgba(2, 132, 199, 0.06)",
                  }}
                >
                  <div style={{ fontSize: 12, color: "#93c5fd" }}>
                    Temperature
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 900, marginTop: 2 }}>
                    {formatNumber(current.temperature_2m, 1)}
                    {unitsLabel.temperature || ""}
                  </div>
                  <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                    Feels like {formatNumber(current.apparent_temperature, 1)}
                    {unitsLabel.temperature || ""}
                  </div>
                </div>

                <div
                  style={{
                    padding: "12px 14px",
                    borderRadius: 14,
                    border: "1px solid rgba(99, 102, 241, 0.20)",
                    background: "rgba(99, 102, 241, 0.06)",
                  }}
                >
                  <div style={{ fontSize: 12, color: "#c4b5fd" }}>
                    Conditions
                  </div>
                  <div style={{ fontSize: 14, fontWeight: 800, marginTop: 4 }}>
                    {weatherCodeLabel(current.weather_code)}
                  </div>
                  <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 6 }}>
                    Humidity: {formatNumber(current.relative_humidity_2m, 0)}% •
                    Wind: {formatNumber(current.wind_speed_10m, 1)}
                    {unitsLabel.wind_speed || ""}
                  </div>
                  <div style={{ fontSize: 12, color: "#94a3b8", marginTop: 4 }}>
                    Precipitation: {formatNumber(current.precipitation, 1)}
                    {unitsLabel.precipitation || ""}
                    {current.cloud_cover !== undefined ? (
                      <>
                        {" "}
                        • Cloud cover: {formatNumber(current.cloud_cover, 0)}%
                      </>
                    ) : null}
                  </div>
                </div>
              </div>
            )}

            <div style={{ fontWeight: 800, marginBottom: 8 }}>
              Daily forecast (PV / clouds / rain)
            </div>
            <div
              style={{
                borderRadius: 14,
                border: "1px solid rgba(148, 163, 184, 0.18)",
                overflowX: "auto",
                overflowY: "hidden",
              }}
            >
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "1.2fr 0.8fr 0.8fr 0.9fr 0.9fr 0.9fr 0.9fr 0.9fr 0.9fr",
                  gap: 0,
                  background: "rgba(15,15,35,0.8)",
                  padding: "10px 12px",
                  fontSize: 12,
                  color: "#94a3b8",
                  borderBottom: "1px solid rgba(255,255,255,0.06)",
                  minWidth: tableMinWidth,
                }}
              >
                <div>Date</div>
                <div>High</div>
                <div>Low</div>
                <div>Precip</div>
                <div>Clouds avg</div>
                <div>Rain prob</div>
                <div>Solar (kWh/m²)</div>
                <div>PV est (kWh)</div>
                <div>Wind max</div>
              </div>

              {dailyRows.length === 0 ? (
                <div
                  style={{
                    padding: "12px",
                    color: "#94a3b8",
                    minWidth: tableMinWidth,
                  }}
                >
                  No daily forecast data returned.
                </div>
              ) : (
                dailyRows.map((r, idx) => (
                  <div
                    key={`${r.date}-${idx}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns:
                        "1.2fr 0.8fr 0.8fr 0.9fr 0.9fr 0.9fr 0.9fr 0.9fr 0.9fr",
                      padding: "10px 12px",
                      fontSize: 12,
                      background:
                        idx % 2 === 0
                          ? "rgba(255,255,255,0.02)"
                          : "rgba(255,255,255,0.00)",
                      borderBottom:
                        idx === dailyRows.length - 1
                          ? "none"
                          : "1px solid rgba(255,255,255,0.05)",
                      minWidth: tableMinWidth,
                    }}
                  >
                    <div style={{ color: "#e5e7eb" }}>{r.date}</div>
                    <div>
                      {formatNumber(r.tmax, 0)}
                      {unitsLabel.temperature || ""}
                    </div>
                    <div>
                      {formatNumber(r.tmin, 0)}
                      {unitsLabel.temperature || ""}
                    </div>
                    <div>
                      {formatNumber(r.precip, 1)}
                      {unitsLabel.precipitation || ""}
                    </div>
                    <div>{formatNumber(r.cloudCoverMean, 0)}%</div>
                    <div>{formatNumber(r.precipProbMax, 0)}%</div>
                    <div>{formatNumber(r.solarKwhM2, 2)}</div>
                    <div>{formatNumber(r.pvKwh, 1)}</div>
                    <div>
                      {formatNumber(r.windMax, 1)}
                      {unitsLabel.wind_speed || ""}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div style={{ marginTop: 12, fontSize: 11, color: "#64748b" }}>
              Provider: {result.provider || "open-meteo"}. Data is fetched at
              request time.
              {geocodingProvider ? (
                <>
                  {" "}
                  Geocoding: {geocodingProvider}
                  {geocodingProvider === "openstreetmap-nominatim" ? (
                    <> (© OpenStreetMap contributors)</>
                  ) : null}
                  .
                </>
              ) : null}{" "}
              PV estimate is approximate.
            </div>
          </>
        )}
      </div>

      {/* Resize handle */}
      <div
        className="resize-handle"
        onMouseDown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsResizing(true);
        }}
        style={{
          position: "absolute",
          bottom: 0,
          right: 0,
          width: 16,
          height: 16,
          cursor: "nwse-resize",
          background:
            "linear-gradient(135deg, rgba(56,189,248,0.0), rgba(56,189,248,0.45))",
        }}
        title="Resize"
      />
    </div>
  );
};

export default WeatherConsole;
