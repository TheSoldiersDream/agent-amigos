import React, { useState, useEffect } from "react";
import axios from "axios";
import "./ModelDashboard.css";

/**
 * Model Selection & Management Dashboard
 * Displays available models, their capabilities, and learning statistics
 */
const ModelDashboard = ({ onModelSelected }) => {
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState(null);
  const [learningStats, setLearningStats] = useState(null);
  const [providerHealth, setProviderHealth] = useState({});
  const [pullingModels, setPullingModels] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("models"); // models, stats, performance

  useEffect(() => {
    fetchModelsAndStats();
    const interval = setInterval(fetchModelsAndStats, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  const fetchModelsAndStats = async () => {
    try {
      const response = await axios.get("/agent/models/config");
      if (response.data) {
        setModels(Object.values(response.data.available_models || {}));
        setLearningStats(response.data.learning_stats);
        setProviderHealth(response.data.provider_health || {});
        setLoading(false);
      }
    } catch (error) {
      console.error("Failed to fetch models:", error);
      setLoading(false);
    }
  };

  const handleModelSelect = (model) => {
    // Only allow selection if model is available/downloaded (or just let backend handle it)
    setSelectedModel(model);
    if (onModelSelected) {
      onModelSelected(model.model_id);
    }
  };

  const handlePullModel = async (e, modelId) => {
    e.stopPropagation();
    if (pullingModels[modelId]) return;

    try {
      setPullingModels((prev) => ({ ...prev, [modelId]: true }));
      await axios.post("/agent/models/ollama/pull", null, {
        params: { model_id: modelId },
      });
      alert(
        `Started pulling ${modelId} in the background. It may take a while!`
      );
    } catch (error) {
      console.error("Failed to pull model:", error);
      alert("Failed to start model pull. Is Ollama running?");
      setPullingModels((prev) => ({ ...prev, [modelId]: false }));
    }
  };

  const isModelAvailable = (model) => {
    if (!model.local) return true; // Assume remote is available
    if (model.provider !== "ollama") return true;

    const ollamaModels = providerHealth.ollama?.models || [];
    // Check for exact match or model:tag match
    return (
      ollamaModels.includes(model.model_id) ||
      ollamaModels.some((m) => m.startsWith(model.model_id + ":"))
    );
  };

  const getModelBadges = (model) => {
    return (
      <div className="model-badges">
        {model.local && <span className="badge badge-local">Local</span>}
        {model.supports_function_calling && (
          <span className="badge badge-functions">Functions</span>
        )}
        {model.supports_vision && (
          <span className="badge badge-vision">Vision</span>
        )}
        {model.types.map((type) => (
          <span key={type} className={`badge badge-type badge-${type}`}>
            {type}
          </span>
        ))}
      </div>
    );
  };

  const getSuccessRateColor = (rate) => {
    if (rate >= 0.95) return "#4CAF50";
    if (rate >= 0.85) return "#FFC107";
    return "#f44336";
  };

  if (loading) {
    return <div className="dashboard-loading">Loading models...</div>;
  }

  return (
    <div className="model-dashboard">
      <div className="dashboard-header">
        <h2>🤖 AI Model Dashboard</h2>
        <p>Open-Source & Commercial Model Management (2025)</p>
      </div>

      <div className="dashboard-tabs">
        <button
          className={`tab-button ${activeTab === "models" ? "active" : ""}`}
          onClick={() => setActiveTab("models")}
        >
          Available Models ({models.length})
        </button>
        <button
          className={`tab-button ${activeTab === "stats" ? "active" : ""}`}
          onClick={() => setActiveTab("stats")}
        >
          Learning Statistics
        </button>
        <button
          className={`tab-button ${
            activeTab === "performance" ? "active" : ""
          }`}
          onClick={() => setActiveTab("performance")}
        >
          Performance Metrics
        </button>
      </div>

      {activeTab === "models" && (
        <div className="models-grid">
          {models.length === 0 ? (
            <div className="no-models">
              <p>
                No models available. Please install Ollama or configure API
                keys.
              </p>
            </div>
          ) : (
            models.map((model) => (
              <div
                key={model.model_id}
                className={`model-card ${
                  selectedModel?.model_id === model.model_id ? "selected" : ""
                }`}
                onClick={() => handleModelSelect(model)}
              >
                <div className="model-header">
                  <h3>{model.name}</h3>
                  <span className="provider-badge">{model.provider}</span>
                </div>

                <p className="model-description">{model.description}</p>

                {getModelBadges(model)}

                <div className="model-specs">
                  <div className="spec-item">
                    <span className="spec-label">Context:</span>
                    <span className="spec-value">
                      {model.context_window.toLocaleString()} tokens
                    </span>
                  </div>

                  {model.success_rate && (
                    <div className="spec-item">
                      <span className="spec-label">Success Rate:</span>
                      <div className="success-bar">
                        <div
                          className="success-fill"
                          style={{
                            width: `${model.success_rate * 100}%`,
                            backgroundColor: getSuccessRateColor(
                              model.success_rate
                            ),
                          }}
                        />
                      </div>
                      <span className="spec-value">
                        {(model.success_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}

                  {model.avg_latency_ms > 0 && (
                    <div className="spec-item">
                      <span className="spec-label">Avg Latency:</span>
                      <span className="spec-value">
                        {model.avg_latency_ms.toFixed(0)}ms
                      </span>
                    </div>
                  )}

                  {model.cost_per_1k_input > 0 && (
                    <div className="spec-item">
                      <span className="spec-label">Cost:</span>
                      <span className="spec-value">
                        ${(model.cost_per_1k_input * 1000).toFixed(4)}/1M input
                        tokens
                      </span>
                    </div>
                  )}
                </div>

                <div className="model-actions">
                  {isModelAvailable(model) ? (
                    <button className="select-button">
                      {selectedModel?.model_id === model.model_id
                        ? "✓ Selected"
                        : "Select Model"}
                    </button>
                  ) : (
                    <button
                      className={`pull-button ${
                        pullingModels[model.model_id] ? "pulling" : ""
                      }`}
                      onClick={(e) => handlePullModel(e, model.model_id)}
                      disabled={pullingModels[model.model_id]}
                    >
                      {pullingModels[model.model_id]
                        ? "⌛ Pulling..."
                        : "⬇️ Pull Model"}
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === "stats" && learningStats && (
        <div className="stats-container">
          <div className="stats-overview">
            <h3>Learning Statistics</h3>
            <div className="stat-boxes">
              <div className="stat-box">
                <h4>Total Interactions</h4>
                <p className="stat-value">
                  {learningStats.total_interactions || 0}
                </p>
              </div>
              <div className="stat-box">
                <h4>Models Trained</h4>
                <p className="stat-value">
                  {Object.keys(learningStats.model_stats || {}).length}
                </p>
              </div>
              <div className="stat-box">
                <h4>Avg Success Rate</h4>
                <p className="stat-value">
                  {learningStats.model_rankings &&
                  learningStats.model_rankings.length > 0
                    ? (
                        (learningStats.model_rankings.reduce(
                          (sum, m) => sum + m.success_rate,
                          0
                        ) /
                          learningStats.model_rankings.length) *
                        100
                      ).toFixed(1)
                    : "0"}
                  %
                </p>
              </div>
            </div>
          </div>

          <div className="model-rankings">
            <h3>Model Rankings by Success Rate</h3>
            <div className="ranking-list">
              {learningStats.model_rankings &&
                learningStats.model_rankings.map((model, index) => (
                  <div key={model.model_id} className="ranking-item">
                    <span className="rank-number">#{index + 1}</span>
                    <div className="rank-info">
                      <h4>{model.model_name}</h4>
                      <p>{model.total_uses} uses</p>
                    </div>
                    <div className="rank-stats">
                      <div className="success-bar" style={{ width: "200px" }}>
                        <div
                          className="success-fill"
                          style={{
                            width: `${model.success_rate * 100}%`,
                            backgroundColor: getSuccessRateColor(
                              model.success_rate
                            ),
                          }}
                        />
                      </div>
                      <span className="rank-value">
                        {(model.success_rate * 100).toFixed(1)}%
                      </span>
                    </div>
                    {model.avg_response_time && (
                      <span className="rank-latency">
                        {model.avg_response_time.toFixed(0)}ms
                      </span>
                    )}
                  </div>
                ))}
            </div>
          </div>

          {learningStats.best_models_by_task && (
            <div className="best-models-by-task">
              <h3>Best Models by Task Type</h3>
              <div className="task-models">
                {Object.entries(learningStats.best_models_by_task).map(
                  ([taskType, modelInfo]) => (
                    <div key={taskType} className="task-model-item">
                      <span className="task-type">{taskType}</span>
                      <span className="model-name">{modelInfo.model_name}</span>
                      <span
                        className="success-badge"
                        style={{
                          backgroundColor: getSuccessRateColor(
                            modelInfo.success_rate
                          ),
                        }}
                      >
                        {(modelInfo.success_rate * 100).toFixed(0)}%
                      </span>
                    </div>
                  )
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "performance" && (
        <div className="performance-container">
          <div className="performance-grid">
            <div className="performance-card">
              <h3>Model Speed Comparison</h3>
              <div className="chart-placeholder">
                {models.length > 0 ? (
                  <ul className="speed-list">
                    {models
                      .filter((m) => m.avg_latency_ms > 0)
                      .sort((a, b) => a.avg_latency_ms - b.avg_latency_ms)
                      .map((model) => (
                        <li key={model.model_id}>
                          <span>{model.name}</span>
                          <div className="latency-bar">
                            <div
                              className="latency-fill"
                              style={{
                                width: `${Math.min(
                                  (model.avg_latency_ms / 1000) * 100,
                                  100
                                )}%`,
                              }}
                            />
                          </div>
                          <span>{model.avg_latency_ms.toFixed(0)}ms</span>
                        </li>
                      ))}
                  </ul>
                ) : (
                  <p>No latency data available</p>
                )}
              </div>
            </div>

            <div className="performance-card">
              <h3>Capability Matrix</h3>
              <div className="capability-matrix">
                {models.slice(0, 5).map((model) => (
                  <div key={model.model_id} className="capability-row">
                    <span className="model-short-name">
                      {model.name.substring(0, 15)}
                    </span>
                    <div className="capabilities">
                      <span
                        className={`cap ${
                          model.supports_function_calling
                            ? "enabled"
                            : "disabled"
                        }`}
                        title="Function Calling"
                      >
                        ⚙️
                      </span>
                      <span
                        className={`cap ${
                          model.supports_vision ? "enabled" : "disabled"
                        }`}
                        title="Vision"
                      >
                        👁️
                      </span>
                      <span
                        className={`cap ${
                          model.local ? "enabled" : "disabled"
                        }`}
                        title="Local"
                      >
                        🏠
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ModelDashboard;
