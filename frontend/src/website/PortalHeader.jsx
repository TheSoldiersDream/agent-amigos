import React from "react";

const PortalHeader = ({ onLaunchDashboard, showDashboard }) => {
  return (
    <header
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        height: "70px",
        background: "rgba(10, 15, 28, 0.85)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(255, 215, 0, 0.2)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 40px",
        zIndex: 11000,
        boxShadow: "0 4px 30px rgba(0, 0, 0, 0.5)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "15px" }}>
        <div
          style={{
            width: "40px",
            height: "40px",
            background: "linear-gradient(135deg, #FFD700, #DAB220)",
            borderRadius: "10px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: "900",
            color: "#000",
            fontSize: "20px",
            boxShadow: "0 0 15px rgba(255, 215, 0, 0.3)",
          }}
        >
          A
        </div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span
            style={{
              color: "#fff",
              fontWeight: "800",
              fontSize: "18px",
              letterSpacing: "1px",
              textTransform: "uppercase",
            }}
          >
            Amigos <span style={{ color: "#FFD700" }}>Group</span>
          </span>
          <span
            style={{
              color: "#64748b",
              fontSize: "10px",
              fontWeight: "600",
              letterSpacing: "2px",
            }}
          >
            EXECUTIVE SOLUTIONS
          </span>
        </div>
      </div>

      <nav style={{ display: "flex", gap: "30px", alignItems: "center" }}>
        {["Overview", "Services", "Pricing", "Investors"].map((item) => (
          <a
            key={item}
            href={`#${item.toLowerCase()}`}
            style={{
              color: "#94a3b8",
              textDecoration: "none",
              fontSize: "13px",
              fontWeight: "600",
              transition: "color 0.3s",
              textTransform: "uppercase",
            }}
            onMouseOver={(e) => (e.target.style.color = "#FFD700")}
            onMouseOut={(e) => (e.target.style.color = "#94a3b8")}
          >
            {item}
          </a>
        ))}

        <button
          onClick={onLaunchDashboard}
          style={{
            padding: "10px 24px",
            background: showDashboard
              ? "rgba(255, 215, 0, 0.1)"
              : "linear-gradient(135deg, #FFD700 0%, #B8860B 100%)",
            border: showDashboard ? "1px solid #FFD700" : "none",
            borderRadius: "8px",
            color: showDashboard ? "#FFD700" : "#000",
            fontWeight: "700",
            fontSize: "12px",
            cursor: "pointer",
            transition: "transform 0.2s, box-shadow 0.2s",
            textTransform: "uppercase",
            letterSpacing: "1px",
          }}
          onMouseOver={(e) => {
            e.target.style.transform = "translateY(-2px)";
            e.target.style.boxShadow = "0 5px 15px rgba(255, 215, 0, 0.3)";
          }}
          onMouseOut={(e) => {
            e.target.style.transform = "translateY(0)";
            e.target.style.boxShadow = "none";
          }}
        >
          {showDashboard ? "Return to Site" : "Executive Portal"}
        </button>
      </nav>
    </header>
  );
};

export default PortalHeader;
