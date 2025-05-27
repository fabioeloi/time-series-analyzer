#!/usr/bin/env python3
"""
Time Series Analyzer Cache Cleaner

This script clears cache files from the backend data directory.
It should be run from the project root directory.
"""

import os
import sys
import shutil
from pathlib import Path


def get_project_root():
    """Get the project root directory."""
    current_dir = Path(__file__).parent.absolute()
    return current_dir


def get_cache_directory():
    """Get the cache directory path relative to project root."""
    project_root = get_project_root()
    cache_dir = project_root / "backend" / "data"
    return cache_dir


def clear_cache_files(cache_dir, file_extensions=None):
    """
    Clear cache files from the specified directory.
    
    Args:
        cache_dir (Path): Directory to clear cache files from
        file_extensions (list): List of file extensions to remove (e.g., ['.pkl', '.cache'])
                               If None, removes all files
    """
    if not cache_dir.exists():
        print(f"Cache directory does not exist: {cache_dir}")
        return False
    
    if not cache_dir.is_dir():
        print(f"Cache path is not a directory: {cache_dir}")
        return False
    
    removed_files = []
    failed_files = []
    
    try:
        for item in cache_dir.iterdir():
            # Skip hidden files and directories that should be preserved
            if item.name.startswith('.'):
                continue
                
            # If file_extensions is specified, only remove matching files
            if file_extensions and item.is_file():
                if not any(item.name.endswith(ext) for ext in file_extensions):
                    continue
            
            try:
                if item.is_file() or item.is_symlink():
                    item.unlink()
                    removed_files.append(str(item))
                    print(f"Removed file: {item.relative_to(get_project_root())}")
                elif item.is_dir():
                    # Only remove directories if no file_extensions filter is specified
                    if not file_extensions:
                        shutil.rmtree(item)
                        removed_files.append(str(item))
                        print(f"Removed directory: {item.relative_to(get_project_root())}")
            except Exception as e:
                failed_files.append((str(item), str(e)))
                print(f"Failed to delete {item.relative_to(get_project_root())}: {e}")
    
    except Exception as e:
        print(f"Error accessing cache directory {cache_dir}: {e}")
        return False
    
    # Summary
    if removed_files:
        print(f"\nSummary: Successfully removed {len(removed_files)} items")
    else:
        print("\nNo cache files found to remove")
    
    if failed_files:
        print(f"Failed to remove {len(failed_files)} items")
        for file_path, error in failed_files:
            print(f"  - {file_path}: {error}")
    
    return len(failed_files) == 0


def clear_specific_cache_files():
    """Clear specific cache files like .pkl files."""
    cache_dir = get_cache_directory()
    
    if not cache_dir.exists():
        print(f"Creating cache directory: {cache_dir}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        return True
    
    # Clear .pkl files specifically (pickle cache files)
    pkl_files_removed = clear_cache_files(cache_dir, ['.pkl'])
    
    # Also remove any other common cache file types
    cache_extensions = ['.cache', '.tmp', '.temp', '.log']
    other_cache_removed = clear_cache_files(cache_dir, cache_extensions)
    
    return pkl_files_removed and other_cache_removed


def main():
    """Main function to clear cache files."""
    print("Time Series Analyzer - Cache Cleaner")
    print("=" * 50)
    
    project_root = get_project_root()
    print(f"Project root: {project_root}")
    
    cache_dir = get_cache_directory()
    print(f"Cache directory: {cache_dir}")
    
    # Change to project root directory to ensure relative paths work correctly
    original_cwd = os.getcwd()
    os.chdir(project_root)
    
    try:
        # Clear specific cache files
        success = clear_specific_cache_files()
        
        if success:
            print("\n✅ Cache clearing completed successfully")
            return 0
        else:
            print("\n❌ Cache clearing completed with errors")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️  Cache clearing interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error during cache clearing: {e}")
        return 1
    finally:
        # Restore original working directory
        os.chdir(original_cwd)


if __name__ == '__main__':
    sys.exit(main())