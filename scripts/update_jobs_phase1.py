import json

def main():
    path = "/Users/bookid/.hermes/cron/jobs.json"
    with open(path, "r") as f:
        data = json.load(f)

    for job in data.get("jobs", []):
        if "base_url" not in job:
            job["base_url"] = None
        if "no_agent" not in job:
            job["no_agent"] = True
            
        if job.get("name") in [
            "stock-portfolio-monitor",
            "william-stock-monitor-auto",
            "group-stock-monitor-9-12",
            "Group-Stock-Analysis-1350"
        ]:
            job["script"] = None

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print("jobs.json restored and updated successfully.")

if __name__ == "__main__":
    main()
