#!/usr/bin/env python3
"""检查 deploy/.env 里的 Supabase 是否配对。用法: python scripts/verify_supabase.py [--online]"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / "deploy" / ".env"


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        print(f"找不到配置文件: {path}")
        sys.exit(1)
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip("\r\n")
    return env


def jwt_role(token: str) -> str | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return data.get("role")
    except Exception:
        return None


def check_offline(env: dict[str, str]) -> list[str]:
    problems: list[str] = []
    ok: list[str] = []

    url = env.get("SUPABASE_URL", "")
    if url and "supabase.co" in url and "xxxxxxxx" not in url:
        ok.append(f"项目地址已填写: {url}")
    else:
        problems.append("SUPABASE_URL 未正确填写（应是 https://xxx.supabase.co）")

    db = env.get("DATABASE_URL", "")
    db_placeholders = ("xxxxx", "aws-0-xxx", "[YOUR-PASSWORD]", "YOUR_DB_PASSWORD", ":password@")
    if not db or any(p in db for p in db_placeholders):
        problems.append(
            "DATABASE_URL 还是模板或未替换密码。请把 [YOUR-PASSWORD] 换成建项目时的数据库密码。"
        )
    else:
        ok.append("DATABASE_URL 已填写（可用 --online 测试能否连上）")

    key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    is_placeholder_key = not key or key.startswith("your-") or "粘贴" in key
    role = jwt_role(key) if not is_placeholder_key else None
    if role == "service_role":
        ok.append("SUPABASE_SERVICE_ROLE_KEY 是 service_role（正确）")
    elif role == "anon":
        problems.append(
            "你把 anon 公钥填进了 SUPABASE_SERVICE_ROLE_KEY。"
            "请到 Settings → API，复制 service_role 那一行的 secret（不要复制 anon）。"
        )
    elif not key or "your-" in key:
        problems.append("SUPABASE_SERVICE_ROLE_KEY 未填写")
    else:
        problems.append(f"SUPABASE_SERVICE_ROLE_KEY 无法识别（role={role}）")

    anon = env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
    if anon and anon != "your-anon-key":
        ok.append("NEXT_PUBLIC_SUPABASE_ANON_KEY 已填写（可选）")
    elif role == "anon":
        ok.append("提示: 可把当前误填在 SERVICE_ROLE 的 anon 密钥移到 NEXT_PUBLIC_SUPABASE_ANON_KEY")

    bucket = env.get("SUPABASE_STORAGE_BUCKET", "")
    if bucket == "clips":
        ok.append("Storage 桶名 clips 已配置")
    else:
        problems.append("SUPABASE_STORAGE_BUCKET 建议设为 clips")

    return problems, ok


def check_online(env: dict[str, str]) -> None:
    url = env["SUPABASE_URL"].rstrip("/")
    key = env["SUPABASE_SERVICE_ROLE_KEY"]

    print("\n--- 联网测试 REST（episodes 表）---")
    try:
        import httpx
    except ImportError:
        print("请先安装: pip install httpx")
        return

    r = httpx.get(
        f"{url}/rest/v1/episodes?select=id&limit=1",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
        timeout=20,
    )
    print("HTTP", r.status_code)
    if r.status_code == 200:
        print("通过: 能访问 Supabase，且 episodes 表存在。")
    else:
        print("失败:", r.text[:400])

    db = env.get("DATABASE_URL", "")
    if "xxxxx" in db or "aws-0-xxx" in db:
        print("\n--- 跳过数据库直连（DATABASE_URL 未配好）---")
        return

    print("\n--- 联网测试 PostgreSQL ---")
    try:
        import psycopg2
    except ImportError:
        print("请先安装: pip install psycopg2-binary")
        return

    try:
        conn = psycopg2.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        print("通过: SELECT 1 =>", cur.fetchone())
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY 1"
        )
        tables = [row[0] for row in cur.fetchall()]
        expected = {"episodes", "subtitle_lines", "clip_assets", "share_bundles"}
        missing = expected - set(tables)
        print("当前表:", ", ".join(tables) or "(无)")
        if missing:
            print("缺少表:", ", ".join(sorted(missing)), "→ 请在 SQL Editor 运行 migrations/001_initial_schema.sql")
        else:
            print("通过: 核心表都在。")
        conn.close()
    except Exception as e:
        print("失败:", e)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true", help="联网测试连接（会用到 .env 里的密钥）")
    args = parser.parse_args()

    env = load_env(ENV_PATH)
    print(f"读取: {ENV_PATH}\n")

    problems, ok = check_offline(env)
    for line in ok:
        print("[OK]", line)
    for line in problems:
        print("[要改]", line)

    if problems:
        print(f"\n结论: 还有 {len(problems)} 项需要修改，改完再运行本脚本。")
    else:
        print("\n结论: 本地检查全部通过。")

    if args.online:
        if problems:
            print("\n仍有配置错误，建议先改 .env 再 --online。")
        else:
            check_online(env)

    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
