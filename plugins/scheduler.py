PLUGIN_NAME = "定时任务"
PLUGIN_DESCRIPTION = "创建自动执行的定时任务"
PLUGIN_KEYWORDS = ["定时", "自动执行", "提醒我", "每隔", "每天", "schedule", "remind"]

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "nova.db"

def init_scheduler_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                params TEXT NOT NULL,
                interval_seconds INTEGER DEFAULT 0,
                cron_hour INTEGER DEFAULT -1,
                cron_minute INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                last_run TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()

init_scheduler_db()

def execute(params: str) -> str:
    """定时任务管理"""
    p = params.strip()

    # 列出任务
    if not p or p in ["列表", "list", "查看"]:
        return list_tasks()

    # 删除任务
    if p.startswith("删除") or p.startswith("delete"):
        tid = p.replace("删除", "").replace("delete", "").strip()
        return delete_task(tid)

    # 启用/禁用
    if p.startswith("启用") or p.startswith("enable"):
        tid = p.replace("启用", "").replace("enable", "").strip()
        return toggle_task(tid, True)
    if p.startswith("禁用") or p.startswith("disable"):
        tid = p.replace("禁用", "").replace("disable", "").strip()
        return toggle_task(tid, False)

    # 创建定时提醒
    # 格式: 提醒我 每隔 X 分钟/小时 做某事
    # 格式: 提醒我 每天 HH:MM 做某事
    return create_task(p)


def create_task(text: str) -> str:
    """创建定时任务"""
    now = datetime.now()

    # 每隔 X 分钟/小时
    if "每隔" in text:
        parts = text.split("每隔", 1)
        rest = parts[1].strip()

        # 解析时间
        interval = 0
        if "分钟" in rest:
            num = ""
            for c in rest:
                if c.isdigit():
                    num += c
                elif num:
                    break
            interval = int(num) * 60 if num else 300
            task_desc = rest.split("分钟", 1)[-1].strip() or "执行任务"
        elif "小时" in rest:
            num = ""
            for c in rest:
                if c.isdigit():
                    num += c
                elif num:
                    break
            interval = int(num) * 3600 if num else 3600
            task_desc = rest.split("小时", 1)[-1].strip() or "执行任务"
        elif "秒" in rest:
            num = ""
            for c in rest:
                if c.isdigit():
                    num += c
                elif num:
                    break
            interval = int(num) if num else 60
            task_desc = rest.split("秒", 1)[-1].strip() or "执行任务"
        else:
            return "格式: 每隔 X 分钟/小时 做某事"

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO scheduled_tasks (name, task_type, params, interval_seconds, created_at) VALUES (?,?,?,?,?)",
                (f"定时: {task_desc[:20]}", "interval", task_desc, interval, now.isoformat()),
            )
            conn.commit()
        return f"✅ 已创建定时任务: 每隔 {interval//60 if interval>=60 else interval}{'分钟' if interval>=60 else '秒'} 执行「{task_desc}」"

    # 每天 HH:MM
    if "每天" in text:
        parts = text.split("每天", 1)
        rest = parts[1].strip()

        # 解析时间
        hour, minute = 9, 0
        for sep in [":", "：", "点"]:
            if sep in rest:
                time_part = rest.split(sep, 1)
                try:
                    hour = int(time_part[0].strip())
                    min_str = time_part[1].strip().replace("分", "")
                    minute = int(min_str[:2]) if min_str[:2].isdigit() else 0
                except:
                    pass
                break

        task_desc = rest
        # 去掉时间部分
        for marker in [":", "：", "点"]:
            if marker in task_desc:
                task_desc = task_desc.split(marker, 1)[1].strip()
                break
        task_desc = task_desc.replace("分", "").strip() or "执行任务"

        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO scheduled_tasks (name, task_type, params, cron_hour, cron_minute, created_at) VALUES (?,?,?,?,?,?)",
                (f"每日: {task_desc[:20]}", "daily", task_desc, hour, minute, now.isoformat()),
            )
            conn.commit()
        return f"✅ 已创建每日任务: 每天 {hour:02d}:{minute:02d} 执行「{task_desc}」"

    # 普通一次性提醒
    # 格式: X 分钟后提醒我 做某事
    if "分钟后" in text:
        num = ""
        for c in text:
            if c.isdigit():
                num += c
            elif num:
                break
        minutes = int(num) if num else 5
        task_desc = text.split("分钟后", 1)[-1].strip() or "提醒"

        run_at = now + timedelta(minutes=minutes)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO scheduled_tasks (name, task_type, params, interval_seconds, created_at) VALUES (?,?,?,?,?)",
                (f"提醒: {task_desc[:20]}", "once", task_desc, int(run_at.timestamp()), now.isoformat()),
            )
            conn.commit()
        return f"✅ 已设置提醒: {minutes}分钟后提醒「{task_desc}」（{run_at.strftime('%H:%M')}）"

    return """创建任务格式：

1. 提醒我 每隔 30 分钟 站起来活动
2. 提醒我 每天 9:00 查看邮件
3. 提醒我 10分钟后 喝水

管理命令：
• 列表 — 查看所有任务
• 删除 ID — 删除任务
• 启用/禁用 ID — 开关任务"""


def list_tasks() -> str:
    """列出所有任务"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM scheduled_tasks ORDER BY id").fetchall()

    if not rows:
        return "暂无定时任务"

    result = ["定时任务列表：\n"]
    for r in rows:
        status = "✅" if r["enabled"] else "❌"
        if r["task_type"] == "interval":
            interval = r["interval_seconds"]
            if interval >= 3600:
                time_str = f"每{interval//3600}小时"
            elif interval >= 60:
                time_str = f"每{interval//60}分钟"
            else:
                time_str = f"每{interval}秒"
        elif r["task_type"] == "daily":
            time_str = f"每天 {r['cron_hour']:02d}:{r['cron_minute']:02d}"
        elif r["task_type"] == "once":
            run_at = datetime.fromtimestamp(r["interval_seconds"])
            time_str = f"一次性 ({run_at.strftime('%m-%d %H:%M')})"
        else:
            time_str = r["task_type"]

        last = f" (上次: {r['last_run'][:16]})" if r["last_run"] else ""
        result.append(f"{status} #{r['id']} [{time_str}] {r['name']}{last}")

    return "\n".join(result)


def delete_task(tid: str) -> str:
    """删除任务"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM scheduled_tasks WHERE id=?", (int(tid),))
            conn.commit()
        return f"✅ 已删除任务 #{tid}"
    except:
        return f"删除失败，任务 #{tid} 不存在"


def toggle_task(tid: str, enabled: bool) -> str:
    """启用/禁用任务"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE scheduled_tasks SET enabled=? WHERE id=?", (1 if enabled else 0, int(tid)))
            conn.commit()
        return f"✅ 任务 #{tid} 已{'启用' if enabled else '禁用'}"
    except:
        return f"操作失败，任务 #{tid} 不存在"


def get_pending_tasks():
    """获取需要执行的任务（由调度器调用）"""
    now = datetime.now()
    tasks = []

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM scheduled_tasks WHERE enabled=1").fetchall()

    for r in rows:
        should_run = False

        if r["task_type"] == "interval":
            # 周期任务
            if r["last_run"]:
                last = datetime.fromisoformat(r["last_run"])
                if (now - last).total_seconds() >= r["interval_seconds"]:
                    should_run = True
            else:
                should_run = True

        elif r["task_type"] == "daily":
            # 每日任务
            if r["last_run"]:
                last = datetime.fromisoformat(r["last_run"])
                if last.date() < now.date() and now.hour >= r["cron_hour"] and now.minute >= r["cron_minute"]:
                    should_run = True
            else:
                if now.hour >= r["cron_hour"] and now.minute >= r["cron_minute"]:
                    should_run = True

        elif r["task_type"] == "once":
            # 一次性任务
            run_at = datetime.fromtimestamp(r["interval_seconds"])
            if now >= run_at and not r["last_run"]:
                should_run = True

        if should_run:
            tasks.append(dict(r))

    return tasks


def mark_task_done(tid):
    """标记任务完成"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE scheduled_tasks SET last_run=? WHERE id=?", (datetime.now().isoformat(), tid))
        # 一次性任务执行后自动禁用
        conn.execute("UPDATE scheduled_tasks SET enabled=0 WHERE id=? AND task_type='once'", (tid,))
        conn.commit()
