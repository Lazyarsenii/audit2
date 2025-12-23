"""
File System Browse API
Allows browsing local directories for repository selection
"""
import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/browse", tags=["browse"])


class DirectoryItem(BaseModel):
    name: str
    path: str
    is_dir: bool
    is_git: bool = False  # True if contains .git folder
    size: Optional[int] = None


class BrowseResponse(BaseModel):
    current_path: str
    parent_path: Optional[str]
    items: List[DirectoryItem]
    is_git_repo: bool = False


@router.get("", response_model=BrowseResponse)
async def browse_directory(
    path: str = Query(default="~", description="Path to browse"),
    show_hidden: bool = Query(default=False, description="Show hidden files/folders"),
    dirs_only: bool = Query(default=True, description="Show only directories"),
):
    """
    Browse a directory and return its contents.
    Returns list of directories (and optionally files) with metadata.
    """
    # Expand ~ to home directory
    if path == "~" or path.startswith("~/"):
        path = os.path.expanduser(path)

    # Resolve to absolute path
    try:
        resolved_path = Path(path).resolve()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

    # Security check - prevent accessing system directories
    forbidden_paths = ["/etc", "/var", "/usr", "/bin", "/sbin", "/lib", "/boot", "/root"]
    if any(str(resolved_path).startswith(fp) for fp in forbidden_paths):
        raise HTTPException(status_code=403, detail="Access to this directory is not allowed")

    # Check if path exists
    if not resolved_path.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {resolved_path}")

    # Check if path is a directory
    if not resolved_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {resolved_path}")

    # Get parent path
    parent_path = str(resolved_path.parent) if resolved_path != resolved_path.parent else None

    # Check if current directory is a git repo
    is_git_repo = (resolved_path / ".git").exists()

    # List directory contents
    items: List[DirectoryItem] = []

    try:
        for entry in sorted(resolved_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files if not requested
            if not show_hidden and entry.name.startswith("."):
                continue

            # Skip files if dirs_only
            if dirs_only and not entry.is_dir():
                continue

            # Check if directory contains .git (is a git repo)
            is_git = False
            if entry.is_dir():
                is_git = (entry / ".git").exists()

            # Get file size for files
            size = None
            if not entry.is_dir():
                try:
                    size = entry.stat().st_size
                except:
                    pass

            items.append(DirectoryItem(
                name=entry.name,
                path=str(entry),
                is_dir=entry.is_dir(),
                is_git=is_git,
                size=size,
            ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied to access this directory")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading directory: {str(e)}")

    return BrowseResponse(
        current_path=str(resolved_path),
        parent_path=parent_path,
        items=items,
        is_git_repo=is_git_repo,
    )


@router.get("/home", response_model=BrowseResponse)
async def browse_home():
    """Get contents of home directory"""
    return await browse_directory(path="~", show_hidden=False, dirs_only=True)


@router.get("/quick-paths")
async def get_quick_paths():
    """
    Get common paths for quick navigation
    """
    home = os.path.expanduser("~")

    quick_paths = [
        {"name": "Home", "path": home, "icon": "home"},
        {"name": "Desktop", "path": os.path.join(home, "Desktop"), "icon": "desktop"},
        {"name": "Documents", "path": os.path.join(home, "Documents"), "icon": "folder"},
        {"name": "Downloads", "path": os.path.join(home, "Downloads"), "icon": "download"},
    ]

    # Add common development directories if they exist
    dev_paths = [
        ("Projects", os.path.join(home, "Projects")),
        ("Developer", os.path.join(home, "Developer")),
        ("Code", os.path.join(home, "Code")),
        ("repos", os.path.join(home, "repos")),
        ("workspace", os.path.join(home, "workspace")),
    ]

    for name, path in dev_paths:
        if os.path.exists(path):
            quick_paths.append({"name": name, "path": path, "icon": "code"})

    return {"paths": quick_paths}
