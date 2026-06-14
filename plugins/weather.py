PLUGIN_NAME = "天气查询"
PLUGIN_DESCRIPTION = "查询指定城市的天气信息"
PLUGIN_KEYWORDS = ["天气", "气温", "weather"]

def execute(params: str) -> str:
    """查询天气（免费 API，无需 key）"""
    import requests

    city = params.strip()
    if not city:
        return "请指定城市，例如：天气 北京"

    try:
        # 使用 wttr.in 免费天气 API
        r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=10)
        r.raise_for_status()
        data = r.json()

        current = data["current_condition"][0]
        temp = current["temp_C"]
        feels = current["FeelsLikeC"]
        humidity = current["humidity"]
        wind = current["windspeedKmph"]
        desc_cn = current["lang_zh"][0]["value"] if current.get("lang_zh") else current["weatherDesc"][0]["value"]

        return f"{city}天气：{desc_cn}，气温 {temp}°C（体感 {feels}°C），湿度 {humidity}%，风速 {wind}km/h"
    except Exception as e:
        return f"天气查询失败: {e}"
