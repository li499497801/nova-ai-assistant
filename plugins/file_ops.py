PLUGIN_NAME = "文件操作"
PLUGIN_DESCRIPTION = "读取、写入、列出文件"
PLUGIN_KEYWORDS = ["读取文件", "写入文件", "列出文件", "文件内容", "read file", "write file"]

import os

def execute(params: str) -> str:
    """文件操作"""
    p = params.strip()

    # 列出文件
    if p.startswith("列出") or p.startswith("list"):
        path = p.replace("列出", "").replace("list", "").strip() or "."
        try:
            items = os.listdir(path)
            result = []
            for item in items[:50]:
                full = os.path.join(path, item)
                if os.path.isdir(full):
                    result.append(f"📁 {item}/")
                else:
                    size = os.path.getsize(full)
                    result.append(f"📄 {item} ({size} bytes)")
            return "\n".join(result) if result else "目录为空"
        except Exception as e:
            return f"列出失败: {e}"

    # 读取文件
    if p.startswith("读取") or p.startswith("read"):
        path = p.replace("读取", "").replace("read", "").strip()
        if not path:
            return "请指定文件路径"
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(10000)
            return content
        except Exception as e:
            return f"读取失败: {e}"

    # 写入文件
    if p.startswith("写入") or p.startswith("write"):
        parts = p.replace("写入", "").replace("write", "").strip().split(" ", 1)
        if len(parts) < 2:
            return "格式: 写入 文件路径 内容"
        path, content = parts[0], parts[1]
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"已写入 {path}"
        except Exception as e:
            return f"写入失败: {e}"

    return "支持的操作：列出 [目录]、读取 文件路径、写入 文件路径 内容"
