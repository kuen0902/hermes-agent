import subprocess
import os

def validate_pdf_health(file_path, min_size_kb=20.0):
    """
    Validates PDF health for financial reports.
    - Checks file existence and size.
    - Checks magic bytes and structure via 'file' command.
    """
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    size_kb = os.path.getsize(file_path) / 1024
    if size_kb < min_size_kb:
        return False, f"File too small ({size_kb:.1f} KB)"

    try:
        # Use system 'file' command to check for PDF identity
        output = subprocess.check_output(["file", file_path]).decode("utf-8")
        if "PDF document" not in output:
            return False, "Invalid PDF header/format"
            
        return True, "Healthy"
    except Exception as e:
        return False, f"System error during check: {str(e)}"
