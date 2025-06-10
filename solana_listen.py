import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime
import time

# ========== 设置 ==========
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"
JUPITER_PROGRAM_ID = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
SOL_MINT = "So11111111111111111111111111111111111111112"
REFRESH_INTERVAL = 5000  # 毫秒

# ========== 页面配置 ==========
st.set_page_config(page_title="🪙 Jupiter 新币监听", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL, key="refresh")
st.title("🪙 监听 Jupiter 7天内新上架与 SOL 配对活跃交易币种")
st.caption("数据实时刷新，每5秒更新 | 来自 Helius RPC + Streamlit")

with st.spinner("数据加载中，请稍等..."):

    def get_market_accounts():
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getProgramAccounts",
            "params": [
                JUPITER_PROGRAM_ID,
                {
                    "encoding": "jsonParsed",
                    "dataSlice": {"offset": 0, "length": 0},
                    "filters": []
                }
            ]
        }
        try:
            r = requests.post(RPC_URL, json=payload)
            result = r.json().get("result", [])
            return [acc["pubkey"] for acc in result]
        except Exception as e:
            st.error(f"获取 Jupiter 市场信息失败: {e}")
            return []

    def get_market_tx(account):
        try:
            url = f"https://api.helius.xyz/v0/addresses/{account}/transactions?api-key={API_KEY}&limit=1000"
            r = requests.get(url)
            if r.status_code != 200:
                return []
            txs = r.json()
            swaps = [tx for tx in txs if tx.get("type") == "SWAP"]
            return swaps
        except:
            return []

    def parse_swap_data(market_account):
        swaps = get_market_tx(market_account)
        token = None
        first_swap_time = None
        total_amount_in = 0
        total_amount_out = 0

        for tx in swaps:
            events = tx.get("events", {})
            swap = events.get("swap")
            if not swap:
                continue

            in_mint = swap.get("nativeInputMint")
            out_mint = swap.get("nativeOutputMint")
            in_amt = swap.get("nativeInputAmount", 0)
            out_amt = swap.get("nativeOutputAmount", 0)
            ts = tx.get("timestamp")

            if SOL_MINT not in [in_mint, out_mint]:
                continue

            token_mint = out_mint if in_mint == SOL_MINT else in_mint

            if not first_swap_time:
                first_swap_time = ts
                token = token_mint

            total_amount_in += in_amt
            total_amount_out += out_amt

        if token and first_swap_time:
            return {
                "Token Mint": token,
                "上架时间": datetime.utcfromtimestamp(first_swap_time).strftime("%Y-%m-%d %H:%M:%S"),
                "成交量": total_amount_out,
                "成交额（SOL）": total_amount_in / 1e9,
            }
        return None

    @st.cache_data(ttl=3600)
    def get_token_name(mint):
        try:
            url = f"https://api.helius.xyz/v0/tokens/metadata?api-key={API_KEY}"
            r = requests.post(url, json={"mints": [mint]})
            if r.status_code != 200:
                return "未知"
            metadata = r.json()
            return metadata[0].get("name") or "未知"
        except:
            return "未知"

    accounts = get_market_accounts()
    rows = []

    for acc in accounts:
        data = parse_swap_data(acc)
        if data:
            data["代币名称"] = get_token_name(data["Token Mint"])
            rows.append(data)

    if not rows:
        st.info("⚠️ 最近7天内未发现活跃的新币市场（与 SOL 配对）。")
    else:
        df = pd.DataFrame(rows)
        df = df.sort_values("成交额（SOL）", ascending=False).head(20)
        st.dataframe(df, use_container_width=True)

    with st.sidebar:
        st.markdown("### 📜 Jupiter 市场账户")
        st.caption(f"共获取到 {len(accounts)} 个市场账户")
        for a in accounts:
            st.code(a, language="text")
