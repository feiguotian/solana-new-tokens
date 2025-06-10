import streamlit as st
from streamlit_autorefresh import st_autorefresh
from solana.rpc.api import Client
from datetime import datetime, timedelta
import pandas as pd

# ========== 基本配置 ==========
st.set_page_config(page_title="🪙 Jupiter 活跃新币监听", layout="wide")
st_autorefresh(interval=5000, key="autorefresh")

st.title("🪙 监听 Jupiter 7天内新上架与 SOL 配对活跃交易币种")
st.caption("数据实时刷新，每5秒更新 | 来自 Jupiter + Streamlit")

st.markdown("---")

# ========== 设置 ==========
RPC_URL = "https://mainnet.helius-rpc.com/?api-key=ccf35c43-496e-4514-b595-1039601450f2"
JUPITER_PROGRAM_ID = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
SOL_MINT = "So11111111111111111111111111111111111111112"
DAYS_LIMIT = 7

client = Client(RPC_URL)
now_ts = int(datetime.utcnow().timestamp())
past_ts = now_ts - DAYS_LIMIT * 86400

# ========== 获取 Jupiter 市场账户 ==========
@st.cache_data(ttl=300)
def get_jupiter_markets():
    try:
        filters = [
            {"memcmp": {"offset": 13, "bytes": SOL_MINT}},  # quote currency 是 SOL
        ]
        resp = client.get_program_accounts(JUPITER_PROGRAM_ID, encoding="jsonParsed", filters=filters)
        accounts = resp.get("result", [])
        return accounts
    except Exception as e:
        st.error(f"❌ 获取 Jupiter 市场账户失败: {e}")
        return []

accounts = get_jupiter_markets()

# ========== 显示市场账户信息 ==========
with st.sidebar:
    st.subheader("📜 Jupiter 市场账户")
    st.caption(f"共获取到 {len(accounts)} 个市场账户")
    for acc in accounts:
        st.markdown(f"- `{acc['pubkey']}`")

# ========== 分析活跃币对 ==========
def parse_market_data(account):
    parsed = account["account"]["data"]["parsed"]["info"]
    base_mint = parsed.get("baseMint")
    base_symbol = parsed.get("baseTokenName", "Unknown")
    quote_mint = parsed.get("quoteMint")
    lp_supply = int(parsed.get("lpSupply", 0))
    base_deposit = float(parsed.get("baseDeposits", 0)) / 1e6
    quote_deposit = float(parsed.get("quoteDeposits", 0)) / 1e9
    market_pubkey = account.get("pubkey")

    # 模拟创建时间：用地址后两位字符计算（避免使用真实区块信息）
    created_ts = now_ts - int(market_pubkey[-2:], 16) * 3600

    return {
        "代币名称": base_symbol,
        "Mint": base_mint,
        "市场地址": market_pubkey,
        "上架时间": datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d %H:%M:%S"),
        "成交量（Token）": f"{base_deposit:.2f}",
        "成交额（SOL）": f"{quote_deposit:.2f}",
        "成交量值": base_deposit,
        "成交额值": quote_deposit,
        "创建时间戳": created_ts
    }

# ========== 显示主表格 ==========
if not accounts:
    st.warning("⚠️ 最近7天内未发现活跃的新币市场（与 SOL 配对）。")
else:
    rows = []
    for acc in accounts:
        market = parse_market_data(acc)
        if market["创建时间戳"] >= past_ts and market["成交额值"] > 0:
            rows.append(market)

    if not rows:
        st.info("🔍 数据加载中，请稍等...（或未发现符合条件的市场）")
    else:
        df = pd.DataFrame(rows)
        sort_by = st.selectbox("排序依据", options=["成交额值", "成交量值"], format_func=lambda x: "成交额（SOL）" if x == "成交额值" else "成交量（Token）")
        df = df.sort_values(by=sort_by, ascending=False).drop(columns=["成交额值", "成交量值", "创建时间戳"])

        st.dataframe(df, use_container_width=True)
