import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta

# ✅ 固定你的 Helius API Key
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE_URL = "https://api.helius.xyz/v0"

# ✅ PumpSwap & Jupiter ProgramID（示例，优先用准确值替换）
PUMPSWAP_PROG = "PSwpF1fQ4NsThF1Dj28Rh3XWRXCR92qvD1V5xU3NTdW"
JUPITER_PROG = "JUP3r1sTpVTTf4tu9PpaFyNNm3b85v8B9kkKMZ6VmF3"

# 设置时间范围：过去7天
seven_days_ago = datetime.utcnow() - timedelta(days=7)

# 📄 页面配置 & 自动刷新
st.set_page_config(page_title="🪙 Solana 新发币监听", layout="wide")
st_autorefresh(interval=5000, key="auto")
st.title("🪙 Solana链上过去7日交易最活跃新发代币")
st.caption("实时监听过去7日新发且交易活跃的新币，最多20个。数据每 5 秒刷新")

# 获取最近7天创建的新币
@st.cache(ttl=60)
def fetch_new_mints(days=7):
    url = f"{BASE_URL}/tokens/created?api-key={API_KEY}&days={days}"
    r = requests.get(url)
    if r.status_code != 200:
        st.error(f"获取新币失败: {r.status_code} {r.text}")
        return []
    return r.json()  # 每项有 mint, timestamp

# 查 mint 的交易明细
@st.cache(ttl=60)
def fetch_transfers(mint):
    start = int(seven_days_ago.timestamp())
    url = f"{BASE_URL}/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start}&limit=500"
    r = requests.get(url)
    return r.json() if r.status_code == 200 else []

# 主逻辑
def analyze_top_mints(mints, top_n=20):
    recs = []
    for token in mints:
        mint = token["mint"]
        ts = token["timestamp"]
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
            if prog == PUMPSWAP_PROG: pump_cnt += 1
            if prog == JUPITER_PROG: jup_cnt += 1

        recs.append({
            "Mint": mint,
            "创建时间": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
            "交易笔数": total,
            "活跃钱包数": len(wallets),
            "PumpSwap%": pump_cnt/total,
            "Jupiter%": jup_cnt/total
        })
    df = pd.DataFrame(recs).sort_values("交易笔数", ascending=False).head(top_n)
    return df

# 展示
mints = fetch_new_mints()
df = analyze_top_mints(mints)

if df.empty:
    st.info("暂无新币数据，等待更新...")
else:
    df["PumpSwap%"] = df["PumpSwap%"].apply(lambda x: f"{x:.2%}")
    df["Jupiter%"] = df["Jupiter%"].apply(lambda x: f"{x:.2%}")
    def style_func(v):
        try:
            return "color:red;" if float(v.strip('%')) > 50 else ""
        except:
            return ""
    st.dataframe(df.style.applymap(style_func, subset=["PumpSwap%", "Jupiter%"]), use_container_width=True)
