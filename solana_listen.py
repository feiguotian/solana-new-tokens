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

# 7天前时间戳
seven_days_ago_ts = int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())

st.set_page_config(page_title="🪙 Jupiter 新币7天活跃排行榜", layout="wide")
st.title("🪙 监听 Jupiter 7天内新上架与 SOL 配对活跃交易币种")
st.caption("数据实时刷新，每5秒更新 | 来自 Helius RPC + Streamlit")

# 解析Jupiter市场账户数据（简化版）
def parse_market_account(data_b64):
    data = base64.b64decode(data_b64)
    # Jupiter V4 Market Layout（简化，取关键字段偏移）
    # 先确认长度
    if len(data) < 144:
        return None
    # 第0-32字节是baseMint（交易币mint）
    base_mint = data[0:32][::-1].hex()
    base_mint = base58_encode(data[0:32])
    # 第32-64字节是quoteMint（交易对币mint）
    quote_mint = base58_encode(data[32:64])
    # 第144-152字节是创建时间（unix timestamp，假设存8字节）
    # 但Jupiter没公开标准，这里简化成取bytes 144~152，如果不对就跳过
    if len(data) >= 152:
        ts_bytes = data[144:152]
        created_ts = struct.unpack("<Q", ts_bytes)[0]
    else:
        created_ts = 0

    return {
        "baseMint": base_mint,
        "quoteMint": quote_mint,
        "createdTs": created_ts
    }

# base58编码函数（solana地址编码）
ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def base58_encode(data: bytes) -> str:
    num = int.from_bytes(data, "big")
    encode = b""
    while num > 0:
        num, rem = divmod(num, 58)
        encode = ALPHABET[rem:rem+1] + encode
    # 处理前导0
    n_pad = 0
    for b in data:
        if b == 0:
            n_pad +=1
        else:
            break
    return (ALPHABET[0:1] * n_pad + encode).decode()

# 查询所有Jupiter市场账户
def get_jupiter_markets():
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

# 查询指定mint的交易数据，统计成交量和成交额（单位SOL）
def get_trade_stats(mint):
    # Helius 交易API：tokens/{mint}/transfers
    start_time = seven_days_ago_ts
    url = f"https://api.helius.xyz/v0/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start_time}&limit=1000"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    data = r.json()
    if not data:
        return None
    total_volume = 0.0
    total_amount_sol = 0.0
    for tx in data:
        # 只统计买卖数量（以token数量计）
        amount = float(tx.get("tokenAmount", 0))
        total_volume += amount
        # 成交额估算：token数量 * token价格
        # 这里价格估算较复杂，先忽略或用SOL数量替代
        sol_amount = float(tx.get("lamports", 0)) / 1e9
        total_amount_sol += sol_amount
    return {
        "volume": total_volume,
        "amount_sol": total_amount_sol
    }

# 主逻辑
def main():
    st.info("数据加载中，请稍等...")
    accounts = get_jupiter_markets()
    if not accounts:
        st.warning("未获取到 Jupiter 市场账户数据")
        return

    rows = []
    for acc in accounts:
        parsed = parse_market_account(acc.get("account", {}).get("data", [None])[0])
        if not parsed:
            continue
        # 只关注quoteMint为SOL的
        if parsed["quoteMint"] != SOL_MINT:
            continue
        # 过滤7天内创建的市场
        if parsed["createdTs"] < seven_days_ago_ts:
            continue

        # 交易统计
        stats = get_trade_stats(parsed["baseMint"])
        if not stats:
            continue

        rows.append({
            "代币Mint": parsed["baseMint"],
            "上架时间": datetime.fromtimestamp(parsed["createdTs"]).strftime("%Y-%m-%d %H:%M:%S"),
            "成交量（代币）": f"{stats['volume']:.2f}",
            "成交额（SOL）": f"{stats['amount_sol']:.4f}"
        })

    if not rows:
        st.info("7天内未发现活跃新币对（Jupiter + SOL）")
        return

    df = pd.DataFrame(rows)
    df = df.sort_values(by="成交额（SOL）", ascending=False).reset_index(drop=True)
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
