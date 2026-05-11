import pathlib
import sys

def scan_home():
    """
    Scans the current user's home directory and maps available subfolders.
    Handles common macOS TCC permission errors gracefully.
    """
    home = pathlib.Path.home()
    print(f"Targeting Profile: {home}")
    
    try:
        # Get all subdirectories
        folders = [f for f in home.iterdir() if f.is_dir()]
        
        print(f"Found {len(folders)} accessible top-level directories:")
        for folder in sorted(folders):
            try:
                # Attempt a shallow peek to verify access
                count = len(list(folder.iterdir()))
                status = f"Accessible ({count} items)"
            except PermissionError:
                status = "Restricted (TCC Permission Required)"
            
            print(f"- {folder.name:20} | {status}")
            
    except Exception as e:
        print(f"Critical scan failure: {e}")

if __name__ == "__main__":
    scan_home()
