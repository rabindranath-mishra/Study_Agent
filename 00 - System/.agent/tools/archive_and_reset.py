r"""
Archive and Reset Tool for Obsidian Vault

Moves all markdown files from content folders to 99-Archive and re-indexes vault.
Follows Vault Constitution containment policy.

Vault root and archive destination are resolved automatically from paths.py —
no path arguments are required.

Usage:
    python archive_and_reset.py [--dry-run] [--yes]

Options:
    --dry-run   Preview what would be moved without making changes (default-safe).
    --yes       Skip confirmation prompt (for agent/CI usage).

Example (run from any directory):
    python "00 - System\\.agent\\tools\\archive_and_reset.py" --dry-run
    python "00 - System\\.agent\\tools\\archive_and_reset.py" --yes
"""

import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import (
    VAULT_ROOT, PYTHON_EXE, ARCHIVE_DIR,
)

# Folders whose markdown notes are eligible for archiving.
# Matches the Study Agent vault layout (Vault Constitution §III).
SOURCE_FOLDERS = [
    "01 - Inbox",
    "02 - Sources",
    "03 - Subjects",
    "04 - Concepts",
    "05 - Practice",
    "06 - Plans",
    "07 - Outputs",
]

# Resolved absolute paths from paths.py — used as defaults throughout.
_VAULT_PATH   = Path(VAULT_ROOT)
_ARCHIVE_PATH = Path(ARCHIVE_DIR)


def find_markdown_files(folders, vault_root=None):
    """Find all .md files in *folders* under the vault root.

    *vault_root* defaults to VAULT_ROOT from paths.py.
    Pass an explicit path only in tests that use a temporary directory.
    """
    vault = Path(vault_root) if vault_root else _VAULT_PATH
    files_by_folder = {}

    for folder in folders:
        folder_path = vault / folder
        if not folder_path.exists():
            continue

        md_files = list(folder_path.rglob("*.md"))
        if md_files:
            files_by_folder[folder] = md_files

    return files_by_folder


def archive_files(files_by_folder, dry_run=False, vault_root=None, archive_root=None):
    """Move files to archive with timestamp-based organisation.

    *vault_root*   defaults to VAULT_ROOT from paths.py.
    *archive_root* defaults to ARCHIVE_DIR from paths.py.
    Pass explicit paths only in tests that use a temporary directory.
    """
    vault        = Path(vault_root)   if vault_root   else _VAULT_PATH
    archive_base = Path(archive_root) if archive_root else _ARCHIVE_PATH
    timestamp    = datetime.now().strftime("%Y-%m-%d")
    archive_batch = archive_base / f"archived-{timestamp}"

    moved_count = 0

    for source_folder, files in files_by_folder.items():
        archive_dest = archive_batch / source_folder

        if not dry_run:
            archive_dest.mkdir(parents=True, exist_ok=True)

        for file_path in files:
            relative_to_source = file_path.relative_to(vault / source_folder)
            dest_path = archive_dest / relative_to_source

            if dry_run:
                print(f"[DRY-RUN] Would move: {file_path.relative_to(vault)} -> {dest_path.relative_to(vault)}")
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(file_path), str(dest_path))
                print(f"Moved: {file_path.relative_to(vault)} -> {dest_path.relative_to(vault)}")

            moved_count += 1

    return moved_count, archive_batch


def reindex_vault(dry_run=False):
    """Re-index vault embeddings after archiving.

    Uses PYTHON_EXE from paths.py — no path argument required.
    """
    if dry_run:
        print("\n[DRY-RUN] Would re-index vault with index_vault.py")
        return True

    index_script = Path(__file__).resolve().parent / "index_vault.py"
    python_exe   = Path(PYTHON_EXE)

    if not python_exe.exists():
        print(f"ERROR: Python executable not found at {python_exe}")
        return False

    print("\nRe-indexing vault...")
    try:
        result = subprocess.run(
            [str(python_exe), str(index_script)],
            capture_output=True,
            text=True,
            timeout=300,
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
    dry_run  = "--dry-run" in sys.argv
    auto_yes = "--yes" in sys.argv

    print("=" * 60)
    print("VAULT ARCHIVE AND RESET TOOL")
    print(f"Vault: {_VAULT_PATH}")
    print("=" * 60)
    if dry_run:
        print("MODE: DRY-RUN (no files will be moved)")
    else:
        print("MODE: LIVE (files will be moved)")
    print()

    # Find files using paths.py vault root
    print("Scanning for markdown files...")
    files_by_folder = find_markdown_files(SOURCE_FOLDERS)

    if not files_by_folder:
        print("No markdown files found in source folders.")
        result = {
            "status": "success",
            "files_moved": 0,
            "message": "No files to archive",
        }
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # Summary
    total_files = sum(len(files) for files in files_by_folder.values())
    print(f"\nFound {total_files} markdown files:")
    for folder, files in files_by_folder.items():
        print(f"  {folder}: {len(files)} files")
    print()

    # Confirm if not dry-run and not auto-confirmed
    if not dry_run and not auto_yes:
        print("⚠️  WARNING: This will move all files to 99-Archive")
        response = input("Continue? (yes/no): ").strip().lower()
        if response != "yes":
            print("Operation cancelled.")
            sys.exit(0)
        print()
    elif not dry_run and auto_yes:
        print("⚠️  WARNING: Auto-confirmed via --yes flag. Moving all files to 99-Archive.")
        print()

    # Archive files
    print("Archiving files...")
    moved_count, archive_batch = archive_files(files_by_folder, dry_run)

    print(f"\n✓ {moved_count} files {'would be' if dry_run else 'moved'} to:")
    print(f"  {archive_batch.relative_to(_VAULT_PATH) if not dry_run else 'N/A (dry-run)'}")

    # Re-index vault
    reindex_success = reindex_vault(dry_run)

    # Output JSON result
    result = {
        "status": "success" if (dry_run or reindex_success) else "partial",
        "vault_root": str(_VAULT_PATH),
        "files_moved": moved_count,
        "archive_location": str(archive_batch.relative_to(_VAULT_PATH)) if not dry_run else None,
        "reindex_success": reindex_success if not dry_run else None,
        "dry_run": dry_run,
    }

    print("\n" + "=" * 60)
    print("RESULT:")
    print(json.dumps(result, indent=2))
    print("=" * 60)


if __name__ == "__main__":
    main()
