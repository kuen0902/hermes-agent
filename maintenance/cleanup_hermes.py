import os
import shutil
import glob
from pathlib import Path

def main():
    home = str(Path.home())
    hermes_dir = os.path.join(home, ".hermes")
    workspace_dir = os.path.join(home, "workspace")
    
    # Target directories
    run_dir = os.path.join(hermes_dir, "run")
    cache_dir = os.path.join(hermes_dir, "cache")
    data_dir = os.path.join(hermes_dir, "data")
    
    # Create target directories
    for d in [workspace_dir, run_dir, cache_dir, data_dir]:
        os.makedirs(d, exist_ok=True)
        print(f"✅ Ensure directory exists: {d}")

    # 1. Move hermes-agent
    source_agent = os.path.join(hermes_dir, "hermes-agent")
    dest_agent = os.path.join(workspace_dir, "hermes-agent")
    if os.path.exists(source_agent):
        print(f"📦 Moving hermes-agent to {dest_agent}...")
        shutil.move(source_agent, dest_agent)
        print("✅ Successfully moved hermes-agent")
    else:
        print("⏭️  hermes-agent not found in .hermes (might be moved already)")

    # 2. Move run files
    run_files = ["gateway.pid", "gateway.lock", "auth.lock", "processes.json"]
    print("\n📦 Moving run files...")
    for f in run_files:
        src = os.path.join(hermes_dir, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(run_dir, f))
            print(f"  - Moved {f}")

    # 3. Move cache files
    cache_files = ["models_dev_cache.json", "ollama_cloud_models_cache.json", "tavily_local_log.json"]
    print("\n📦 Moving cache files...")
    for f in cache_files:
        src = os.path.join(hermes_dir, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(cache_dir, f))
            print(f"  - Moved {f}")

    # 4. Move data files (including wildcards like state.db-wal)
    print("\n📦 Moving database and state files...")
    data_patterns = ["state.db*", "kanban.db*", ".restart_last_processed.json"]
    for pattern in data_patterns:
        for src in glob.glob(os.path.join(hermes_dir, pattern)):
            filename = os.path.basename(src)
            shutil.move(src, os.path.join(data_dir, filename))
            print(f"  - Moved {filename}")

    print("\n🎉 目錄結構重構完成！")
    print("⚠️ 提醒：請記得將任何自動啟動腳本中的路徑更新為 ~/workspace/hermes-agent/run_agent.py")

if __name__ == "__main__":
    main()
