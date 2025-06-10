import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
from datetime import datetime, timedelta
import pytz
import pandas as pd

# 固定你的API KEY，不用每次输入
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
BASE_URL = f"https://api.helius.xyz/v0"

# 这两个是PumpSwap和Jupiter的ProgramID（示例，准确ID请替换）
PUMPSWAP_PROGRAM_ID = "PSwpF1fQ4NsThF1Dj28Rh3XWRXCR92qvD1V5xU3NTdW"
JUPITER_PROGRAM_ID = "JUP3r1sTpVTTf4tu9PpaFyNNm3b85v8B9kkKMZ6VmF3"

# 设置时间范围 - 7天内
now = datetime.utcnow().replace(tzinfo=pytz.UTC)
seven_days_ago = now - timedelta(days=7)

# 页面配置和自动刷新 每5秒刷新一次
st.set_page_config(page_title="Solana 新发币监听", layout="wide")
st_autorefresh(interval=5000, limit=None, key="refresh")

st.title("🚀 Solana链上过去7日交易最活跃的新发代币")
st.caption("实时监听Solana链上7日创建并交易活跃的新代币，最多显示20个。\n\n数据每5秒自动刷新 | 来自 Helius + Streamlit")

@st.cache_data(ttl=60)
def get_new_tokens():
    url = f"{BASE_URL}/addresses/11111111111111111111111111111111/transactions?api-key={API_KEY}&limit=200"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        txs = res.json()
    except Exception as e:
        st.error(f"获取交易失败: {e}")
        return []

    new_mints = {}
    for tx in txs:
        ts = tx.get("timestamp")
        if not ts:
            continue
        tx_time = datetime.utcfromtimestamp(ts).replace(tzinfo=pytz.UTC)
        if tx_time < seven_days_ago:
            continue
        for ix in tx.get("instructions", []):
            if ix.get("program") == "spl-token" and ix.get("parsed", {}).get("type") == "initializeMint":
                mint = ix.get("accounts", [None])[0]
                if mint and mint not in new_mints:
                    new_mints[mint] = tx_time
    # 返回新mint及创建时间，按时间倒序排序
    sorted_list = sorted(new_mints.items(), key=lambda x: x[1], reverse=True)
    return sorted_list[:20]

@st.cache_data(ttl=60)
def get_token_transfers(mint):
    start_time = int(seven_days_ago.timestamp())
    url = f"{BASE_URL}/tokens/{mint}/transfers?api-key={API_KEY}&startTime={start_time}&limit=500"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.json()
    except:
        return []

def analyze_tokens(mints):
    rows = []
    for mint, created_at in mints:
        transfers = get_token_transfers(mint)
        wallet_set = set()
        pumpswap_count = 0
        jupiter_count = 0
        total_count = len(transfers)

        for tx in transfers:
            wallet_set.add(tx.get("source"))
            wallet_set.add(tx.get("destination"))
            program_id = tx.get("programId")
            if program_id == PUMPSWAP_PROGRAM_ID:
                pumpswap_count += 1
            if program_id == JUPITER_PROGRAM_ID:
                jupiter_count += 1

        # 计算占比，防止除零
        pumpswap_share = pumpswap_count / total_count if total_count else 0
        jupiter_share = jupiter_count / total_count if total_count else 0

        rows.append({
            "Token Mint": mint,
            "创建时间": created_at.strftime("%Y-%m-%d %H:%M"),
            "交易笔数": total_count,
            "活跃钱包数": len(wallet_set),
            "PumpSwap占比": pumpswap_share,
            "Jupiter占比": jupiter_share
        })
    return rows

def render_table(data):
    if not data:
        st.info("暂无新币数据，等待更新...")
        return

    df = pd.DataFrame(data)

    # 转换占比为百分比格式，便于展示
    df["PumpSwap占比"] = df["PumpSwap占比"].apply(lambda x: f"{x:.2%}")
    df["Jupiter占比"] = df["Jupiter占比"].apply(lambda x: f"{x:.2%}")

    # 样式：占比大于20%的显示红色
    def color_red(val):
        try:
            return 'color: red;' if float(val.strip('%')) > 20 else ''
        except:
            return ''

    styled_df = df.style.applymap(color_red, subset=["PumpSwap占比", "Jupiter占比"])

    st.table(styled_df)

def main():
    mints = get_new_tokens()
    data = analyze_tokens(mints)
    render_table(data)

if __name__ == "__main__":
    main()
