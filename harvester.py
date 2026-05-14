import re
import requests
import os

BASE_URL = "https://facebook-ad-scaler.pages.dev"
ASSETS_DIR = "/mnt/c/facebook-ad-scaler/static/assets"

# Identified chunks from previous recon
chunks = [
    "index-r215tC_7.js", "index-DnZrT2z0.css", 
    "Dashboard-JKh4wXFv.js", "rolldown-runtime-S-ySWqyJ.js", 
    "react-vendor-C0IOBbdh.js", "CartesianChart-DvZ9Ka_W.js",
    "createLucideIcon-CZdZkbWY.js", "chart-column-DcT2Lgok.js",
    "AdsGPT-6XzW7m5v.js", "Campaigns-okGSZ_-n.js", "Rules-DbQk4gH6.js"
]

def download():
    print(f"🚀 Starting Asset Harvest from {BASE_URL}...")
    for chunk in chunks:
        url = f"{BASE_URL}/assets/{chunk}"
        path = os.path.join(ASSETS_DIR, chunk)
        print(f"  ➜ Pulling {chunk}...")
        try:
            r = requests.get(url)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    f.write(r.content)
            else:
                print(f"  ❌ Failed: {chunk} (Status {r.status_code})")
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    download()
