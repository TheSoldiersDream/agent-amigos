import os
from datetime import datetime
from typing import Dict, Any, Optional

class ReportTools:
    def __init__(self):
        # Use absolute path relative to this file
        self.reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "media_outputs", "reports")
        os.makedirs(self.reports_dir, exist_ok=True)

    def write_report(self, title: str, content: str, filename: Optional[str] = None, format: str = "markdown") -> Dict[str, Any]:
        """
        Write a report to a file in the media_outputs/reports directory.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if not filename:
                safe_title = "".join([c if c.isalnum() else "_" for c in title])
                filename = f"{safe_title}_{timestamp}"
            
            if format.lower() in ["markdown", "md"]:
                if not filename.endswith(".md"):
                    filename += ".md"
                
                full_content = f"# {title}\n\nDate: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n{content}"
                
                filepath = os.path.join(self.reports_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(full_content)
                    
                return {
                    "success": True, 
                    "filepath": filepath, 
                    "filename": filename, 
                    "format": "markdown",
                    "url": f"/media/reports/{filename}" # Assuming we'll serve this
                }
            
            elif format.lower() == "html":
                if not filename.endswith(".html"):
                    filename += ".html"
                
                html_content = f"""
                <html>
                <head>
                    <title>{title}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                        h1 {{ color: #333; }}
                        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; white-space: pre-wrap; }}
                        .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
                    </style>
                </head>
                <body>
                    <h1>{title}</h1>
                    <div class="meta">Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                    <hr>
                    <div class="content">
                        {content.replace(chr(10), '<br>')}
                    </div>
                </body>
                </html>
                """
                filepath = os.path.join(self.reports_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_content)
                    
                return {
                    "success": True, 
                    "filepath": filepath, 
                    "filename": filename, 
                    "format": "html",
                    "url": f"/media/reports/{filename}"
                }
            
            else:
                return {"success": False, "error": f"Unsupported format: {format}. Use 'markdown' or 'html'."}

        except Exception as e:
            return {"success": False, "error": str(e)}

report_tools = ReportTools()
