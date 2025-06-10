import streamlit as st
from solana.publickey import PublicKey

st.title("Solana SDK Import Test")

try:
    # 测试创建一个公钥对象
    pk = PublicKey("4Nd1mZLrLeYJ6TXYDck6kK8U7zF6B7DzKh6V9N6pXYbP")
    st.write("PublicKey 创建成功:", pk)
except Exception as e:
    st.error(f"导入或使用 solana 出错: {e}")
