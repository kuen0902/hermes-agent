import os
import glob
from pathlib import Path

def main():
    old_prefix = "/Users/bookid/.hermes/hermes-agent"
    new_prefix = "/Users/bookid/workspace/hermes-agent"
    bin_dir = "/Users/bookid/workspace/hermes-agent/venv/bin"
    
    print(f"🔧 正在修正 {bin_dir} 及其子目錄中的路徑...")
    
    # 遞迴走訪整個 venv 目錄
    venv_dir = "/Users/bookid/workspace/hermes-agent/venv"
    for root, dirs, files in os.walk(venv_dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            # 跳過軟連結和一些顯然不是文字檔案的副檔名
            if os.path.islink(filepath):
                continue
            if filename.endswith(('.so', '.pyc', '.pyo', '.bin', '.exe', '.dll')):
                continue
                
            try:
                with open(filepath, "rb") as f:
                    content = f.read()
                
                if old_prefix.encode() in content:
                    print(f"  - 修正: {os.path.relpath(filepath, venv_dir)}")
                    new_content = content.replace(old_prefix.encode(), new_prefix.encode())
                    with open(filepath, "wb") as f:
                        f.write(new_content)
            except Exception as e:
                # 靜默處理讀取錯誤 (可能是大型二進位檔)
                pass

    print("\n✅ 虛擬環境路徑修正完畢！")

if __name__ == "__main__":
    main()
