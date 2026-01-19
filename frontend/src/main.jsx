import React from "react";
import ReactDOM from "react-dom/client";
import "./premium-theme.css";

const showFatal = (title, error) => {
  try {
    const root = document.getElementById("root");
    if (!root) return;
    // If a React root exists, unmount it to avoid React trying to remove nodes
    if (window.__APP_REACT_ROOT__) {
      try {
        // Defer unmount to avoid synchronous unmount while React is rendering
        setTimeout(() => {
          try {
            window.__APP_REACT_ROOT__?.unmount();
          } catch {}
        }, 0);
      } catch {}
    }
    const message =
      error instanceof Error
        ? `${error.name}: ${error.message}\n\n${error.stack || ""}`
        : String(error);
    root.innerHTML = `
      <div style="height:100vh;display:flex;align-items:center;justify-content:center;background:#050508;color:#e5e7eb;padding:24px;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;">
        <div style="max-width:980px;width:100%;border:1px solid rgba(148,163,184,.25);border-radius:16px;background:rgba(15,15,35,.75);backdrop-filter:blur(12px);padding:20px;">
          <div style="font-weight:800;font-size:18px;margin-bottom:10px;">${title}</div>
          <pre style="white-space:pre-wrap;word-break:break-word;margin:0;font-size:12px;line-height:1.4;color:#cbd5e1;">${message.replace(
            /</g,
            "&lt;"
          )}</pre>
          <div style="margin-top:12px;font-size:12px;color:#94a3b8;">Open DevTools Console for more details.</div>
        </div>
      </div>
    `;
  } catch {
    // If even this fails, avoid recursion.
  }
};

window.addEventListener("error", (e) => {
  showFatal("Frontend error", e?.error || e?.message || e);
});
window.addEventListener("unhandledrejection", (e) => {
  showFatal("Unhandled promise rejection", e?.reason || e);
});

(async () => {
  try {
    const { default: App } = await import("./App.jsx");
    const root = document.getElementById("root");
    if (!root) return;

    // If a previous root exists (HMR or multiple loads), unmount it first
    if (!window.__APP_REACT_ROOT__) {
      window.__APP_REACT_ROOT__ = ReactDOM.createRoot(root);
    } else {
      try {
        // Schedule unmount to avoid unmounting while React renders
        setTimeout(() => {
          try {
            window.__APP_REACT_ROOT__?.unmount();
          } catch {}
        }, 0);
      } catch {}
    }

    window.__APP_REACT_ROOT__.render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
  } catch (err) {
    showFatal("Failed to start UI", err);
  }
})();
