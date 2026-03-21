r"""
Archive and Reset Tool for Obsidian Vault

Moves all markdown files from content folders to 99-Archive and re-indexes vault.
Follows Vault Constitution containment policy.

Usage:
    python archive_and_reset.py <vault_root> [--dry-run]

Example (run from vault root):
    python "00 - System\\.agent\\tools\\archive_and_reset.py" .
    python "00 - System\\.agent\\tools\\archive_and_reset.py" . --dry-run
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import (
    VAULT_ROOT, PYTHON_EXE, FAISS_STORE, MODEL_PATH,
    ARCHIVE_DIR,
)

# Folders to archive
SOURCE_FOLDERS = [
    "02 - Sources",
    "03 - Research",
    "04 - Evergreen", 
    "05 - Maps",
    "06 - Projects",
    "07 - Writing"
]

ARCHIVE_FOLDER = "99 - Archive"


def find_markdown_files(vault_root, folders):
    """Find all .md files in specified folders."""
    files_by_folder = {}
    
    for folder in folders:
        folder_path = Path(vault_root) / folder
        if not folder_path.exists():
            continue
            
        md_files = list(folder_path.rglob("*.md"))
        if md_files:
            files_by_folder[folder] = md_files
    
    return files_by_folder


def archive_files(vault_root, files_by_folder, dry_run=False):
    """Move files to archive with timestamp-based organization."""
    vault_path = Path(vault_root)
    archive_root = vault_path / ARCHIVE_FOLDER
    timestamp = datetime.now().strftime("%Y-%m-%d")
    archive_batch = archive_root / f"archived-{timestamp}"
    
    moved_count = 0
    
    for source_folder, files in files_by_folder.items():
        # Create archive subfolder preserving original folder name
        archive_dest = archive_batch / source_folder
        
        if not dry_run:
            archive_dest.mkdir(parents=True, exist_ok=True)
        
        for file_path in files:
            # Preserve subdirectory structure within source folder
            relative_to_source = file_path.relative_to(vault_path / source_folder)
            dest_path = archive_dest / relative_to_source
            
            if dry_run:
                print(f"[DRY-RUN] Would move: {file_path.relative_to(vault_path)} -> {dest_path.relative_to(vault_path)}")
            else:
                # Create parent directories if needed
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(dest_path))
                print(f"Moved: {file_path.relative_to(vault_path)} -> {dest_path.relative_to(vault_path)}")
            
            moved_count += 1
    
    return moved_count, archive_batch


def reindex_vault(vault_root, dry_run=False):
    """Re-index vault embeddings after archiving."""
    if dry_run:
        print("\n[DRY-RUN] Would re-index vault with:")
        print(f"  index_vault.py {vault_root}")
        return True

    index_script = Path(PYTHON_EXE).parent.parent / "tools" / "index_vault.py"
    python_exe   = Path(PYTHON_EXE)

    if not python_exe.exists():
        print(f"ERROR: Python executable not found at {python_exe}")
        return False

    print("\nRe-indexing vault...")
    try:
        result = subprocess.run(
            [str(python_exe), str(index_script), str(vault_root), FAISS_STORE, MODEL_PATH],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print("✓ Vault re-indexed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"ERROR: Indexing failed with return code {result.returncode}")
            if result.stderr:
                print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("ERROR: Indexing timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"ERROR: Failed to run indexing: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python archive_and_reset.py <vault_root> [--dry-run]")
        sys.exit(1)
    
    vault_root = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    
    if not Path(vault_root).exists():
        print(f"ERROR: Vault root not found: {vault_root}")
        sys.exit(1)
    
    print("=" * 60)
    print("VAULT ARCHIVE AND RESET TOOL")
    print("=" * 60)
    if dry_run:
        print("MODE: DRY-RUN (no files will be moved)")
    else:
        print("MODE: LIVE (files will be moved)")
    print()
    
    # Find files
    print("Scanning for markdown files...")
    files_by_folder = find_markdown_files(vault_root, SOURCE_FOLDERS)
    
    if not files_by_folder:
        print("No markdown files found in source folders.")
        result = {
            "status": "success",
            "files_moved": 0,
            "message": "No files to archive"
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)
    
    # Summary
    total_files = sum(len(files) for files in files_by_folder.values())
    print(f"\nFound {total_files} markdown files:")
    for folder, files in files_by_folder.items():
        print(f"  {folder}: {len(files)} files")
    print()
    
    # Confirm if not dry-run
    if not dry_run:
        print("⚠️  WARNING: This will move all files to 99-Archive")
        response = input("Continue? (yes/no): ").strip().lower()
        if response != "yes":
            print("Operation cancelled.")
            sys.exit(0)
        print()
    
    # Archive files
    print("Archiving files...")
    moved_count, archive_batch = archive_files(vault_root, files_by_folder, dry_run)
    
    print(f"\n✓ {moved_count} files {'would be' if dry_run else ''} moved to:")
    print(f"  {archive_batch.relative_to(vault_root) if not dry_run else 'N/A (dry-run)'}")
    
    # Re-index vault
    if not dry_run:
        reindex_success = reindex_vault(vault_root, dry_run)
    else:
        reindex_vault(vault_root, dry_run)
        reindex_success = True
    
    # Output JSON result
    result = {
        "status": "success" if (dry_run or reindex_success) else "partial",
        "files_moved": moved_count,
        "archive_location": str(archive_batch.relative_to(vault_root)) if not dry_run else None,
        "reindex_success": reindex_success if not dry_run else None,
        "dry_run": dry_run
    }
    
    print("\n" + "=" * 60)
    print("RESULT:")
    print(json.dumps(result, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()
