PLUGIN_NAME = "计算器"
PLUGIN_DESCRIPTION = "数学计算和表达式求值"
PLUGIN_KEYWORDS = ["计算", "算一下", "多少", "等于", "calculator"]

import re
import math

def execute(params: str) -> str:
    """安全地计算数学表达式"""
    expr = params.strip()
    if not expr:
        return "请提供计算表达式，例如：计算 2+3*4"

    # 清理表达式
    expr = expr.replace("×", "*").replace("÷", "/").replace("（", "(").replace("）", ")")

    # 安全检查：只允许数字、运算符、括号、小数点、空格
    if not re.match(r'^[\d\s\+\-\*\/\(\)\.\%\^\,]+$', expr):
        return f"不支持的表达式: {expr}"

    try:
        # 替换 ^ 为 **
        expr = expr.replace("^", "**")
        # 安全求值
        result = eval(expr, {"__builtins__": {}}, {"math": math, "abs": abs, "round": round})
        return f"{params.strip()} = {result}"
    except Exception as e:
        return f"计算错误: {e}"
