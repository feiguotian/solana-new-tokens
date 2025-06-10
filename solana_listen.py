import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta
from solana.publickey import PublicKey
from solana.rpc.api import Client
import base64
import json
from time import sleep

# 配置 - 建议将API_KEY移到环境变量中
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"
JUPITER_PROG = PublicKey("JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4")
SOL_MINT = "So11111111111111111111111111111111111111112"
TOKEN_LIST_URL = "https://cdn.jsdelivr.net/gh/solana-labs/token-list@main/src/tokens/solana.tokenlist.json"
REFRESH_INTERVAL_MS = 15000  # 改为15秒刷新避免速率限制

# 初始化Solana客户端
client = Client(HELIUS_RPC)

st.set_page_config(page_title="🪙 Jupiter新币监控", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="refresh")

st.title("🪙 Jupiter 7天内新上架与SOL配对的交易币种")
st.caption(f"数据每{REFRESH_INTERVAL_MS//1000}秒刷新 | 数据来源: Jupiter + Helius")

@st.cache_data(ttl=3600)
def load_token_list():
    """加载Solana代币列表"""
    try:
        response = requests.get(TOKEN_LIST_URL, timeout=10)
        response.raise_for_status()
        return response.json().get('tokens', [])
    except Exception as e:
        st.error(f"❌ 加载代币列表失败: {str(e)}")
        return []

def fetch_jupiter_markets(max_retries=3):
    """获取Jupiter市场账户，带有重试机制"""
    for attempt in range(max_retries):
        try:
            accounts_resp = client.get_program_accounts(
                JUPITER_PROG,
                encoding="base64",
                data_size=165,  # 典型的市场账户大小
                commitment="confirmed"
            )
            if 'result' in accounts_resp:
                return accounts_resp['result']
            return []
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"❌ 获取Jupiter市场失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            sleep(1)
    return []

def parse_market_account(acc):
    """更安全的账户解析方法"""
    try:
        data = base64.b64decode(acc['account']['data'][0])
        
        # 更稳健的解析方式 - 这里需要根据Jupiter实际账户结构调整
        if len(data) < 128:  # 确保数据足够长
            return None
            
        # 示例解析 - 实际偏移量需要确认
        mint = PublicKey(data[32:64]).to_base58().decode() if len(data) >= 64 else None
        base_mint = PublicKey(data[64:96]).to_base58().decode() if len(data) >= 96 else None
        quote_mint = PublicKey(data[96:128]).to_base58().decode() if len(data) >= 128 else None
        
        if not all([mint, base_mint, quote_mint]):
            return None
            
        # 使用区块时间作为近似创建时间
        return {
            "mint": mint,
            "base_mint": base_mint,
            "quote_mint": quote_mint,
            "created_ts": acc['account']['lamports']  # 临时使用lamports作为时间替代
        }
    except Exception as e:
        st.warning(f"账户解析警告: {str(e)}")
        return None

def get_token_metadata(mint, token_list):
    """获取代币元数据，带有更好的回退处理"""
    mint_str = str(mint)
    for token in token_list:
        if token['address'] == mint_str:
            return {
                "name": token.get('name', 'Unknown'),
                "symbol": token.get('symbol', 'UNK'),
                "logo": token.get('logoURI')
            }
    return {
        "name": f"Unknown ({mint_str[:4]}...{mint_str[-4:]})",
        "symbol": "UNK",
        "logo": None
    }

def main():
    # 加载代币列表
    token_list = load_token_list()
    
    # 获取市场数据
    with st.spinner("🔄 正在加载市场数据..."):
        accounts = fetch_jupiter_markets()
    
    if not accounts:
        st.error("无法获取市场数据，请检查网络连接或API密钥")
        return
    
    # 处理数据
    now_ts = datetime.utcnow().timestamp()
    seven_days_ago_ts = now_ts - 7 * 24 * 3600
    
    valid_markets = []
    for acc in accounts:
        market = parse_market_account(acc)
        if not market:
            continue
        if SOL_MINT not in [market['base_mint'], market['quote_mint']]:
            continue
        if market.get('created_ts', 0) < seven_days_ago_ts:
            continue
        valid_markets.append(market)
    
    if not valid_markets:
        st.info("⚠️ 最近7天内未发现与SOL配对的新币市场")
        return
    
    # 显示结果
    st.success(f"发现 {len(valid_markets)} 个符合条件的市场")
    
    # 创建表格数据
    table_data = []
    for market in valid_markets[:50]:  # 限制显示数量
        meta = get_token_metadata(market['mint'], token_list)
        table_data.append({
            "代币": meta['name'],
            "符号": meta['symbol'],
            "Mint地址": market['mint'],
            "交易对": f"{'SOL' if market['base_mint'] == SOL_MINT else meta['symbol']}/{'SOL' if market['quote_mint'] == SOL_MINT else 'OTHER'}",
            "创建时间": datetime.fromtimestamp(market.get('created_ts', now_ts)).strftime("%Y-%m-%d %H:%M"),
            "Logo": meta['logo']
        })
    
    # 显示表格
    st.dataframe(
        pd.DataFrame(table_data),
        use_container_width=True,
        column_config={
            "Logo": st.column_config.ImageColumn("Logo", width="small"),
            "Mint地址": st.column_config.TextColumn("Mint地址", help="代币合约地址")
        },
        hide_index=True
    )

if __name__ == "__main__":
    main()
