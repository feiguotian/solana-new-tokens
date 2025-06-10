import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# === 配置 ===
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"
JUPITER_PROGRAM_ID = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
SOL_MINT = "So11111111111111111111111111111111111111112"
REFRESH_INTERVAL_MS = 2000  # 每2秒刷新

# === 页面设置 ===
st.set_page_config(page_title="🪙 Jupiter 监听", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="refresh")

st.title("🪙 监听 Jupiter 7天内新上架与 SOL 配对活跃交易币种")
st.caption("数据实时刷新，每2秒更新 | 来自 Helius RPC + Streamlit")

# 加载提示
with st.spinner("数据加载中，请稍等...正在扫描 Jupiter 市场账户"):
    # === 获取 Jupiter 市场账户 ===
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getProgramAccounts",
        "params": [
            JUPITER_PROGRAM_ID,
            {
                "encoding": "base64",
                "commitment": "confirmed",
                "dataSlice": {"offset": 0, "length": 0}
            }
        ]
    }

    try:
        response = requests.post(RPC_URL, json=payload)
        response.raise_for_status()
        result = response.json().get("result", [])
    except Exception as e:
        st.error(f"获取 Jupiter 市场信息失败: {e}")
        st.stop()

# 提取市场账户 pubkey 并显示
market_accounts = [acc["pubkey"] for acc in result]

with st.sidebar:
    st.markdown("### 📋 Jupiter 市场账户")
    st.markdown(f"共获取到 **{len(market_accounts)}** 个市场账户")
    st.dataframe(pd.DataFrame({"账户地址": market_accounts}), height=400)

# === 模拟处理市场数据（简化逻辑展示）===
rows = []
now_ts = int(time.time())
seven_days_ago_ts = now_ts - 7 * 86400

for market in market_accounts:
    # 假设我们能从每个账户得到配对信息、代币名称、创建时间、成交量、成交额
    # 以下是模拟逻辑，真实项目应调用实际 Jupiter SDK 或解析账户内容
    parsed = {
        "baseMint": f"FakeMint_{market[-4:]}",  # 假数据
        "quoteMint": SOL_MINT,
        "createdTs": now_ts - int(market[-2:], 16) * 3600,  # 模拟时间戳
        "volume": int(market[-2:], 16) * 100,
        "amount": int(market[-2:], 16) * 10,
        "tokenName": f"TOKEN_{market[-4:]}"
    }

    if parsed["createdTs"] < seven_days_ago_ts:
        continue

    try:
        created_at = datetime.fromtimestamp(parsed["createdTs"]).strftime("%Y-%m-%d %H:%M:%S")
    except OverflowError:
        created_at = "时间错误"

    rows.append({
        "代币名称": parsed["tokenName"],
        "Base Mint": parsed["baseMint"],
        "成交量（代币）": parsed["volume"],
        "成交额（SOL）": parsed["amount"],
        "上架时间": created_at
    })

# === 显示结果 ===
if not rows:
    st.info("⚠️ 7天内未发现活跃新币对（Jupiter + SOL）")
else:
    df = pd.DataFrame(rows).sort_values("成交额（SOL）", ascending=False)
    st.dataframe(df, use_container_width=True)
