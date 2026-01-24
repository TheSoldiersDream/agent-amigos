import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import AppErrorBoundary from "./components/AppErrorBoundary.jsx";
import "./premium-theme.css";

console.log("main.jsx: Initializing React root...");

const rootElement = document.getElementById("root");
if (rootElement) {
  console.log("main.jsx: Found root element, rendering App wrapper...");
  const root = ReactDOM.createRoot(rootElement);
  root.render(
    <React.StrictMode>
      <div style={{color:'white', position:'fixed', top:0, left:0, zIndex:99999, background:'black'}}>Diagnostic: React is Rendering</div>
      <AppErrorBoundary>
        <App />
      </AppErrorBoundary>
    </React.StrictMode>
  );
} else {
  console.error("main.jsx: Failed to find root element");
  document.body.innerHTML = "<div style='color:red;padding:20px;background:white;'>FATAL: No #root element found in HTML!</div>";
}
