import os
import shutil
import glob
from pathlib import Path

def main():
    home = str(Path.home())
    hermes_dir = os.path.join(home, ".hermes")
    actual_workspace = os.path.join(home, "workspace")
    wrong_workspace = os.path.join(hermes_dir, "workspace")
    data_dir = os.path.join(hermes_dir, "data")
    
    # 1. 修正 hermes-agent 路徑
    wrong_agent = os.path.join(wrong_workspace, "hermes-agent")
    right_agent = os.path.join(actual_workspace, "hermes-agent")
    
    if os.path.exists(wrong_agent):
        print("🔧 修正：將 hermes-agent 從錯誤路徑移至正確的 ~/workspace/hermes-agent ...")
        shutil.move(wrong_agent, right_agent)
        try:
            os.rmdir(wrong_workspace)
        except OSError:
            pass
        print("✅ 完成")
        
    # 2. 還原 Database (非常重要)
    print("\n🔧 修正：還原資料庫檔案到 ~/.hermes/ 根目錄 ...")
    data_patterns = ["state.db*", "kanban.db*", ".restart_last_processed.json"]
    for pattern in data_patterns:
        for src in glob.glob(os.path.join(data_dir, pattern)):
            filename = os.path.basename(src)
            dest = os.path.join(hermes_dir, filename)
            # 覆蓋 Hermes 剛剛自動生成的空資料庫，還原您原本帶有歷史紀錄的資料庫
            if os.path.exists(dest):
                os.remove(dest)
            shutil.move(src, dest)
            print(f"  - 成功還原 {filename}")
            
    print("\n🎉 修正完畢！您可以安全地重新啟動 Hermes 了。")

if __name__ == "__main__":
    main()
