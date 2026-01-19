import json
import urllib.request
import urllib.parse
import time
import websocket # pip install websocket-client
import uuid
import os
from typing import Dict, Any, Optional

class ComfyClient:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.ws = None

    def queue_prompt(self, prompt: Dict[str, Any]) -> Dict[str, Any]:
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = urllib.request.Request(f"http://{self.server_address}/prompt", data=data)
        return json.loads(urllib.request.urlopen(req).read())

    def get_image(self, filename: str, subfolder: str, folder_type: str):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        with urllib.request.urlopen(f"http://{self.server_address}/view?{url_values}") as response:
            return response.read()

    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        with urllib.request.urlopen(f"http://{self.server_address}/history/{prompt_id}") as response:
            return json.loads(response.read())

    def connect(self):
        self.ws = websocket.WebSocket()
        self.ws.connect(f"ws://{self.server_address}/ws?clientId={self.client_id}")

    def close(self):
        if self.ws:
            self.ws.close()

    def generate(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a workflow and wait for the result.
        Returns a dictionary containing the outputs (e.g., video paths).
        """
        try:
            self.connect()
            prompt_id = self.queue_prompt(workflow)['prompt_id']
            
            output_files = []
            
            while True:
                out = self.ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            break # Execution finished
                else:
                    continue # Binary data
            
            # Get history to find outputs
            history = self.get_history(prompt_id)[prompt_id]
            outputs = history['outputs']
            
            results = {}
            for node_id, node_output in outputs.items():
                if 'gifs' in node_output:
                    results['gifs'] = node_output['gifs']
                if 'images' in node_output:
                    results['images'] = node_output['images']
                if 'videos' in node_output: # Some custom nodes output 'videos'
                    results['videos'] = node_output['videos']
                    
            return {"success": True, "outputs": results, "prompt_id": prompt_id}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.close()
