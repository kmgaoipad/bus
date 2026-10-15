import os
import pandas as pd
import streamlit as st
from datetime import datetime
from supabase import create_client, Client

st.set_page_config(page_title="KMSH校車驗證系統", page_icon="🚌", layout="centered")

USER_FILE = "校車驗證系統使用者名單.xlsx"

# 1. Supabase 連線設定
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None

supabase = init_supabase()

def clean_seat_number(val):
    if val is None:
        return ""
    if not isinstance(val, (str, int, float)):
        return ""
    val_str = str(val).strip()
    if not val_str or "DeltaGenerator" in val_str:
        return ""
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
    return val_str

@st.cache_data
def load_users():
    if not os.path.exists(USER_FILE):
        return None
    try:
        df_users = pd.read_excel(USER_FILE)
        for col in df_users.columns:
            df_users[col] = df_users[col].apply(clean_seat_number)
        return df_users
    except Exception:
        return None

# 初始化 Session State
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_id" not in st.session_state:
    st.session_state["user_id"] = ""
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""
if "log_id" not in st.session_state:
    st.session_state["log_id"] = None

# ---------------------------------------------------------
# 🔒 1. 登入畫面
# ---------------------------------------------------------
if not st.session_state["authenticated"]:
    st.title("🔒 KMSH 校車驗證系統 - 登入")
    st.caption("請輸入使用者編號與密碼。")
    
    df_users = load_users()
    if df_users is None:
        st.error(f"❌ 找不到使用者名單檔案 (`{USER_FILE}`)，請確認檔案已上傳！")
        st.stop()
        
    with st.form("login_form"):
        user_input = st.text_input("使用者編號 (或姓名)", placeholder="例如：user1").strip()
        password_input = st.text_input("密碼", type="password").strip()
        submit_button = st.form_submit_button("登入系統")
        
        if submit_button:
            if not user_input or not password_input:
                st.error("請輸入帳號與密碼！")
            else:
                matched_user = df_users[
                    ((df_users["使用者編號"] == user_input) | (df_users["使用者姓名"] == user_input)) & 
                    (df_users["使用者密碼"] == password_input)
                ]
                
                if not matched_user.empty:
                    user_info = matched_user.iloc[0]
                    st.session_state["authenticated"] = True
                    st.session_state["user_id"] = str(user_info["使用者編號"])
                    st.session_state["user_name"] = str(user_info["使用者姓名"])
                    
                    if supabase:
                        try:
                            log_res = supabase.table("usage_logs").insert({
                                "user_email": f"{st.session_state['user_id']} ({st.session_state['user_name']})",
                                "login_time": datetime.now().isoformat()
                            }).execute()
                            if log_res.data:
                                st.session_state["log_id"] = log_res.data[0]["id"]
                        except Exception:
                            pass
                            
                    st.success(f"✅ 歡迎 {st.session_state['user_name']}，請選擇您的裝置類型進入系統...")
                    st.rerun()
                else:
                    st.error("❌ 登入失敗：使用者編號或密碼錯誤，請重新確認。")
    st.stop()

# ---------------------------------------------------------
# 📱 2. 裝置選單頁面 (驗證通過後)
# ---------------------------------------------------------
st.title("🚌 KMSH 校車驗證系統")
st.write(f"👤 當前登入者：**{st.session_state['user_name']} ({st.session_state['user_id']})**")
st.divider()

st.subheader("請點選您的手機裝置類型進入驗證頁面：")

col1, col2 = st.columns(2)

with col1:
    st.info("### 🍎 iPhone / iPad")
    st.caption("針對 Safari 瀏覽器優化 Canvas 相機防黑屏技術。")
    if st.button("進入 🍎 iOS 驗證頁面", use_container_width=True):
        st.switch_page("pages/1_iOS.py")

with col2:
    st.success("### 🤖 Android 手機")
    st.caption("針對 Chrome 瀏覽器優化 Html5Qrcode 相機硬體引擎。")
    if st.button("進入 🤖 Android 驗證頁面", use_container_width=True):
        st.switch_page("pages/2_Android.py")

st.divider()
if st.button("🚪 安全登出系統"):
    if st.session_state["log_id"] and supabase:
        try:
            supabase.table("usage_logs").update({
                "logout_time": datetime.now().isoformat()
            }).eq("id", st.session_state["log_id"]).execute()
        except Exception:
            pass
    st.session_state["authenticated"] = False
    st.session_state["user_id"] = ""
    st.session_state["user_name"] = ""
    st.session_state["log_id"] = None
    st.rerun()