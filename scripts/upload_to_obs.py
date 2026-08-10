#!/usr/bin/env python3
"""下载 URL 文件并上传到华为云 OBS，用 STS 临时凭证生成不掩码的预签名 URL"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import requests


def get_sts_credentials(ak, sk, region, duration=3600):
    iam = f'https://iam.{region}.myhuaweicloud.com'
    token_resp = requests.post(f'{iam}/v3/auth/tokens', json={
        'auth': {'identity': {'methods': ['hw_ak_sk'],
            'hw_ak_sk': {'access': {'key': ak}, 'secret': {'key': sk}}},
            'scope': {'project': {'name': region}}}
    })
    if token_resp.status_code != 201:
        print(f"Token request failed: {token_resp.status_code} {token_resp.text[:200]}")
        sys.exit(1)
    token = token_resp.headers['X-Subject-Token']

    resp = requests.post(f'{iam}/v3.0/OS-CREDENTIAL/securitytokens',
        headers={'X-Auth-Token': token},
        json={'auth': {'identity': {'methods': ['token'], 'token': {'duration_seconds': duration}}}})
    if resp.status_code != 201:
        print(f"STS request failed: {resp.status_code} {resp.text[:200]}")
        sys.exit(1)
    c = resp.json()['credential']
    return c['access'], c['secret'], c['securitytoken']


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


def upload_and_sign(local_path, obs_key, bucket, sts_ak, sts_sk, sts_token, perm_ak, perm_sk, endpoint, region, expire_days=7):
    from obs import ObsClient, Lifecycle, Rule, Expiration

    obs_sts = ObsClient(access_key_id=sts_ak, secret_access_key=sts_sk, server=endpoint, security_token=sts_token)
    obs_perm = ObsClient(access_key_id=perm_ak, secret_access_key=perm_sk, server=endpoint)

    print(f"Uploading to OBS: {bucket}/{obs_key}")
    import os
    file_size = os.path.getsize(str(local_path))
    if file_size > 5 * 1024 * 1024 * 1024:  # > 5GB, use multipart
        print(f"Large file ({file_size:,} bytes), using multipart upload...")
        resp = obs_sts.uploadFile(bucket, obs_key, str(local_path), taskNum=5, partSize=9*1024*1024*1024)
    else:
        resp = obs_sts.putFile(bucket, obs_key, str(local_path))
    if resp.status < 300:
        print(f"Upload OK: status={resp.status} (via STS temp AK={sts_ak})")
    else:
        print(f"Upload FAILED: status={resp.status}, reason={resp.reason}")
        if resp.body:
            print(f"  Body: {resp.body}")
        sys.exit(1)

    lc_resp = obs_perm.getBucketLifecycle(bucket)
    has_rule = False
    if lc_resp.status < 300 and lc_resp.body:
        rules = lc_resp.body.get('lifecycleConfig', {}).get('rule', [])
        for r in rules:
            if r.get('id') == 'auto-delete-download-7d':
                has_rule = True
                break
    if not has_rule:
        rule = Rule(id='auto-delete-download-7d', prefix='下载/', status='Enabled', expiration=Expiration(days=expire_days))
        obs_perm.setBucketLifecycle(bucket, Lifecycle(rule=[rule]))
        print(f"Lifecycle rule set: 下载/ auto-delete after {expire_days} days")
    else:
        print(f"Lifecycle rule already exists: 下载/ auto-delete after {expire_days} days")

    signed_resp = obs_perm.createSignedUrl('GET', bucket, obs_key, expires=expire_days * 86400)
    signed_url = signed_resp.get('signedUrl')

    Path("/tmp/download_link.txt").write_text(signed_url + "\n")
    print(f"\n{'='*60}")
    print(f"7-day download link (auto-deletes in {expire_days} days):")
    print(f"  >> See artifact: download-link/download_link.txt <<")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Download URL and upload to OBS via STS")
    parser.add_argument("--url", required=True, help="URL to download")
    parser.add_argument("--obs-key", default="", help="Path under 下载/ (default: <filename>)")
    parser.add_argument("--bucket", default="xieyucheng", help="OBS bucket name")
    parser.add_argument("--region", default="cn-north-9", help="OBS region")
    parser.add_argument("--obs-ak", default=os.environ.get("OBS_AK"), help="OBS AK (or env OBS_AK)")
    parser.add_argument("--obs-sk", default=os.environ.get("OBS_SK"), help="OBS SK (or env OBS_SK)")
    parser.add_argument("--header", action="append", default=[], help="Extra header")
    args = parser.parse_args()

    if not args.obs_ak or not args.obs_sk:
        print("Error: --obs-ak and --obs-sk are required (or set OBS_AK/OBS_SK env vars)")
        sys.exit(2)

    endpoint = f"obs.{args.region}.myhuaweicloud.com"

    headers = {}
    for h in args.header:
        k, v = h.split(":", 1)
        headers[k.strip()] = v.strip()

    filename = Path(urlparse(args.url).path).name or "downloaded_file"
    output_path = Path(f"/tmp/{filename}")

    download_file(args.url, output_path, headers)

    if args.obs_key:
        key = args.obs_key if args.obs_key.startswith("下载/") else f"下载/{args.obs_key}"
    else:
        key = f"下载/{filename}"

    print("Getting STS temporary credentials...")
    temp_ak, temp_sk, temp_token = get_sts_credentials(args.obs_ak, args.obs_sk, args.region)
    print(f"STS OK: temp AK={temp_ak}")

    upload_and_sign(output_path, key, args.bucket, temp_ak, temp_sk, temp_token,
                    args.obs_ak, args.obs_sk, endpoint, args.region)

    output_path.unlink(missing_ok=True)
    print("Done!")


if __name__ == "__main__":
    main()
