import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta

API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE = "https://api.helius.xyz/v0"

PUMPSWAP_PROG = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
JUPITER_PROG = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
seven_days_ago = datetime.utcnow() - timedelta(days=7)

st.set_page_config(page_title="🪙 Solana DEX 已上架新币监听", layout="wide")
st_autorefresh(interval=5000, key="auto")

st.title("🪙 最近7天已上架至 PumpSwap 或 Jupiter 并交易活跃的新币")
st.caption("仅显示那些在这两个 DEX 上出现交易、最活跃的20个 token，每 5 秒刷新")

@st.cache_data(ttl=60)
def fetch_created_mints(days=7):
    r = requests.get(f"{BASE}/tokens/created?api-key={API_KEY}&days={days}")
    return r.json() if r.status_code==200 else []

@st.cache_data(ttl=60)
def fetch_transfers(mint):
    start = int(seven_days_ago.timestamp())
    r = requests.get(f"{BASE}/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start}&limit=500")
    return r.json() if r.status_code==200 else []

def analyze_mints(mints, top_n=20):
    rows = []
    for item in mints:
        mint = item["mint"]
        ts = item["timestamp"]
        transfers = fetch_transfers(mint)
        pumps = [tx for tx in transfers if tx.get("programId")==PUMPSWAP_PROG]
        jups = [tx for tx in transfers if tx.get("programId")==JUPITER_PROG]
        total = len(transfers)
        if total == 0 or (not pumps and not jups):
            continue
        rows.append({
            "Mint": mint,
            "创建时间": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
            "总交易": total,
            "PumpSwap交易": len(pumps),
            "Jupiter交易": len(jups),
            "PumpSwap占比": len(pumps)/total,
            "Jupiter占比": len(jups)/total
        })
    df = pd.DataFrame(rows).sort_values("总交易", ascending=False).head(top_n)
    for col in ["PumpSwap占比", "Jupiter占比"]:
        df[col] = df[col].apply(lambda x: f"{x:.2%}")
    return df

mints = fetch_created_mints()
df = analyze_mints(mints)

if df.empty:
    st.info("最近7天内，PumpSwap 或 Jupiter 上架后进行交易的新币暂无或尚未活跃。")
else:
    def hl(val):
        try:
            return 'color:red;font-weight:bold' if float(val.strip('%')) > 20 else ''
        except:
            return ''
    st.dataframe(df.style.applymap(hl, subset=["PumpSwap占比","Jupiter占比"]), use_container_width=True)
