#!/usr/bin/env python3
"""下载 URL 文件并上传到华为云 OBS"""

import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse


def download_file(url, output_path, headers=None):
    import subprocess
    cmd = ["curl", "-fSL", "--retry", "3", "--retry-delay", "5", "-o", str(output_path)]
    if headers:
        for k, v in headers.items():
            cmd.extend(["-H", f"{k}: {v}"])
    cmd.append(url)
    print(f"Downloading: {url}")
    subprocess.run(cmd, check=True)
    size = output_path.stat().st_size
    print(f"Downloaded: {output_path} ({size:,} bytes)")
    return size


def upload_to_obs(local_path, obs_key, bucket, ak, sk, endpoint, region):
    from obs import ObsClient
    obs = ObsClient(access_key_id=ak, secret_access_key=sk, server=endpoint)

    key = obs_key if obs_key else local_path.name
    print(f"Uploading to OBS: {bucket}/{key}")

    resp = obs.putFile(bucket, key, str(local_path))
    if resp.status < 300:
        print(f"Upload OK: status={resp.status}")
        obs_url = f"https://{bucket}.obs.{region}.myhuaweicloud.com/{key}"
        print(f"OBS URL: {obs_url}")
        return obs_url
    else:
        print(f"Upload FAILED: status={resp.status}, reason={resp.reason}")
        if resp.body:
            print(f"  Body: {resp.body}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download URL and upload to OBS")
    parser.add_argument("--url", required=True, help="URL to download")
    parser.add_argument("--obs-key", default="", help="OBS target key (default: filename from URL)")
    parser.add_argument("--bucket", default="xieyucheng", help="OBS bucket name")
    parser.add_argument("--region", default="cn-north-9", help="OBS region")
    parser.add_argument("--obs-ak", default=os.environ.get("OBS_AK"), required=True)
    parser.add_argument("--obs-sk", default=os.environ.get("OBS_SK"), required=True)
    parser.add_argument("--header", action="append", default=[], help="Extra header, e.g. 'Authorization: Bearer xxx'")
    args = parser.parse_args()

    endpoint = f"obs.{args.region}.myhuaweicloud.com"

    headers = {}
    for h in args.header:
        k, v = h.split(":", 1)
        headers[k.strip()] = v.strip()

    filename = Path(urlparse(args.url).path).name or "downloaded_file"
    output_path = Path(f"/tmp/{filename}")

    size = download_file(args.url, output_path, headers)

    key = args.obs_key if args.obs_key else filename
    if not key.startswith("下载/") and not key.startswith("/"):
        key = f"下载/{key}"

    upload_to_obs(output_path, key, args.bucket, args.obs_ak, args.obs_sk, endpoint, args.region)

    output_path.unlink(missing_ok=True)
    print("Done!")


if __name__ == "__main__":
    main()
