import subprocess
import sys

def run_git(args):
    try:
        result = subprocess.run(['git'] + args, capture_output=True, text=True)
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return result.returncode
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    # Add everything
    run_git(['add', '.'])
    # Commit
    with open('.git_commit_msg', 'r') as f:
        msg = f.read()
    run_git(['commit', '-m', msg])
