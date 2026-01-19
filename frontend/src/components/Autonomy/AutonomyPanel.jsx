import React, { useState, useEffect } from "react";

export default function AutonomyPanel({ onClose, apiUrl }) {
  const [config, setConfig] = useState(null);
  const [log, setLog] = useState([]);
  const [editingKey, setEditingKey] = useState({});

  // Continuous mode controls - removed for simplicity

  const base = (apiUrl || "").replace(/\/$/, "");
  const url = (path) => (base ? `${base}${path}` : path);

  useEffect(() => {
    fetch(url("/security/status"))
      .then((res) => res.json())
      .then((data) => setConfig(data))
      .catch(() => {});
    fetch(url("/agent/autonomy/log"))
      .then((res) => res.json())
      .then(setLog)
      .catch(() => {});
  }, [base]);

  function refreshLog() {
    fetch(url("/agent/autonomy/log"))
      .then((r) => r.json())
      .then(setLog)
      .catch(() => {});
  }

  function grantConsent() {
    fetch(url("/agent/autonomy/consent"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ consent: true }),
    }).then(() =>
      fetch(url("/security/status"))
        .then((r) => r.json())
        .then(setConfig)
    );
  }

  function setAutonomyMode(mode) {
    fetch(url("/security/autonomy"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    }).then(() =>
      fetch(url("/security/status"))
        .then((r) => r.json())
        .then(setConfig)
    );
  }

  function toggleKill() {
    // Toggle kill switch: if currently killed, unkill; if not, kill
    const target = !killSwitch;
    if (target) {
      fetch(url("/agent/autonomy/kill"), { method: "POST" })
        .then(() => fetch(url("/security/status")))
        .then((r) => r.json())
        .then(setConfig)
        .catch(() => {});
    } else {
      // Unset kill switch by updating config
      fetch(url("/agent/autonomy"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ killSwitch: false }),
      })
        .then(() => fetch(url("/security/status")))
        .then((r) => r.json())
        .then(setConfig)
        .catch(() => {});
    }
  }

  function toggleAutoApproveSafeTools(enabled) {
    // Toggle backend flag to auto-approve safe tools
    fetch(url("/agent/autonomy"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ autoApproveSafeTools: enabled }),
    })
      .then(() =>
        fetch(url("/security/status"))
          .then((r) => r.json())
          .then(setConfig)
      )
      .catch((e) => alert(`Failed to update: ${e.message}`));
  }

  function runExampleWorkflow() {
    fetch(url("/agent/workflow/example"))
      .then((r) => r.json())
      .then((data) => {
        alert(`Example workflow status: ${JSON.stringify(data)}`);
        fetch(url("/agent/autonomy/log"))
          .then((res) => res.json())
          .then(setLog);
      })
      .catch((e) => alert(`Example workflow error: ${e.message}`));
  }

  function validateAllProviders() {
    fetch(url("/agent/providers/validate_all"))
      .then((res) => res.json())
      .then((data) => {
        setValidateResults(data.providers);
      })
      .catch((e) => {
        alert(`Validate All Providers error: ${e.message}`);
      });
  }

  // Derived, safe defaults to avoid undefined errors
  const autonomyMode = (
    config?.autonomy_mode ||
    config?.autonomyMode ||
    "off"
  ).toString();
  const killSwitch = Boolean(config?.kill_switch ?? config?.killSwitch);
  const allowedActions = Array.isArray(config?.allowed_actions)
    ? config.allowed_actions
    : Array.isArray(config?.allowedActions)
    ? config.allowedActions
    : [];

  return (
    <div
      style={{
        padding: 20,
        background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
        color: "#e0e0e0",
        borderRadius: 12,
        boxShadow: "0 8px 32px rgba(0,0,0,0.3)",
        maxWidth: 800,
        margin: "0 auto",
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      }}
    >
      <h2
        style={{
          color: "#00d4ff",
          marginBottom: 20,
          textAlign: "center",
          fontSize: "1.8em",
          fontWeight: 300,
          textShadow: "0 2px 4px rgba(0,0,0,0.5)",
        }}
      >
        🤖 Autonomy Control Panel
      </h2>
      {config && (
        <div style={{ display: "grid", gap: 12 }}>
          <div
            style={{
              background: "rgba(255,255,255,0.05)",
              padding: 20,
              borderRadius: 8,
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            <div style={{ marginBottom: 15 }}>
              <div
                style={{ fontSize: "1.1em", fontWeight: 500, color: "#00d4ff" }}
              >
                Current Mode:{" "}
                <span
                  style={{
                    color:
                      autonomyMode === "off"
                        ? "#ff6b6b"
                        : autonomyMode === "safe"
                        ? "#ffd93d"
                        : "#6bcf7f",
                  }}
                >
                  {autonomyMode.toUpperCase()}
                </span>
              </div>
              <div style={{ marginTop: 8, fontSize: "0.9em", opacity: 0.8 }}>
                Allowed Actions:{" "}
                {allowedActions.length > 0 ? allowedActions.join(", ") : "None"}
              </div>
            </div>

            <div
              style={{
                display: "flex",
                gap: 12,
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <label style={{ fontWeight: 500, color: "#e0e0e0" }}>
                Autonomy Mode:
              </label>
              <select
                value={autonomyMode}
                onChange={(e) => setAutonomyMode(e.target.value)}
                style={{
                  padding: "8px 12px",
                  background: "rgba(255,255,255,0.1)",
                  color: "#e0e0e0",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: 6,
                  fontSize: "0.9em",
                  minWidth: 120,
                }}
              >
                <option
                  value="off"
                  style={{ background: "#1a1a2e", color: "#e0e0e0" }}
                >
                  🚫 Off
                </option>
                <option
                  value="safe"
                  style={{ background: "#1a1a2e", color: "#e0e0e0" }}
                >
                  🛡️ Safe
                </option>
                <option
                  value="full"
                  style={{ background: "#1a1a2e", color: "#e0e0e0" }}
                >
                  ⚡ Full
                </option>
              </select>
              <button
                onClick={() => toggleKill()}
                style={{
                  padding: "8px 16px",
                  background: killSwitch ? "#ff4757" : "rgba(255,255,255,0.1)",
                  color: "#e0e0e0",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: "0.9em",
                  transition: "all 0.2s ease",
                }}
                onMouseOver={(e) =>
                  (e.target.style.background = killSwitch
                    ? "#ff3742"
                    : "rgba(255,255,255,0.2)")
                }
                onMouseOut={(e) =>
                  (e.target.style.background = killSwitch
                    ? "#ff4757"
                    : "rgba(255,255,255,0.1)")
                }
              >
                {killSwitch ? "🔴 KILL ACTIVE" : "🟢 Kill Switch"}
              </button>
            </div>
          </div>

          {/* Removed auto-approve safe tools for simplicity */}

          <div
            style={{
              display: "flex",
              gap: 12,
              justifyContent: "center",
              flexWrap: "wrap",
            }}
          >
            <button
              onClick={() => grantConsent()}
              style={{
                padding: "10px 20px",
                background: "linear-gradient(45deg, #667eea 0%, #764ba2 100%)",
                color: "white",
                border: "none",
                borderRadius: 8,
                cursor: "pointer",
                fontSize: "0.9em",
                fontWeight: 500,
                transition: "transform 0.2s ease",
              }}
              onMouseOver={(e) =>
                (e.target.style.transform = "translateY(-2px)")
              }
              onMouseOut={(e) => (e.target.style.transform = "translateY(0)")}
            >
              ✅ Grant Consent
            </button>
            <button
              onClick={() => refreshLog()}
              style={{
                padding: "10px 20px",
                background: "linear-gradient(45deg, #f093fb 0%, #f5576c 100%)",
                color: "white",
                border: "none",
                borderRadius: 8,
                cursor: "pointer",
                fontSize: "0.9em",
                fontWeight: 500,
                transition: "transform 0.2s ease",
              }}
              onMouseOver={(e) =>
                (e.target.style.transform = "translateY(-2px)")
              }
              onMouseOut={(e) => (e.target.style.transform = "translateY(0)")}
            >
              🔄 Refresh Logs
            </button>
            <button
              onClick={onClose}
              style={{
                padding: "10px 20px",
                background: "linear-gradient(45deg, #4facfe 0%, #00f2fe 100%)",
                color: "white",
                border: "none",
                borderRadius: 8,
                cursor: "pointer",
                fontSize: "0.9em",
                fontWeight: 500,
                transition: "transform 0.2s ease",
              }}
              onMouseOver={(e) =>
                (e.target.style.transform = "translateY(-2px)")
              }
              onMouseOut={(e) => (e.target.style.transform = "translateY(0)")}
            >
              ❌ Close
            </button>
          </div>

          <div style={{ marginTop: 20 }}>
            <h3
              style={{ color: "#00d4ff", marginBottom: 15, fontSize: "1.2em" }}
            >
              📋 Recent Autonomous Actions
            </h3>
            <div
              style={{
                maxHeight: 300,
                overflowY: "auto",
                background: "rgba(0,0,0,0.3)",
                border: "1px solid rgba(255,255,255,0.1)",
                padding: 15,
                borderRadius: 8,
                scrollbarWidth: "thin",
                scrollbarColor: "rgba(255,255,255,0.3) transparent",
              }}
            >
              {Array.isArray(log) && log.length > 0 ? (
                log
                  .slice(-20)
                  .reverse()
                  .map((entry, i) => (
                    <div
                      key={i}
                      style={{
                        padding: 12,
                        borderBottom:
                          i < log.slice(-20).length - 1
                            ? "1px solid rgba(255,255,255,0.1)"
                            : "none",
                        background:
                          i % 2 === 0
                            ? "rgba(255,255,255,0.02)"
                            : "transparent",
                        borderRadius: 6,
                        marginBottom: 8,
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
                        <div
                          style={{
                            fontWeight: 600,
                            color: "#00d4ff",
                            fontSize: "0.9em",
                          }}
                        >
                          {entry.action || entry.event || "action"}
                        </div>
                        <div style={{ opacity: 0.6, fontSize: "0.8em" }}>
                          {entry.timestamp || entry.time || ""}
                        </div>
                      </div>
                      <div
                        style={{
                          marginBottom: 8,
                          fontSize: "0.85em",
                          opacity: 0.9,
                        }}
                      >
                        {entry.details ? JSON.stringify(entry.details) : ""}
                      </div>
                      {entry.result && (
                        <pre
                          style={{
                            marginTop: 8,
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                            maxHeight: 100,
                            overflow: "auto",
                            background: "rgba(0,0,0,0.5)",
                            padding: 8,
                            borderRadius: 4,
                            fontSize: "0.8em",
                            border: "1px solid rgba(255,255,255,0.1)",
                          }}
                        >
                          {JSON.stringify(entry.result, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))
              ) : (
                <div style={{ textAlign: "center", opacity: 0.7, padding: 20 }}>
                  📝 No recent autonomous actions recorded.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
