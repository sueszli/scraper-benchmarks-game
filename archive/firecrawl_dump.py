# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "polars",
#   "requests",
#   "tqdm",
#   "playwright",
# ]
# ///

import subprocess
from pathlib import Path

import polars as pl
import requests
from playwright.sync_api import sync_playwright
from tqdm import tqdm

subprocess.run(["playwright", "install", "chromium"], check=True)


data_dir = Path("data")
data_dir.mkdir(exist_ok=True)


csv_path = data_dir / "eval.csv"
if not csv_path.exists():
    r = requests.get("https://huggingface.co/datasets/firecrawl/scrape-content-dataset-v1/resolve/main/1-0-0.csv", allow_redirects=True)
    r.raise_for_status()
    csv_path.write_bytes(r.content)


# columns:
# - truth_text: ~100-word core snippet (main content)
# - lie_text: ~10-word non-core snippet (navigation/footer/ads)
# - error: Optional error message if page retrieval failed
df = pl.read_csv(csv_path)
before = len(df)
df = df.filter(pl.col("truth_text").is_not_null())
after = len(df)
print(f"dropped invalid rows ({(before - after)/before:.0%})")


bar = tqdm(df.iter_rows(named=True), total=len(df))
with sync_playwright() as p:
    browser = p.chromium.launch()

    for row in bar:
        url = (row["url"] or "").strip()
        if not url:
            continue
        page_id = row["id"]

        html_path = data_dir / f"index-{page_id:04d}.html"
        if html_path.exists():
            continue

        # fetch
        try:
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=20000)
            html = page.content()
            page.close()
            html_path.write_text(html, encoding="utf-8")
        except Exception:
            html_path.touch()  # dont try again later
            continue

        # push
        subprocess.run(["git", "add", "."])
        result = subprocess.run(["git", "commit", "-m", "up"])
        if result.returncode == 0:
            subprocess.run(["git", "push"])

    browser.close()
