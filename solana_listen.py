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
        accounts_resp = client.get_program_accounts(JUPITER_PROG, limit=1000)
        if "result" not in accounts_resp or not accounts_resp["result"]:
            return []
        return accounts_resp["result"]
    except Exception as e:
        st.error(f"❌ 获取 Jupiter 市场信息失败: {e}")
        return []

def parse_market_account(acc):
    # 这里简单示意如何解析账户数据：
    # 实际使用请替换为正确的反序列化逻辑，依据Jupiter市场数据格式
    try:
        # acc["account"]["data"]是base64编码字符串，需要解码处理
        data = acc.get("account", {}).get("data", [None, None])
        if not data or data[0] is None:
            return None
        import base64
        decoded = base64.b64decode(data[0])
        # 示例：假设offset和长度，读取mint地址等信息（需要根据实际格式调整）
        # 这里用占位符模拟
        mint = "示例Mint地址1234"
        base_mint = SOL_MINT
        quote_mint = "示例交易对Mint5678"
        # 模拟创建时间，取当前时间减随机小时数
        import random
        created_ts = int(datetime.utcnow().timestamp()) - random.randint(0, 7*24)*3600
        return {
            "mint": mint,
            "base_mint": base_mint,
            "quote_mint": quote_mint,
            "created_ts": created_ts
        }
    except Exception:
        return None

def get_token_name(mint):
    # 你可以扩展此函数调用Solana Token List等接口获取代币名称
    # 目前简单返回mint后8位示意
    return mint[-8:]

def filter_and_enrich_markets(accounts):
    rows = []
    now_ts = int(datetime.utcnow().timestamp())
    seven_days_ago_ts = now_ts - 7*24*3600

    for acc in accounts:
        parsed = parse_market_account(acc)
        if not parsed:
            continue
        if parsed["base_mint"] != SOL_MINT and parsed["quote_mint"] != SOL_MINT:
            continue
        if parsed["created_ts"] < seven_days_ago_ts:
            continue

        # 模拟成交量和成交额，真实项目请调用相关API替换
        volume = round(1000 + (now_ts - parsed["created_ts"]) % 1000, 2)
        amount_sol = round(100 + (now_ts - parsed["created_ts"]) % 100, 2)

        rows.append({
            "代币名称": get_token_name(parsed["mint"]),
            "代币Mint": parsed["mint"],
            "交易对BaseMint": parsed["base_mint"],
            "交易对QuoteMint": parsed["quote_mint"],
            "上架时间": datetime.utcfromtimestamp(parsed["created_ts"]).strftime("%Y-%m-%d %H:%M:%S"),
            "成交量": volume,
            "成交额(SOL)": amount_sol
        })

    rows = sorted(rows, key=lambda x: x["成交额(SOL)"], reverse=True)[:20]
    return rows

def main():
    with st.spinner("数据加载中，请稍等..."):
        accounts = fetch_jupiter_markets()

    st.sidebar.header(f"📜 Jupiter 市场账户 共{len(accounts)}个")
    if accounts:
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
