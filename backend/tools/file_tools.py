"""
File Tools Module - File system operations
Read, write, create, delete, move files and directories
"""
import os
import shutil
import json
import glob
from typing import Optional, List
from datetime import datetime


class FileTools:
    """File system operations"""
    
    def __init__(self):
        self.allowed_extensions = None  # None = allow all
        # Get the backend directory (where this file lives)
        self.backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def _resolve_path(self, path: str) -> str:
        """Resolve path, handling relative paths intelligently"""
        # If already absolute, use as-is
        if os.path.isabs(path):
            return path
        
        # If path starts with 'backend/' and we're in the backend dir, strip it
        if path.startswith('backend/') or path.startswith('backend\\'):
            # Check if we're already in the backend directory
            cwd = os.getcwd()
            if os.path.basename(cwd) == 'backend' or cwd.endswith('backend'):
                # Strip the leading 'backend/' since we're already there
                path = path[8:]  # len('backend/') = 8
        
        # For paths starting with 'data/', resolve from backend dir
        if path.startswith('data/') or path.startswith('data\\'):
            return os.path.join(self.backend_dir, path)
        
        return os.path.abspath(path)
    
    # --- Read Operations ---
    
    def read_file(self, path: str, encoding: str = "utf-8") -> dict:
        """Read contents of a file (supports txt, pdf, docx)"""
        try:
            path = self._resolve_path(path)
            if not os.path.exists(path):
                return {"success": False, "error": f"File not found: {path}"}
            
            ext = os.path.splitext(path)[1].lower()
            
            # Handle PDF
            if ext == '.pdf':
                try:
                    import PyPDF2
                    text = []
                    with open(path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        for page in reader.pages:
                            text.append(page.extract_text() or "")
                    content = "\n".join(text)
                    return {
                        "success": True,
                        "path": path,
                        "content": content,
                        "size": len(content),
                        "lines": content.count("\n") + 1,
                        "type": "pdf"
                    }
                except ImportError:
                    return {"success": False, "error": "PyPDF2 not installed"}
                except Exception as e:
                    return {"success": False, "error": f"Error reading PDF: {str(e)}"}

            # Handle DOCX
            if ext == '.docx':
                try:
                    import docx
                    doc = docx.Document(path)
                    content = "\n".join([para.text for para in doc.paragraphs])
                    return {
                        "success": True,
                        "path": path,
                        "content": content,
                        "size": len(content),
                        "lines": content.count("\n") + 1,
                        "type": "docx"
                    }
                except ImportError:
                    return {"success": False, "error": "python-docx not installed"}
                except Exception as e:
                    return {"success": False, "error": f"Error reading DOCX: {str(e)}"}

            with open(path, "r", encoding=encoding) as f:
                content = f.read()
            
            return {
                "success": True,
                "path": path,
                "content": content,
                "size": len(content),
                "lines": content.count("\n") + 1
            }
        except UnicodeDecodeError:
            # Try reading as binary
            try:
                with open(path, "rb") as f:
                    content = f.read()
                return {
                    "success": True,
                    "path": path,
                    "content": f"[Binary file: {len(content)} bytes]",
                    "size": len(content),
                    "binary": True
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def read_lines(self, path: str, start: int = 0, count: int = 100) -> dict:
        """Read specific lines from a file"""
        try:
            path = self._resolve_path(path)
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            selected = lines[start:start + count]
            return {
                "success": True,
                "path": path,
                "lines": selected,
                "start": start,
                "count": len(selected),
                "total_lines": len(lines)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def file_exists(self, path: str) -> dict:
        """Check if a file exists"""
        path = self._resolve_path(path)
        exists = os.path.exists(path)
        is_file = os.path.isfile(path) if exists else False
        is_dir = os.path.isdir(path) if exists else False
        return {
            "success": True,
            "path": path,
            "exists": exists,
            "is_file": is_file,
            "is_directory": is_dir
        }
    
    def get_file_info(self, path: str) -> dict:
        """Get detailed file information"""
        try:
            path = self._resolve_path(path)
            if not os.path.exists(path):
                return {"success": False, "error": f"Path not found: {path}"}
            
            stat = os.stat(path)
            return {
                "success": True,
                "path": path,
                "name": os.path.basename(path),
                "directory": os.path.dirname(path),
                "extension": os.path.splitext(path)[1],
                "size_bytes": stat.st_size,
                "size_human": self._human_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "is_file": os.path.isfile(path),
                "is_directory": os.path.isdir(path)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_directory(self, path: str, pattern: str = "*", 
                       include_hidden: bool = False) -> dict:
        """List contents of a directory"""
        try:
            path = self._resolve_path(path)
            if not os.path.isdir(path):
                return {"success": False, "error": f"Not a directory: {path}"}
            
            items = []
            for item in os.listdir(path):
                if not include_hidden and item.startswith("."):
                    continue
                
                # Apply pattern filter
                if pattern != "*" and not glob.fnmatch.fnmatch(item, pattern):
                    continue
                
                full_path = os.path.join(path, item)
                is_dir = os.path.isdir(full_path)
                size = os.path.getsize(full_path) if not is_dir else 0
                
                items.append({
                    "name": item,
                    "type": "directory" if is_dir else "file",
                    "size": size,
                    "size_human": self._human_size(size) if not is_dir else "-"
                })
            
            # Sort: directories first, then files
            items.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
            
            return {
                "success": True,
                "path": path,
                "count": len(items),
                "items": items
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_files(self, directory: str, pattern: str, recursive: bool = True) -> dict:
        """Search for files matching a pattern"""
        try:
            directory = self._resolve_path(directory)
            if recursive:
                search_pattern = os.path.join(directory, "**", pattern)
                matches = glob.glob(search_pattern, recursive=True)
            else:
                search_pattern = os.path.join(directory, pattern)
                matches = glob.glob(search_pattern)
            
            return {
                "success": True,
                "directory": directory,
                "pattern": pattern,
                "recursive": recursive,
                "count": len(matches),
                "files": matches[:100]  # Limit to 100 results
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_in_files(self, directory: str, search_text: str, 
                        pattern: str = "*.txt", case_sensitive: bool = False) -> dict:
        """Search for text within files"""
        try:
            directory = os.path.abspath(directory)
            matches = []
            search_pattern = os.path.join(directory, "**", pattern)
            
            if not case_sensitive:
                search_text = search_text.lower()
            
            for file_path in glob.glob(search_pattern, recursive=True):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            search_line = line if case_sensitive else line.lower()
                            if search_text in search_line:
                                matches.append({
                                    "file": file_path,
                                    "line": line_num,
                                    "content": line.strip()[:200]
                                })
                                if len(matches) >= 50:  # Limit results
                                    break
                except:
                    continue
                
                if len(matches) >= 50:
                    break
            
            return {
                "success": True,
                "search_text": search_text,
                "count": len(matches),
                "matches": matches
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Write Operations ---
    
    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> dict:
        """Write content to a file (overwrites existing)"""
        try:
            path = os.path.abspath(path)
            # Create directory if needed
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, "w", encoding=encoding) as f:
                f.write(content)
            
            return {
                "success": True,
                "path": path,
                "size": len(content),
                "lines": content.count("\n") + 1
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def append_file(self, path: str, content: str, encoding: str = "utf-8") -> dict:
        """Append content to a file"""
        try:
            path = os.path.abspath(path)
            with open(path, "a", encoding=encoding) as f:
                f.write(content)
            
            return {"success": True, "path": path, "appended": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_file(self, path: str, content: str = "") -> dict:
        """Create a new file (fails if exists)"""
        try:
            path = os.path.abspath(path)
            if os.path.exists(path):
                return {"success": False, "error": f"File already exists: {path}"}
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return {"success": True, "path": path, "created": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_directory(self, path: str) -> dict:
        """Create a directory"""
        try:
            path = os.path.abspath(path)
            os.makedirs(path, exist_ok=True)
            return {"success": True, "path": path, "created": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Modify Operations ---
    
    def copy_file(self, source: str, destination: str) -> dict:
        """Copy a file"""
        try:
            source = os.path.abspath(source)
            destination = os.path.abspath(destination)
            
            if not os.path.exists(source):
                return {"success": False, "error": f"Source not found: {source}"}
            
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source, destination)
            
            return {"success": True, "source": source, "destination": destination}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def move_file(self, source: str, destination: str) -> dict:
        """Move/rename a file"""
        try:
            source = os.path.abspath(source)
            destination = os.path.abspath(destination)
            
            if not os.path.exists(source):
                return {"success": False, "error": f"Source not found: {source}"}
            
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.move(source, destination)
            
            return {"success": True, "source": source, "destination": destination}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def rename(self, path: str, new_name: str) -> dict:
        """Rename a file or directory"""
        try:
            path = os.path.abspath(path)
            new_path = os.path.join(os.path.dirname(path), new_name)
            
            if not os.path.exists(path):
                return {"success": False, "error": f"Path not found: {path}"}
            
            os.rename(path, new_path)
            return {"success": True, "old_path": path, "new_path": new_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_file(self, path: str) -> dict:
        """Delete a file"""
        try:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                return {"success": False, "error": f"File not found: {path}"}
            
            if os.path.isdir(path):
                return {"success": False, "error": f"Path is a directory. Use delete_directory instead."}
            
            os.remove(path)
            return {"success": True, "deleted": path}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_directory(self, path: str, recursive: bool = False) -> dict:
        """Delete a directory"""
        try:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                return {"success": False, "error": f"Directory not found: {path}"}
            
            if not os.path.isdir(path):
                return {"success": False, "error": f"Path is not a directory: {path}"}
            
            if recursive:
                shutil.rmtree(path)
            else:
                os.rmdir(path)  # Only works on empty directories
            
            return {"success": True, "deleted": path, "recursive": recursive}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # --- Utility ---
    
    def _human_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(size_bytes) < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def get_current_directory(self) -> dict:
        """Get current working directory"""
        return {"success": True, "cwd": os.getcwd()}
    
    def change_directory(self, path: str) -> dict:
        """Change current working directory"""
        try:
            path = os.path.abspath(path)
            if not os.path.isdir(path):
                return {"success": False, "error": f"Not a directory: {path}"}
            os.chdir(path)
            return {"success": True, "cwd": os.getcwd()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # SECRETARY FUNCTIONS - Document creation, memos, drafts, notes
    # ------------------------------------------------------------------
    
    def _get_documents_dir(self) -> str:
        """Get user's Documents folder, create secretary subfolder"""
        docs = os.path.join(os.path.expanduser("~"), "Documents", "AgentAmigos")
        os.makedirs(docs, exist_ok=True)
        return docs
    
    def _get_secretary_subdir(self, subdir: str) -> str:
        """Get or create a secretary subdirectory"""
        path = os.path.join(self._get_documents_dir(), subdir)
        os.makedirs(path, exist_ok=True)
        return path
    
    def create_document(
        self,
        title: str,
        content: str,
        doc_type: str = "document",
        folder: Optional[str] = None
    ) -> dict:
        """
        Create a document with proper formatting.
        
        Args:
            title: Document title
            content: Document content/body
            doc_type: Type of document (document, letter, report, proposal)
            folder: Optional subfolder to save in
        """
        try:
            timestamp = datetime.now()
            date_str = timestamp.strftime("%Y-%m-%d")
            time_str = timestamp.strftime("%I:%M %p")
            
            # Build formatted document
            if doc_type == "letter":
                formatted = f"""
{'='*60}
                        LETTER
{'='*60}

Date: {date_str}

{content}


Sincerely,
Darrell Buttigieg

{'='*60}
Created by Agent Amigos on {date_str} at {time_str}
"""
            elif doc_type == "report":
                formatted = f"""
{'='*60}
                    {title.upper()}
                        REPORT
{'='*60}

Date: {date_str}
Author: Darrell Buttigieg

{'-'*60}

{content}

{'-'*60}
End of Report

{'='*60}
Generated by Agent Amigos on {date_str} at {time_str}
"""
            elif doc_type == "proposal":
                formatted = f"""
{'='*60}
                    PROPOSAL
            {title}
{'='*60}

Prepared by: Darrell Buttigieg
Date: {date_str}

{'─'*60}
EXECUTIVE SUMMARY
{'─'*60}

{content}

{'─'*60}

Thank you for your consideration.

{'='*60}
Document created by Agent Amigos on {date_str} at {time_str}
"""
            else:
                # Standard document
                formatted = f"""
{'='*60}
{title.upper()}
{'='*60}

Date: {date_str}

{content}

{'='*60}
Created by Agent Amigos on {date_str} at {time_str}
"""
            
            # Determine save location
            if folder:
                save_dir = self._get_secretary_subdir(folder)
            else:
                save_dir = self._get_secretary_subdir("Documents")
            
            # Create filename
            safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in title)
            safe_title = safe_title.replace(' ', '_')[:50]
            filename = f"{safe_title}_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(save_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted)
            
            return {
                "success": True,
                "path": filepath,
                "title": title,
                "type": doc_type,
                "created": timestamp.isoformat(),
                "message": f"Document '{title}' saved to {filepath}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def take_memo(
        self,
        subject: str,
        content: str,
        priority: str = "normal",
        recipient: Optional[str] = None
    ) -> dict:
        """
        Create a memo/quick note.
        
        Args:
            subject: Memo subject line
            content: Memo content
            priority: Priority level (low, normal, high, urgent)
            recipient: Optional recipient name
        """
        try:
            timestamp = datetime.now()
            date_str = timestamp.strftime("%Y-%m-%d")
            time_str = timestamp.strftime("%I:%M %p")
            
            priority_emoji = {
                "low": "🟢",
                "normal": "🔵", 
                "high": "🟠",
                "urgent": "🔴"
            }.get(priority.lower(), "🔵")
            
            memo = f"""
┌{'─'*58}┐
│  MEMO {priority_emoji} [{priority.upper()}]
├{'─'*58}┤
│  Date: {date_str} {time_str}
│  From: Darrell Buttigieg
│  To: {recipient or 'Self'}
│  Subject: {subject}
├{'─'*58}┤

{content}

└{'─'*58}┘
"""
            
            save_dir = self._get_secretary_subdir("Memos")
            safe_subject = "".join(c if c.isalnum() or c in ' -_' else '' for c in subject)
            safe_subject = safe_subject.replace(' ', '_')[:40]
            filename = f"memo_{safe_subject}_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(save_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(memo)
            
            return {
                "success": True,
                "path": filepath,
                "subject": subject,
                "priority": priority,
                "created": timestamp.isoformat(),
                "message": f"Memo saved: {subject}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def write_draft(
        self,
        title: str,
        content: str,
        draft_type: str = "general",
        notes: Optional[str] = None
    ) -> dict:
        """
        Save a draft for later editing.
        
        Args:
            title: Draft title
            content: Draft content
            draft_type: Type (email, post, article, speech, general)
            notes: Optional notes about the draft
        """
        try:
            timestamp = datetime.now()
            
            draft = f"""
╔{'═'*58}╗
║  DRAFT - {draft_type.upper()}
║  Status: Work in Progress
╠{'═'*58}╣
║  Title: {title}
║  Created: {timestamp.strftime('%Y-%m-%d %I:%M %p')}
║  Last Modified: {timestamp.strftime('%Y-%m-%d %I:%M %p')}
╚{'═'*58}╝

{'─'*60}
CONTENT:
{'─'*60}

{content}

"""
            if notes:
                draft += f"""
{'─'*60}
NOTES/TODO:
{'─'*60}
{notes}

"""
            draft += f"""
{'─'*60}
[Draft saved by Agent Amigos]
"""
            
            save_dir = self._get_secretary_subdir("Drafts")
            safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in title)
            safe_title = safe_title.replace(' ', '_')[:40]
            filename = f"draft_{draft_type}_{safe_title}_{timestamp.strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = os.path.join(save_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(draft)
            
            return {
                "success": True,
                "path": filepath,
                "title": title,
                "type": draft_type,
                "created": timestamp.isoformat(),
                "message": f"Draft saved: {title}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def quick_note(self, note: str, category: str = "general") -> dict:
        """
        Quickly jot down a note.
        
        Args:
            note: The note content
            category: Category for organization (ideas, tasks, reminders, general)
        """
        try:
            timestamp = datetime.now()
            
            # Append to daily notes file
            save_dir = self._get_secretary_subdir("Notes")
            date_str = timestamp.strftime('%Y-%m-%d')
            filename = f"notes_{date_str}.txt"
            filepath = os.path.join(save_dir, filename)
            
            entry = f"""
[{timestamp.strftime('%I:%M %p')}] [{category.upper()}]
{note}
{'─'*40}
"""
            
            # Create or append
            mode = 'a' if os.path.exists(filepath) else 'w'
            if mode == 'w':
                header = f"""
{'='*60}
NOTES FOR {date_str}
{'='*60}

"""
                entry = header + entry
            
            with open(filepath, mode, encoding='utf-8') as f:
                f.write(entry)
            
            return {
                "success": True,
                "path": filepath,
                "category": category,
                "time": timestamp.strftime('%I:%M %p'),
                "message": f"Note added to {filename}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_meeting_notes(
        self,
        meeting_title: str,
        attendees: List[str],
        agenda: List[str],
        notes: str,
        action_items: Optional[List[str]] = None,
        next_meeting: Optional[str] = None
    ) -> dict:
        """
        Create formatted meeting notes.
        
        Args:
            meeting_title: Title of the meeting
            attendees: List of attendee names
            agenda: List of agenda items
            notes: Meeting notes/discussion
            action_items: Optional list of action items
            next_meeting: Optional next meeting date/time
        """
        try:
            timestamp = datetime.now()
            
            attendees_str = "\n".join(f"  • {a}" for a in attendees)
            agenda_str = "\n".join(f"  {i+1}. {item}" for i, item in enumerate(agenda))
            
            doc = f"""
╔{'═'*58}╗
║              MEETING NOTES
╚{'═'*58}╝

Meeting: {meeting_title}
Date: {timestamp.strftime('%A, %B %d, %Y')}
Time: {timestamp.strftime('%I:%M %p')}

{'─'*60}
ATTENDEES:
{'─'*60}
{attendees_str}

{'─'*60}
AGENDA:
{'─'*60}
{agenda_str}

{'─'*60}
DISCUSSION NOTES:
{'─'*60}
{notes}

"""
            if action_items:
                action_str = "\n".join(f"  ☐ {item}" for item in action_items)
                doc += f"""
{'─'*60}
ACTION ITEMS:
{'─'*60}
{action_str}

"""
            if next_meeting:
                doc += f"""
{'─'*60}
NEXT MEETING: {next_meeting}
{'─'*60}

"""
            doc += f"""
{'═'*60}
Notes taken by Agent Amigos
{timestamp.strftime('%Y-%m-%d %I:%M %p')}
"""
            
            save_dir = self._get_secretary_subdir("Meetings")
            safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in meeting_title)
            safe_title = safe_title.replace(' ', '_')[:40]
            filename = f"meeting_{safe_title}_{timestamp.strftime('%Y%m%d')}.txt"
            filepath = os.path.join(save_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(doc)
            
            return {
                "success": True,
                "path": filepath,
                "title": meeting_title,
                "attendees_count": len(attendees),
                "action_items_count": len(action_items) if action_items else 0,
                "message": f"Meeting notes saved: {meeting_title}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_todo_list(
        self,
        title: str,
        items: List[str],
        priority_items: Optional[List[int]] = None
    ) -> dict:
        """
        Create a to-do list.
        
        Args:
            title: List title
            items: List of to-do items
            priority_items: Optional indices of high-priority items (0-based)
        """
        try:
            timestamp = datetime.now()
            priority_set = set(priority_items) if priority_items else set()
            
            items_str = ""
            for i, item in enumerate(items):
                marker = "⭐" if i in priority_set else "☐"
                items_str += f"  {marker} {item}\n"
            
            doc = f"""
┌{'─'*58}┐
│  TO-DO LIST: {title}
│  Created: {timestamp.strftime('%Y-%m-%d %I:%M %p')}
├{'─'*58}┤

{items_str}
├{'─'*58}┤
│  ☐ = Pending  ☑ = Done  ⭐ = Priority
└{'─'*58}┘
"""
            
            save_dir = self._get_secretary_subdir("TodoLists")
            safe_title = "".join(c if c.isalnum() or c in ' -_' else '' for c in title)
            safe_title = safe_title.replace(' ', '_')[:40]
            filename = f"todo_{safe_title}_{timestamp.strftime('%Y%m%d')}.txt"
            filepath = os.path.join(save_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(doc)
            
            return {
                "success": True,
                "path": filepath,
                "title": title,
                "items_count": len(items),
                "priority_count": len(priority_set),
                "message": f"To-do list created: {title}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def list_secretary_files(self, folder: Optional[str] = None) -> dict:
        """
        List all secretary-created files.
        
        Args:
            folder: Optional specific folder (Documents, Memos, Drafts, Notes, Meetings, TodoLists)
        """
        try:
            base_dir = self._get_documents_dir()
            
            if folder:
                search_dir = os.path.join(base_dir, folder)
                if not os.path.exists(search_dir):
                    return {"success": True, "files": [], "message": f"No {folder} folder yet"}
                folders_to_scan = [folder]
            else:
                folders_to_scan = ["Documents", "Memos", "Drafts", "Notes", "Meetings", "TodoLists"]
            
            files = []
            for folder_name in folders_to_scan:
                folder_path = os.path.join(base_dir, folder_name)
                if os.path.exists(folder_path):
                    for filename in os.listdir(folder_path):
                        filepath = os.path.join(folder_path, filename)
                        if os.path.isfile(filepath):
                            stat = os.stat(filepath)
                            files.append({
                                "name": filename,
                                "folder": folder_name,
                                "path": filepath,
                                "size": self._human_size(stat.st_size),
                                "modified": datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %I:%M %p')
                            })
            
            # Sort by modified date, newest first
            files.sort(key=lambda x: x["modified"], reverse=True)
            
            return {
                "success": True,
                "base_directory": base_dir,
                "files": files,
                "count": len(files)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton instance
files = FileTools()
