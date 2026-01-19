/**
 * 🧠🎨 Agent Amigos Canvas - Index Export
 */

import CanvasPanel from "./CanvasPanel";
import CanvasSurface, { TOOLS, DEFAULT_STYLES } from "./CanvasSurface";
import ToolsToolbar, { MODES } from "./ToolsToolbar";
import LayersPanel, { DEFAULT_LAYERS } from "./LayersPanel";

// Default export for easy importing
export default CanvasPanel;

// Named exports for granular access
export {
  CanvasPanel,
  CanvasSurface,
  TOOLS,
  DEFAULT_STYLES,
  ToolsToolbar,
  MODES,
  LayersPanel,
  DEFAULT_LAYERS,
};
