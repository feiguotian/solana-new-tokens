import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE = "https://api.helius.xyz/v0"

JUPITER_PROGRAM_ID = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
SOL_MINT = "So11111111111111111111111111111111111111112"  # Solana 原生代币 Mint 地址

seven_days_ago = datetime.utcnow() - timedelta(days=7)
seven_days_ago_ts = int(seven_days_ago.timestamp())

st.set_page_config(page_title="🪙 Jupiter 7天内上架新币监听", layout="wide")
st.title("🪙 Jupiter 7天内上架且与 SOL 组成交易对的新币活跃排行榜")
st.caption("每5秒自动刷新，仅显示成交量或成交额最高的20个币种。数据来自 Helius API。")

# 自动刷新
st_autorefresh(interval=5000, key="auto_refresh")

@st.cache_data(ttl=60)
def fetch_jupiter_markets():
    """获取 Jupiter 7 天内的交易市场信息（filter新币，带SOL交易对）"""
    url = f"{BASE}/programs/{JUPITER_PROGRAM_ID}/accounts?api-key={API_KEY}&limit=1000"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        return data.get("accounts", [])
    except Exception as e:
        st.error(f"获取 Jupiter 市场信息失败: {e}")
        return []

@st.cache_data(ttl=60)
def fetch_token_info(mint):
    """获取代币信息，含名称"""
    url = f"{BASE}/tokens/metadata?api-key={API_KEY}&mint={mint}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()
        if data:
            return data[0]  # 返回第一个匹配的代币信息
        return {}
    except:
        return {}

@st.cache_data(ttl=60)
def fetch_market_volume(market_id):
    """获取某市场最近7天内的成交量和成交额（单位：代币数量和SOL数量）"""
    start_time = seven_days_ago_ts
    url = f"{BASE}/accounts/{market_id}/transactions?api-key={API_KEY}&limit=1000&startTime={start_time}"
    try:
        res = requests.get(url)
        res.raise_for_status()
        txs = res.json()
        total_volume = 0  # 交易代币数量
        total_amount_sol = 0  # 交易金额，SOL计价
        for tx in txs:
            # 这里简单统计价格*数量为成交额，具体字段根据API调整
            # 只做示例，实际要根据交易数据结构解析
            # 假设tx中有字段amount和price_sol（需根据实际接口改）
            amount = tx.get("amount", 0)
            price_sol = tx.get("price_sol", 0)
            total_volume += amount
            total_amount_sol += amount * price_sol
        return total_volume, total_amount_sol
    except Exception as e:
        return 0, 0

def parse_markets(raw_markets):
    """过滤出7天内上架且有SOL交易对的市场，返回含必要信息的列表"""
    results = []
    for market in raw_markets:
        # 过滤时间，必须有timestamp字段
        ts = market.get("timestamp")
        if not ts or ts < seven_days_ago_ts:
            continue
        # 解析交易对，判断是否与SOL配对
        base_mint = market.get("baseMint")
        quote_mint = market.get("quoteMint")
        if not base_mint or not quote_mint:
            continue
        if SOL_MINT not in (base_mint, quote_mint):
            continue

        mint = base_mint if quote_mint == SOL_MINT else quote_mint
        results.append({
            "market_id": market.get("pubkey"),
            "mint": mint,
            "listed_at": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
            "base_mint": base_mint,
            "quote_mint": quote_mint,
        })
    return results

def main():
    st.write("数据加载中，请稍等...")

    raw_markets = fetch_jupiter_markets()
    if not raw_markets:
        st.info("未获取到 Jupiter 市场数据。")
        return

    markets = parse_markets(raw_markets)

    rows = []
    for m in markets:
        token_info = fetch_token_info(m["mint"])
        token_name = token_info.get("name") or token_info.get("symbol") or "未知"
        vol, amt_sol = fetch_market_volume(m["market_id"])

        rows.append({
            "代币名称": token_name,
            "Mint 地址": m["mint"],
            "上架时间": m["listed_at"],
            "成交量（代币数量）": vol,
            "成交额（SOL）": round(amt_sol, 4),
        })

    if not rows:
        st.info("7天内无符合条件的 Jupiter 新币。")
        return

    df = pd.DataFrame(rows)
    sort_by = st.selectbox("排序方式", options=["成交额（SOL）", "成交量（代币数量）"], index=0)
    ascending = st.checkbox("升序排列", value=False)
    df = df.sort_values(sort_by, ascending=ascending).head(20)

    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
