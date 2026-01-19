import React, { useState, useEffect } from "react";
import axios from "axios";
import "./AgentCapabilities.css";

/**
 * Agent Capabilities & Learning Statistics Dashboard
 * Shows each agent's skills, learning progress, and success patterns
 */
const AgentCapabilities = () => {
  const [agents, setAgents] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [agentDetails, setAgentDetails] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 10000); // Refresh every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchAgents = async () => {
    try {
      const response = await axios.get("/agent/capabilities");
      if (response.data) {
        setAgents(response.data.agents || []);
        setLoading(false);
      }
    } catch (error) {
      console.error("Failed to fetch agents:", error);
      setLoading(false);
    }
  };

  const fetchAgentDetails = async (agentName) => {
    try {
      const response = await axios.get(`/agent/capabilities/${agentName}`);
      setAgentDetails(response.data);
      setSelectedAgent(agentName);
    } catch (error) {
      console.error("Failed to fetch agent details:", error);
    }
  };

  const getSkillLevel = (proficiency) => {
    if (proficiency >= 0.9) return { level: "Expert", color: "#4CAF50" };
    if (proficiency >= 0.7) return { level: "Proficient", color: "#8BC34A" };
    if (proficiency >= 0.5) return { level: "Learning", color: "#FFC107" };
    return { level: "Developing", color: "#FF9800" };
  };

  const getSuccessColor = (rate) => {
    if (rate >= 0.9) return "#4CAF50";
    if (rate >= 0.75) return "#8BC34A";
    if (rate >= 0.6) return "#FFC107";
    return "#f44336";
  };

  if (loading) {
    return (
      <div className="capabilities-loading">Loading agent capabilities...</div>
    );
  }

  return (
    <div className="agent-capabilities">
      <div className="capabilities-header">
        <h2>🎯 Agent Capabilities & Learning</h2>
        <p>Real-time agent performance and adaptive learning metrics</p>
      </div>

      <div className="capabilities-layout">
        {/* Agent List */}
        <div className="agent-list">
          <h3>Agents</h3>
          <div className="agents-container">
            {agents.length === 0 ? (
              <div className="no-agents">
                <p>No agents initialized yet.</p>
              </div>
            ) : (
              agents.map((agent) => (
                <div
                  key={agent.name}
                  className={`agent-item ${
                    selectedAgent === agent.name ? "active" : ""
                  }`}
                  onClick={() => fetchAgentDetails(agent.name)}
                >
                  <div className="agent-name">
                    <span className="agent-icon">
                      {agent.type === "coding" ? "💻" : "🤖"}
                    </span>
                    <div>
                      <h4>{agent.name}</h4>
                      <p className="agent-type">{agent.type}</p>
                    </div>
                  </div>
                  <div className="agent-summary">
                    <span className="interactions-count">
                      {agent.total_interactions}
                    </span>
                    <div className="success-indicator">
                      <div
                        className="success-dot"
                        style={{
                          backgroundColor: getSuccessColor(agent.success_rate),
                        }}
                      />
                      <span>{(agent.success_rate * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Agent Details */}
        <div className="agent-details">
          {selectedAgent && agentDetails ? (
            <>
              <div className="details-header">
                <h3>{selectedAgent}</h3>
                <div className="header-stats">
                  <div className="stat">
                    <span className="stat-label">Total Uses</span>
                    <span className="stat-value">
                      {agentDetails.total_interactions}
                    </span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Success Rate</span>
                    <span
                      className="stat-value"
                      style={{
                        color: getSuccessColor(agentDetails.success_rate),
                      }}
                    >
                      {(agentDetails.success_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="stat">
                    <span className="stat-label">Models Available</span>
                    <span className="stat-value">
                      {agentDetails.models_available}
                    </span>
                  </div>
                </div>
              </div>

              {/* Skills Section */}
              <div className="details-section">
                <h4>Skills & Proficiency</h4>
                <div className="skills-grid">
                  {Object.entries(agentDetails.skills || {}).length === 0 ? (
                    <p className="no-data">No skills learned yet</p>
                  ) : (
                    Object.entries(agentDetails.skills || {}).map(
                      ([skill, proficiency]) => {
                        const skillLevel = getSkillLevel(proficiency);
                        return (
                          <div key={skill} className="skill-item">
                            <div className="skill-header">
                              <span className="skill-name">{skill}</span>
                              <span
                                className="skill-level"
                                style={{ color: skillLevel.color }}
                              >
                                {skillLevel.level}
                              </span>
                            </div>
                            <div className="skill-bar">
                              <div
                                className="skill-fill"
                                style={{
                                  width: `${proficiency * 100}%`,
                                  backgroundColor: skillLevel.color,
                                }}
                              />
                            </div>
                            <span className="skill-percentage">
                              {(proficiency * 100).toFixed(0)}%
                            </span>
                          </div>
                        );
                      }
                    )
                  )}
                </div>
              </div>

              {/* Recent Successes Section */}
              <div className="details-section">
                <h4>Recent Successful Patterns</h4>
                <div className="patterns-list">
                  {agentDetails.recent_successes &&
                  agentDetails.recent_successes.length > 0 ? (
                    agentDetails.recent_successes.map((pattern, index) => (
                      <div key={index} className="pattern-item">
                        <div className="pattern-header">
                          <span className="pattern-task">{pattern.task}</span>
                          <span className="pattern-duration">
                            {pattern.duration_ms.toFixed(0)}ms
                          </span>
                        </div>
                        <div className="pattern-details">
                          {pattern.tools_used &&
                            pattern.tools_used.length > 0 && (
                              <div className="tools-used">
                                {pattern.tools_used.map((tool) => (
                                  <span key={tool} className="tool-badge">
                                    {tool}
                                  </span>
                                ))}
                              </div>
                            )}
                          <span className="pattern-model">{pattern.model}</span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="no-data">No success patterns yet</p>
                  )}
                </div>
              </div>

              {/* Metrics Section */}
              {agentDetails.metrics && (
                <div className="details-section">
                  <h4>Performance Metrics</h4>
                  <div className="metrics-grid">
                    <div className="metric-item">
                      <h5>Avg Response Time</h5>
                      <p className="metric-value">
                        {agentDetails.metrics.avg_response_time?.toFixed(0)}ms
                      </p>
                    </div>
                    <div className="metric-item">
                      <h5>Tool Usage</h5>
                      <p className="metric-value">
                        {
                          Object.keys(
                            agentDetails.metrics.tools_used_count || {}
                          ).length
                        }{" "}
                        types
                      </p>
                    </div>
                    <div className="metric-item">
                      <h5>Model Preferences</h5>
                      <p className="metric-value">
                        {
                          Object.keys(
                            agentDetails.metrics.model_preferences || {}
                          ).length
                        }{" "}
                        models
                      </p>
                    </div>
                  </div>

                  {/* Tools Used Breakdown */}
                  {Object.keys(agentDetails.metrics.tools_used_count || {})
                    .length > 0 && (
                    <div className="tools-breakdown">
                      <h5>Tools Usage Breakdown</h5>
                      <div className="breakdown-list">
                        {Object.entries(
                          agentDetails.metrics.tools_used_count || {}
                        ).map(([tool, count]) => (
                          <div key={tool} className="breakdown-item">
                            <span className="tool-name">{tool}</span>
                            <div className="breakdown-bar">
                              <div
                                className="breakdown-fill"
                                style={{
                                  width: `${
                                    (count /
                                      Math.max(
                                        ...Object.values(
                                          agentDetails.metrics
                                            .tools_used_count || {}
                                        )
                                      )) *
                                    100
                                  }%`,
                                }}
                              />
                            </div>
                            <span className="tool-count">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="no-selection">
              <p>
                Select an agent to view its capabilities and learning progress
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Learning Legend */}
      <div className="learning-legend">
        <h4>Learning Levels</h4>
        <div className="legend-items">
          <div className="legend-item">
            <div
              className="legend-color"
              style={{ backgroundColor: "#4CAF50" }}
            />
            <span>Expert (90%+)</span>
          </div>
          <div className="legend-item">
            <div
              className="legend-color"
              style={{ backgroundColor: "#8BC34A" }}
            />
            <span>Proficient (70%+)</span>
          </div>
          <div className="legend-item">
            <div
              className="legend-color"
              style={{ backgroundColor: "#FFC107" }}
            />
            <span>Learning (50%+)</span>
          </div>
          <div className="legend-item">
            <div
              className="legend-color"
              style={{ backgroundColor: "#FF9800" }}
            />
            <span>Developing (&lt;50%)</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgentCapabilities;
