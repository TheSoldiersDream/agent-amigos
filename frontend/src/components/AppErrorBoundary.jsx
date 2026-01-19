import React from "react";

/**
 * Catches React render errors so the app doesn't appear as a blank screen.
 * This is especially useful when a single console (e.g., Game Trainer) throws
 * during render.
 */
export default class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Keep a copy of component stack for display.
    this.setState({ info });
    // Also log for DevTools.
    // eslint-disable-next-line no-console
    console.error("[AppErrorBoundary]", error, info);
  }

  handleReload = () => {
    try {
      window.location.reload();
    } catch {
      // ignore
    }
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    const errorText = this.state.error
      ? String(
          this.state.error?.stack ||
            this.state.error?.message ||
            this.state.error
        )
      : "Unknown error";

    const stack = this.state.info?.componentStack
      ? String(this.state.info.componentStack)
      : "";

    return (
      <div
        style={{
          minHeight: "100vh",
          padding: 24,
          background: "linear-gradient(135deg, #0b1220 0%, #111827 100%)",
          color: "#e5e7eb",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial",
        }}
      >
        <h2 style={{ margin: 0, fontSize: "1.25em" }}>
          UI crashed (render error)
        </h2>
        <p style={{ marginTop: 8, color: "#94a3b8", lineHeight: 1.4 }}>
          A component threw an error during render. This usually causes a blank
          screen. The details below can help pinpoint which console needs
          fixing.
        </p>

        <div
          style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12 }}
        >
          <button
            onClick={this.handleReload}
            style={{
              padding: "10px 14px",
              borderRadius: 10,
              border: "none",
              background: "linear-gradient(135deg, #fb923c, #ea580c)",
              color: "#0b0b15",
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Reload
          </button>
        </div>

        <div
          style={{
            marginTop: 16,
            padding: 12,
            borderRadius: 12,
            background: "rgba(0,0,0,0.35)",
            border: "1px solid rgba(255,255,255,0.10)",
            whiteSpace: "pre-wrap",
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            fontSize: "0.85em",
          }}
        >
          {errorText}
          {stack ? `\n\nComponent stack:${stack}` : ""}
        </div>
      </div>
    );
  }
}
