import React, { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";

const FileManagementConsole = ({
  isOpen,
  onToggle,
  apiUrl,
  onScreenUpdate,
}) => {
  const backendUrl = apiUrl || "http://127.0.0.1:65252";

  // Tab state
  const [activeTab, setActiveTab] = useState("browse");

  const DEFAULT_START_PATH = "C:\\Users\\user";
  const PATH_STORAGE_KEY = "amigos-file-console-last-path";

  // File browser state
  const getStoredPath = () => {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage.getItem(PATH_STORAGE_KEY);
    } catch (err) {
      console.warn("File console path storage read failed", err);
      return null;
    }
  };

  const persistPath = (path) => {
    if (!path || typeof window === "undefined") return;
    try {
      window.localStorage.setItem(PATH_STORAGE_KEY, path);
    } catch (err) {
      console.warn("File console path storage write failed", err);
    }
  };

  const initialPath = getStoredPath() || DEFAULT_START_PATH;
  const [currentPath, setCurrentPath] = useState(initialPath);
  const [pathHistory, setPathHistory] = useState([initialPath]);
  const [historyIndex, setHistoryIndex] = useState(0);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Initialization state
  const [hasLoadedInitialPath, setHasLoadedInitialPath] = useState(false);
  const [initializingPath, setInitializingPath] = useState(false);

  // Selected file state
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState("");
  const [fileInfo, setFileInfo] = useState(null);
  const [loadingContent, setLoadingContent] = useState(false);

  // Upload state
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  // AI Analysis state
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // Write/Create state
  const [newFileName, setNewFileName] = useState("");
  const [newFileContent, setNewFileContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  // 👀 SCREEN AWARENESS - Report data to Agent Amigos
  useEffect(() => {
    if (onScreenUpdate && isOpen) {
      onScreenUpdate({
        currentPath,
        files,
        selectedFile: selectedFile
          ? {
              name: selectedFile.name,
              is_directory: selectedFile.is_directory,
              size: selectedFile.size,
            }
          : null,
        fileContent: fileContent?.slice(0, 500), // Preview only
        searchQuery,
        searchResults: searchResults?.slice(0, 10),
      });
    }
  }, [
    currentPath,
    files,
    selectedFile,
    fileContent,
    searchQuery,
    searchResults,
    isOpen,
    onScreenUpdate,
  ]);

  // Draggable state - Load from localStorage
  const [position, setPosition] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-file-console-pos");
      return saved ? JSON.parse(saved) : { x: 80, y: 80 };
    } catch {
      return { x: 80, y: 80 };
    }
  });
  const [size, setSize] = useState(() => {
    try {
      const saved = localStorage.getItem("amigos-file-console-size");
      return saved ? JSON.parse(saved) : { width: 950, height: 700 };
    } catch {
      return { width: 950, height: 700 };
    }
  });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);

  // Save position to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-file-console-pos", JSON.stringify(position));
  }, [position]);

  // Save size to localStorage when it changes
  useEffect(() => {
    localStorage.setItem("amigos-file-console-size", JSON.stringify(size));
  }, [size]);

  // Drag handlers
  const handleMouseDown = (e) => {
    if (
      e.target.closest(".resize-handle") ||
      e.target.closest("button") ||
      e.target.closest("input") ||
      e.target.closest("textarea") ||
      e.target.closest("select")
    )
      return;
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
          width: Math.max(700, e.clientX - rect.left + 10),
          height: Math.max(500, e.clientY - rect.top + 10),
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
    if (isDragging || isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
      return () => {
        document.removeEventListener("mousemove", handleMouseMove);
        document.removeEventListener("mouseup", handleMouseUp);
      };
    }
  }, [isDragging, isResizing, handleMouseMove, handleMouseUp]);

  // Resolve starting path from backend once when console opens
  useEffect(() => {
    if (!isOpen || hasLoadedInitialPath) return;

    const resolveStartPath = async () => {
      setInitializingPath(true);
      const fallback = getStoredPath() || DEFAULT_START_PATH;
      let resolvedPath = fallback;

      try {
        const response = await axios.post(`${backendUrl}/execute_tool`, {
          tool_name: "get_current_directory",
          arguments: {},
        });

        if (response.data?.result?.cwd) {
          resolvedPath = response.data.result.cwd;
        }
      } catch (err) {
        setError(
          (prev) => prev || `Unable to detect working directory: ${err.message}`
        );
      } finally {
        setCurrentPath(resolvedPath);
        setPathHistory([resolvedPath]);
        setHistoryIndex(0);
        persistPath(resolvedPath);
        setHasLoadedInitialPath(true);
        setInitializingPath(false);
      }
    };

    resolveStartPath();
  }, [isOpen, hasLoadedInitialPath, backendUrl]);

  // Load directory when path changes after initialization
  useEffect(() => {
    if (isOpen && hasLoadedInitialPath && currentPath && !initializingPath) {
      loadDirectory(currentPath);
    }
  }, [isOpen, currentPath, hasLoadedInitialPath, initializingPath]);

  // Load directory contents
  const loadDirectory = async (path) => {
    setLoading(true);
    setError("");
    try {
      const response = await axios.post(`${backendUrl}/execute_tool`, {
        tool_name: "list_directory",
        arguments: { path, include_hidden: false },
      });

      if (response.data.status === "success" && response.data.result?.success) {
        persistPath(path);
        setFiles(response.data.result.items || []);
      } else {
        setError(response.data.result?.error || "Failed to load directory");
        setFiles([]);
      }
    } catch (err) {
      setError(err.message);
      setFiles([]);
    } finally {
      setLoading(false);
    }
  };

  // Navigate to path
  const navigateTo = (path) => {
    const newHistory = [...pathHistory.slice(0, historyIndex + 1), path];
    setPathHistory(newHistory);
    setHistoryIndex(newHistory.length - 1);
    setCurrentPath(path);
    persistPath(path);
    setSelectedFile(null);
    setFileContent("");
    setFileInfo(null);
  };

  // Go back in history
  const goBack = () => {
    if (historyIndex > 0) {
      setHistoryIndex(historyIndex - 1);
      setCurrentPath(pathHistory[historyIndex - 1]);
    }
  };

  // Go forward in history
  const goForward = () => {
    if (historyIndex < pathHistory.length - 1) {
      setHistoryIndex(historyIndex + 1);
      setCurrentPath(pathHistory[historyIndex + 1]);
    }
  };

  // Go up one directory
  const goUp = () => {
    const parts = currentPath.split(/[/\\]/);
    if (parts.length > 1) {
      parts.pop();
      const parentPath = parts.join("\\") || "C:\\";
      navigateTo(parentPath);
    }
  };

  // Handle file/folder click
  const handleItemClick = async (item) => {
    if (item.type === "directory") {
      navigateTo(`${currentPath}\\${item.name}`);
    } else {
      setSelectedFile(item);
      setLoadingContent(true);

      try {
        // Get file info
        const infoResponse = await axios.post(`${backendUrl}/execute_tool`, {
          tool_name: "get_file_info",
          arguments: { path: `${currentPath}\\${item.name}` },
        });

        if (infoResponse.data.result?.success) {
          setFileInfo(infoResponse.data.result);
        }

        // Get file content (for text files)
        const textExts = [
          ".txt",
          ".md",
          ".json",
          ".xml",
          ".yaml",
          ".yml",
          ".csv",
          ".log",
          ".py",
          ".js",
          ".jsx",
          ".ts",
          ".tsx",
          ".html",
          ".css",
          ".java",
          ".cpp",
          ".c",
          ".h",
          ".go",
          ".rs",
          ".rb",
          ".php",
          ".sql",
          ".sh",
          ".bat",
          ".ps1",
          ".ini",
          ".cfg",
          ".conf",
        ];
        const ext = item.name
          .substring(item.name.lastIndexOf("."))
          .toLowerCase();

        if (textExts.includes(ext) || item.size < 500000) {
          const contentResponse = await axios.post(
            `${backendUrl}/execute_tool`,
            {
              tool_name: "read_file",
              arguments: { path: `${currentPath}\\${item.name}` },
            }
          );

          if (contentResponse.data.result?.success) {
            setFileContent(contentResponse.data.result.content || "");
          } else {
            setFileContent("[Cannot read file content]");
          }
        } else {
          setFileContent("[Binary or large file - cannot display content]");
        }
      } catch (err) {
        setFileContent(`[Error reading file: ${err.message}]`);
      } finally {
        setLoadingContent(false);
      }
    }
  };

  // Upload file for analysis
  const handleFileUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(
        `${backendUrl}/file/upload-for-analysis`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" }, timeout: 60000 }
      );

      if (response.data.success) {
        const uploadedFile = {
          name: response.data.filename,
          content: response.data.content,
          info: response.data.file_info,
          truncated: response.data.truncated,
          uploadedAt: new Date().toISOString(),
        };
        setUploadedFiles((prev) => [uploadedFile, ...prev]);
        setSelectedFile({
          name: uploadedFile.name,
          type: "file",
          uploaded: true,
        });
        setFileContent(uploadedFile.content);
        setFileInfo(uploadedFile.info);
        setActiveTab("preview");
      } else {
        setError(response.data.error || "Upload failed");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // AI Analysis
  const analyzeFile = async () => {
    if (!fileContent || !selectedFile) return;

    setIsAnalyzing(true);
    setAnalysisResult(null);

    try {
      const response = await axios.post(
        `${backendUrl}/chat`,
        {
          messages: [
            {
              role: "user",
              content: `Analyze this file and provide a comprehensive report:\n\nFilename: ${
                selectedFile.name
              }\nFile Info: ${JSON.stringify(
                fileInfo || {}
              )}\n\nContent:\n${fileContent.slice(
                0,
                30000
              )}\n\nPlease provide:\n1. File type and purpose\n2. Structure analysis\n3. Key insights and data summary\n4. Potential issues or improvements\n5. Quick statistics`,
            },
          ],
        },
        { timeout: 120000 }
      );

      setAnalysisResult(response.data.content);
    } catch (err) {
      setAnalysisResult(`Analysis failed: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Read file content aloud with TTS
  const readAloud = () => {
    if (!fileContent || isSpeaking) return;

    // Use Web Speech API
    const utterance = new SpeechSynthesisUtterance(fileContent.slice(0, 5000));
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  // Stop speaking
  const stopSpeaking = () => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  // Search files
  const searchFiles = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setSearchResults([]);

    try {
      const response = await axios.post(`${backendUrl}/execute_tool`, {
        tool_name: "search_files",
        arguments: {
          directory: currentPath,
          pattern: `*${searchQuery}*`,
          recursive: true,
        },
      });

      if (response.data.result?.success) {
        setSearchResults(response.data.result.files || []);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSearching(false);
    }
  };

  // Create new file
  const createNewFile = async () => {
    if (!newFileName.trim()) return;

    setIsSaving(true);
    try {
      const fullPath = `${currentPath}\\${newFileName}`;
      const response = await axios.post(`${backendUrl}/execute_tool`, {
        tool_name: "write_file",
        arguments: { path: fullPath, content: newFileContent },
      });

      if (response.data.result?.success) {
        setNewFileName("");
        setNewFileContent("");
        loadDirectory(currentPath);
        setActiveTab("browse");
      } else {
        setError(response.data.result?.error || "Failed to create file");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  // Get file icon
  const getFileIcon = (item) => {
    if (item.type === "directory") return "📁";
    const ext = item.name.substring(item.name.lastIndexOf(".")).toLowerCase();
    const iconMap = {
      ".txt": "📄",
      ".md": "📝",
      ".json": "📋",
      ".xml": "📋",
      ".csv": "📊",
      ".py": "🐍",
      ".js": "📜",
      ".jsx": "⚛️",
      ".ts": "📘",
      ".tsx": "⚛️",
      ".html": "🌐",
      ".css": "🎨",
      ".java": "☕",
      ".cpp": "⚙️",
      ".c": "⚙️",
      ".jpg": "🖼️",
      ".jpeg": "🖼️",
      ".png": "🖼️",
      ".gif": "🖼️",
      ".bmp": "🖼️",
      ".mp3": "🎵",
      ".wav": "🎵",
      ".mp4": "🎬",
      ".mov": "🎬",
      ".avi": "🎬",
      ".pdf": "📕",
      ".doc": "📘",
      ".docx": "📘",
      ".xls": "📗",
      ".xlsx": "📗",
      ".zip": "📦",
      ".rar": "📦",
      ".7z": "📦",
      ".exe": "⚡",
      ".msi": "⚡",
    };
    return iconMap[ext] || "📄";
  };

  // Format file size
  const formatSize = (bytes) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  };

  if (!isOpen) return null;

  // Styles
  const tabBtn = (key) => ({
    flex: 1,
    padding: "10px 8px",
    background: activeTab === key ? "rgba(34, 197, 94, 0.15)" : "transparent",
    border: "none",
    borderBottom:
      activeTab === key ? "2px solid #22c55e" : "2px solid transparent",
    color: activeTab === key ? "#22c55e" : "#6b7280",
    cursor: "pointer",
    fontSize: "0.8em",
    fontWeight: activeTab === key ? 600 : 400,
  });

  const inputStyle = {
    padding: "10px 12px",
    borderRadius: "8px",
    border: "1px solid rgba(34, 197, 94, 0.3)",
    backgroundColor: "rgba(17, 24, 39, 0.8)",
    color: "white",
    fontSize: "0.85em",
    width: "100%",
    outline: "none",
  };

  const btnPrimary = {
    padding: "10px 16px",
    borderRadius: "8px",
    border: "none",
    background: "linear-gradient(135deg, #22c55e, #16a34a)",
    color: "white",
    fontWeight: "bold",
    cursor: "pointer",
    fontSize: "0.85em",
    boxShadow: "0 4px 15px rgba(34, 197, 94, 0.3)",
  };

  const btnSecondary = {
    padding: "8px 14px",
    borderRadius: "8px",
    border: "1px solid rgba(34, 197, 94, 0.3)",
    background: "transparent",
    color: "#22c55e",
    cursor: "pointer",
    fontSize: "0.8em",
  };

  const card = {
    padding: "14px",
    borderRadius: "10px",
    border: "1px solid rgba(255, 255, 255, 0.08)",
    backgroundColor: "rgba(17, 24, 39, 0.6)",
    marginBottom: "12px",
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        left: position.x,
        top: position.y,
        width: size.width,
        height: size.height,
        backgroundColor: "rgba(11, 11, 21, 0.97)",
        backdropFilter: "blur(20px)",
        borderRadius: "16px",
        border: "1px solid rgba(34, 197, 94, 0.5)",
        boxShadow:
          "0 20px 60px rgba(0,0,0,0.5), 0 0 40px rgba(34, 197, 94, 0.15)",
        zIndex: 999,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        cursor: isDragging ? "grabbing" : "default",
      }}
    >
      {/* Header */}
      <div
        onMouseDown={handleMouseDown}
        style={{
          padding: "14px 18px",
          background:
            "linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.1))",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(34, 197, 94, 0.2)",
          cursor: "grab",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              borderRadius: "12px",
              background: "linear-gradient(135deg, #22c55e, #16a34a)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "1.4em",
              boxShadow: "0 8px 25px rgba(34, 197, 94, 0.4)",
            }}
          >
            📂
          </div>
          <div>
            <div
              style={{ fontWeight: "bold", fontSize: "1em", color: "white" }}
            >
              File Management Console
            </div>
            <div style={{ fontSize: "0.7em", color: "#94a3b8" }}>
              Browse • Upload • Analyze • Read Aloud
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
          }}
        >
          ×
        </button>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <button style={tabBtn("browse")} onClick={() => setActiveTab("browse")}>
          📁 Browse
        </button>
        <button style={tabBtn("upload")} onClick={() => setActiveTab("upload")}>
          📤 Upload
        </button>
        <button
          style={tabBtn("preview")}
          onClick={() => setActiveTab("preview")}
        >
          👁️ Preview
        </button>
        <button
          style={tabBtn("analyze")}
          onClick={() => setActiveTab("analyze")}
        >
          🤖 AI Analyze
        </button>
        <button style={tabBtn("create")} onClick={() => setActiveTab("create")}>
          ✏️ Create
        </button>
      </div>

      {/* Content */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "16px",
          display: "flex",
          gap: "16px",
        }}
      >
        {/* Browse Tab */}
        {activeTab === "browse" && (
          <div style={{ flex: 1 }}>
            {/* Navigation Bar */}
            <div
              style={{
                display: "flex",
                gap: "8px",
                marginBottom: "12px",
                alignItems: "center",
              }}
            >
              <button
                style={btnSecondary}
                onClick={goBack}
                disabled={historyIndex <= 0}
              >
                ←
              </button>
              <button
                style={btnSecondary}
                onClick={goForward}
                disabled={historyIndex >= pathHistory.length - 1}
              >
                →
              </button>
              <button style={btnSecondary} onClick={goUp}>
                ↑
              </button>
              <input
                type="text"
                value={currentPath}
                onChange={(e) => setCurrentPath(e.target.value)}
                onKeyDown={(e) =>
                  e.key === "Enter" && loadDirectory(currentPath)
                }
                style={{ ...inputStyle, flex: 1 }}
              />
              <button
                style={btnPrimary}
                onClick={() => loadDirectory(currentPath)}
              >
                🔄
              </button>
            </div>

            {/* Search */}
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: "6px",
                marginBottom: "12px",
              }}
            >
              <input
                type="text"
                placeholder="Search files..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && searchFiles()}
                style={{ ...inputStyle, flex: 1, minWidth: "120px" }}
              />
              <button
                style={{ ...btnSecondary, flexShrink: 0 }}
                onClick={searchFiles}
                disabled={isSearching}
              >
                {isSearching ? "..." : "🔍"}
              </button>
            </div>

            {/* Error */}
            {error && (
              <div
                style={{
                  ...card,
                  borderColor: "#ef4444",
                  color: "#f87171",
                  fontSize: "0.85em",
                }}
              >
                {error}
              </div>
            )}

            {/* Search Results */}
            {searchResults.length > 0 && (
              <div style={{ ...card, borderColor: "#3b82f6" }}>
                <div
                  style={{
                    color: "#60a5fa",
                    fontWeight: "500",
                    marginBottom: "8px",
                  }}
                >
                  🔍 Search Results ({searchResults.length})
                </div>
                <div style={{ maxHeight: "150px", overflowY: "auto" }}>
                  {searchResults.slice(0, 20).map((path, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "6px 8px",
                        borderBottom: "1px solid rgba(255,255,255,0.05)",
                        fontSize: "0.8em",
                        color: "#94a3b8",
                        cursor: "pointer",
                      }}
                      onClick={() => {
                        const parts = path.split("\\");
                        parts.pop();
                        navigateTo(parts.join("\\"));
                      }}
                    >
                      {path}
                    </div>
                  ))}
                </div>
                <button
                  style={{ ...btnSecondary, marginTop: "8px" }}
                  onClick={() => setSearchResults([])}
                >
                  Clear Results
                </button>
              </div>
            )}

            {/* File List */}
            <div style={{ ...card, maxHeight: "400px", overflowY: "auto" }}>
              {loading ? (
                <div
                  style={{
                    textAlign: "center",
                    color: "#6b7280",
                    padding: "20px",
                  }}
                >
                  Loading...
                </div>
              ) : files.length === 0 ? (
                <div
                  style={{
                    textAlign: "center",
                    color: "#6b7280",
                    padding: "20px",
                  }}
                >
                  Empty directory
                </div>
              ) : (
                files.map((item, idx) => (
                  <div
                    key={idx}
                    onClick={() => handleItemClick(item)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      cursor: "pointer",
                      background:
                        selectedFile?.name === item.name
                          ? "rgba(34, 197, 94, 0.15)"
                          : "transparent",
                      borderBottom: "1px solid rgba(255,255,255,0.05)",
                    }}
                  >
                    <span style={{ fontSize: "1.2em" }}>
                      {getFileIcon(item)}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ color: "white", fontSize: "0.9em" }}>
                        {item.name}
                      </div>
                      <div style={{ color: "#6b7280", fontSize: "0.75em" }}>
                        {item.type === "directory"
                          ? "Folder"
                          : item.size_human || formatSize(item.size)}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Upload Tab */}
        {activeTab === "upload" && (
          <div style={{ flex: 1 }}>
            <div style={card}>
              <div
                style={{
                  color: "#22c55e",
                  fontWeight: "600",
                  marginBottom: "12px",
                }}
              >
                📤 Upload File for Analysis
              </div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".txt,.md,.json,.xml,.yaml,.yml,.csv,.tsv,.py,.js,.jsx,.ts,.tsx,.html,.css,.java,.cpp,.c,.h,.go,.rs,.rb,.php,.sql,.sh,.bat,.ps1,.log"
                style={{ display: "none" }}
              />
              <div
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: "2px dashed rgba(34, 197, 94, 0.4)",
                  borderRadius: "12px",
                  padding: "40px",
                  textAlign: "center",
                  cursor: "pointer",
                  background: "rgba(34, 197, 94, 0.05)",
                }}
              >
                {isUploading ? (
                  <div style={{ color: "#22c55e" }}>⏳ Uploading...</div>
                ) : (
                  <>
                    <div style={{ fontSize: "2em", marginBottom: "8px" }}>
                      📂
                    </div>
                    <div style={{ color: "#22c55e", fontWeight: "500" }}>
                      Click to Upload
                    </div>
                    <div
                      style={{
                        color: "#6b7280",
                        fontSize: "0.8em",
                        marginTop: "4px",
                      }}
                    >
                      Supports text, code, JSON, CSV, and more
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Uploaded Files List */}
            {uploadedFiles.length > 0 && (
              <div style={card}>
                <div
                  style={{
                    color: "#22c55e",
                    fontWeight: "500",
                    marginBottom: "10px",
                  }}
                >
                  📋 Recently Uploaded ({uploadedFiles.length})
                </div>
                {uploadedFiles.map((file, idx) => (
                  <div
                    key={idx}
                    onClick={() => {
                      setSelectedFile({
                        name: file.name,
                        type: "file",
                        uploaded: true,
                      });
                      setFileContent(file.content);
                      setFileInfo(file.info);
                      setActiveTab("preview");
                    }}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "10px",
                      borderRadius: "8px",
                      cursor: "pointer",
                      borderBottom: "1px solid rgba(255,255,255,0.05)",
                    }}
                  >
                    <div>
                      <div style={{ color: "white", fontSize: "0.9em" }}>
                        📄 {file.name}
                      </div>
                      <div style={{ color: "#6b7280", fontSize: "0.75em" }}>
                        {file.info?.line_count || 0} lines •{" "}
                        {formatSize(file.info?.size_bytes || 0)}
                      </div>
                    </div>
                    <button
                      style={btnSecondary}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile({
                          name: file.name,
                          type: "file",
                          uploaded: true,
                        });
                        setFileContent(file.content);
                        setFileInfo(file.info);
                        setActiveTab("analyze");
                      }}
                    >
                      🤖 Analyze
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Preview Tab */}
        {activeTab === "preview" && (
          <div style={{ flex: 1 }}>
            {selectedFile ? (
              <>
                {/* File Info Bar */}
                <div
                  style={{
                    ...card,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ color: "white", fontWeight: "500" }}>
                      {getFileIcon(selectedFile)} {selectedFile.name}
                    </div>
                    <div style={{ color: "#6b7280", fontSize: "0.8em" }}>
                      {fileInfo?.line_count || 0} lines •{" "}
                      {formatSize(fileInfo?.size_bytes || 0)}
                      {fileInfo?.modified &&
                        ` • Modified: ${new Date(
                          fileInfo.modified
                        ).toLocaleDateString()}`}
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      style={{
                        ...btnSecondary,
                        borderColor: isSpeaking ? "#ef4444" : "#22c55e",
                        color: isSpeaking ? "#ef4444" : "#22c55e",
                      }}
                      onClick={isSpeaking ? stopSpeaking : readAloud}
                    >
                      {isSpeaking ? "🛑 Stop" : "🔊 Read Aloud"}
                    </button>
                    <button
                      style={btnPrimary}
                      onClick={() => setActiveTab("analyze")}
                    >
                      🤖 Analyze
                    </button>
                  </div>
                </div>

                {/* Content Preview */}
                <div style={card}>
                  <div
                    style={{
                      color: "#22c55e",
                      fontWeight: "500",
                      marginBottom: "10px",
                    }}
                  >
                    📄 File Content
                  </div>
                  {loadingContent ? (
                    <div
                      style={{
                        textAlign: "center",
                        color: "#6b7280",
                        padding: "20px",
                      }}
                    >
                      Loading content...
                    </div>
                  ) : (
                    <pre
                      style={{
                        maxHeight: "400px",
                        overflowY: "auto",
                        padding: "12px",
                        background: "rgba(0,0,0,0.3)",
                        borderRadius: "8px",
                        fontSize: "0.8em",
                        color: "#e2e8f0",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        fontFamily: "monospace",
                      }}
                    >
                      {fileContent || "[No content]"}
                    </pre>
                  )}
                </div>
              </>
            ) : (
              <div
                style={{
                  ...card,
                  textAlign: "center",
                  color: "#6b7280",
                  padding: "40px",
                }}
              >
                Select a file from Browse or Upload to preview
              </div>
            )}
          </div>
        )}

        {/* AI Analyze Tab */}
        {activeTab === "analyze" && (
          <div style={{ flex: 1 }}>
            {selectedFile ? (
              <>
                <div
                  style={{
                    ...card,
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <div style={{ color: "white", fontWeight: "500" }}>
                      🤖 AI Analysis: {selectedFile.name}
                    </div>
                    <div style={{ color: "#6b7280", fontSize: "0.8em" }}>
                      Get insights, structure analysis, and recommendations
                    </div>
                  </div>
                  <button
                    style={btnPrimary}
                    onClick={analyzeFile}
                    disabled={isAnalyzing || !fileContent}
                  >
                    {isAnalyzing ? "⏳ Analyzing..." : "🔍 Run Analysis"}
                  </button>
                </div>

                {/* Analysis Result */}
                {analysisResult && (
                  <div style={card}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "10px",
                      }}
                    >
                      <div style={{ color: "#22c55e", fontWeight: "500" }}>
                        📊 Analysis Report
                      </div>
                      <button
                        style={btnSecondary}
                        onClick={() => {
                          const utterance = new SpeechSynthesisUtterance(
                            analysisResult.slice(0, 3000)
                          );
                          window.speechSynthesis.speak(utterance);
                        }}
                      >
                        🔊 Read Report
                      </button>
                    </div>
                    <div
                      style={{
                        maxHeight: "400px",
                        overflowY: "auto",
                        padding: "12px",
                        background: "rgba(0,0,0,0.3)",
                        borderRadius: "8px",
                        fontSize: "0.85em",
                        color: "#e2e8f0",
                        whiteSpace: "pre-wrap",
                        lineHeight: "1.6",
                      }}
                    >
                      {analysisResult}
                    </div>
                  </div>
                )}

                {/* Quick Stats */}
                {fileInfo && (
                  <div style={card}>
                    <div
                      style={{
                        color: "#22c55e",
                        fontWeight: "500",
                        marginBottom: "10px",
                      }}
                    >
                      📈 Quick Stats
                    </div>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(3, 1fr)",
                        gap: "12px",
                      }}
                    >
                      <div
                        style={{
                          textAlign: "center",
                          padding: "12px",
                          background: "rgba(34, 197, 94, 0.1)",
                          borderRadius: "8px",
                        }}
                      >
                        <div
                          style={{
                            color: "#22c55e",
                            fontSize: "1.2em",
                            fontWeight: "bold",
                          }}
                        >
                          {fileInfo.line_count || 0}
                        </div>
                        <div style={{ color: "#6b7280", fontSize: "0.75em" }}>
                          Lines
                        </div>
                      </div>
                      <div
                        style={{
                          textAlign: "center",
                          padding: "12px",
                          background: "rgba(59, 130, 246, 0.1)",
                          borderRadius: "8px",
                        }}
                      >
                        <div
                          style={{
                            color: "#60a5fa",
                            fontSize: "1.2em",
                            fontWeight: "bold",
                          }}
                        >
                          {fileInfo.char_count || fileContent.length}
                        </div>
                        <div style={{ color: "#6b7280", fontSize: "0.75em" }}>
                          Characters
                        </div>
                      </div>
                      <div
                        style={{
                          textAlign: "center",
                          padding: "12px",
                          background: "rgba(168, 85, 247, 0.1)",
                          borderRadius: "8px",
                        }}
                      >
                        <div
                          style={{
                            color: "#a855f7",
                            fontSize: "1.2em",
                            fontWeight: "bold",
                          }}
                        >
                          {formatSize(fileInfo.size_bytes || 0)}
                        </div>
                        <div style={{ color: "#6b7280", fontSize: "0.75em" }}>
                          Size
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div
                style={{
                  ...card,
                  textAlign: "center",
                  color: "#6b7280",
                  padding: "40px",
                }}
              >
                Select a file to analyze with AI
              </div>
            )}
          </div>
        )}

        {/* Create Tab */}
        {activeTab === "create" && (
          <div style={{ flex: 1 }}>
            <div style={card}>
              <div
                style={{
                  color: "#22c55e",
                  fontWeight: "600",
                  marginBottom: "12px",
                }}
              >
                ✏️ Create New File
              </div>
              <div style={{ marginBottom: "12px" }}>
                <label
                  style={{
                    color: "#94a3b8",
                    fontSize: "0.8em",
                    display: "block",
                    marginBottom: "6px",
                  }}
                >
                  File Name (will be created in: {currentPath})
                </label>
                <input
                  type="text"
                  placeholder="example.txt"
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                  style={inputStyle}
                />
              </div>
              <div style={{ marginBottom: "12px" }}>
                <label
                  style={{
                    color: "#94a3b8",
                    fontSize: "0.8em",
                    display: "block",
                    marginBottom: "6px",
                  }}
                >
                  File Content
                </label>
                <textarea
                  placeholder="Enter file content..."
                  value={newFileContent}
                  onChange={(e) => setNewFileContent(e.target.value)}
                  style={{
                    ...inputStyle,
                    minHeight: "200px",
                    resize: "vertical",
                    fontFamily: "monospace",
                  }}
                />
              </div>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  style={btnPrimary}
                  onClick={createNewFile}
                  disabled={isSaving || !newFileName.trim()}
                >
                  {isSaving ? "⏳ Saving..." : "💾 Create File"}
                </button>
                <button
                  style={btnSecondary}
                  onClick={() => {
                    setNewFileName("");
                    setNewFileContent("");
                  }}
                >
                  🗑️ Clear
                </button>
              </div>
            </div>

            {/* AI Writing Assistant */}
            <div style={{ ...card, borderColor: "rgba(168, 85, 247, 0.3)" }}>
              <div
                style={{
                  color: "#a855f7",
                  fontWeight: "500",
                  marginBottom: "10px",
                }}
              >
                🤖 AI Writing Assistant
              </div>
              <div
                style={{
                  color: "#94a3b8",
                  fontSize: "0.8em",
                  marginBottom: "12px",
                }}
              >
                Let AI help you write content. Describe what you need and AI
                will generate it.
              </div>
              <button
                style={{
                  ...btnSecondary,
                  borderColor: "#a855f7",
                  color: "#a855f7",
                }}
                onClick={async () => {
                  if (!newFileName.trim()) {
                    setError("Please enter a filename first");
                    return;
                  }
                  setIsSaving(true);
                  try {
                    const response = await axios.post(
                      `${backendUrl}/chat`,
                      {
                        messages: [
                          {
                            role: "user",
                            content: `Generate content for a file named "${newFileName}". ${
                              newFileContent
                                ? `Additional instructions: ${newFileContent}`
                                : "Create appropriate default content based on the file extension."
                            }. Only respond with the file content, no explanations.`,
                          },
                        ],
                      },
                      { timeout: 60000 }
                    );
                    setNewFileContent(response.data.content || "");
                  } catch (err) {
                    setError(err.message);
                  } finally {
                    setIsSaving(false);
                  }
                }}
                disabled={isSaving}
              >
                ✨ Generate Content with AI
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Resize Handle */}
      <div
        className="resize-handle"
        style={{
          position: "absolute",
          bottom: 0,
          right: 0,
          width: "20px",
          height: "20px",
          cursor: "se-resize",
          background: "linear-gradient(135deg, transparent 50%, #22c55e 50%)",
          borderRadius: "0 0 16px 0",
        }}
        onMouseDown={(e) => {
          e.stopPropagation();
          setIsResizing(true);
        }}
      />
    </div>
  );
};

export default FileManagementConsole;
