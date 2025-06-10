import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta

# ✅ 你的 Helius API KEY（自动填入）
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE = "https://api.helius.xyz/v0"

# ✅ Jupiter 的真实 Program ID
JUPITER_PROG = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"

seven_days_ago = datetime.utcnow() - timedelta(days=7)

st.set_page_config(page_title="🪙 Jupiter 新币监听", layout="wide")
st_autorefresh(interval=5000, key="auto")

st.title("🪙 最近7天已在 Jupiter 上上架并交易的新币")
st.caption("仅显示过去7天内在 Jupiter 上发生交易、最活跃的20个 token。\n数据每 5 秒刷新 | 数据来自 Helius + Streamlit")

@st.cache_data(ttl=60)
def fetch_created_mints(days=7):
    """获取过去 N 天内创建的新 token mint 列表"""
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
    """获取某个 token mint 的交易记录"""
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
        jups = [tx for tx in transfers if tx.get("programId") == JUPITER_PROG]
        total = len(jups)

        if total == 0:
            continue

        rows.append({
            "Mint": mint,
            "创建时间": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
            "Jupiter交易": total
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    return df.sort_values("Jupiter交易", ascending=False).head(top_n)

# 主体执行
mints = fetch_created_mints()
df = analyze_mints(mints)

if df.empty:
    st.info("最近7天内，在 Jupiter 上交易的新币暂未发现。")
else:
    st.dataframe(df, use_container_width=True)
