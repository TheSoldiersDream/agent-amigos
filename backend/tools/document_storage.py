"""
Document Storage System for Agent Amigos
=========================================
Persistent storage for uploaded documents, images, videos, URLs, and plans.
Agents can store, retrieve, and learn from these documents across sessions.

Features:
- Store documents (PDFs, text, images, videos, URLs)
- Extract and index content for searching
- Track document usage and relevance
- Enable agents to reference stored documents in tasks
- Auto-extract text from PDFs and images (OCR)

Owner: Darrell Buttigieg
"""

import json
import os
import shutil
import hashlib
import base64
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import re
import mimetypes

# ═══════════════════════════════════════════════════════════════════════════════
# STORAGE PATHS
# ═══════════════════════════════════════════════════════════════════════════════

DOCUMENTS_DIR = Path(__file__).parent.parent / "data" / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Sub-directories for different content types
IMAGES_DIR = DOCUMENTS_DIR / "images"
VIDEOS_DIR = DOCUMENTS_DIR / "videos"
PDFS_DIR = DOCUMENTS_DIR / "pdfs"
TEXTS_DIR = DOCUMENTS_DIR / "texts"
URLS_DIR = DOCUMENTS_DIR / "urls"
PLANS_DIR = DOCUMENTS_DIR / "plans"

for d in [IMAGES_DIR, VIDEOS_DIR, PDFS_DIR, TEXTS_DIR, URLS_DIR, PLANS_DIR]:
    d.mkdir(exist_ok=True)

# Database file
DOCUMENT_DB_FILE = DOCUMENTS_DIR / "document_index.json"


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

DOCUMENT_TYPES = {
    "image": {
        "extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico"],
        "directory": IMAGES_DIR,
        "description": "Images and graphics"
    },
    "video": {
        "extensions": [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"],
        "directory": VIDEOS_DIR,
        "description": "Videos and animations"
    },
    "pdf": {
        "extensions": [".pdf"],
        "directory": PDFS_DIR,
        "description": "PDF documents"
    },
    "text": {
        "extensions": [".txt", ".md", ".json", ".xml", ".csv", ".html", ".htm", ".log", ".yaml", ".yml"],
        "directory": TEXTS_DIR,
        "description": "Text documents and data files"
    },
    "url": {
        "extensions": [],
        "directory": URLS_DIR,
        "description": "Saved URLs and web content"
    },
    "plan": {
        "extensions": [],
        "directory": PLANS_DIR,
        "description": "Project plans and strategies"
    }
}


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT STORAGE CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class DocumentStorage:
    """
    Central document storage system for all agents.
    Stores, indexes, and retrieves documents for learning and reference.
    """
    
    def __init__(self):
        self._db = self._load_database()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all directories exist."""
        for dtype, info in DOCUMENT_TYPES.items():
            info["directory"].mkdir(parents=True, exist_ok=True)
    
    def _load_database(self) -> Dict:
        """Load document index database."""
        if DOCUMENT_DB_FILE.exists():
            try:
                with open(DOCUMENT_DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading document database: {e}")
        
        # Default structure
        return {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "documents": {},
            "tags": {},
            "categories": {},
            "usage_stats": {},
            "search_index": {}
        }
    
    def _save_database(self):
        """Save document index database."""
        self._db["last_updated"] = datetime.now().isoformat()
        try:
            with open(DOCUMENT_DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._db, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving document database: {e}")
    
    def _generate_id(self, content: Union[str, bytes]) -> str:
        """Generate unique document ID."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:16]
    
    def _detect_type(self, filename: str = None, content_type: str = None) -> str:
        """Detect document type from filename or content type."""
        if filename:
            ext = Path(filename).suffix.lower()
            for dtype, info in DOCUMENT_TYPES.items():
                if ext in info["extensions"]:
                    return dtype
        
        if content_type:
            if "image" in content_type:
                return "image"
            elif "video" in content_type:
                return "video"
            elif "pdf" in content_type:
                return "pdf"
        
        return "text"
    
    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF file."""
        try:
            # Try PyPDF2 first
            try:
                import PyPDF2
                text = []
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text.append(page.extract_text() or "")
                return "\n".join(text)
            except ImportError:
                pass
            
            # Try pdfplumber
            try:
                import pdfplumber
                text = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text.append(page.extract_text() or "")
                return "\n".join(text)
            except ImportError:
                pass
            
            return f"[PDF file stored at: {file_path}. Install PyPDF2 or pdfplumber for text extraction]"
        except Exception as e:
            return f"[Error extracting PDF text: {e}]"
    
    def _extract_text_from_image(self, file_path: Path) -> str:
        """Extract text from image using OCR."""
        try:
            import pytesseract
            from PIL import Image
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip() if text.strip() else "[No text detected in image]"
        except ImportError:
            return "[Image stored. Install pytesseract for OCR text extraction]"
        except Exception as e:
            return f"[Error extracting image text: {e}]"
    
    def _build_search_index(self, doc_id: str, content: str):
        """Build search index for document."""
        if not content:
            return
        
        # Extract keywords
        words = re.findall(r'\b[a-zA-Z]{3,}\b', content.lower())
        stopwords = {'the', 'and', 'for', 'that', 'this', 'with', 'you', 'are', 'was', 'have', 'has', 
                    'not', 'but', 'can', 'all', 'will', 'just', 'been', 'from', 'they', 'their'}
        keywords = [w for w in words if w not in stopwords]
        
        # Add to search index
        for keyword in set(keywords):
            if keyword not in self._db["search_index"]:
                self._db["search_index"][keyword] = []
            if doc_id not in self._db["search_index"][keyword]:
                self._db["search_index"][keyword].append(doc_id)
    
    # ───────────────────────────────────────────────────────────────────────────
    # STORE DOCUMENTS
    # ───────────────────────────────────────────────────────────────────────────
    
    def store_file(
        self,
        file_path: str = None,
        file_content: bytes = None,
        filename: str = None,
        title: str = None,
        description: str = "",
        tags: List[str] = None,
        category: str = "general",
        source: str = "upload",
        agent: str = "amigos"
    ) -> Dict[str, Any]:
        """
        Store a file document (image, video, PDF, text, etc.)
        
        Args:
            file_path: Path to existing file to copy
            file_content: Raw file content (bytes)
            filename: Original filename
            title: Document title
            description: Document description
            tags: List of tags
            category: Document category
            source: Where this came from (upload, conversation, web)
            agent: Which agent stored this
            
        Returns:
            Document info dict with ID and status
        """
        tags = tags or []
        
        try:
            # Get file content and determine type
            if file_path:
                file_path = Path(file_path)
                if not file_path.exists():
                    return {"success": False, "error": f"File not found: {file_path}"}
                filename = filename or file_path.name
                with open(file_path, 'rb') as f:
                    file_content = f.read()
            
            if not file_content:
                return {"success": False, "error": "No file content provided"}
            
            if not filename:
                return {"success": False, "error": "Filename required"}
            
            # Detect document type
            doc_type = self._detect_type(filename)
            target_dir = DOCUMENT_TYPES[doc_type]["directory"]
            
            # Generate ID and save path
            doc_id = self._generate_id(file_content)
            ext = Path(filename).suffix.lower()
            safe_filename = f"{doc_id}{ext}"
            save_path = target_dir / safe_filename
            
            # Check if already exists
            if doc_id in self._db["documents"]:
                existing = self._db["documents"][doc_id]
                existing["access_count"] = existing.get("access_count", 0) + 1
                existing["last_accessed"] = datetime.now().isoformat()
                self._save_database()
                return {
                    "success": True,
                    "doc_id": doc_id,
                    "status": "already_exists",
                    "document": existing
                }
            
            # Save file
            with open(save_path, 'wb') as f:
                f.write(file_content)
            
            # Extract text content for indexing
            extracted_text = ""
            if doc_type == "pdf":
                extracted_text = self._extract_text_from_pdf(save_path)
            elif doc_type == "image":
                extracted_text = self._extract_text_from_image(save_path)
            elif doc_type == "text":
                try:
                    extracted_text = file_content.decode('utf-8')
                except:
                    extracted_text = "[Binary text file]"
            
            # Create document entry
            doc_entry = {
                "id": doc_id,
                "type": doc_type,
                "filename": filename,
                "safe_filename": safe_filename,
                "path": str(save_path),
                "title": title or filename,
                "description": description,
                "tags": tags,
                "category": category,
                "source": source,
                "stored_by": agent,
                "stored_at": datetime.now().isoformat(),
                "file_size": len(file_content),
                "extracted_text": extracted_text[:10000],  # Limit stored text
                "access_count": 0,
                "last_accessed": None,
                "metadata": {
                    "original_filename": filename,
                    "mime_type": mimetypes.guess_type(filename)[0]
                }
            }
            
            # Store in database
            self._db["documents"][doc_id] = doc_entry
            
            # Update tags index
            for tag in tags:
                if tag not in self._db["tags"]:
                    self._db["tags"][tag] = []
                self._db["tags"][tag].append(doc_id)
            
            # Update category index
            if category not in self._db["categories"]:
                self._db["categories"][category] = []
            self._db["categories"][category].append(doc_id)
            
            # Build search index
            search_content = f"{title or ''} {description} {' '.join(tags)} {extracted_text}"
            self._build_search_index(doc_id, search_content)
            
            self._save_database()
            
            return {
                "success": True,
                "doc_id": doc_id,
                "status": "stored",
                "document": doc_entry
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def store_url(
        self,
        url: str,
        title: str = None,
        description: str = "",
        content: str = "",
        tags: List[str] = None,
        category: str = "web",
        agent: str = "amigos"
    ) -> Dict[str, Any]:
        """
        Store a URL with optional scraped content.
        
        Args:
            url: The URL to store
            title: Page title
            description: Description of the content
            content: Scraped/extracted content from the URL
            tags: List of tags
            category: Category
            agent: Which agent stored this
        """
        tags = tags or []
        
        try:
            doc_id = self._generate_id(url)
            
            # Check if exists
            if doc_id in self._db["documents"]:
                existing = self._db["documents"][doc_id]
                existing["access_count"] = existing.get("access_count", 0) + 1
                existing["last_accessed"] = datetime.now().isoformat()
                # Update content if new content provided
                if content and len(content) > len(existing.get("extracted_text", "")):
                    existing["extracted_text"] = content[:20000]
                self._save_database()
                return {
                    "success": True,
                    "doc_id": doc_id,
                    "status": "already_exists",
                    "document": existing
                }
            
            # Save URL content to file
            url_file = URLS_DIR / f"{doc_id}.json"
            url_data = {
                "url": url,
                "title": title,
                "content": content,
                "scraped_at": datetime.now().isoformat()
            }
            with open(url_file, 'w', encoding='utf-8') as f:
                json.dump(url_data, f, indent=2)
            
            # Create document entry
            doc_entry = {
                "id": doc_id,
                "type": "url",
                "url": url,
                "path": str(url_file),
                "title": title or url,
                "description": description,
                "tags": tags,
                "category": category,
                "source": "web",
                "stored_by": agent,
                "stored_at": datetime.now().isoformat(),
                "extracted_text": content[:20000] if content else "",
                "access_count": 0,
                "last_accessed": None
            }
            
            self._db["documents"][doc_id] = doc_entry
            
            # Update indices
            for tag in tags:
                if tag not in self._db["tags"]:
                    self._db["tags"][tag] = []
                self._db["tags"][tag].append(doc_id)
            
            if category not in self._db["categories"]:
                self._db["categories"][category] = []
            self._db["categories"][category].append(doc_id)
            
            self._build_search_index(doc_id, f"{title or ''} {description} {content}")
            self._save_database()
            
            return {
                "success": True,
                "doc_id": doc_id,
                "status": "stored",
                "document": doc_entry
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def store_plan(
        self,
        title: str,
        content: str,
        plan_type: str = "general",
        tags: List[str] = None,
        category: str = "plans",
        agent: str = "amigos"
    ) -> Dict[str, Any]:
        """
        Store a plan or strategy document.
        
        Args:
            title: Plan title
            content: Plan content
            plan_type: Type of plan (project, strategy, workflow, etc.)
            tags: List of tags
            category: Category
            agent: Which agent stored this
        """
        tags = tags or []
        tags.append(f"plan_type:{plan_type}")
        
        try:
            doc_id = self._generate_id(f"{title}:{content[:500]}")
            
            # Save plan content to file
            plan_file = PLANS_DIR / f"{doc_id}.json"
            plan_data = {
                "title": title,
                "content": content,
                "plan_type": plan_type,
                "created_at": datetime.now().isoformat(),
                "version": 1,
                "history": []
            }
            with open(plan_file, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, indent=2)
            
            # Create document entry
            doc_entry = {
                "id": doc_id,
                "type": "plan",
                "path": str(plan_file),
                "title": title,
                "description": f"{plan_type} plan",
                "tags": tags,
                "category": category,
                "source": "agent",
                "stored_by": agent,
                "stored_at": datetime.now().isoformat(),
                "extracted_text": content,
                "plan_type": plan_type,
                "access_count": 0,
                "last_accessed": None
            }
            
            self._db["documents"][doc_id] = doc_entry
            
            # Update indices
            for tag in tags:
                if tag not in self._db["tags"]:
                    self._db["tags"][tag] = []
                self._db["tags"][tag].append(doc_id)
            
            if category not in self._db["categories"]:
                self._db["categories"][category] = []
            self._db["categories"][category].append(doc_id)
            
            self._build_search_index(doc_id, f"{title} {content}")
            self._save_database()
            
            return {
                "success": True,
                "doc_id": doc_id,
                "status": "stored",
                "document": doc_entry
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def store_text(
        self,
        content: str,
        title: str = None,
        description: str = "",
        tags: List[str] = None,
        category: str = "notes",
        agent: str = "amigos"
    ) -> Dict[str, Any]:
        """
        Store a text document or note.
        """
        tags = tags or []
        title = title or f"Note_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Store as text file
        doc_id = self._generate_id(content)
        text_file = TEXTS_DIR / f"{doc_id}.txt"
        
        try:
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            doc_entry = {
                "id": doc_id,
                "type": "text",
                "path": str(text_file),
                "title": title,
                "description": description,
                "tags": tags,
                "category": category,
                "source": "agent",
                "stored_by": agent,
                "stored_at": datetime.now().isoformat(),
                "extracted_text": content[:20000],
                "access_count": 0,
                "last_accessed": None
            }
            
            self._db["documents"][doc_id] = doc_entry
            self._build_search_index(doc_id, f"{title} {description} {content}")
            self._save_database()
            
            return {
                "success": True,
                "doc_id": doc_id,
                "status": "stored",
                "document": doc_entry
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ───────────────────────────────────────────────────────────────────────────
    # RETRIEVE DOCUMENTS
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get a document by ID."""
        doc = self._db["documents"].get(doc_id)
        if doc:
            doc["access_count"] = doc.get("access_count", 0) + 1
            doc["last_accessed"] = datetime.now().isoformat()
            self._save_database()
        return doc
    
    def get_document_content(self, doc_id: str) -> Optional[str]:
        """Get the text content of a document."""
        doc = self.get_document(doc_id)
        if not doc:
            return None
        
        # Return extracted text if available
        if doc.get("extracted_text"):
            return doc["extracted_text"]
        
        # Try to read from file
        file_path = Path(doc.get("path", ""))
        if file_path.exists():
            try:
                if doc["type"] == "text":
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                elif doc["type"] in ["url", "plan"]:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get("content", "")
            except Exception as e:
                return f"[Error reading content: {e}]"
        
        return None
    
    def get_document_file(self, doc_id: str) -> Optional[bytes]:
        """Get raw file content for a document."""
        doc = self.get_document(doc_id)
        if not doc:
            return None
        
        file_path = Path(doc.get("path", ""))
        if file_path.exists():
            with open(file_path, 'rb') as f:
                return f.read()
        return None
    
    def search_documents(
        self,
        query: str = None,
        doc_type: str = None,
        tags: List[str] = None,
        category: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search for documents.
        
        Args:
            query: Text search query
            doc_type: Filter by type (image, video, pdf, text, url, plan)
            tags: Filter by tags
            category: Filter by category
            limit: Max results
        """
        results = []
        
        # Get candidate document IDs
        candidates = set(self._db["documents"].keys())
        
        # Filter by type
        if doc_type:
            candidates = {doc_id for doc_id in candidates 
                         if self._db["documents"][doc_id].get("type") == doc_type}
        
        # Filter by tags
        if tags:
            for tag in tags:
                tag_docs = set(self._db["tags"].get(tag, []))
                candidates &= tag_docs
        
        # Filter by category
        if category:
            cat_docs = set(self._db["categories"].get(category, []))
            candidates &= cat_docs
        
        # Search by query
        if query:
            query_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', query.lower()))
            query_matches = set()
            for word in query_words:
                word_docs = self._db["search_index"].get(word, [])
                query_matches.update(word_docs)
            candidates &= query_matches
        
        # Build results
        for doc_id in candidates:
            doc = self._db["documents"].get(doc_id)
            if doc:
                results.append(doc)
        
        # Sort by access count and recency
        results.sort(key=lambda x: (
            x.get("access_count", 0),
            x.get("stored_at", "")
        ), reverse=True)
        
        return results[:limit]
    
    def get_recent_documents(self, limit: int = 10) -> List[Dict]:
        """Get recently stored documents."""
        docs = list(self._db["documents"].values())
        docs.sort(key=lambda x: x.get("stored_at", ""), reverse=True)
        return docs[:limit]
    
    def get_frequently_accessed(self, limit: int = 10) -> List[Dict]:
        """Get frequently accessed documents."""
        docs = list(self._db["documents"].values())
        docs.sort(key=lambda x: x.get("access_count", 0), reverse=True)
        return docs[:limit]
    
    def list_by_type(self, doc_type: str, limit: int = 50) -> List[Dict]:
        """List documents by type."""
        return self.search_documents(doc_type=doc_type, limit=limit)
    
    def list_by_tag(self, tag: str, limit: int = 50) -> List[Dict]:
        """List documents by tag."""
        return self.search_documents(tags=[tag], limit=limit)
    
    # ───────────────────────────────────────────────────────────────────────────
    # DELETE & MANAGE
    # ───────────────────────────────────────────────────────────────────────────
    
    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """Delete a document."""
        doc = self._db["documents"].get(doc_id)
        if not doc:
            return {"success": False, "error": "Document not found"}
        
        try:
            # Delete file
            file_path = Path(doc.get("path", ""))
            if file_path.exists():
                file_path.unlink()
            
            # Remove from indices
            for tag in doc.get("tags", []):
                if tag in self._db["tags"]:
                    self._db["tags"][tag] = [d for d in self._db["tags"][tag] if d != doc_id]
            
            category = doc.get("category")
            if category and category in self._db["categories"]:
                self._db["categories"][category] = [d for d in self._db["categories"][category] if d != doc_id]
            
            # Remove from search index
            for keyword, docs in self._db["search_index"].items():
                self._db["search_index"][keyword] = [d for d in docs if d != doc_id]
            
            # Remove from documents
            del self._db["documents"][doc_id]
            
            self._save_database()
            return {"success": True, "deleted": doc_id}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_document(self, doc_id: str, updates: Dict) -> Dict[str, Any]:
        """Update document metadata."""
        doc = self._db["documents"].get(doc_id)
        if not doc:
            return {"success": False, "error": "Document not found"}
        
        # Allowed updates
        allowed_fields = ["title", "description", "tags", "category"]
        for field in allowed_fields:
            if field in updates:
                doc[field] = updates[field]
        
        doc["updated_at"] = datetime.now().isoformat()
        self._save_database()
        
        return {"success": True, "document": doc}
    
    # ───────────────────────────────────────────────────────────────────────────
    # STATISTICS & INFO
    # ───────────────────────────────────────────────────────────────────────────
    
    def get_stats(self) -> Dict[str, Any]:
        """Get document storage statistics."""
        docs = self._db["documents"]
        
        type_counts = {}
        total_size = 0
        for doc in docs.values():
            dtype = doc.get("type", "unknown")
            type_counts[dtype] = type_counts.get(dtype, 0) + 1
            total_size += doc.get("file_size", 0)
        
        return {
            "total_documents": len(docs),
            "by_type": type_counts,
            "total_tags": len(self._db["tags"]),
            "categories": list(self._db["categories"].keys()),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "search_index_size": len(self._db["search_index"]),
            "storage_path": str(DOCUMENTS_DIR)
        }
    
    def get_context_for_task(self, task_description: str, limit: int = 5) -> str:
        """
        Get relevant document context for a task.
        Used by agents to reference stored documents.
        """
        relevant_docs = self.search_documents(query=task_description, limit=limit)
        
        if not relevant_docs:
            return ""
        
        context_parts = ["Relevant stored documents:"]
        for doc in relevant_docs:
            title = doc.get("title", "Untitled")
            dtype = doc.get("type", "unknown")
            excerpt = doc.get("extracted_text", "")[:300]
            context_parts.append(f"\n• [{dtype}] {title}:\n  {excerpt}...")
        
        return "\n".join(context_parts)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

document_storage = DocumentStorage()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS FOR AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

def store_document(file_path: str = None, file_content: bytes = None, filename: str = None,
                   title: str = None, tags: List[str] = None, category: str = "general") -> Dict:
    """Quick helper to store a document."""
    return document_storage.store_file(
        file_path=file_path,
        file_content=file_content,
        filename=filename,
        title=title,
        tags=tags,
        category=category
    )

def store_url_content(url: str, title: str = None, content: str = "", tags: List[str] = None) -> Dict:
    """Quick helper to store a URL."""
    return document_storage.store_url(url=url, title=title, content=content, tags=tags)

def store_plan_document(title: str, content: str, plan_type: str = "general") -> Dict:
    """Quick helper to store a plan."""
    return document_storage.store_plan(title=title, content=content, plan_type=plan_type)

def find_documents(query: str, doc_type: str = None, limit: int = 10) -> List[Dict]:
    """Quick helper to search documents."""
    return document_storage.search_documents(query=query, doc_type=doc_type, limit=limit)

def get_doc(doc_id: str) -> Optional[Dict]:
    """Quick helper to get a document."""
    return document_storage.get_document(doc_id)

def get_doc_content(doc_id: str) -> Optional[str]:
    """Quick helper to get document content."""
    return document_storage.get_document_content(doc_id)

def get_relevant_docs(task: str, limit: int = 5) -> str:
    """Quick helper to get relevant document context for a task."""
    return document_storage.get_context_for_task(task, limit)

def get_document_stats() -> Dict:
    """Quick helper to get storage stats."""
    return document_storage.get_stats()
