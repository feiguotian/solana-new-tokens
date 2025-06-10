import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta

API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE_URL = "https://api.helius.xyz/v0"

PUMPSWAP_PROG = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
JUPITER_PROG   = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"

seven_days_ago = datetime.utcnow() - timedelta(days=7)

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
        ts = item.get("timestamp")
        transfers = fetch_transfers(mint)
        total = len(transfers)
        if total == 0:
            continue

        wallets = set()
        pump_cnt = jup_cnt = 0
        for tx in transfers:
            wallets.add(tx.get("source"))
            wallets.add(tx.get("destination"))
            prog = tx.get("programId", "")
            if prog == PUMPSWAP_PROG:
                pump_cnt += 1
            if prog == JUPITER_PROG:
                jup_cnt += 1

        recs.append({
            "Mint": mint,
            "创建时间": datetime.utcfromtimestamp(ts).strftime("%Y‑%m‑%d %H:%M"),
            "交易笔数": total,
            "活跃钱包数": len(wallets),
            "PumpSwap%": pump_cnt / total,
            "Jupiter%": jup_cnt / total
        })

    df = pd.DataFrame(recs)
    if df.empty:
        return df
    df = df.sort_values("交易笔数", ascending=False).head(top_n)
    df["PumpSwap%"] = df["PumpSwap%"].apply(lambda x: f"{x:.2%}")
    df["Jupiter%"] = df["Jupiter%"].apply(lambda x: f"{x:.2%}")
    return df

mints = fetch_new_mints()
df = analyze_mints(mints)

if df.empty:
    st.info("暂无活跃新币（最近创建且有交易）")
else:
    def highlight_red(val):
        try:
            return 'color:red; font-weight:bold' if float(val.strip('%')) > 50 else ''
        except:
            return ''
    st.dataframe(df.style.applymap(highlight_red, subset=["PumpSwap%", "Jupiter%"]), use_container_width=True)
