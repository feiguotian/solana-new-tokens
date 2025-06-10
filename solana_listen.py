import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta

# —— 固定 Helius API Key，无需自填
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE_URL = "https://api.helius.xyz/v0"

# 🎯 自行替换为真实的PumpSwap和Jupiter ProgramID（如不知道可先留空）
PUMPSWAP_PROG = ""
JUPITER_PROG = ""

# 时间范围：过去 7 天
seven_days_ago = datetime.utcnow() - timedelta(days=7)

# 页面配置 + 自动刷新
st.set_page_config(page_title="🪙 Solana 新发币监听", layout="wide")
st_autorefresh(interval=5000, key="auto_refresh")

st.title("🪙 Solana链上过去7日交易最活跃新发代币")
st.caption("实时监听过去7日创建并交易活跃的新币（最多20个），每 5 秒刷新")

@st.cache_data(ttl=60)
def fetch_new_mints():
    url = f"{BASE_URL}/tokens/created?api-key={API_KEY}&days=7"
    r = requests.get(url)
    if r.status_code != 200:
        st.error(f"获取新币失败：{r.status_code} {r.text}")
        return []
    return r.json()

@st.cache_data(ttl=60)
def fetch_transfers(mint):
    start_ts = int(seven_days_ago.timestamp())
    url = f"{BASE_URL}/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start_ts}&limit=500"
    r = requests.get(url)
    return r.json() if r.status_code == 200 else []

def analyze_mints(mints, top_n=20):
    recs = []
    for item in mints:
        mint = item.get("mint")
        created_ts = item.get("timestamp")
        transfers = fetch_transfers(mint)
        total = len(transfers)
        if total == 0:
            continue

        wallets = set()
        pump_count = 0
        jup_count = 0
        for tx in transfers:
            wallets.add(tx.get("source"))
            wallets.add(tx.get("destination"))
            prog = tx.get("programId", "")
            if prog == PUMPSWAP_PROG:
                pump_count += 1
            if prog == JUPITER_PROG:
                jup_count += 1

        recs.append({
            "Mint": mint,
            "创建时间": datetime.utcfromtimestamp(created_ts).strftime("%Y‑%m‑%d %H:%M"),
            "交易笔数": total,
            "活跃钱包数": len(wallets),
            "PumpSwap%": pump_count / total,
            "Jupiter%": jup_count / total
        })

    df = pd.DataFrame(recs)
    if df.empty:
        return df
    df = df.sort_values("交易笔数", ascending=False).head(top_n)
    df["PumpSwap%"] = df["PumpSwap%"].apply(lambda x: f"{x:.2%}")
    df["Jupiter%"] = df["Jupiter%"].apply(lambda x: f"{x:.2%}")
    return df

# 主逻辑
mints = fetch_new_mints()
df = analyze_mints(mints)

if df.empty:
    st.info("暂无活跃新币（最近创建且有交易）")
else:
    def highlight_red(val):
        try:
            val_f = float(val.strip('%'))
            return 'color:red; font-weight:bold' if val_f > 50 else ''
        except:
            return ''
    st.dataframe(df.style.applymap(highlight_red, subset=["PumpSwap%", "Jupiter%"]), use_container_width=True)
