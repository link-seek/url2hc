#!/usr/bin/env python3
"""设置 SWR 镜像仓库公开属性，并按需添加存活时间老化规则"""

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
    parser.add_argument("--ak", default=os.environ.get("HCLOUD_AK") or os.environ.get("PROD_HCLOUD_AK"))
    parser.add_argument("--sk", default=os.environ.get("HCLOUD_SK") or os.environ.get("PROD_HCLOUD_SK"))
    parser.add_argument("--expire-days", type=int, default=7,
                        help="Retention days; <=0 skips retention rule")
    parser.add_argument("--tag-pattern", default=".*",
                        help="Retention tag selector regexp")
    parser.add_argument("--public", dest="is_public", action=argparse.BooleanOptionalAction,
                        default=True, help="--public / --no-public")
    args = parser.parse_args()

    credentials = BasicCredentials(ak=args.ak, sk=args.sk)
    client = SwrClient.new_builder().with_credentials(credentials).with_region(SwrRegion.value_of(args.region)).build()

    failed = False

    # Set repo visibility
    update_body = UpdateRepoRequestBody(is_public=args.is_public)
    request = UpdateRepoRequest(namespace=args.namespace, repository=args.repo, body=update_body)
    try:
        client.update_repo(request)
        print(f"Set {args.namespace}/{args.repo} public={args.is_public}: OK")
    except Exception as e:
        # Fail loud: a silent no-op here once left a repo private (wrong region),
        # blocking all downstream pulls with Authenticate Error.
        print(f"Set visibility error: {e}")
        failed = True

    # Set retention rule (skip when expire-days <= 0)
    if args.expire_days > 0:
        tag_selector = RetentionSelector(kind="regexp", pattern=args.tag_pattern)
        rule = RetentionRule(
            template="date_rule",
            params={"days": str(args.expire_days)},
            tag_selectors=[tag_selector],
        )
        retention_body = CreateRetentionRequestBody(algorithm="or", rules=[rule])
        retention_req = CreateRetentionRequest(namespace=args.namespace, repository=args.repo, body=retention_body)
        try:
            client.create_retention(retention_req)
            print(f"Set {args.expire_days}-day retention rule: OK")
        except Exception as e:
            err_str = str(e)
            if "already" in err_str.lower() or "exist" in err_str.lower():
                print("Retention rule already exists, skipping")
            else:
                print(f"Retention rule error: {e}")
                failed = True
    else:
        print("Retention skipped (expire-days<=0)")

    print("Done!")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
