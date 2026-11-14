#!/usr/bin/env python3
"""下载 URL 文件并上传到华为云 OBS，直接用 AK/SK 签名（无需 STS 换 token）"""

import argparse
import os
import re
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def download_file(url, output_path, headers=None):
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


def normalize_prefix(prefix):
    """Ensure prefix ends with / when non-empty, no leading /. Empty means bucket root."""
    p = (prefix or "").strip().lstrip("/")
    if not p:
        return ""
    return p if p.endswith("/") else p + "/"


def default_rule_id(prefix, expire_days):
    """Backward compat: 下载/ + 7d -> auto-delete-download-7d."""
    p = normalize_prefix(prefix).rstrip("/")
    if "下载" in p:
        safe = "download"
    else:
        safe = re.sub(r"[^A-Za-z0-9-]", "", p) or "data"
    return f"auto-delete-{safe}-{expire_days}d"


def upload_and_sign(local_path, obs_key, bucket, ak, sk, endpoint, expire_days=7,
                    prefix="下载/", rule_id="", output="/tmp/download_link.txt"):
    from obs import ObsClient, Lifecycle, Rule, Expiration

    obs = ObsClient(access_key_id=ak, secret_access_key=sk, server=endpoint)

    print(f"Uploading to OBS: {bucket}/{obs_key}")
    file_size = os.path.getsize(str(local_path))
    if file_size > 5 * 1024 * 1024 * 1024:
        print(f"Large file ({file_size:,} bytes), using multipart upload...")
        resp = obs.uploadFile(bucket, obs_key, str(local_path), taskNum=5, partSize=9 * 1024 * 1024 * 1024)
    else:
        resp = obs.putFile(bucket, obs_key, str(local_path))
    if resp.status < 300:
        print(f"Upload OK: status={resp.status}")
    else:
        print(f"Upload FAILED: status={resp.status}, reason={resp.reason}")
        if resp.body:
            print(f"  Body: {resp.body}")
        sys.exit(1)

    if expire_days > 0:
        norm_prefix = normalize_prefix(prefix)
        rid = rule_id or default_rule_id(norm_prefix, expire_days)
        lc_resp = obs.getBucketLifecycle(bucket)
        has_rule = False
        if lc_resp.status < 300 and lc_resp.body:
            rules = lc_resp.body.get('lifecycleConfig', {}).get('rule', [])
            for r in rules:
                if r.get('id') == rid:
                    has_rule = True
                    break
        if not has_rule:
            scope = norm_prefix if norm_prefix else obs_key
            rule = Rule(id=rid, prefix=scope, status='Enabled', expiration=Expiration(days=expire_days))
            obs.setBucketLifecycle(bucket, Lifecycle(rule=[rule]))
            print(f"Lifecycle rule set: {scope} auto-delete after {expire_days} days (id={rid})")
        else:
            print(f"Lifecycle rule already exists: id={rid}")

        signed_resp = obs.createSignedUrl('GET', bucket, obs_key, expires=expire_days * 86400)
        signed_url = signed_resp.get('signedUrl')

        Path(output).write_text(signed_url + "\n")
        print(f"\n{'='*60}")
        print(f"{expire_days}-day download link (auto-deletes in {expire_days} days):")
        print(f"  >> See artifact: download-link/{Path(output).name} <<")
        print(f"{'='*60}\n")
    else:
        print(f"No expiry set (expire-days<=0), object kept permanently: {bucket}/{obs_key}")


def main():
    parser = argparse.ArgumentParser(description="Download URL and upload to OBS")
    parser.add_argument("--url", required=True, help="URL to download")
    parser.add_argument("--obs-key", default="", help="Path under <prefix> (default: <filename>)")
    parser.add_argument("--bucket", default="xieyucheng", help="OBS bucket name")
    parser.add_argument("--region", default="cn-north-9", help="OBS region")
    parser.add_argument("--prefix", default="下载/", help="OBS key prefix (empty = bucket root, no extra lifecycle scope)")
    parser.add_argument("--expire-days", type=int, default=7, help="Auto-delete + signed-URL days; <=0 keeps permanently")
    parser.add_argument("--endpoint", default="", help="OBS endpoint override (default: obs.<region>.myhuaweicloud.com)")
    parser.add_argument("--rule-id", default="", help="Lifecycle rule id (default: auto-derived)")
    parser.add_argument("--output", default="/tmp/download_link.txt", help="Where to write signed URL")
    parser.add_argument("--obs-ak", default=os.environ.get("OBS_AK") or os.environ.get("PROD_HCLOUD_AK"), help="OBS AK (or env OBS_AK/PROD_HCLOUD_AK)")
    parser.add_argument("--obs-sk", default=os.environ.get("OBS_SK") or os.environ.get("PROD_HCLOUD_SK"), help="OBS SK (or env OBS_SK/PROD_HCLOUD_SK)")
    parser.add_argument("--header", action="append", default=[], help="Extra header")
    args = parser.parse_args()

    if not args.obs_ak or not args.obs_sk:
        print("Error: --obs-ak and --obs-sk are required (or set OBS_AK/OBS_SK env vars)")
        sys.exit(2)

    endpoint = args.endpoint or f"obs.{args.region}.myhuaweicloud.com"

    headers = {}
    for h in args.header:
        k, v = h.split(":", 1)
        headers[k.strip()] = v.strip()

    filename = Path(urlparse(args.url).path).name or "downloaded_file"
    output_path = Path(f"/tmp/{filename}")

    download_file(args.url, output_path, headers)

    norm_prefix = normalize_prefix(args.prefix)
    if args.obs_key:
        key = args.obs_key.lstrip("/")
        if norm_prefix and not key.startswith(norm_prefix):
            key = f"{norm_prefix}{key}"
    else:
        key = f"{norm_prefix}{filename}"

    upload_and_sign(output_path, key, args.bucket, args.obs_ak, args.obs_sk,
                    endpoint, args.expire_days, norm_prefix,
                    args.rule_id, args.output)

    output_path.unlink(missing_ok=True)
    print("Done!")


if __name__ == "__main__":
    main()
