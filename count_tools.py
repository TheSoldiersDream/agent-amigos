import sys
import os

# Mock dependencies to import agent_init.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# We need to mock several things because agent_init.py imports a lot of stuff
class Mock:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None

sys.modules['backend.utils.autonomy_controller'] = Mock()
sys.modules['backend.tools.computer_tools'] = Mock()
sys.modules['backend.tools.window_tools'] = Mock()
sys.modules['backend.tools.web_tools'] = Mock()
sys.modules['backend.tools.scraper_tools'] = Mock()
sys.modules['backend.tools.report_tools'] = Mock()
sys.modules['backend.tools.file_tools'] = Mock()
sys.modules['backend.tools.system_tools'] = Mock()
sys.modules['backend.tools.weather_tools'] = Mock()
sys.modules['backend.tools.media_tools'] = Mock()
sys.modules['backend.tools.game_trainer'] = Mock()
sys.modules['backend.tools.forms_db'] = Mock()
sys.modules['backend.tools.recording_tools'] = Mock()
sys.modules['backend.tools.agent_memory'] = Mock()
sys.modules['backend.utils.tool_registry'] = Mock()
sys.modules['backend.utils.openwork_integration'] = Mock()
sys.modules['backend.tools.agent_coordinator'] = Mock()
sys.modules['backend.tools.shop_tools'] = Mock()
sys.modules['backend.tools.canvas_design'] = Mock()
sys.modules['backend.tools.map_tools'] = Mock()
sys.modules['backend.tools.progress_tools'] = Mock()
sys.modules['backend.tools.doc_storage'] = Mock()
sys.modules['backend.tools.canvas_tools'] = Mock()

import backend.agent_init as agent_init

print(f"Total tools in dictionary: {len(agent_init.TOOLS)}")
for i, name in enumerate(sorted(agent_init.TOOLS.keys())):
    print(f"{i+1}: {name}")
