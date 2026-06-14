PLUGIN_NAME = "系统命令"
PLUGIN_DESCRIPTION = "执行系统命令（文件操作、进程管理等）"
PLUGIN_KEYWORDS = ["执行", "运行", "命令", "cmd", "shell", "run", "exec"]

import subprocess
import os

def execute(params: str) -> str:
    """执行系统命令"""
    cmd = params.strip()
    if not cmd:
        return "请提供要执行的命令，例如：执行 dir"

    try:
        # 执行命令
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.expanduser("~"),
        )

        output = []
        if result.stdout:
            output.append(result.stdout)
        if result.stderr:
            output.append(f"[stderr]\n{result.stderr}")
        output.append(f"[exit code: {result.returncode}]")

        return "\n".join(output) if output else "命令执行完成，无输出"

    except subprocess.TimeoutExpired:
        return "命令执行超时（30秒）"
    except Exception as e:
        return f"命令执行失败: {e}"
