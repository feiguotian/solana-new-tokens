import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List

API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE_URL = "https://api.helius.xyz/v0"

# Jupiter程序ID
JUPITER_PROG = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"

# 过去7天时间点
seven_days_ago = datetime.utcnow() - timedelta(days=7)

st.set_page_config(page_title="🪙 Jupiter 7天内SOL交易对新币活跃排行", layout="wide")
st.title("🪙 Jupiter 7天内与SOL交易对新币活跃排行榜")
st.caption("仅统计与SOL组成交易对的代币，按成交量或成交额排序。数据每5秒刷新")

# 自动刷新页面
st.experimental_set_query_params(refresh_interval=5)
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0
st.session_state.refresh_counter += 1
st.experimental_rerun = lambda: None  # 解决可能报错

@st.cache_data(ttl=60)
def get_jupiter_markets():
    """获取所有Jupiter市场对信息"""
    url = "https://quote-api.jup.ag/v1/markets"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json().get("data", [])
    else:
        st.warning(f"获取Jupiter市场数据失败，状态码 {r.status_code}")
        return []

@st.cache_data(ttl=60)
def get_token_metadata(mint_addresses: List[str]):
    """批量获取代币名称等元数据"""
    if not mint_addresses:
        return {}
    url = f"{BASE_URL}/tokens/metadata?api-key={API_KEY}"
    payload = {"mints": mint_addresses}
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            results = r.json()
            # 返回 Mint 到 Name 的映射
            return {item["mint"]: item.get("name", "未知") for item in results}
        else:
            st.warning(f"获取代币元数据失败: {r.status_code} {r.text}")
            return {}
    except Exception as e:
        st.error(f"请求代币元数据异常: {e}")
        return {}

@st.cache_data(ttl=60)
def get_jupiter_trades(mint: str, start_time: int):
    """获取指定mint与SOL组成交易对7天内交易记录"""
    url = f"{BASE_URL}/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start_time}&limit=1000"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
        else:
            return []
    except Exception:
        return []

def analyze_active_tokens():
    markets = get_jupiter_markets()

    # 过滤出与 SOL 交易对，且上架时间在7天内的市场
    sol_mint = "So11111111111111111111111111111111111111112"
    active_markets = []
    for m in markets:
        if m.get("baseMint") == sol_mint or m.get("quoteMint") == sol_mint:
            # 判断上架时间
            listed_at = m.get("listedAt")
            if listed_at and datetime.utcfromtimestamp(listed_at) >= seven_days_ago:
                active_markets.append(m)

    # 去重代币 Mint（非 SOL 那个）
    token_mints = set()
    mint_to_listed = {}
    for market in active_markets:
        base = market.get("baseMint")
        quote = market.get("quoteMint")
        if base != sol_mint:
            token_mints.add(base)
            mint_to_listed[base] = market.get("listedAt")
        elif quote != sol_mint:
            token_mints.add(quote)
            mint_to_listed[quote] = market.get("listedAt")

    if not token_mints:
        return pd.DataFrame()

    # 查询代币名称
    metadata = get_token_metadata(list(token_mints))

    # 获取当前时间戳
    start_time = int(seven_days_ago.timestamp())

    rows = []
    for mint in token_mints:
        transfers = get_jupiter_trades(mint, start_time)
        if not transfers:
            continue
        # 计算成交量（Token数量）、成交额（SOL数量）、成交笔数
        total_token_amount = 0
        total_sol_amount = 0
        count = 0
        for tx in transfers:
            # 只统计Jupiter程序的交易
            if tx.get("programId") != JUPITER_PROG:
                continue
            # 交易方向和金额判断（这里简单累计数量和金额）
            token_amount = 0
            sol_amount = 0
            for change in tx.get("tokenBalanceChanges", []):
                if change.get("mint") == mint:
                    token_amount += int(change.get("change", 0))
                if change.get("mint") == sol_mint:
                    sol_amount += int(change.get("change", 0))
            total_token_amount += abs(token_amount)
            total_sol_amount += abs(sol_amount)
            count += 1

        if count == 0:
            continue

        rows.append({
            "代币名称": metadata.get(mint, "未知"),
            "Mint": mint,
            "上架时间": datetime.utcfromtimestamp(mint_to_listed.get(mint, start_time)).strftime("%Y-%m-%d %H:%M"),
            "成交量（Token）": total_token_amount,
            "成交额（SOL）": total_sol_amount / 1e9,  # 转换为SOL单位（Lamports -> SOL）
            "成交笔数": count,
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # 排序选项
    sort_col = st.selectbox("排序字段", ["成交量（Token）", "成交额（SOL）"], index=1)
    sort_asc = st.checkbox("升序排列", value=False)

    df = df.sort_values(sort_col, ascending=sort_asc)
    return df

df = analyze_active_tokens()

if df.empty:
    st.info("最近7天内，Jupiter上与SOL组成交易对的新币暂无活跃交易。")
else:
    st.dataframe(df, use_container_width=True)
