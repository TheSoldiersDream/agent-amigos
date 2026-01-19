"""
System Tools Module - System commands, processes, clipboard, and environment
"""
import os
import subprocess
import platform
import json
from typing import Optional, List, Dict
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False


class SystemTools:
    """System operations - commands, processes, clipboard"""
    
    def __init__(self):
        self.system = platform.system()
        self.is_windows = self.system == "Windows"
    
    # --- Command Execution ---
    
    def run_command(self, command: str, shell: bool = True, 
                    timeout: int = 60, cwd: Optional[str] = None) -> dict:
        """Execute a shell command"""
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            
            return {
                "success": True,
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout[:5000] if result.stdout else "",
                "stderr": result.stderr[:2000] if result.stderr else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Command timed out after {timeout} seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def run_powershell(self, script: str, timeout: int = 60) -> dict:
        """Execute a PowerShell script (Windows)"""
        if not self.is_windows:
            return {"success": False, "error": "PowerShell is only available on Windows"}
        
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "success": True,
                "script": script,
                "return_code": result.returncode,
                "stdout": result.stdout[:5000] if result.stdout else "",
                "stderr": result.stderr[:2000] if result.stderr else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Script timed out after {timeout} seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def start_program(
        self,
        path: Optional[str] = None,
        args: List[str] = None,
        wait: bool = False,
        program: Optional[str] = None,
    ) -> dict:
        """Start a program/application.

        Accepts either `path` (preferred) or `program` (legacy alias).
        """
        try:
            resolved_path = path or program
            if not resolved_path:
                return {"success": False, "error": "Missing required argument: path"}

            cmd = [resolved_path] + (args or [])
            
            if wait:
                result = subprocess.run(cmd, capture_output=True, text=True)
                return {
                    "success": True,
                    "path": resolved_path,
                    "return_code": result.returncode,
                    "stdout": result.stdout[:2000] if result.stdout else ""
                }
            else:
                if self.is_windows:
                    # Use startfile for Windows to open with default app
                    if args:
                        subprocess.Popen(cmd, shell=True)
                    else:
                        os.startfile(resolved_path)
                else:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                return {"success": True, "started": resolved_path, "args": args}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def open_file_with_app(self, file_path: str) -> dict:
        """Open a file with its default application"""
        try:
            file_path = os.path.abspath(file_path)
            if not os.path.exists(file_path):
                return {"success": False, "error": f"File not found: {file_path}"}
            
            if self.is_windows:
                os.startfile(file_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", file_path])
            else:
                subprocess.run(["xdg-open", file_path])
            
            return {"success": True, "opened": file_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Clipboard ---
    
    def copy_to_clipboard(self, text: str) -> dict:
        """Copy text to clipboard"""
        if not PYPERCLIP_AVAILABLE:
            # Fallback for Windows
            if self.is_windows:
                try:
                    subprocess.run(
                        ["powershell", "-Command", f"Set-Clipboard -Value '{text}'"],
                        check=True
                    )
                    return {"success": True, "copied": len(text)}
                except:
                    return {"success": False, "error": "pyperclip not installed. Run: pip install pyperclip"}
            return {"success": False, "error": "pyperclip not installed"}
        
        try:
            pyperclip.copy(text)
            return {"success": True, "copied": len(text)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def paste_from_clipboard(self) -> dict:
        """Get text from clipboard"""
        if not PYPERCLIP_AVAILABLE:
            if self.is_windows:
                try:
                    result = subprocess.run(
                        ["powershell", "-Command", "Get-Clipboard"],
                        capture_output=True,
                        text=True
                    )
                    return {"success": True, "content": result.stdout.strip()}
                except:
                    return {"success": False, "error": "pyperclip not installed"}
            return {"success": False, "error": "pyperclip not installed"}
        
        try:
            content = pyperclip.paste()
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- System Information ---
    
    def get_system_info(self) -> dict:
        """Get system information"""
        try:
            info = {
                "success": True,
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version()
            }
            
            if PSUTIL_AVAILABLE:
                info["cpu_count"] = psutil.cpu_count()
                info["memory_total_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
            
            return info
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_system_stats(self) -> dict:
        """Get current CPU, memory, disk usage"""
        if not PSUTIL_AVAILABLE:
            return {"success": False, "error": "psutil not installed. Run: pip install psutil"}
        
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                "success": True,
                "cpu_percent": cpu,
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "percent": disk.percent
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Process Management ---
    
    def list_processes(self, name_filter: Optional[str] = None) -> dict:
        """List running processes"""
        if not PSUTIL_AVAILABLE:
            return {"success": False, "error": "psutil not installed"}
        
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    if name_filter and name_filter.lower() not in info['name'].lower():
                        continue
                    processes.append({
                        "pid": info['pid'],
                        "name": info['name'],
                        "cpu": info['cpu_percent'],
                        "memory": round(info['memory_percent'], 2)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by memory usage
            processes.sort(key=lambda x: x['memory'], reverse=True)
            
            return {
                "success": True,
                "count": len(processes),
                "processes": processes[:50]  # Top 50
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def kill_process(self, pid: int = None, name: str = None) -> dict:
        """Kill a process by PID or name"""
        if not PSUTIL_AVAILABLE:
            return {"success": False, "error": "psutil not installed"}
        
        try:
            killed = []
            
            if pid:
                proc = psutil.Process(pid)
                proc.terminate()
                killed.append({"pid": pid, "name": proc.name()})
            elif name:
                for proc in psutil.process_iter(['pid', 'name']):
                    if name.lower() in proc.info['name'].lower():
                        proc.terminate()
                        killed.append({"pid": proc.info['pid'], "name": proc.info['name']})
            else:
                return {"success": False, "error": "Provide either pid or name"}
            
            return {"success": True, "killed": killed}
        except psutil.NoSuchProcess:
            return {"success": False, "error": f"Process not found: {pid or name}"}
        except psutil.AccessDenied:
            return {"success": False, "error": "Access denied. Run as administrator."}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Environment ---
    
    def get_env_var(self, name: str) -> dict:
        """Get an environment variable"""
        value = os.environ.get(name)
        return {
            "success": True,
            "name": name,
            "value": value,
            "exists": value is not None
        }
    
    def set_env_var(self, name: str, value: str) -> dict:
        """Set an environment variable (for current process)"""
        try:
            os.environ[name] = value
            return {"success": True, "name": name, "value": value}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_env_vars(self) -> dict:
        """List all environment variables"""
        return {
            "success": True,
            "count": len(os.environ),
            "variables": dict(os.environ)
        }
    
    # --- Notifications ---
    
    def show_notification(self, title: str, message: str) -> dict:
        """Show a system notification"""
        try:
            if self.is_windows:
                # Use PowerShell for Windows toast notification
                ps_script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
                $template = @"
                <toast>
                    <visual>
                        <binding template="ToastText02">
                            <text id="1">{title}</text>
                            <text id="2">{message}</text>
                        </binding>
                    </visual>
                </toast>
"@
                $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
                $xml.LoadXml($template)
                $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Agent Amigos").Show($toast)
                '''
                subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
                return {"success": True, "title": title, "message": message}
            else:
                # For Linux/Mac, use notify-send or osascript
                if platform.system() == "Darwin":
                    os.system(f'''osascript -e 'display notification "{message}" with title "{title}"' ''')
                else:
                    os.system(f'notify-send "{title}" "{message}"')
                return {"success": True, "title": title, "message": message}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Date/Time ---
    
    def get_datetime(self) -> dict:
        """Get current date and time"""
        now = datetime.now()
        return {
            "success": True,
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "day": now.strftime("%A"),
            "timezone": str(now.astimezone().tzinfo)
        }


# Singleton instance
system = SystemTools()
