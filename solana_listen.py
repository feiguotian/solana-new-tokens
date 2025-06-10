import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from solana.rpc.api import Client
from datetime import datetime, timedelta

# ===== 设置与初始化 =====
st.set_page_config(page_title="🪙 Jupiter 新币监听器", layout="wide")
st_autorefresh(interval=5000, key="refresh")  # 每 5 秒刷新

st.title("🪙 监听 Jupiter 7天内新上架与 SOL 配对活跃交易币种")
st.caption("数据实时刷新，每5秒更新 | 来自 Jupiter + Helius RPC")

# ===== 初始化客户端与参数 =====
RPC_URL = "https://mainnet.helius-rpc.com/?api-key=ccf35c43-496e-4514-b595-1039601450f2"
client = Client(RPC_URL)

NOW = datetime.utcnow()
SEVEN_DAYS_AGO = NOW - timedelta(days=7)
SEVEN_DAYS_AGO_TS = int(SEVEN_DAYS_AGO.timestamp())

# ===== 获取 Jupiter 所有市场账户 =====
@st.cache_data(ttl=60)
def get_jupiter_markets():
    try:
        resp = client.get_program_accounts("JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4")
        accounts = resp.get("result", [])
        return accounts
    except Exception as e:
        st.error(f"❌ 获取 Jupiter 市场信息失败: {e}")
        return []

# ===== 模拟解析市场账户数据（仅示例，实际应解码Account数据） =====
def parse_market_accounts(accounts):
    rows = []
    now_ts = int(datetime.utcnow().timestamp())
    for acc in accounts:
        pubkey = acc.get("pubkey")
        if not pubkey:
            continue
        try:
            # ⚠️ 模拟创建时间，仅用于展示
            mock_hours_ago = int(pubkey[-2:], 16) % (24 * 7)
            created_ts = now_ts - mock_hours_ago * 3600

            if created_ts < SEVEN_DAYS_AGO_TS:
                continue

            # ⚠️ 模拟名称与交易数据
            mock_token = f"Token_{pubkey[:4]}"
            mock_volume = round((int(pubkey[:4], 16) % 1000) + 1, 2)
            mock_amount = round(mock_volume * 0.01, 4)

            rows.append({
                "代币名称": mock_token,
                "交易对地址": pubkey,
                "上架时间": datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d %H:%M:%S"),
                "成交量（Token）": mock_volume,
                "成交额（SOL）": mock_amount
            })
        except Exception:
            continue
    return rows

# ===== 主逻辑 =====
def main():
    with st.spinner("数据加载中，请稍等..."):
        accounts = get_jupiter_markets()
        if not accounts:
            st.warning("⚠️ 最近7天内未发现活跃的新币市场（与 SOL 配对）。")
            return

        parsed = parse_market_accounts(accounts)
        if not parsed:
            st.warning("⚠️ 没有符合条件的市场数据。")
            return

        df = pd.DataFrame(parsed)
        df = df.sort_values(by="成交额（SOL）", ascending=False)

        st.dataframe(df, use_container_width=True)

        # 侧边栏显示市场账户
        with st.sidebar:
            st.subheader("📜 Jupiter 市场账户")
            st.caption(f"共获取到 {len(accounts)} 个市场账户")
            for acc in accounts:
                st.markdown(f"- `{acc.get('pubkey', '未知')}`")

# ===== 启动程序 =====
if __name__ == "__main__":
    main()
