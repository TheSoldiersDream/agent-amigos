/**
 * 🧠🎨 Agent Amigos Canvas - Canvas Surface
 *
 * Core drawing canvas with multi-layer support, zoom/pan, and various drawing modes.
 * Supports freehand drawing, shapes, text, images, and CAD-style elements.
 *
 * Created by Darrell Buttigieg (@darrellbuttigieg) #thesoldiersdream
 */

import React, {
  useRef,
  useEffect,
  useState,
  useCallback,
  forwardRef,
  useImperativeHandle,
} from "react";

// Drawing tools configuration
const TOOLS = {
  SELECT: "select",
  PEN: "pen",
  BRUSH: "brush",
  ERASER: "eraser",
  LINE: "line",
  RECTANGLE: "rectangle",
  ELLIPSE: "ellipse",
  ARROW: "arrow",
  TEXT: "text",
  IMAGE: "image",
  WALL: "wall",
  DOOR: "door",
  WINDOW: "window",
  DIMENSION: "dimension",
};

// Default styles
const DEFAULT_STYLES = {
  strokeColor: "#ffffff",
  fillColor: "transparent",
  strokeWidth: 2,
  fontSize: 16,
  fontFamily: "Inter, sans-serif",
  opacity: 1,
};

const CanvasSurface = forwardRef(
  (
    {
      width = 1920,
      height = 1080,
      tool = TOOLS.PEN,
      styles = DEFAULT_STYLES,
      gridEnabled = false,
      gridSize = 20,
      snapToGrid = false,
      layers = [],
      activeLayerId = "default",
      onObjectAdd,
      onObjectUpdate,
      onObjectDelete,
      onSelectionChange,
      mode = "sketch", // sketch, diagram, cad, media, text
    },
    ref
  ) => {
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const [ctx, setCtx] = useState(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [currentPath, setCurrentPath] = useState([]);
    const [objects, setObjects] = useState([]);
    const [selectedObjectIds, setSelectedObjectIds] = useState([]);
    const [pan, setPan] = useState({ x: 0, y: 0 });
    const [zoom, setZoom] = useState(1);
    const [isPanning, setIsPanning] = useState(false);
    const [lastPanPoint, setLastPanPoint] = useState({ x: 0, y: 0 });
    const [history, setHistory] = useState([]);
    const [historyIndex, setHistoryIndex] = useState(-1);
    const [startPoint, setStartPoint] = useState(null);

    // Initialize canvas
    useEffect(() => {
      const canvas = canvasRef.current;
      if (canvas) {
        const context = canvas.getContext("2d");
        setCtx(context);

        // Set initial transform
        context.setTransform(zoom, 0, 0, zoom, pan.x, pan.y);
      }
    }, []);

    // Handle zoom and pan changes
    useEffect(() => {
      if (ctx) {
        redraw();
      }
    }, [zoom, pan, objects, gridEnabled]);

    // Snap point to grid if enabled
    const snapPoint = useCallback(
      (x, y) => {
        if (snapToGrid && gridEnabled) {
          return {
            x: Math.round(x / gridSize) * gridSize,
            y: Math.round(y / gridSize) * gridSize,
          };
        }
        return { x, y };
      },
      [snapToGrid, gridEnabled, gridSize]
    );

    // Convert screen coordinates to canvas coordinates
    const screenToCanvas = useCallback(
      (screenX, screenY) => {
        const rect = canvasRef.current.getBoundingClientRect();
        return {
          x: (screenX - rect.left - pan.x) / zoom,
          y: (screenY - rect.top - pan.y) / zoom,
        };
      },
      [pan, zoom]
    );

    // Draw grid
    const drawGrid = useCallback(
      (context) => {
        if (!gridEnabled) return;

        context.save();
        context.strokeStyle =
          mode === "cad"
            ? "rgba(0, 200, 255, 0.15)"
            : "rgba(255, 255, 255, 0.08)";
        context.lineWidth = 0.5;

        const startX = Math.floor(-pan.x / zoom / gridSize) * gridSize;
        const startY = Math.floor(-pan.y / zoom / gridSize) * gridSize;
        const endX = startX + width / zoom + gridSize * 2;
        const endY = startY + height / zoom + gridSize * 2;

        // Vertical lines
        for (let x = startX; x < endX; x += gridSize) {
          context.beginPath();
          context.moveTo(x, startY);
          context.lineTo(x, endY);
          context.stroke();
        }

        // Horizontal lines
        for (let y = startY; y < endY; y += gridSize) {
          context.beginPath();
          context.moveTo(startX, y);
          context.lineTo(endX, y);
          context.stroke();
        }

        // Draw major grid lines every 5 cells in CAD mode
        if (mode === "cad") {
          context.strokeStyle = "rgba(0, 200, 255, 0.3)";
          context.lineWidth = 1;

          for (let x = startX; x < endX; x += gridSize * 5) {
            context.beginPath();
            context.moveTo(x, startY);
            context.lineTo(x, endY);
            context.stroke();
          }

          for (let y = startY; y < endY; y += gridSize * 5) {
            context.beginPath();
            context.moveTo(startX, y);
            context.lineTo(endX, y);
            context.stroke();
          }
        }

        context.restore();
      },
      [gridEnabled, gridSize, pan, zoom, width, height, mode]
    );

    // Draw a single object
    const drawObject = useCallback(
      (context, obj) => {
        context.save();

        // Apply object styles
        context.strokeStyle = obj.strokeColor || styles.strokeColor;
        context.fillStyle = obj.fillColor || styles.fillColor;
        context.lineWidth = obj.strokeWidth || styles.strokeWidth;
        context.globalAlpha = obj.opacity ?? styles.opacity;
        context.lineCap = "round";
        context.lineJoin = "round";

        switch (obj.type) {
          case "path":
            if (obj.points && obj.points.length > 0) {
              context.beginPath();
              context.moveTo(obj.points[0].x, obj.points[0].y);
              for (let i = 1; i < obj.points.length; i++) {
                context.lineTo(obj.points[i].x, obj.points[i].y);
              }
              context.stroke();
            }
            break;

          case "line":
            context.beginPath();
            context.moveTo(obj.x1, obj.y1);
            context.lineTo(obj.x2, obj.y2);
            context.stroke();
            break;

          case "arrow":
            // Draw line
            context.beginPath();
            context.moveTo(obj.x1, obj.y1);
            context.lineTo(obj.x2, obj.y2);
            context.stroke();

            // Draw arrowhead
            const angle = Math.atan2(obj.y2 - obj.y1, obj.x2 - obj.x1);
            const headLength = 15;
            context.beginPath();
            context.moveTo(obj.x2, obj.y2);
            context.lineTo(
              obj.x2 - headLength * Math.cos(angle - Math.PI / 6),
              obj.y2 - headLength * Math.sin(angle - Math.PI / 6)
            );
            context.moveTo(obj.x2, obj.y2);
            context.lineTo(
              obj.x2 - headLength * Math.cos(angle + Math.PI / 6),
              obj.y2 - headLength * Math.sin(angle + Math.PI / 6)
            );
            context.stroke();
            break;

          case "rectangle":
            context.beginPath();
            context.rect(obj.x, obj.y, obj.width, obj.height);
            if (obj.fillColor && obj.fillColor !== "transparent") {
              context.fill();
            }
            context.stroke();
            break;

          case "ellipse":
            context.beginPath();
            context.ellipse(
              obj.x + obj.width / 2,
              obj.y + obj.height / 2,
              Math.abs(obj.width / 2),
              Math.abs(obj.height / 2),
              0,
              0,
              Math.PI * 2
            );
            if (obj.fillColor && obj.fillColor !== "transparent") {
              context.fill();
            }
            context.stroke();
            break;

          case "text":
            context.font = `${obj.fontSize || styles.fontSize}px ${
              obj.fontFamily || styles.fontFamily
            }`;
            context.fillStyle = obj.strokeColor || styles.strokeColor;
            context.fillText(obj.text, obj.x, obj.y);
            break;

          case "image":
            if (obj.imageData) {
              const img = new Image();
              img.onload = () => {
                context.drawImage(img, obj.x, obj.y, obj.width, obj.height);
              };
              img.src = obj.imageData;
            }
            break;

          // CAD Elements
          case "wall":
            context.lineWidth = obj.thickness || 8;
            context.strokeStyle = obj.strokeColor || "#64748b";
            context.beginPath();
            context.moveTo(obj.x1, obj.y1);
            context.lineTo(obj.x2, obj.y2);
            context.stroke();
            break;

          case "door":
            // Draw door opening with swing arc
            context.strokeStyle = obj.strokeColor || "#22c55e";
            context.lineWidth = 2;
            const doorWidth = obj.width || 40;
            context.beginPath();
            context.moveTo(obj.x, obj.y);
            context.lineTo(obj.x + doorWidth, obj.y);
            context.stroke();
            // Arc
            context.beginPath();
            context.arc(obj.x, obj.y, doorWidth, 0, -Math.PI / 2, true);
            context.stroke();
            break;

          case "window":
            context.strokeStyle = obj.strokeColor || "#3b82f6";
            context.lineWidth = 4;
            context.beginPath();
            context.moveTo(obj.x1, obj.y1);
            context.lineTo(obj.x2, obj.y2);
            context.stroke();
            // Window panes
            context.lineWidth = 1;
            const midX = (obj.x1 + obj.x2) / 2;
            const midY = (obj.y1 + obj.y2) / 2;
            context.beginPath();
            context.moveTo(midX - 5, midY - 5);
            context.lineTo(midX + 5, midY + 5);
            context.moveTo(midX + 5, midY - 5);
            context.lineTo(midX - 5, midY + 5);
            context.stroke();
            break;

          case "dimension":
            // Dimension line with measurement
            context.strokeStyle = obj.strokeColor || "#f59e0b";
            context.lineWidth = 1;
            const dx = obj.x2 - obj.x1;
            const dy = obj.y2 - obj.y1;
            const distance = Math.sqrt(dx * dx + dy * dy);
            const dimAngle = Math.atan2(dy, dx);

            // Extension lines
            const ext = 10;
            context.beginPath();
            context.moveTo(obj.x1, obj.y1 - ext);
            context.lineTo(obj.x1, obj.y1 + ext);
            context.moveTo(obj.x2, obj.y2 - ext);
            context.lineTo(obj.x2, obj.y2 + ext);
            context.stroke();

            // Dimension line
            context.beginPath();
            context.moveTo(obj.x1, obj.y1);
            context.lineTo(obj.x2, obj.y2);
            context.stroke();

            // Measurement text
            context.font = "12px Inter, sans-serif";
            context.fillStyle = "#f59e0b";
            const label =
              obj.unit === "mm"
                ? `${Math.round(distance * 10)}mm`
                : `${(distance / 50).toFixed(2)}m`;
            context.save();
            context.translate((obj.x1 + obj.x2) / 2, (obj.y1 + obj.y2) / 2);
            context.rotate(dimAngle);
            context.fillText(label, -20, -5);
            context.restore();
            break;

          default:
            break;
        }

        // Draw selection handles if selected
        if (selectedObjectIds.includes(obj.id)) {
          context.strokeStyle = "#6366f1";
          context.lineWidth = 2;
          context.setLineDash([5, 5]);

          const bounds = getObjectBounds(obj);
          context.strokeRect(
            bounds.x - 5,
            bounds.y - 5,
            bounds.width + 10,
            bounds.height + 10
          );

          context.setLineDash([]);
        }

        context.restore();
      },
      [styles, selectedObjectIds]
    );

    // Get bounding box of an object
    const getObjectBounds = (obj) => {
      switch (obj.type) {
        case "path":
          if (!obj.points || obj.points.length === 0)
            return { x: 0, y: 0, width: 0, height: 0 };
          const xs = obj.points.map((p) => p.x);
          const ys = obj.points.map((p) => p.y);
          return {
            x: Math.min(...xs),
            y: Math.min(...ys),
            width: Math.max(...xs) - Math.min(...xs),
            height: Math.max(...ys) - Math.min(...ys),
          };
        case "line":
        case "arrow":
        case "wall":
        case "window":
        case "dimension":
          return {
            x: Math.min(obj.x1, obj.x2),
            y: Math.min(obj.y1, obj.y2),
            width: Math.abs(obj.x2 - obj.x1),
            height: Math.abs(obj.y2 - obj.y1),
          };
        case "rectangle":
        case "ellipse":
        case "text":
        case "image":
        case "door":
          return {
            x: obj.x,
            y: obj.y,
            width: obj.width || 100,
            height: obj.height || 20,
          };
        default:
          return { x: 0, y: 0, width: 0, height: 0 };
      }
    };

    // Redraw entire canvas
    const redraw = useCallback(() => {
      if (!ctx || !canvasRef.current) return;

      const canvas = canvasRef.current;

      // Clear canvas
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);

      // Background based on mode
      if (mode === "cad") {
        ctx.fillStyle = "#0f172a";
      } else {
        ctx.fillStyle = "#1a1a2e";
      }
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.restore();

      // Apply transform
      ctx.save();
      ctx.setTransform(zoom, 0, 0, zoom, pan.x, pan.y);

      // Draw grid
      drawGrid(ctx);

      // Draw all objects by layer
      const sortedObjects = [...objects].sort((a, b) => {
        const layerA = layers.findIndex((l) => l.id === a.layerId) || 0;
        const layerB = layers.findIndex((l) => l.id === b.layerId) || 0;
        return layerA - layerB;
      });

      console.log(`🎨 Redrawing ${sortedObjects.length} objects`);

      sortedObjects.forEach((obj) => {
        const layer = layers.find((l) => l.id === obj.layerId);
        if (!layer || layer.visible !== false) {
          drawObject(ctx, obj);
        }
      });

      // Draw current path being drawn
      if (currentPath.length > 0) {
        ctx.strokeStyle = styles.strokeColor;
        ctx.lineWidth = styles.strokeWidth;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.beginPath();
        ctx.moveTo(currentPath[0].x, currentPath[0].y);
        for (let i = 1; i < currentPath.length; i++) {
          ctx.lineTo(currentPath[i].x, currentPath[i].y);
        }
        ctx.stroke();
      }

      ctx.restore();
    }, [
      ctx,
      zoom,
      pan,
      objects,
      currentPath,
      layers,
      mode,
      drawGrid,
      drawObject,
      styles,
    ]);

    // Mouse event handlers
    const handleMouseDown = (e) => {
      const point = screenToCanvas(e.clientX, e.clientY);
      const snapped = snapPoint(point.x, point.y);

      // Middle mouse button or spacebar held = pan
      if (e.button === 1 || (e.button === 0 && e.altKey)) {
        setIsPanning(true);
        setLastPanPoint({ x: e.clientX, y: e.clientY });
        return;
      }

      if (tool === TOOLS.SELECT) {
        // Selection logic
        const clickedObj = objects.find((obj) => {
          const bounds = getObjectBounds(obj);
          return (
            point.x >= bounds.x &&
            point.x <= bounds.x + bounds.width &&
            point.y >= bounds.y &&
            point.y <= bounds.y + bounds.height
          );
        });

        if (clickedObj) {
          setSelectedObjectIds(
            e.shiftKey ? [...selectedObjectIds, clickedObj.id] : [clickedObj.id]
          );
          onSelectionChange?.([clickedObj.id]);
        } else {
          setSelectedObjectIds([]);
          onSelectionChange?.([]);
        }
      } else if (tool === TOOLS.ERASER) {
        // Find and remove object under cursor
        const clickedObj = objects.find((obj) => {
          const bounds = getObjectBounds(obj);
          return (
            point.x >= bounds.x - 10 &&
            point.x <= bounds.x + bounds.width + 10 &&
            point.y >= bounds.y - 10 &&
            point.y <= bounds.y + bounds.height + 10
          );
        });
        if (clickedObj) {
          const newObjects = objects.filter((o) => o.id !== clickedObj.id);
          setObjects(newObjects);
          onObjectDelete?.(clickedObj.id);
          saveHistory(newObjects);
        }
      } else if ([TOOLS.PEN, TOOLS.BRUSH].includes(tool)) {
        setIsDrawing(true);
        setCurrentPath([snapped]);
      } else if (
        [
          TOOLS.LINE,
          TOOLS.ARROW,
          TOOLS.RECTANGLE,
          TOOLS.ELLIPSE,
          TOOLS.WALL,
          TOOLS.WINDOW,
          TOOLS.DIMENSION,
        ].includes(tool)
      ) {
        setIsDrawing(true);
        setStartPoint(snapped);
      } else if (tool === TOOLS.TEXT) {
        const text = prompt("Enter text:");
        if (text) {
          const newObj = {
            id: `obj_${Date.now()}`,
            type: "text",
            text,
            x: snapped.x,
            y: snapped.y,
            fontSize: styles.fontSize,
            fontFamily: styles.fontFamily,
            strokeColor: styles.strokeColor,
            layerId: activeLayerId,
            timestamp: Date.now(),
          };
          const newObjects = [...objects, newObj];
          setObjects(newObjects);
          onObjectAdd?.(newObj);
          saveHistory(newObjects);
        }
      } else if (tool === TOOLS.DOOR) {
        const newObj = {
          id: `obj_${Date.now()}`,
          type: "door",
          x: snapped.x,
          y: snapped.y,
          width: 40,
          strokeColor: "#22c55e",
          layerId: activeLayerId,
          timestamp: Date.now(),
        };
        const newObjects = [...objects, newObj];
        setObjects(newObjects);
        onObjectAdd?.(newObj);
        saveHistory(newObjects);
      }
    };

    const handleMouseMove = (e) => {
      if (isPanning) {
        const dx = e.clientX - lastPanPoint.x;
        const dy = e.clientY - lastPanPoint.y;
        setPan({ x: pan.x + dx, y: pan.y + dy });
        setLastPanPoint({ x: e.clientX, y: e.clientY });
        return;
      }

      if (!isDrawing) return;

      const point = screenToCanvas(e.clientX, e.clientY);
      const snapped = snapPoint(point.x, point.y);

      if ([TOOLS.PEN, TOOLS.BRUSH].includes(tool)) {
        setCurrentPath([...currentPath, snapped]);
      }

      redraw();

      // Draw preview for shape tools
      if (startPoint && ctx) {
        ctx.save();
        ctx.setTransform(zoom, 0, 0, zoom, pan.x, pan.y);
        ctx.strokeStyle = styles.strokeColor;
        ctx.lineWidth = styles.strokeWidth;
        ctx.setLineDash([5, 5]);

        if (
          tool === TOOLS.LINE ||
          tool === TOOLS.ARROW ||
          tool === TOOLS.WALL ||
          tool === TOOLS.WINDOW ||
          tool === TOOLS.DIMENSION
        ) {
          ctx.beginPath();
          ctx.moveTo(startPoint.x, startPoint.y);
          ctx.lineTo(snapped.x, snapped.y);
          ctx.stroke();
        } else if (tool === TOOLS.RECTANGLE) {
          ctx.strokeRect(
            startPoint.x,
            startPoint.y,
            snapped.x - startPoint.x,
            snapped.y - startPoint.y
          );
        } else if (tool === TOOLS.ELLIPSE) {
          ctx.beginPath();
          const cx = (startPoint.x + snapped.x) / 2;
          const cy = (startPoint.y + snapped.y) / 2;
          const rx = Math.abs(snapped.x - startPoint.x) / 2;
          const ry = Math.abs(snapped.y - startPoint.y) / 2;
          ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
          ctx.stroke();
        }

        ctx.setLineDash([]);
        ctx.restore();
      }
    };

    const handleMouseUp = (e) => {
      if (isPanning) {
        setIsPanning(false);
        return;
      }

      if (!isDrawing) return;

      const point = screenToCanvas(e.clientX, e.clientY);
      const snapped = snapPoint(point.x, point.y);

      let newObj = null;

      if ([TOOLS.PEN, TOOLS.BRUSH].includes(tool) && currentPath.length > 1) {
        newObj = {
          id: `obj_${Date.now()}`,
          type: "path",
          points: [...currentPath, snapped],
          strokeColor: styles.strokeColor,
          strokeWidth:
            tool === TOOLS.BRUSH ? styles.strokeWidth * 2 : styles.strokeWidth,
          layerId: activeLayerId,
          timestamp: Date.now(),
        };
      } else if (startPoint) {
        const toolTypeMap = {
          [TOOLS.LINE]: "line",
          [TOOLS.ARROW]: "arrow",
          [TOOLS.WALL]: "wall",
          [TOOLS.WINDOW]: "window",
          [TOOLS.DIMENSION]: "dimension",
        };

        if (toolTypeMap[tool]) {
          newObj = {
            id: `obj_${Date.now()}`,
            type: toolTypeMap[tool],
            x1: startPoint.x,
            y1: startPoint.y,
            x2: snapped.x,
            y2: snapped.y,
            strokeColor: styles.strokeColor,
            strokeWidth: tool === TOOLS.WALL ? 8 : styles.strokeWidth,
            layerId: activeLayerId,
            timestamp: Date.now(),
            unit: mode === "cad" ? "mm" : "px",
          };
        } else if (tool === TOOLS.RECTANGLE) {
          newObj = {
            id: `obj_${Date.now()}`,
            type: "rectangle",
            x: Math.min(startPoint.x, snapped.x),
            y: Math.min(startPoint.y, snapped.y),
            width: Math.abs(snapped.x - startPoint.x),
            height: Math.abs(snapped.y - startPoint.y),
            strokeColor: styles.strokeColor,
            fillColor: styles.fillColor,
            strokeWidth: styles.strokeWidth,
            layerId: activeLayerId,
            timestamp: Date.now(),
          };
        } else if (tool === TOOLS.ELLIPSE) {
          newObj = {
            id: `obj_${Date.now()}`,
            type: "ellipse",
            x: Math.min(startPoint.x, snapped.x),
            y: Math.min(startPoint.y, snapped.y),
            width: Math.abs(snapped.x - startPoint.x),
            height: Math.abs(snapped.y - startPoint.y),
            strokeColor: styles.strokeColor,
            fillColor: styles.fillColor,
            strokeWidth: styles.strokeWidth,
            layerId: activeLayerId,
            timestamp: Date.now(),
          };
        }
      }

      if (newObj) {
        const newObjects = [...objects, newObj];
        setObjects(newObjects);
        onObjectAdd?.(newObj);
        saveHistory(newObjects);
      }

      setIsDrawing(false);
      setCurrentPath([]);
      setStartPoint(null);
      redraw();
    };

    // Wheel handler for zoom - attached manually to support non-passive event
    const handleWheel = useCallback(
      (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        const newZoom = Math.max(0.1, Math.min(5, zoom * delta));

        // Zoom towards cursor
        const rect = canvasRef.current.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const newPanX = mouseX - (mouseX - pan.x) * (newZoom / zoom);
        const newPanY = mouseY - (mouseY - pan.y) * (newZoom / zoom);

        setZoom(newZoom);
        setPan({ x: newPanX, y: newPanY });
      },
      [zoom, pan]
    );

    useEffect(() => {
      const canvas = canvasRef.current;
      if (canvas) {
        canvas.addEventListener("wheel", handleWheel, { passive: false });
      }
      return () => {
        if (canvas) {
          canvas.removeEventListener("wheel", handleWheel);
        }
      };
    }, [handleWheel]);

    // History management
    const saveHistory = (newObjects) => {
      const newHistory = history.slice(0, historyIndex + 1);
      newHistory.push(JSON.stringify(newObjects));
      setHistory(newHistory);
      setHistoryIndex(newHistory.length - 1);
    };

    const undo = useCallback(() => {
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setObjects(JSON.parse(history[newIndex]));
      }
    }, [history, historyIndex]);

    const redo = useCallback(() => {
      if (historyIndex < history.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setObjects(JSON.parse(history[newIndex]));
      }
    }, [history, historyIndex]);

    // Expose methods to parent
    useImperativeHandle(ref, () => ({
      undo,
      redo,
      clear: () => {
        setObjects([]);
        saveHistory([]);
      },
      addObject: (obj) => {
        setObjects((prev) => {
          const newObj = {
            ...obj,
            id: obj.id || `obj_${Date.now()}`,
            layerId: obj.layerId || activeLayerId,
          };
          const newObjects = [...prev, newObj];
          saveHistory(newObjects);
          return newObjects;
        });
      },
      addObjects: (objs) => {
        setObjects((prev) => {
          const processedObjs = objs.map((obj) => ({
            ...obj,
            id:
              obj.id ||
              `obj_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            layerId: obj.layerId || activeLayerId,
          }));
          const newObjects = [...prev, ...processedObjs];
          console.log("🎨 CanvasSurface: Adding objects", newObjects.length);
          saveHistory(newObjects);
          return newObjects;
        });
      },
      removeObject: (id) => {
        setObjects((prev) => {
          const newObjects = prev.filter((o) => o.id !== id);
          saveHistory(newObjects);
          return newObjects;
        });
      },
      updateObject: (id, updates) => {
        setObjects((prev) => {
          const newObjects = prev.map((o) =>
            o.id === id ? { ...o, ...updates } : o
          );
          saveHistory(newObjects);
          return newObjects;
        });
      },
      getObjects: () => objects,
      setObjects: (newObjects) => {
        setObjects(newObjects);
        saveHistory(newObjects);
      },
      exportPNG: () => canvasRef.current?.toDataURL("image/png"),
      exportSVG: () => generateSVG(),
      setZoom: (z) => setZoom(z),
      setPan: (p) => setPan(p),
      resetView: () => {
        setZoom(1);
        setPan({ x: 0, y: 0 });
      },
      redraw,
    }));

    // Generate SVG export
    const generateSVG = () => {
      let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">`;
      svg += `<rect width="100%" height="100%" fill="#1a1a2e"/>`;

      objects.forEach((obj) => {
        switch (obj.type) {
          case "path":
            if (obj.points?.length > 0) {
              const d = `M ${obj.points
                .map((p) => `${p.x},${p.y}`)
                .join(" L ")}`;
              svg += `<path d="${d}" stroke="${obj.strokeColor}" stroke-width="${obj.strokeWidth}" fill="none"/>`;
            }
            break;
          case "rectangle":
            svg += `<rect x="${obj.x}" y="${obj.y}" width="${
              obj.width
            }" height="${obj.height}" stroke="${
              obj.strokeColor
            }" stroke-width="${obj.strokeWidth}" fill="${
              obj.fillColor || "none"
            }"/>`;
            break;
          case "ellipse":
            svg += `<ellipse cx="${obj.x + obj.width / 2}" cy="${
              obj.y + obj.height / 2
            }" rx="${obj.width / 2}" ry="${obj.height / 2}" stroke="${
              obj.strokeColor
            }" stroke-width="${obj.strokeWidth}" fill="${
              obj.fillColor || "none"
            }"/>`;
            break;
          case "text":
            svg += `<text x="${obj.x}" y="${obj.y}" fill="${obj.strokeColor}" font-size="${obj.fontSize}">${obj.text}</text>`;
            break;
          case "line":
          case "wall":
            svg += `<line x1="${obj.x1}" y1="${obj.y1}" x2="${obj.x2}" y2="${obj.y2}" stroke="${obj.strokeColor}" stroke-width="${obj.strokeWidth}"/>`;
            break;
        }
      });

      svg += "</svg>";
      return svg;
    };

    return (
      <div
        ref={containerRef}
        style={{
          width: "100%",
          height: "100%",
          overflow: "hidden",
          cursor: isPanning
            ? "grabbing"
            : tool === TOOLS.SELECT
            ? "default"
            : "crosshair",
        }}
      >
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          style={{
            display: "block",
            touchAction: "none",
          }}
        />
      </div>
    );
  }
);

CanvasSurface.displayName = "CanvasSurface";
export { TOOLS, DEFAULT_STYLES };
export default CanvasSurface;
