#!/usr/bin/env python3
"""创建 Supabase Storage 桶 clips（若不存在）。用法: python scripts/init_supabase_storage.py"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / "deploy" / ".env")

import os

from supabase import create_client


def main() -> None:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "clips")
    public = os.environ.get("SUPABASE_STORAGE_PUBLIC", "true").lower() in ("1", "true", "yes")

    sb = create_client(url, key)

    # 列出已有桶
    try:
        buckets = sb.storage.list_buckets()
        names = [b.name for b in buckets] if buckets else []
        if hasattr(buckets, "__iter__") and buckets and not names:
            # 部分版本返回 dict 列表
            names = [b.get("name", b.get("id", "")) for b in buckets]
    except Exception as e:
        print(f"list_buckets 警告: {e}")
        names = []

    if bucket in names:
        print(f"桶 '{bucket}' 已存在，无需创建。")
        return

    print(f"正在创建桶 '{bucket}' (public={public}) ...")
    try:
        sb.storage.create_bucket(bucket, options={"public": public})
        print(f"成功创建桶: {bucket}")
    except Exception as e:
        err = str(e)
        if "already exists" in err.lower() or "duplicate" in err.lower():
            print(f"桶 '{bucket}' 已存在。")
            return
        print(f"创建失败: {e}")
        print("\n请手动创建：Supabase 控制台 → Storage → New bucket")
        print(f"  Name: {bucket}")
        print(f"  Public bucket: {'勾选' if public else '不勾选'}")
        sys.exit(1)

    print("完成。请重新点击「生成视频片段」。")


if __name__ == "__main__":
    main()
