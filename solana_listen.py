import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# API 设置
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE_URL = "https://api.helius.xyz/v0"
RPC_URL = "https://mainnet.helius-rpc.com/?api-key=" + API_KEY

# 时间范围
now = datetime.utcnow().replace(tzinfo=pytz.UTC)
seven_days_ago = now - timedelta(days=7)
start_time = int(seven_days_ago.timestamp())

# 缓存新币
if "seen" not in st.session_state:
    st.session_state.seen = {}

# 页面标题
st.set_page_config(page_title="🪙 Solana 新发代币监听", layout="wide")
st.title("🪙 新发代币监听")
st.caption("实时监听Solana链上过去7日创建并交易活跃的新代币，最多显示20个。")
st.caption("PumpSwap、Jupiter 的交易活动以红色标记另一种币种。")
st.caption("数据每5秒刷新一次。")

@st.cache_data(ttl=5)
def fetch_new_tokens():
    url = f"{BASE_URL}/addresses/11111111111111111111111111111111/transactions?api-key={API_KEY}&limit=100"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        txs = res.json()
    except Exception as e:
        st.error(f"获取交易失败: {e}")
        return []

    results = []
    for tx in txs:
        for ix in tx.get("instructions", []):
            if ix.get("program") == "spl-token" and ix.get("parsed", {}).get("type") == "initializeMint":
                mint = ix.get("accounts", [None])[0]
                timestamp = tx.get("timestamp", 0)
                created_at = datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC)
                if mint and mint not in st.session_state.seen and created_at > seven_days_ago:
                    st.session_state.seen[mint] = created_at
                    results.append({
                        "mint": mint,
                        "created_at": created_at
                    })
    return results

def get_token_transfers(mint):
    try:
        url = f"{BASE_URL}/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start_time}&limit=200"
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.json()
    except:
        return []

def analyze_tokens(mints):
    data = []
    for token in mints:
        mint = token["mint"]
        created_at = token["created_at"]
        txs = get_token_transfers(mint)
        wallets = set()
        jup_count = 0
        pump_count = 0
        for tx in txs:
            src = tx.get("source")
            dst = tx.get("destination")
            if src: wallets.add(src)
            if dst: wallets.add(dst)
            desc = tx.get("description", "").lower()
            if "jupiter" in desc:
                jup_count += 1
            if "pump" in desc:
                pump_count += 1
        total_tx = len(txs)
        if total_tx == 0:
            continue
        data.append({
            "Token Mint": mint,
            "创建时间": created_at.strftime("%Y-%m-%d %H:%M"),
            "交易笔数": total_tx,
            "活跃钱包数": len(wallets),
            "Jupiter 占比": jup_count / total_tx,
            "Pump 占比": pump_count / total_tx
        })
    data.sort(key=lambda x: x["交易笔数"], reverse=True)
    return data[:20]

# 主流程
new_tokens = fetch_new_tokens()
top_tokens = analyze_tokens(new_tokens)

if not top_tokens:
    st.warning("暂无新币数据，等待更新...")
else:
    df = pd.DataFrame(top_tokens)
    for col in ["Jupiter 占比", "Pump 占比"]:
        df[col] = df[col].apply(lambda x: f"**:red[{x:.2%}]**" if float(x) > 0.5 else f"{x:.2%}")

    st.dataframe(df, use_container_width=True)
    st.download_button("📥 导出为 CSV", data=df.to_csv(index=False).encode("utf-8"), file_name="top20_tokens.csv", mime="text/csv")
