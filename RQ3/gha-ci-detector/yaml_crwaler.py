import os
import csv
import requests

CSV_PATH = "yaml_list.csv"
DEST_DIR = "yaml_files"

os.makedirs(DEST_DIR, exist_ok=True)

def download_yaml(repo, yaml_file, branch="main"):
    # GitHub raw URL 생성
    dest_path = os.path.join(DEST_DIR, f"{repo.replace('/', '_')}__{yaml_file}")
    # branch 정보가 있으면 해당 브랜치부터 시도
    url_branch = f"https://raw.githubusercontent.com/{repo}/{branch}/.github/workflows/{yaml_file}"
    try:
        resp = requests.get(url_branch)
        if resp.status_code == 200:
            with open(dest_path, "wb") as f:
                f.write(resp.content)
            print(f"Downloaded ({branch}): {dest_path}")
            return
        elif resp.status_code == 404:
            # main 브랜치가 아니면 main 브랜치로 재시도
            if branch != "main":
                url_main = f"https://raw.githubusercontent.com/{repo}/main/.github/workflows/{yaml_file}"
                resp_main = requests.get(url_main)
                if resp_main.status_code == 200:
                    with open(dest_path, "wb") as f:
                        f.write(resp_main.content)
                    print(f"Downloaded (main): {dest_path}")
                    return
                elif resp_main.status_code == 404:
                    # master 브랜치로 재시도
                    url_master = f"https://raw.githubusercontent.com/{repo}/master/.github/workflows/{yaml_file}"
                    resp_master = requests.get(url_master)
                    if resp_master.status_code == 200:
                        with open(dest_path, "wb") as f:
                            f.write(resp_master.content)
                        print(f"Downloaded (master): {dest_path}")
                        return
                    else:
                        print(f"Failed ({resp_master.status_code}): {url_master}")
                else:
                    print(f"Failed ({resp_main.status_code}): {url_main}")
            else:
                # branch가 main인데 404면 master로 재시도
                url_master = f"https://raw.githubusercontent.com/{repo}/master/.github/workflows/{yaml_file}"
                resp_master = requests.get(url_master)
                if resp_master.status_code == 200:
                    with open(dest_path, "wb") as f:
                        f.write(resp_master.content)
                    print(f"Downloaded (master): {dest_path}")
                    return
                else:
                    print(f"Failed ({resp_master.status_code}): {url_master}")
        else:
            print(f"Failed ({resp.status_code}): {url_branch}")
    except Exception as e:
        print(f"Error downloading {url_branch}: {e}")

with open(CSV_PATH, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        org = row["Org"].strip()
        repo = row["Repo"].strip()
        repo = f"{org}/{repo}" if org else repo
        if not repo:
            continue
        yaml_file = row["Yaml"].strip()
        branch = row.get("Branch", "main").strip() if row.get("Branch") else "main"
        if repo and yaml_file:
            download_yaml(repo, yaml_file, branch)