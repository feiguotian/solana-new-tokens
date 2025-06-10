import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta

API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE = "https://api.helius.xyz/v0"

# PumpSwap 与 Jupiter 程序地址
PUMPSWAP_PROG = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
JUPITER_PROG = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"

seven_days_ago = datetime.utcnow() - timedelta(days=7)

st.set_page_config(page_title="🪙 Solana DEX 已上架新币监听", layout="wide")
st_autorefresh(interval=5000, key="auto")

st.title("🪙 最近7天已上架至 PumpSwap 或 Jupiter 并交易活跃的新币")
st.caption("仅显示那些在这两个 DEX 上出现交易、最活跃的20个 token，每 5 秒刷新")

@st.cache_data(ttl=60)
def fetch_created_mints(days=7):
    try:
        r = requests.get(f"{BASE}/tokens/created?api-key={API_KEY}&days={days}")
        if r.status_code == 200:
            return r.json()
        else:
            st.warning(f"获取新币失败：{r.status_code} {r.text}")
            return []
    except Exception as e:
        st.error(f"请求失败：{e}")
        return []

@st.cache_data(ttl=60)
def fetch_transfers(mint):
    try:
        start = int(seven_days_ago.timestamp())
        r = requests.get(f"{BASE}/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start}&limit=500")
        if r.status_code == 200:
            return r.json()
        else:
            return []
    except:
        return []

def analyze_mints(mints, top_n=20):
    rows = []
    for item in mints:
        mint = item.get("mint")
        ts = item.get("timestamp")
        if not mint or not ts:
            continue

        transfers = fetch_transfers(mint)
        pumps = [tx for tx in transfers if tx.get("programId") == PUMPSWAP_PROG]
        jups = [tx for tx in transfers if tx.get("programId") == JUPITER_PROG]
        total = len(transfers)

        if total == 0 or (not pumps and not jups):
            continue

        rows.append({
            "Mint": mint,
            "创建时间": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
            "总交易": total,
            "PumpSwap交易": len(pumps),
            "Jupiter交易": len(jups),
            "PumpSwap占比": f"{len(pumps)/total:.2%}",
            "Jupiter占比": f"{len(jups)/total:.2%}"
        })

    if not rows:
        return pd.DataFrame()  # 返回空 DataFrame

    df = pd.DataFrame(rows)

    if "总交易" not in df.columns:
        st.warning("数据没有包含 '总交易' 列，跳过排序。")
        return df

    return df.sort_values("总交易", ascending=False).head(top_n)

# ========== 主体执行 ==========
mints = fetch_created_mints()
df = analyze_mints(mints)

if df.empty:
    st.info("最近7天内，在 PumpSwap 或 Jupiter 上进行交易的新币暂未发现。")
else:
    st.dataframe(df, use_container_width=True)
