import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta
import base64
import json
from time import sleep
import sys

# --- 兼容性导入处理 ---
try:
    # 新版本推荐导入方式 (solana>=0.29.0)
    from solders.pubkey import Pubkey as PublicKey
    from solana.rpc.api import Client
except ImportError:
    try:
        # 旧版本回退方案
        from solana.publickey import PublicKey
        from solana.rpc.api import Client
    except ImportError as e:
        st.error(f"❌ 关键依赖缺失: {str(e)}")
        st.error("""
            ⚠️ 请通过以下命令安装依赖:
            pip install solana==0.29.0 solders==0.26.0
        """)
        st.stop()

# --- 配置 ---
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"  # 建议改为环境变量
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"
JUPITER_PROG = PublicKey("JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4")
SOL_MINT = "So11111111111111111111111111111111111111112"
TOKEN_LIST_URL = "https://cdn.jsdelivr.net/gh/solana-labs/token-list@main/src/tokens/solana.tokenlist.json"
REFRESH_INTERVAL_MS = 15000  # 15秒刷新避免API限制

# --- 初始化 ---
client = Client(HELIUS_RPC)
st.set_page_config(page_title="🪙 Jupiter新币监控", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="refresh")

st.title("🪙 Jupiter 7天内新上架与SOL配对的交易币种")
st.caption(f"数据每{REFRESH_INTERVAL_MS//1000}秒刷新 | 数据来源: Jupiter + Helius")

# --- 核心函数 ---
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
                data_size=165,
                commitment="confirmed"
            )
            return accounts_resp.get('result', [])
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"❌ 获取市场失败 (尝试 {attempt+1}/{max_retries}): {str(e)}")
            sleep(1)
    return []

def parse_market_account(acc, token_list):
    """安全解析市场账户"""
    try:
        data = base64.b64decode(acc['account']['data'][0])
        
        # 基础验证
        if len(data) < 128:
            return None
            
        # 解析关键字段
        mint = PublicKey(data[32:64]).__str__() if len(data) >= 64 else None
        base_mint = PublicKey(data[64:96]).__str__() if len(data) >= 96 else None
        quote_mint = PublicKey(data[96:128]).__str__() if len(data) >= 128 else None
        
        if not all([mint, base_mint, quote_mint]):
            return None
            
        # 获取代币元数据
        token_meta = get_token_metadata(mint, token_list)
        
        return {
            "mint": mint,
            "base_mint": base_mint,
            "quote_mint": quote_mint,
            "created_ts": acc['account']['lamports'],  # 临时替代方案
            "name": token_meta['name'],
            "symbol": token_meta['symbol'],
            "logo": token_meta['logo']
        }
    except Exception as e:
        st.warning(f"账户解析警告: {str(e)}")
        return None

def get_token_metadata(mint, token_list):
    """获取代币元数据"""
    for token in token_list:
        if token['address'] == mint:
            return {
                "name": token.get('name', 'Unknown'),
                "symbol": token.get('symbol', 'UNK'),
                "logo": token.get('logoURI')
            }
    return {
        "name": f"Unknown ({mint[:4]}...{mint[-4:]})",
        "symbol": "UNK",
        "logo": None
    }

# --- 主函数 ---
def main():
    # 加载数据
    token_list = load_token_list()
    
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
        market = parse_market_account(acc, token_list)
        if not market:
            continue
        if SOL_MINT not in [market['base_mint'], market['quote_mint']]:
            continue
        if market.get('created_ts', 0) < seven_days_ago_ts:
            continue
        valid_markets.append(market)
    
    # 显示结果
    if not valid_markets:
        st.info("⚠️ 最近7天内未发现与SOL配对的新币市场")
        return
    
    st.success(f"发现 {len(valid_markets)} 个符合条件的市场")
    
    # 构建表格数据
    df_data = []
    for market in valid_markets[:50]:  # 限制显示数量
        df_data.append({
            "代币": market['name'],
            "符号": market['symbol'],
            "Mint地址": market['mint'],
            "交易对": f"{'SOL' if market['base_mint'] == SOL_MINT else market['symbol']}/{'SOL' if market['quote_mint'] == SOL_MINT else 'OTHER'}",
            "创建时间": datetime.fromtimestamp(market.get('created_ts', now_ts)).strftime("%Y-%m-%d %H:%M"),
            "Logo": market['logo']
        })
    
    # 显示表格
    st.dataframe(
        pd.DataFrame(df_data),
        use_container_width=True,
        column_config={
            "Logo": st.column_config.ImageColumn("Logo", width="small"),
            "Mint地址": st.column_config.TextColumn("Mint地址", help="代币合约地址")
        },
        hide_index=True
    )

if __name__ == "__main__":
    main()
