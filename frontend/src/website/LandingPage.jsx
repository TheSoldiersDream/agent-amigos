import React, { useEffect, useMemo, useState } from "react";

const LandingPage = ({ onEnter, apiUrl }) => {
  const [report, setReport] = useState(null);
  const [teamStatus, setTeamStatus] = useState(null);
  const [email, setEmail] = useState("");
  const [subscribeStatus, setSubscribeStatus] = useState("");
  const [dataError, setDataError] = useState("");

  const baseUrl = apiUrl || "http://127.0.0.1:65252";

  useEffect(() => {
    let active = true;
    const loadData = async () => {
      try {
        const [reportRes, teamRes] = await Promise.all([
          fetch(`${baseUrl}/openwork/company/report`),
          fetch(`${baseUrl}/agents/team`),
        ]);
        const reportData = await reportRes.json();
        const teamData = await teamRes.json();
        if (!active) return;
        if (reportData?.success) {
          setReport(reportData.report || null);
        }
        if (teamData?.success) {
          setTeamStatus(teamData.data || null);
        }
        setDataError("");
      } catch (err) {
        if (!active) return;
        setDataError(err?.message || "Unable to load live metrics");
      }
    };
    loadData();
    const timer = setInterval(loadData, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [baseUrl]);

  const metrics = useMemo(() => {
    const byStatus = report?.tasks?.by_status || {};
    const completed = Number(byStatus.completed || byStatus.done || 0) || 0;
    const totalTasks = Number(report?.tasks?.total || 0) || 0;
    const activeSessions = Number(report?.sessions?.active || 0) || 0;
    const totalSessions = Number(report?.sessions?.total || 0) || 0;
    const online = Number(teamStatus?.summary?.online || 0) || 0;
    const totalAgents =
      Number(
        teamStatus?.summary?.total_agents || teamStatus?.summary?.total || 0,
      ) || Object.keys(teamStatus?.agents || {}).length;
    const lastKpi = report?.kpi?.title || "No KPI updates yet";
    return [
      {
        label: "Tasks Completed",
        val: `${completed}/${totalTasks}`,
        sub: "OpenWork execution log",
      },
      {
        label: "Active Sessions",
        val: `${activeSessions}/${totalSessions}`,
        sub: "Live OpenWork sessions",
      },
      {
        label: "Agents Online",
        val: `${online}/${totalAgents || 0}`,
        sub: "Live team telemetry",
      },
      {
        label: "Latest KPI",
        val: lastKpi,
        sub: report?.kpi?.updated_at || "Awaiting KPI update",
      },
    ];
  }, [report, teamStatus]);

  const buildProspectusHtml = () => {
    const timestamp = new Date().toLocaleString();
    const tasks = report?.tasks?.top_5 || [];
    const kpi = report?.kpi;
    const summary = report?.summary || "Live status snapshot";
    const team = teamStatus?.summary || {};
    return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Amigos Group Prospectus</title>
  <style>
    body { font-family: Inter, Arial, sans-serif; margin: 32px; color: #0f172a; }
    h1 { margin-bottom: 4px; }
    h2 { margin-top: 28px; }
    .muted { color: #64748b; font-size: 12px; }
    .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .card { border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; font-size: 14px; }
    th { background: #f8fafc; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; background: #eef2ff; color: #4338ca; font-size: 12px; }
    .cta { margin-top: 18px; padding: 10px 14px; border-radius: 10px; border: 1px solid #0f172a; background: #0f172a; color: #fff; cursor: pointer; }
  </style>
</head>
<body>
  <h1>Amigos Group Prospectus</h1>
  <div class="muted">Generated ${timestamp}</div>
  <p>${summary}</p>

  <h2>Live Telemetry</h2>
  <div class="grid">
    <div class="card"><div class="muted">Sessions</div><div><strong>${report?.sessions?.active || 0}</strong> active / ${report?.sessions?.total || 0} total</div></div>
    <div class="card"><div class="muted">Tasks</div><div><strong>${report?.tasks?.total || 0}</strong> total</div></div>
    <div class="card"><div class="muted">Agents Online</div><div><strong>${team?.online || 0}</strong> / ${team?.total_agents || team?.total || 0}</div></div>
  </div>

  <h2>Top Active Tasks</h2>
  <table>
    <thead><tr><th>Title</th><th>Status</th><th>Owner</th></tr></thead>
    <tbody>
      ${tasks.map((t) => `<tr><td>${t.title || "Untitled"}</td><td>${t.status || "pending"}</td><td>${t.owner || "unassigned"}</td></tr>`).join("")}
    </tbody>
  </table>

  <h2>Latest KPI</h2>
  <div class="card">
    <div><strong>${kpi?.title || "No KPI updates"}</strong></div>
    <div class="muted">Updated: ${kpi?.updated_at || "N/A"}</div>
  </div>

  <button class="cta" onclick="window.print()">Print / Save as PDF</button>
</body>
</html>`;
  };

  const handleDownloadProspectus = () => {
    if (!report) {
      alert("Prospectus unavailable until live metrics are loaded.");
      return;
    }
    const html = buildProspectusHtml();
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const tab = window.open(url, "_blank");
    if (!tab) {
      const link = document.createElement("a");
      link.href = url;
      link.download = "amigos-prospectus.html";
      link.click();
    }
    URL.revokeObjectURL(url);
  };

  const handleSubscribe = async () => {
    const trimmed = email.trim();
    if (!trimmed) return;
    setSubscribeStatus("Submitting...");
    try {
      const res = await fetch(`${baseUrl}/marketing/subscribe`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: trimmed,
          source: "landing_page",
        }),
      });
      const data = await res.json();
      if (!data?.success) {
        throw new Error(data?.detail || "Subscription failed");
      }
      setSubscribeStatus("Subscribed.");
      setEmail("");
    } catch (err) {
      setSubscribeStatus(err?.message || "Subscription failed");
    }
  };
  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#050810",
        color: "#fff",
        fontFamily: "'Inter', sans-serif",
        paddingTop: "120px",
        overflowX: "hidden",
      }}
    >
      {/* Hero Section */}
      <section
        id="overview"
        style={{
          maxWidth: "1200px",
          margin: "0 auto",
          padding: "0 40px",
          textAlign: "center",
        }}
      >
        <div
          style={{
            display: "inline-block",
            padding: "8px 16px",
            background: "rgba(255, 215, 0, 0.1)",
            border: "1px solid rgba(255, 215, 0, 0.3)",
            borderRadius: "100px",
            color: "#FFD700",
            fontSize: "12px",
            fontWeight: "700",
            letterSpacing: "2px",
            marginBottom: "30px",
            textTransform: "uppercase",
          }}
        >
          Revolutionizing AI Revenue
        </div>

        <h1
          style={{
            fontSize: "72px",
            fontWeight: "900",
            lineHeight: "1.1",
            background: "linear-gradient(to bottom, #fff 0%, #94a3b8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            marginBottom: "24px",
          }}
        >
          Autonomous Intelligence. <br />
          <span style={{ color: "#FFD700" }}>Exponential Growth.</span>
        </h1>

        <p
          style={{
            fontSize: "20px",
            color: "#94a3b8",
            maxWidth: "800px",
            margin: "0 auto 40px",
            lineHeight: "1.6",
          }}
        >
          Agent Amigos is the world's first fully autonomous AI revenue engine.
          We deploy specialized agents to acquire, automate, and accelerate your
          business while you focus on high-level strategy.
        </p>

        <div style={{ display: "flex", gap: "20px", justifyContent: "center" }}>
          <button
            onClick={onEnter}
            style={{
              padding: "18px 40px",
              background: "linear-gradient(135deg, #FFD700 0%, #B8860B 100%)",
              border: "none",
              borderRadius: "12px",
              color: "#000",
              fontWeight: "800",
              fontSize: "16px",
              cursor: "pointer",
              boxShadow: "0 10px 30px rgba(255, 215, 0, 0.2)",
            }}
          >
            Launch Command Center
          </button>
          <button
            onClick={handleDownloadProspectus}
            style={{
              padding: "18px 40px",
              background: "transparent",
              border: "1px solid rgba(255, 215, 0, 0.3)",
              borderRadius: "12px",
              color: "#FFD700",
              fontWeight: "700",
              fontSize: "16px",
              cursor: "pointer",
            }}
          >
            Open Prospectus (PDF-ready)
          </button>
        </div>
        {dataError && (
          <div
            style={{ marginTop: "16px", fontSize: "12px", color: "#fbbf24" }}
          >
            {dataError}
          </div>
        )}
      </section>

      {/* Metrics Section */}
      <div
        style={{
          marginTop: "100px",
          background: "rgba(10, 15, 28, 0.5)",
          borderTop: "1px solid rgba(255, 215, 0, 0.1)",
          borderBottom: "1px solid rgba(255, 215, 0, 0.1)",
          padding: "60px 0",
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "40px",
            textAlign: "center",
          }}
        >
          {metrics.map((stat, i) => (
            <div key={i}>
              <div
                style={{
                  color: "#FFD700",
                  fontSize: "32px",
                  fontWeight: "900",
                  marginBottom: "8px",
                }}
              >
                {stat.val}
              </div>
              <div
                style={{
                  color: "#fff",
                  fontSize: "14px",
                  fontWeight: "700",
                  marginBottom: "4px",
                }}
              >
                {stat.label}
              </div>
              <div style={{ color: "#64748b", fontSize: "12px" }}>
                {stat.sub}
              </div>
            </div>
          ))}
        </div>
      </div>

      <section
        id="services"
        style={{ maxWidth: "1100px", margin: "100px auto", padding: "0 40px" }}
      >
        <h2 style={{ fontSize: "32px", marginBottom: "20px" }}>Services</h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "20px",
          }}
        >
          {[
            {
              title: "OpenWork Ops",
              desc: "AI-managed task execution with audit trails.",
            },
            {
              title: "Agent Fleet",
              desc: "Live agent coordination with status telemetry.",
            },
            {
              title: "Automation Studio",
              desc: "Scraping, workflows, and tool orchestration.",
            },
            {
              title: "Media Engine",
              desc: "Content pipelines for video, image, and copy.",
            },
            {
              title: "Canvas & Planning",
              desc: "Strategy boards with AI assistance.",
            },
            {
              title: "Governance",
              desc: "Meeting logs, approvals, and leadership actions.",
            },
          ].map((item) => (
            <div
              key={item.title}
              style={{
                padding: "18px",
                borderRadius: "16px",
                background: "rgba(10, 15, 28, 0.6)",
                border: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: "8px" }}>
                {item.title}
              </div>
              <div style={{ color: "#94a3b8", fontSize: "14px" }}>
                {item.desc}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Subscription Section */}
      <section
        id="pricing"
        style={{
          maxWidth: "900px",
          margin: "120px auto",
          padding: "60px",
          background:
            "linear-gradient(135deg, rgba(255, 215, 0, 0.05) 0%, rgba(10, 15, 28, 0.5) 100%)",
          borderRadius: "30px",
          border: "1px solid rgba(255, 215, 0, 0.2)",
          textAlign: "center",
        }}
      >
        <h2 style={{ fontSize: "32px", marginBottom: "16px" }}>
          Pricing & Access
        </h2>
        <p style={{ color: "#94a3b8", marginBottom: "32px" }}>
          Pricing is scoped to your workflow volume, compliance requirements,
          and agent concurrency. Request a tailored quote and attach your
          current operational goals below.
        </p>

        <div
          style={{
            display: "flex",
            gap: "12px",
            maxWidth: "500px",
            margin: "0 auto",
          }}
        >
          <input
            type="email"
            placeholder="Enter your executive email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{
              flex: 1,
              background: "rgba(0,0,0,0.5)",
              border: "1px solid rgba(255,215,0,0.2)",
              borderRadius: "10px",
              padding: "16px",
              color: "#fff",
              outline: "none",
            }}
          />
          <button
            onClick={handleSubscribe}
            style={{
              padding: "0 30px",
              background: "#FFD700",
              color: "#000",
              border: "none",
              borderRadius: "10px",
              fontWeight: "800",
              cursor: "pointer",
            }}
          >
            Submit
          </button>
        </div>
        {subscribeStatus && (
          <p style={{ fontSize: "12px", color: "#e2e8f0", marginTop: "12px" }}>
            {subscribeStatus}
          </p>
        )}
        <p style={{ fontSize: "11px", color: "#64748b", marginTop: "16px" }}>
          * Limited to 500 premium memberships worldwide.
        </p>
      </section>

      <section
        id="investors"
        style={{ maxWidth: "900px", margin: "80px auto", padding: "0 40px" }}
      >
        <h2 style={{ fontSize: "28px", marginBottom: "14px" }}>Investors</h2>
        <p style={{ color: "#94a3b8", marginBottom: "14px" }}>
          Investor updates are generated from live OpenWork execution logs.
          Download the prospectus for the latest audit snapshot and KPIs.
        </p>
        <button
          onClick={handleDownloadProspectus}
          style={{
            padding: "10px 18px",
            background: "rgba(255, 215, 0, 0.15)",
            border: "1px solid rgba(255, 215, 0, 0.4)",
            borderRadius: "10px",
            color: "#FFD700",
            fontWeight: 700,
            cursor: "pointer",
          }}
        >
          View Latest Prospectus
        </button>
      </section>

      {/* Footer */}
      <footer
        style={{
          padding: "60px 0",
          textAlign: "center",
          borderTop: "1px solid rgba(255,255,255,0.05)",
          color: "#64748b",
          fontSize: "13px",
        }}
      >
        © 2025 Amigos Group. Created by Darrell Buttigieg. #darrellbuttigieg
        #thesoldiersdream
      </footer>
    </div>
  );
};

export default LandingPage;
