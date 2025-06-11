import streamlit as st
from streamlit_autorefresh import st_autorefresh
import requests
import pandas as pd
from datetime import datetime, timedelta
import base64
import json
from time import sleep
import sys

# --- 强制使用兼容导入方案 ---
try:
    from solders.pubkey import Pubkey as PublicKey
    from solana.rpc.api import Client
except ImportError as e:
    st.error(f"""
    ❌ 关键依赖错误: {str(e)}
    ============================================
    请确保已安装正确版本的依赖:
    1. 删除现有的虚拟环境
    2. 执行: pip install -r requirements.txt
    3. 确认安装的版本:
       - solana==0.30.0
       - solders==0.26.0
    """)
    sys.exit(1)

# --- 配置 ---
API_KEY = "ccf35c43-496e-4514-b595-1039601450f2"  # 建议改为环境变量
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={API_KEY}"
JUPITER_PROG = PublicKey("JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4")
SOL_MINT = "So11111111111111111111111111111111111111112"
TOKEN_LIST_URL = "https://cdn.jsdelivr.net/gh/solana-labs/token-list@main/src/tokens/solana.tokenlist.json"
REFRESH_INTERVAL_MS = 15000

# --- 初始化 ---
client = Client(HELIUS_RPC)
st.set_page_config(page_title="🪙 Jupiter新币监控", layout="wide")
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="refresh")

# --- 数据获取函数 ---
@st.cache_data(ttl=3600)
def load_token_list():
    try:
        response = requests.get(TOKEN_LIST_URL, timeout=10)
        response.raise_for_status()
        return response.json().get('tokens', [])
    except Exception as e:
        st.error(f"❌ 代币列表加载失败: {str(e)}")
        return []

def safe_get_accounts(max_retries=3):
    for attempt in range(max_retries):
        try:
            result = client.get_program_accounts(
                JUPITER_PROG,
                encoding="base64",
                data_size=165,
                commitment="confirmed"
            )
            return result.get('result', [])
        except Exception as e:
            if attempt == max_retries - 1:
                st.error(f"⚠️ 获取账户失败 (最终尝试): {str(e)}")
            sleep(1)
    return []

# --- 主逻辑 ---
def main():
    st.title("🪙 Jupiter 7天内新上架币种 (SOL交易对)")
    
    with st.spinner("🔄 加载数据中..."):
        token_list = load_token_list()
        accounts = safe_get_accounts()
    
    if not accounts:
        st.error("无法获取市场数据，请检查网络或API密钥")
        return
    
    # 数据处理
    valid_markets = []
    for acc in accounts:
        try:
            data = base64.b64decode(acc['account']['data'][0])
            mint = PublicKey(data[32:64]).__str__()
            base_mint = PublicKey(data[64:96]).__str__()
            quote_mint = PublicKey(data[96:128]).__str__()
            
            if SOL_MINT not in [base_mint, quote_mint]:
                continue
                
            # 获取代币信息
            token_info = next((t for t in token_list if t['address'] == mint), None)
            if not token_info:
                continue
                
            valid_markets.append({
                "name": token_info.get('name', f"Unknown ({mint[:4]}...)"),
                "symbol": token_info.get('symbol', 'UNK'),
                "mint": mint,
                "pair": f"{'SOL' if base_mint == SOL_MINT else token_info['symbol']}/{'SOL' if quote_mint == SOL_MINT else 'OTHER'}",
                "logo": token_info.get('logoURI')
            })
        except Exception:
            continue
    
    # 显示结果
    if not valid_markets:
        st.info("⚠️ 未发现近期新币")
        return
        
    st.success(f"🎉 发现 {len(valid_markets)} 个新币")
    
    # 表格显示
    st.dataframe(
        pd.DataFrame(valid_markets),
        column_config={
            "logo": st.column_config.ImageColumn("图标"),
            "mint": st.column_config.TextColumn("合约地址", help="点击复制")
        },
        use_container_width=True
    )

if __name__ == "__main__":
    main()
