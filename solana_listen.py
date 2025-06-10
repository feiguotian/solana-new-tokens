import streamlit as st
import requests
import base64
import struct
import pandas as pd
from datetime import datetime, timezone, timedelta

API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"

JUPITER_PROGRAM_ID = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
SOL_MINT = "So11111111111111111111111111111111111111112"

seven_days_ago_ts = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())

st.set_page_config(page_title="🪙 Jupiter 新币7天活跃排行榜", layout="wide")
st.title("🪙 监听 Jupiter 7天内新上架与 SOL 配对活跃交易币种")
st.caption("数据实时刷新，每5秒更新 | 来自 Helius RPC + Streamlit")

def base58_encode(data: bytes) -> str:
    ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = int.from_bytes(data, "big")
    encode = b""
    while num > 0:
        num, rem = divmod(num, 58)
        encode = ALPHABET[rem:rem+1] + encode
    n_pad = 0
    for b in data:
        if b == 0:
            n_pad += 1
        else:
            break
    return (ALPHABET[0:1] * n_pad + encode).decode()

def parse_market_account(data_b64):
    data = base64.b64decode(data_b64)
    if len(data) < 152:
        return None
    base_mint = base58_encode(data[0:32])
    quote_mint = base58_encode(data[32:64])
    created_ts = struct.unpack("<Q", data[144:152])[0]
    return {
        "baseMint": base_mint,
        "quoteMint": quote_mint,
        "createdTs": created_ts
    }

def get_jupiter_markets():
    with st.spinner("正在获取 Jupiter 市场账户..."):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getProgramAccounts",
            "params": [
                JUPITER_PROGRAM_ID,
                {
                    "encoding": "base64",
                    "filters": []
                }
            ]
        }
        r = requests.post(RPC_URL, json=payload)
        if r.status_code != 200:
            st.error(f"请求失败，状态码：{r.status_code}")
            return []
        resp = r.json()
        if "error" in resp:
            st.error(f"RPC 错误：{resp['error']}")
            return []
        return resp.get("result", [])

def get_trade_stats(mint):
    start_time = seven_days_ago_ts
    url = f"https://api.helius.xyz/v0/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start_time}&limit=1000"
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        total_volume = 0.0
        total_amount_sol = 0.0
        for tx in data:
            amount = float(tx.get("tokenAmount", 0))
            total_volume += amount
            sol_amount = float(tx.get("lamports", 0)) / 1e9
            total_amount_sol += sol_amount
        return {
            "volume": total_volume,
            "amount_sol": total_amount_sol
        }
    except Exception as e:
        st.warning(f"查询交易数据出错: {e}")
        return None

def main():
    st.info("数据加载中，请稍等...")

    accounts = get_jupiter_markets()
    if not accounts:
        st.warning("未获取到 Jupiter 市场账户数据")
        return

    # 右侧边栏展示账户列表和总数
    with st.sidebar:
        st.header("Jupiter 市场账户列表")
        st.write(f"共获取到 {len(accounts)} 个 Jupiter 市场账户")
        sidebar_rows = []
        for acc in accounts:
            pubkey = acc.get("pubkey", "未知")
            data_b64 = acc.get("account", {}).get("data", [None])[0]
            parsed = parse_market_account(data_b64) if data_b64 else None
            created_time = (
                datetime.fromtimestamp(parsed["createdTs"]).strftime("%Y-%m-%d %H:%M:%S")
                if parsed and parsed.get("createdTs")
                else "未知"
            )
            base_mint = parsed.get("baseMint") if parsed else "解析失败"
            quote_mint = parsed.get("quoteMint") if parsed else "解析失败"
            sidebar_rows.append({
                "账户地址": pubkey,
                "创建时间": created_time,
                "BaseMint": base_mint,
                "QuoteMint": quote_mint,
            })
        if sidebar_rows:
            sidebar_df = pd.DataFrame(sidebar_rows)
            st.dataframe(sidebar_df, use_container_width=True)
        else:
            st.write("无有效市场账户数据")

    rows = []
    progress_bar = st.progress(0)
    total = len(accounts)
    count = 0

    for acc in accounts:
        parsed = parse_market_account(acc.get("account", {}).get("data", [None])[0])
        count += 1
        progress_bar.progress(count / total)

        if not parsed:
            continue
        if parsed["quoteMint"] != SOL_MINT:
            continue
        if parsed["createdTs"] < seven_days_ago_ts:
            continue

        st.write(f"分析代币: {parsed['baseMint']} ...")

        stats = get_trade_stats(parsed["baseMint"])
        if not stats:
            continue

        rows.append({
            "代币Mint": parsed["baseMint"],
            "上架时间": datetime.fromtimestamp(parsed["createdTs"]).strftime("%Y-%m-%d %H:%M:%S"),
            "成交量（代币）": f"{stats['volume']:.2f}",
            "成交额（SOL）": f"{stats['amount_sol']:.4f}"
        })

    progress_bar.empty()

    if not rows:
        st.info("7天内未发现活跃新币对（Jupiter + SOL）")
        return

    df = pd.DataFrame(rows)
    df = df.sort_values(by="成交额（SOL）", ascending=False).reset_index(drop=True)
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
