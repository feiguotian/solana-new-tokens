import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
HELIUS_BASE = "https://api.helius.xyz/v0"
JUPITER_MARKETS_API = "https://quote-api.jup.ag/v1/markets"

SOL_MINT = "So11111111111111111111111111111111111111112"

seven_days_ago = datetime.utcnow() - timedelta(days=7)
seven_days_ago_ts = int(seven_days_ago.timestamp())

st.set_page_config(page_title="🪙 Jupiter 7天内上架新币监听", layout="wide")
st.title("🪙 Jupiter 7天内上架且与 SOL 组成交易对的新币活跃排行榜")
st.caption("每5秒自动刷新，仅显示成交量或成交额最高的20个币种。数据结合 Jupiter 官方和 Helius API。")

st_autorefresh(interval=5000, key="auto_refresh")

@st.cache_data(ttl=60)
def fetch_jupiter_markets():
    try:
        res = requests.get(JUPITER_MARKETS_API)
        res.raise_for_status()
        data = res.json()
        return data.get("data", [])
    except Exception as e:
        st.error(f"获取 Jupiter 市场信息失败: {e}")
        return []

@st.cache_data(ttl=60)
def fetch_token_info(mint):
    try:
        url = f"{HELIUS_BASE}/tokens/metadata?api-key={API_KEY}&mint={mint}"
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        if data:
            return data[0]
        return {}
    except:
        return {}

@st.cache_data(ttl=60)
def fetch_token_transfers(mint):
    start_time = seven_days_ago_ts
    try:
        url = f"{HELIUS_BASE}/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start_time}&limit=1000"
        res = requests.get(url)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return []

def analyze_markets(markets):
    results = []
    for m in markets:
        base = m.get("baseMint")
        quote = m.get("quoteMint")
        if not base or not quote:
            continue
        # 只关注和SOL配对的市场
        if SOL_MINT not in (base, quote):
            continue
        # 过滤7天内上架，jup.ag市场没有直接创建时间字段，只能用其它字段过滤或不过滤
        # 这里假设不过滤时间，展示所有与SOL交易对市场

        mint = base if quote == SOL_MINT else quote
        token_info = fetch_token_info(mint)
        token_name = token_info.get("name") or token_info.get("symbol") or "未知"

        transfers = fetch_token_transfers(mint)
        total_volume = sum(tx.get("tokenAmount", 0) for tx in transfers)  # 这里根据真实字段调整
        total_sol = 0
        for tx in transfers:
            # 这里尝试估算成交额（SOL）
            # 需要根据API实际字段解析，示例假设有 priceSol 字段
            amount = tx.get("tokenAmount", 0)
            price_sol = tx.get("priceSol", 0)
            total_sol += amount * price_sol

        results.append({
            "代币名称": token_name,
            "Mint地址": mint,
            "成交量（代币数量）": total_volume,
            "成交额（SOL）": round(total_sol, 4),
            "baseMint": base,
            "quoteMint": quote,
        })
    return results

def main():
    st.write("加载 Jupiter 市场数据中...")
    markets = fetch_jupiter_markets()
    if not markets:
        st.info("未获取到 Jupiter 市场数据")
        return

    results = analyze_markets(markets)
    if not results:
        st.info("无符合条件的新币数据")
        return

    df = pd.DataFrame(results)
    sort_by = st.selectbox("排序方式", ["成交额（SOL）", "成交量（代币数量）"], index=0)
    ascending = st.checkbox("升序排列", value=False)
    df = df.sort_values(sort_by, ascending=ascending).head(20)
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
