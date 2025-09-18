"""
file-storage-service - File Storage Service

Secure file upload, download, and management service
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import uuid
import shutil
from datetime import datetime
from pathlib import Path
import mimetypes
import hashlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="file-storage-service",
    description="Secure file upload, download, and management service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
ALLOWED_EXTENSIONS = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    "document": [".pdf", ".doc", ".docx", ".txt", ".rtf"],
    "archive": [".zip", ".rar", ".7z", ".tar", ".gz"],
    "video": [".mp4", ".avi", ".mov", ".wmv", ".flv"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg"]
}

# Create upload directory
UPLOAD_DIR.mkdir(exist_ok=True)

# Models
class FileMetadata(BaseModel):
    id: str
    filename: str
    original_filename: str
    content_type: str
    size: int
    file_type: str
    storage_path: str
    owner_id: Optional[str] = None
    is_public: bool = False
    created_at: datetime
    tags: List[str] = []
    checksum: str

class FileUploadResponse(BaseModel):
    id: str
    filename: str
    size: int
    content_type: str
    file_type: str
    message: str

class FileListResponse(BaseModel):
    files: List[FileMetadata]
    total: int
    limit: int
    offset: int

class ShareLinkResponse(BaseModel):
    file_id: str
    share_url: str
    expires_at: Optional[datetime] = None

# In-memory storage (use database in production)
files_db = {}
share_links = {}

# Utility functions
def get_file_type(filename: str) -> str:
    """Determine file type based on extension"""
    ext = Path(filename).suffix.lower()
    
    for file_type, extensions in ALLOWED_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    
    return "other"

def calculate_checksum(file_path: Path) -> str:
    """Calculate MD5 checksum of file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    ext = Path(filename).suffix.lower()
    all_extensions = []
    for extensions in ALLOWED_EXTENSIONS.values():
        all_extensions.extend(extensions)
    return ext in all_extensions

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[str]:
    """Get current user from token (simplified)"""
    # In production, validate token with auth service
    return "user123"  # Simulated user ID

# Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "file-storage-service",
        "version": "1.0.0",
        "status": "running",
        "description": "Secure file upload, download, and management service",
        "features": [
            "File upload/download",
            "File metadata management",
            "Access control",
            "File sharing",
            "Multiple file types support"
        ],
        "endpoints": {
            "upload": "/upload",
            "download": "/download/{file_id}",
            "files": "/files",
            "file_info": "/files/{file_id}",
            "delete": "/files/{file_id}",
            "share": "/files/{file_id}/share",
            "health": "/health"
        },
        "supported_types": list(ALLOWED_EXTENSIONS.keys()),
        "max_file_size": f"{MAX_FILE_SIZE / (1024*1024):.1f}MB"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "file-storage-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "stats": {
            "total_files": len(files_db),
            "storage_used": sum(f["size"] for f in files_db.values()),
            "upload_dir": str(UPLOAD_DIR),
            "max_file_size": MAX_FILE_SIZE
        }
    }

@app.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    is_public: bool = False,
    tags: str = "",
    current_user: str = Depends(get_current_user)
):
    """Upload a file"""
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )
    
    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Supported types: {list(ALLOWED_EXTENSIONS.keys())}"
        )
    
    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    file_extension = Path(file.filename).suffix
    unique_filename = f"{file_id}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Calculate checksum
        checksum = calculate_checksum(file_path)
        
        # Store metadata
        file_metadata = {
            "id": file_id,
            "filename": unique_filename,
            "original_filename": file.filename,
            "content_type": file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream",
            "size": len(content),
            "file_type": get_file_type(file.filename),
            "storage_path": str(file_path),
            "owner_id": current_user,
            "is_public": is_public,
            "created_at": datetime.utcnow(),
            "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
            "checksum": checksum
        }
        
        files_db[file_id] = file_metadata
        
        logger.info(f"File uploaded successfully: {file.filename} -> {file_id}")
        
        return FileUploadResponse(
            id=file_id,
            filename=file.filename,
            size=len(content),
            content_type=file_metadata["content_type"],
            file_type=file_metadata["file_type"],
            message="File uploaded successfully"
        )
        
    except Exception as e:
        # Clean up file if metadata storage fails
        if file_path.exists():
            file_path.unlink()
        
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file"
        )

@app.get("/download/{file_id}")
async def download_file(
    file_id: str,
    current_user: str = Depends(get_current_user)
):
    """Download a file"""
    
    file_metadata = files_db.get(file_id)
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions
    if not file_metadata["is_public"] and file_metadata["owner_id"] != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    file_path = Path(file_metadata["storage_path"])
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    return FileResponse(
        path=file_path,
        filename=file_metadata["original_filename"],
        media_type=file_metadata["content_type"]
    )

@app.get("/files", response_model=FileListResponse)
async def list_files(
    limit: int = 50,
    offset: int = 0,
    file_type: Optional[str] = None,
    current_user: str = Depends(get_current_user)
):
    """List user's files"""
    
    # Filter files by user and type
    user_files = []
    for file_metadata in files_db.values():
        if file_metadata["owner_id"] == current_user or file_metadata["is_public"]:
            if not file_type or file_metadata["file_type"] == file_type:
                user_files.append(FileMetadata(**file_metadata))
    
    # Apply pagination
    total = len(user_files)
    files_slice = user_files[offset:offset + limit]
    
    return FileListResponse(
        files=files_slice,
        total=total,
        limit=limit,
        offset=offset
    )

@app.get("/files/{file_id}")
async def get_file_info(
    file_id: str,
    current_user: str = Depends(get_current_user)
):
    """Get file metadata"""
    
    file_metadata = files_db.get(file_id)
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions
    if not file_metadata["is_public"] and file_metadata["owner_id"] != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return FileMetadata(**file_metadata)

@app.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: str = Depends(get_current_user)
):
    """Delete a file"""
    
    file_metadata = files_db.get(file_id)
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions
    if file_metadata["owner_id"] != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Delete file from disk
    file_path = Path(file_metadata["storage_path"])
    if file_path.exists():
        file_path.unlink()
    
    # Remove from database
    del files_db[file_id]
    
    logger.info(f"File deleted: {file_id}")
    
    return {"message": "File deleted successfully"}

@app.post("/files/{file_id}/share", response_model=ShareLinkResponse)
async def create_share_link(
    file_id: str,
    current_user: str = Depends(get_current_user)
):
    """Create a shareable link for a file"""
    
    file_metadata = files_db.get(file_id)
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Check permissions
    if file_metadata["owner_id"] != current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Generate share link
    share_token = str(uuid.uuid4())
    share_url = f"/shared/{share_token}"
    
    share_links[share_token] = {
        "file_id": file_id,
        "created_at": datetime.utcnow(),
        "created_by": current_user
    }
    
    return ShareLinkResponse(
        file_id=file_id,
        share_url=share_url
    )

@app.get("/shared/{share_token}")
async def download_shared_file(share_token: str):
    """Download file via share link"""
    
    share_info = share_links.get(share_token)
    if not share_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or expired"
        )
    
    file_id = share_info["file_id"]
    file_metadata = files_db.get(file_id)
    
    if not file_metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    file_path = Path(file_metadata["storage_path"])
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    return FileResponse(
        path=file_path,
        filename=file_metadata["original_filename"],
        media_type=file_metadata["content_type"]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True
    )