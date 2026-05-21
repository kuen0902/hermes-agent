import os
import json
import glob
import subprocess

# Configuration
REPORTS_ROOT = os.path.expanduser("~/Documents/Reports")
CALENDAR_FILE = os.path.expanduser("~/.hermes/data/earnings_calendar.json")

def check_pdf_health(file_path):
    """Checks if a PDF is healthy: exists, not empty, and valid magic bytes."""
    if not os.path.exists(file_path):
        return False, "File missing"
    
    # Check size (threshold: 20KB for a typical report)
    size_kb = os.path.getsize(file_path) / 1024
    if size_kb < 20:
        return False, f"File too small ({size_kb:.1f} KB)"
    
    # Check magic bytes using 'file' command
    try:
        output = subprocess.check_output(["file", file_path]).decode("utf-8")
        if "PDF document" not in output:
            return False, "Not a valid PDF format"
    except Exception as e:
        return False, f"Recognition error: {str(e)}"
    
    return True, "Healthy"

def run_health_check():
    print("Starting Financial Report Health Check...")
    
    # Find all PDFs in reports directory
    pdf_files = glob.glob(os.path.join(REPORTS_ROOT, "**/*.pdf"), recursive=True)
    report_count = len(pdf_files)
    
    summary = {
        "total": report_count,
        "healthy": 0,
        "unhealthy": [],
        "details": {}
    }
    
    for pdf in pdf_files:
        is_healthy, reason = check_pdf_health(pdf)
        filename = os.path.basename(pdf)
        
        if is_healthy:
            summary["healthy"] += 1
        else:
            summary["unhealthy"].append({
                "file": filename,
                "reason": reason,
                "path": pdf
            })
        
        summary["details"][filename] = {"status": "Healthy" if is_healthy else "Unhealthy", "reason": reason}

    print(f"Check Complete: {summary['healthy']}/{summary['total']} healthy.")
    
    if summary["unhealthy"]:
        print("ALERT: Found unhealthy reports!")
        for item in summary["unhealthy"]:
            print(f"- {item['file']}: {item['reason']}")
            
    return summary

if __name__ == "__main__":
    run_health_check()
