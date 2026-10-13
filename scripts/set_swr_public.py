#!/usr/bin/env python3
"""设置 SWR 镜像仓库为公开，并添加 7 天存活时间老化规则"""

import argparse
import os
import sys

from huaweicloudsdkcore.auth.credentials import BasicCredentials
from huaweicloudsdkswr.v2.swr_client import SwrClient
from huaweicloudsdkswr.v2.region.swr_region import SwrRegion
from huaweicloudsdkswr.v2.model import (
    UpdateRepoRequest, UpdateRepoRequestBody,
    CreateRetentionRequest, CreateRetentionRequestBody,
    RetentionRule, RetentionSelector,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--region", default="cn-north-4")
    parser.add_argument("--ak", default=os.environ.get("HCLOUD_AK"))
    parser.add_argument("--sk", default=os.environ.get("HCLOUD_SK"))
    parser.add_argument("--expire-days", type=int, default=7)
    args = parser.parse_args()

    credentials = BasicCredentials(ak=args.ak, sk=args.sk)
    client = SwrClient.new_builder().with_credentials(credentials).with_region(SwrRegion.value_of(args.region)).build()

    # Set repo public
    update_body = UpdateRepoRequestBody(is_public=True)
    request = UpdateRepoRequest(namespace=args.namespace, repository=args.repo, body=update_body)
    failed = False
    try:
        resp = client.update_repo(request)
        print(f"Set {args.namespace}/{args.repo} public: OK")
    except Exception as e:
        # Fail loud: a silent no-op here once left a repo private (wrong region),
        # blocking all downstream pulls with Authenticate Error.
        print(f"Set public error: {e}")
        failed = True

    # Set 7-day retention rule
    tag_selector = RetentionSelector(kind="regexp", pattern=".*")
    rule = RetentionRule(
        template="date_rule",
        params={"days": str(args.expire_days)},
        tag_selectors=[tag_selector],
    )
    retention_body = CreateRetentionRequestBody(algorithm="or", rules=[rule])
    retention_req = CreateRetentionRequest(namespace=args.namespace, repository=args.repo, body=retention_body)
    try:
        retention_resp = client.create_retention(retention_req)
        print(f"Set {args.expire_days}-day retention rule: OK")
    except Exception as e:
        err_str = str(e)
        if "already" in err_str.lower() or "exist" in err_str.lower():
            print(f"Retention rule already exists, skipping")
        else:
            print(f"Retention rule error: {e}")
            failed = True

    print("Done!")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
