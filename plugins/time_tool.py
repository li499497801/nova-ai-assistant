PLUGIN_NAME = "时间工具"
PLUGIN_DESCRIPTION = "查询当前时间、日期、倒计时"
PLUGIN_KEYWORDS = ["几点了", "现在时间", "今天日期", "星期几", "what time", "time now"]

from datetime import datetime, timedelta

def execute(params: str) -> str:
    """查询时间相关信息"""
    now = datetime.now()
    p = params.strip().lower()

    if "星期" in p or "周" in p:
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        return f"今天是 {now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]}"

    if "日期" in p or "今天" in p:
        return f"今天是 {now.strftime('%Y年%m月%d日')}"

    # 默认返回完整时间
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return f"现在是 {now.strftime('%Y年%m月%d日 %H:%M:%S')} {weekdays[now.weekday()]}"
