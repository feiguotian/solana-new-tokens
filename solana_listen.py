import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta
from solana.publickey import PublicKey
from solana.rpc.api import Client

# 配置
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"
JUPITER_PROG = PublicKey("JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4")
SOL_MINT = "So11111111111111111111111111111111111111112"  # SOL 原生代币mint地址
REFRESH_INTERVAL_MS = 5000

# 初始化Solana客户端
client = Client(HELIUS_RPC)

st.set_page_config(page_title="🪙 监听Jupiter新币（7天内）与SOL配对活跃排行榜", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="refresh")

st.title("🪙 监听 Jupiter 7天内新上架与 SOL 配对活跃交易币种")
st.caption("数据实时刷新，每5秒更新 | 来自 Jupiter Program + Helius RPC")

def fetch_jupiter_markets():
    try:
        # getProgramAccounts 需要传入 PublicKey 类型
        accounts_resp = client.get_program_accounts(JUPITER_PROG, limit=1000)
        if "result" not in accounts_resp or not accounts_resp["result"]:
            return []
        return accounts_resp["result"]
    except Exception as e:
        st.error(f"❌ 获取 Jupiter 市场信息失败: {e}")
        return []

def parse_market_account(data):
    # 此处是示例，需要根据 Jupiter 市场账户数据结构解码
    # 这里只简单示意：实际你需要反序列化bytes得到市场信息，比如mint地址、baseMint、quoteMint、创建时间等
    # 由于反序列化较复杂，以下示意取mint等假数据
    try:
        # 以下示例假设数据以某种格式存储，你需要替换为正确的解析逻辑
        # 这里暂时mock数据结构，供展示用
        mint = "示例Mint地址"
        base_mint = SOL_MINT
        quote_mint = "示例交易对Mint"
        created_ts = int(datetime.utcnow().timestamp()) - 3600 * 24  # 模拟1天前创建
        return {
            "mint": mint,
            "base_mint": base_mint,
            "quote_mint": quote_mint,
            "created_ts": created_ts
        }
    except Exception:
        return None

def filter_and_enrich_markets(accounts):
    rows = []
    now_ts = int(datetime.utcnow().timestamp())
    seven_days_ago_ts = now_ts - 7*24*3600

    for acc in accounts:
        parsed = parse_market_account(acc)
        if not parsed:
            continue
        # 只看base或quote是SOL的市场对
        if parsed["base_mint"] != SOL_MINT and parsed["quote_mint"] != SOL_MINT:
            continue
        # 只要7天内创建
        if parsed["created_ts"] < seven_days_ago_ts:
            continue

        # 这里需要调用Helius或者其他接口查询该市场对应代币的实时成交量和成交额
        # 以下用模拟数据替代，生产环境请替换为真实数据获取逻辑
        volume = 12345.67   # 模拟成交量
        amount_sol = 890.12 # 模拟成交额

        rows.append({
            "代币Mint": parsed["mint"],
            "交易对BaseMint": parsed["base_mint"],
            "交易对QuoteMint": parsed["quote_mint"],
            "上架时间": datetime.utcfromtimestamp(parsed["created_ts"]).strftime("%Y-%m-%d %H:%M:%S"),
            "成交量": volume,
            "成交额(SOL)": amount_sol
        })

    # 按成交额降序排序，只保留前20个
    rows = sorted(rows, key=lambda x: x["成交额(SOL)"], reverse=True)[:20]

    return rows

def main():
    with st.spinner("数据加载中，请稍等..."):
        accounts = fetch_jupiter_markets()
    st.sidebar.header(f"📜 Jupiter 市场账户 共{len(accounts)}个")
    if accounts:
        # 简单展示账户列表
        account_list = [acc["pubkey"] for acc in accounts]
        st.sidebar.write(account_list)
    else:
        st.sidebar.write("无市场账户数据")

    rows = filter_and_enrich_markets(accounts)
    if not rows:
        st.info("⚠️ 最近7天内未发现活跃的新币市场（与 SOL 配对）。")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
