"""
Nova — AI 私人助手
简单、可进化、可扩展
"""

import json
import os
import sys
import time
import uuid
import importlib.util
import sqlite3
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request

# ── 初始化 ──────────────────────────────────────────────────

app = Flask(__name__)
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
DB_PATH = BASE_DIR / "nova.db"
PLUGINS_DIR = BASE_DIR / "plugins"

# 加载配置
def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

CONFIG = load_config()

# ── 数据库 ──────────────────────────────────────────────────

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                model TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                plugin_used TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()

# ── 会话管理 ────────────────────────────────────────────────

def create_session(name=None):
    sid = str(uuid.uuid4())[:8]
    if not name:
        name = f"对话 {datetime.now().strftime('%m-%d %H:%M')}"
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO sessions (id, name, model, created_at, updated_at) VALUES (?,?,?,?,?)",
            (sid, name, CONFIG["default_model"], now, now),
        )
        conn.commit()
    return {"id": sid, "name": name, "model": CONFIG["default_model"], "created_at": now}

def get_sessions():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]

def delete_session(sid):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM messages WHERE session_id=?", (sid,))
        conn.execute("DELETE FROM sessions WHERE id=?", (sid,))
        conn.commit()

def get_messages(sid, limit=100):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id=? ORDER BY created_at ASC LIMIT ?",
            (sid, limit),
        ).fetchall()
    return [dict(r) for r in rows]

def save_message(sid, role, content, plugin_used=None):
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, plugin_used, created_at) VALUES (?,?,?,?,?)",
            (sid, role, content, plugin_used, now),
        )
        conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now, sid))
        conn.commit()

# ── 记忆系统 ────────────────────────────────────────────────

def add_memory(content):
    now = datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO memories (content, created_at) VALUES (?,?)", (content, now))
        conn.commit()

def get_memories(limit=20):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]

def delete_memory(mid):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM memories WHERE id=?", (mid,))
        conn.commit()

# ── 插件系统 ────────────────────────────────────────────────

plugins = {}

def load_plugins():
    """扫描 plugins/ 目录，自动加载所有插件"""
    global plugins
    plugins = {}
    if not PLUGINS_DIR.exists():
        return

    for f in PLUGINS_DIR.glob("*.py"):
        if f.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f.stem, f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            if hasattr(mod, "execute") and callable(mod.execute):
                plugins[f.stem] = {
                    "name": getattr(mod, "PLUGIN_NAME", f.stem),
                    "description": getattr(mod, "PLUGIN_DESCRIPTION", ""),
                    "keywords": getattr(mod, "PLUGIN_KEYWORDS", []),
                    "execute": mod.execute,
                    "file": f.name,
                }
                print(f"  [插件] 已加载: {plugins[f.stem]['name']} ({f.name})")
        except Exception as e:
            print(f"  [插件] 加载失败: {f.name} — {e}")

def find_plugin(message):
    """根据关键词匹配插件（优先匹配更长的关键词）"""
    msg_lower = message.lower()
    best_match = None
    best_keyword_len = 0

    for pid, p in plugins.items():
        for kw in p["keywords"]:
            kw_lower = kw.lower()
            if kw_lower in msg_lower and len(kw_lower) > best_keyword_len:
                best_match = (pid, p)
                best_keyword_len = len(kw_lower)

    return best_match if best_match else (None, None)

def get_plugin_list():
    """返回插件列表（不含 execute 函数）"""
    return [
        {"id": pid, "name": p["name"], "description": p["description"], "keywords": p["keywords"], "file": p["file"]}
        for pid, p in plugins.items()
    ]

# ── 模型调用 ────────────────────────────────────────────────

def call_model(messages, model_id=None, stream=False):
    """统一模型调用接口（OpenAI 兼容协议）"""
    if not model_id:
        model_id = CONFIG["default_model"]

    model_cfg = CONFIG["models"].get(model_id)
    if not model_cfg:
        return f"错误：未找到模型 {model_id}"

    url = f"{model_cfg['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {model_cfg['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_cfg["model_id"],
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.7,
        "stream": stream,
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"模型调用失败: {e}"

def build_messages(sid, user_msg, model_id=None):
    """构建完整的消息列表（系统提示 + 记忆 + 历史 + 当前消息）"""
    msgs = []

    # 系统提示
    system = CONFIG.get("system_prompt", "你是 Nova，一个智能 AI 助手。")

    # 注入长期记忆
    memories = get_memories(10)
    if memories:
        mem_text = "\n".join(f"- {m['content']}" for m in memories)
        system += f"\n\n用户让你记住的事情：\n{mem_text}"

    msgs.append({"role": "system", "content": system})

    # 历史消息（滑动窗口）
    history = get_messages(sid, limit=CONFIG.get("max_context_turns", 20) * 2)
    for m in history:
        msgs.append({"role": m["role"], "content": m["content"]})

    # 当前消息
    msgs.append({"role": "user", "content": user_msg})

    return msgs

# ── 处理用户消息 ────────────────────────────────────────────

def process_message(sid, user_msg, model_id=None):
    """处理用户消息：检查插件 → 调用模型 → 返回结果"""
    plugin_used = None

    # 1. 检查是否要记住东西
    if user_msg.startswith("记住") or user_msg.lower().startswith("remember"):
        content = user_msg.replace("记住", "").replace("remember", "").strip()
        if content:
            add_memory(content)
            return f"好的，我记住了：{content}", "memory"

    # 2. 检查插件匹配
    pid, plugin = find_plugin(user_msg)
    if plugin:
        try:
            # 提取参数（去掉关键词本身）
            params = user_msg
            for kw in plugin["keywords"]:
                params = params.replace(kw, "").strip()
            result = plugin["execute"](params or user_msg)
            plugin_used = pid
            # 把插件结果和用户问题一起给模型润色
            msgs = build_messages(sid, f"用户问：{user_msg}\n\n插件查询结果：{result}\n\n请根据以上结果回答用户的问题。", model_id)
            answer = call_model(msgs, model_id)
            return answer, plugin_used
        except Exception as e:
            return f"插件执行出错: {e}", pid

    # 3. 直接调用模型
    msgs = build_messages(sid, user_msg, model_id)
    answer = call_model(msgs, model_id)
    return answer, None

# ── API 路由 ────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.json
    sid = data.get("session_id")
    msg = data.get("message", "").strip()
    model = data.get("model")

    if not sid or not msg:
        return jsonify({"error": "缺少 session_id 或 message"}), 400

    # 保存用户消息
    save_message(sid, "user", msg)

    # 处理消息
    answer, plugin_used = process_message(sid, msg, model)

    # 保存助手回复
    save_message(sid, "assistant", answer, plugin_used)

    return jsonify({
        "reply": answer,
        "plugin_used": plugin_used,
        "model": model or CONFIG["default_model"],
    })

@app.route("/api/sessions", methods=["GET"])
def api_sessions():
    return jsonify(get_sessions())

@app.route("/api/sessions", methods=["POST"])
def api_create_session():
    data = request.json or {}
    session = create_session(data.get("name"))
    return jsonify(session)

@app.route("/api/sessions/<sid>", methods=["DELETE"])
def api_delete_session(sid):
    delete_session(sid)
    return jsonify({"ok": True})

@app.route("/api/sessions/<sid>/messages")
def api_messages(sid):
    return jsonify(get_messages(sid))

@app.route("/api/models")
def api_models():
    models = []
    for mid, cfg in CONFIG["models"].items():
        models.append({"id": mid, "name": cfg.get("name", mid)})
    return jsonify({
        "models": models,
        "default": CONFIG["default_model"],
    })

@app.route("/api/models/switch", methods=["POST"])
def api_switch_model():
    data = request.json
    model_id = data.get("model")
    if model_id and model_id in CONFIG["models"]:
        CONFIG["default_model"] = model_id
        # 保存到配置文件
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, indent=2, ensure_ascii=False)
        return jsonify({"ok": True, "default": model_id})
    return jsonify({"error": "无效的模型 ID"}), 400

@app.route("/api/plugins")
def api_plugins():
    return jsonify(get_plugin_list())

@app.route("/api/memories", methods=["GET"])
def api_memories():
    return jsonify(get_memories())

@app.route("/api/memories", methods=["POST"])
def api_add_memory():
    data = request.json
    content = data.get("content", "").strip()
    if content:
        add_memory(content)
        return jsonify({"ok": True})
    return jsonify({"error": "内容不能为空"}), 400

@app.route("/api/memories/<int:mid>", methods=["DELETE"])
def api_delete_memory(mid):
    delete_memory(mid)
    return jsonify({"ok": True})

@app.route("/api/reload-plugins", methods=["POST"])
def api_reload_plugins():
    load_plugins()
    return jsonify({"ok": True, "plugins": get_plugin_list()})

# ── 通知系统 ────────────────────────────────────────────────

notifications = []  # 存储待推送的通知

def add_notification(title: str, content: str, task_id: int = None):
    """添加通知"""
    notifications.append({
        "id": len(notifications) + 1,
        "title": title,
        "content": content,
        "task_id": task_id,
        "time": datetime.now().isoformat(),
        "read": False,
    })
    print(f"[通知] {title}: {content[:50]}")

@app.route("/api/notifications")
def api_notifications():
    """获取通知列表"""
    return jsonify(notifications[-50:])

@app.route("/api/notifications/<int:nid>/read", methods=["POST"])
def api_read_notification(nid):
    """标记通知已读"""
    for n in notifications:
        if n["id"] == nid:
            n["read"] = True
    return jsonify({"ok": True})

@app.route("/api/notifications/clear", methods=["POST"])
def api_clear_notifications():
    """清空通知"""
    notifications.clear()
    return jsonify({"ok": True})

# ── 后台调度器 ──────────────────────────────────────────────

def run_scheduled_tasks():
    """执行定时任务"""
    try:
        # 导入调度器插件
        if "scheduler" in plugins:
            from plugins.scheduler import get_pending_tasks, mark_task_done
            tasks = get_pending_tasks()
            for task in tasks:
                print(f"[调度] 执行任务: {task['name']}")
                try:
                    # 调用模型生成回复
                    prompt = f"执行定时任务: {task['params']}\n请直接给出简洁的执行结果或提醒内容。"
                    result = call_model([{"role": "user", "content": prompt}])
                    add_notification(task["name"], result, task["id"])
                    mark_task_done(task["id"])
                except Exception as e:
                    add_notification(f"任务失败: {task['name']}", str(e), task["id"])
    except Exception as e:
        print(f"[调度器错误] {e}")

def scheduler_loop():
    """后台调度器主循环"""
    import time
    time.sleep(5)  # 等待启动完成
    print("[调度器] 后台任务调度器已启动")
    while True:
        try:
            run_scheduled_tasks()
        except Exception as e:
            print(f"[调度器错误] {e}")
        time.sleep(30)  # 每30秒检查一次

# ── 主动报告 ────────────────────────────────────────────────

def proactive_report():
    """主动报告：定期生成状态报告"""
    import time
    time.sleep(10)  # 等待启动完成
    print("[报告] 主动报告系统已启动")
    while True:
        try:
            # 每小时生成一次摘要
            time.sleep(3600)

            # 获取最近的对话
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                recent = conn.execute(
                    "SELECT role, content FROM messages ORDER BY created_at DESC LIMIT 20"
                ).fetchall()

            if recent:
                history = "\n".join(f"[{r['role']}] {r['content'][:100]}" for r in reversed(recent))
                prompt = f"以下是最近的对话记录，请生成一份简洁的摘要报告：\n\n{history}"
                summary = call_model([{"role": "user", "content": prompt}])
                add_notification("📊 每小时报告", summary)

        except Exception as e:
            print(f"[报告错误] {e}")

# ── 启动 ────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  Nova — AI 私人助手")
    print("=" * 50)

    init_db()
    print("[数据库] 已初始化")

    load_plugins()
    print(f"[插件] 已加载 {len(plugins)} 个插件")

    host = CONFIG.get("host", "127.0.0.1")
    port = CONFIG.get("port", 8888)
    url = f"http://localhost:{port}"

    print(f"[模型] 默认: {CONFIG['default_model']}")
    print(f"[服务] {url}")
    print(f"[模式] {'本地' if host == '127.0.0.1' else '局域网'}")
    print("=" * 50)

    # 启动后台调度器
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()

    # 启动主动报告
    report_thread = threading.Thread(target=proactive_report, daemon=True)
    report_thread.start()

    # 自动打开浏览器
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    app.run(host=host, port=port, debug=False)
