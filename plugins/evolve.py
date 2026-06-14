PLUGIN_NAME = "自我进化"
PLUGIN_DESCRIPTION = "AI 自我迭代：修改自身配置、创建插件、优化行为"
PLUGIN_KEYWORDS = ["进化", "迭代", "自我改进", "创建插件", "修改配置", "evolve", "upgrade"]

import os
import json
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
PLUGINS_DIR = BASE_DIR / "plugins"
CONFIG_PATH = BASE_DIR / "config.json"
EVOLVE_LOG = BASE_DIR / "evolve.log"

def log_action(action: str):
    """记录进化操作"""
    with open(EVOLVE_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat()}] {action}\n")

def execute(params: str) -> str:
    """自我进化操作"""
    p = params.strip().lower()

    # ── 创建新插件 ──
    if p.startswith("创建插件") or p.startswith("create plugin"):
        return create_plugin(params)

    # ── 修改系统提示词 ──
    if p.startswith("修改提示词") or p.startswith("system prompt"):
        return modify_system_prompt(params)

    # ── 修改配置 ──
    if p.startswith("修改配置") or p.startswith("config"):
        return modify_config(params)

    # ── 查看自身状态 ──
    if "状态" in p or "status" in p:
        return get_status()

    # ── 查看进化日志 ──
    if "日志" in p or "log" in p:
        return get_evolve_log()

    # ── 优化插件 ──
    if "优化" in p or "improve" in p:
        return improve_plugin(params)

    return """自我进化支持的操作：

1. 创建插件 <名称> <代码>
   - 创建新的 .py 插件文件

2. 修改提示词 <新提示词>
   - 修改系统提示词（影响 AI 行为）

3. 修改配置 <key> <value>
   - 修改 config.json 中的配置项

4. 状态
   - 查看 Nova 自身状态

5. 日志
   - 查看进化历史日志

6. 优化 <插件名>
   - 改进指定插件的代码"""


def create_plugin(params: str) -> str:
    """创建新插件"""
    # 提取插件名和代码
    text = params.replace("创建插件", "").replace("create plugin", "").strip()

    if "```" in text:
        # 从代码块提取
        parts = text.split("```")
        name_part = parts[0].strip()
        code_part = parts[1].strip()
        if code_part.startswith("python"):
            code_part = code_part[6:]
    else:
        # 格式: 名称|代码
        if "|" in text:
            name_part, code_part = text.split("|", 1)
        else:
            return "格式: 创建插件 插件名 | 代码内容\n或: 创建插件 插件名 ```python\ncode\n```"

    plugin_name = name_part.strip().replace(" ", "_")
    if not plugin_name:
        return "请提供插件名称"

    filepath = PLUGINS_DIR / f"{plugin_name}.py"

    # 备份旧文件
    if filepath.exists():
        backup = filepath.with_suffix(f".py.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}")
        shutil.copy2(filepath, backup)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code_part.strip())

    log_action(f"Created plugin: {plugin_name}.py")
    return f"✅ 插件已创建: {plugin_name}.py\n路径: {filepath}\n重启 Nova 后生效，或调用 /api/reload-plugins 热加载"


def modify_system_prompt(params: str) -> str:
    """修改系统提示词"""
    new_prompt = params.replace("修改提示词", "").replace("system prompt", "").strip()
    if not new_prompt:
        return "请提供新的系统提示词"

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    old_prompt = config.get("system_prompt", "")
    config["system_prompt"] = new_prompt

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    log_action(f"System prompt changed: {old_prompt[:50]}... -> {new_prompt[:50]}...")
    return f"✅ 系统提示词已更新\n新提示词: {new_prompt}"


def modify_config(params: str) -> str:
    """修改配置"""
    text = params.replace("修改配置", "").replace("config", "").strip()
    parts = text.split(" ", 1)
    if len(parts) < 2:
        return "格式: 修改配置 key value\n例如: 修改配置 max_context_turns 500"

    key, value = parts[0], parts[1]

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 尝试解析为数字
    try:
        value = int(value)
    except ValueError:
        try:
            value = float(value)
        except ValueError:
            pass

    config[key] = value

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    log_action(f"Config changed: {key} = {value}")
    return f"✅ 配置已更新: {key} = {value}"


def get_status() -> str:
    """查看 Nova 状态"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    plugins = list(PLUGINS_DIR.glob("*.py"))
    plugin_names = [p.stem for p in plugins if not p.name.startswith("_")]

    return f"""Nova 状态：

模型: {config.get('default_model', 'unknown')}
上下文轮数: {config.get('max_context_turns', 20)}
端口: {config.get('port', 8888)}

已加载插件 ({len(plugin_names)}):
{chr(10).join(f'  • {p}' for p in plugin_names)}

配置文件: {CONFIG_PATH}
插件目录: {PLUGINS_DIR}
数据库: {BASE_DIR / 'nova.db'}"""


def get_evolve_log() -> str:
    """查看进化日志"""
    if not EVOLVE_LOG.exists():
        return "暂无进化日志"
    with open(EVOLVE_LOG, "r", encoding="utf-8") as f:
        return f"进化日志：\n{f.read()[-2000:]}"


def improve_plugin(params: str) -> str:
    """优化插件（返回当前代码供 AI 分析改进）"""
    plugin_name = params.replace("优化", "").replace("improve", "").strip()
    filepath = PLUGINS_DIR / f"{plugin_name}.py"

    if not filepath.exists():
        return f"插件 {plugin_name} 不存在"

    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()

    return f"当前 {plugin_name}.py 代码：\n\n```python\n{code}\n```\n\n请分析并提供改进后的代码，然后用「创建插件 {plugin_name}」覆盖。"
