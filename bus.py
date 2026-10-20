import os
import pandas as pd
import streamlit as st
from datetime import datetime
from supabase import create_client, Client
from streamlit_qrcode_scanner import qrcode_scanner

# 隱藏左側邊欄
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

# 設定網頁標題與頁面圖示
st.set_page_config(page_title="KMSH校車驗證系統", page_icon="🚌", layout="centered")

USER_FILE = "校車驗證系統使用者名單.xlsx"

# 管理者預設帳密
ADMIN_USER = "kmsh"
ADMIN_PASS = "kmsh"

# 路線類別與檔案對應設定
CATEGORY_CONFIG = {
    "上學": {"file": "上學各路線名單.xlsx", "filter": None},
    "大放學 (第1梯)": {"file": "大放學12各路線名單.xlsx", "filter": "大放1"},
    "大放學 (第2梯)": {"file": "大放學12各路線名單.xlsx", "filter": "大放2"},
    "週一小放學 (第1梯)": {"file": "週1小放學1梯各路線名單.xlsx", "filter": None},
    "週一小放學 (第2梯)": {"file": "週1小放學2梯各路線名單.xlsx", "filter": None},
    "週二小放學 (第1梯)": {"file": "週2小放學1梯各路線名單.xlsx", "filter": None},
    "週二小放學 (第2梯)": {"file": "週2小放學2梯各路線名單.xlsx", "filter": None},
    "週三小放學 (第1梯)": {"file": "週3小放學1梯各路線名單.xlsx", "filter": None},
    "週三小放學 (第2梯)": {"file": "週3小放學2梯各路線名單.xlsx", "filter": None},
    "週四小放學 (第1梯)": {"file": "週4小放學1梯各路線名單.xlsx", "filter": None},
    "週四小放學 (第2梯)": {"file": "週4小放學2梯各路線名單.xlsx", "filter": None},
    "週五小放學 (第1梯)": {"file": "週5小放學1梯各路線名單.xlsx", "filter": None},
    "週五小放學 (第2梯)": {"file": "週5小放學2梯各路線名單.xlsx", "filter": None}
}

# 1. Supabase 連線設定
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "您的_SUPABASE_URL")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "您的_SUPABASE_ANON_KEY")

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None

supabase = init_supabase()

# 整理班級座號字串（處理 float 自動補 .0 的問題）
def clean_seat_number(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s

# 讀取使用者名單 Excel
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

@st.cache_data
def load_category_data(file_path, prefix_filter=None):
    if not os.path.exists(file_path):
        return None, None
        
    xls = pd.ExcelFile(file_path)
    all_dfs = []
    
    target_sheets = xls.sheet_names
    if prefix_filter:
        target_sheets = [s for s in xls.sheet_names if s.startswith(prefix_filter)]
        
    for sheet_name in target_sheets:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df['路線名稱'] = sheet_name.strip()
        all_dfs.append(df)
        
    if not all_dfs:
        return None, None
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df['班級座號'] = combined_df['班級座號'].apply(clean_seat_number)
    
    return combined_df, target_sheets

# CSS 樣式設定 (專門優化手機版下拉選單高度與觸控體驗)
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.8rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        h1 {
            font-size: 1.3rem !important;
            margin-bottom: 0.3rem !important;
        }
        div[data-testid="stVerticalBlock"] > div {
            gap: 0.5rem !important;
        }
        
        /* 1. 解決下拉選單在手機版向上展開時最上方被切掉或無法選到的問題 */
        div[data-baseweb="popover"] {
            z-index: 99999 !important;
        }
        div[data-baseweb="popover"] > div {
            max-height: 45vh !important;
            overflow-y: auto !important;
        }
        ul[role="listbox"] {
            max-height: 40vh !important;
            overflow-y: auto !important;
        }
        li[role="option"] {
            padding-top: 10px !important;
            padding-bottom: 10px !important;
            font-size: 0.95rem !important;
        }
        
        /* 2. 限制掃描器層級與高度，避免遮擋頂部彈出的選單 */
        iframe[title*="qrcode_scanner"] {
            max-height: 180px !important;
            position: relative !important;
            z-index: 1 !important;
        }
        
        .stAlert {
            padding: 8px 12px !important;
            margin-top: 0.3rem !important;
            margin-bottom: 0.3rem !important;
        }
        .route-info {
            font-size: 0.85rem !important;
            color: #155724;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 4px;
            padding: 4px 8px;
            margin-bottom: 0.2rem;
            display: inline-block;
            width: 100%;
        }
        [data-testid="stMetric"] {
            background-color: #f8f9fa;
            padding: 4px 6px !important;
            border-radius: 4px;
            border: 1px solid #e9ecef;
        }
        [data-testid="stMetricValue"] {
            font-size: 1rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.75rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# 初始化 Session State
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False
if "user_id" not in st.session_state:
    st.session_state["user_id"] = ""
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""
if "log_id" not in st.session_state:
    st.session_state["log_id"] = None

# ---------------------------------------------------------
# 🔒 登入驗證畫面
# ---------------------------------------------------------
if not st.session_state["authenticated"]:
    st.title("🔒 KMSH 校車驗證系統")
    st.caption("請輸入使用者編號與密碼，或管理者帳密。")
    
    df_users = load_users()
    
    with st.form("login_form"):
        user_input = st.text_input("使用者編號 (或帳號)").strip()
        password_input = st.text_input("密碼", type="password").strip()
        submit_button = st.form_submit_button("登入系統")
        
        if submit_button:
            if not user_input or not password_input:
                st.error("請輸入帳號與密碼！")
            else:
                # 1. 管理者登入
                if user_input == ADMIN_USER and password_input == ADMIN_PASS:
                    st.session_state["authenticated"] = True
                    st.session_state["is_admin"] = True
                    st.session_state["user_id"] = ADMIN_USER
                    st.session_state["user_name"] = "系統管理者"
                    st.success("✅ 管理者登入成功！")
                    st.rerun()
                
                # 2. 一般使用者登入
                elif df_users is not None:
                    matched_user = df_users[
                        ((df_users["使用者編號"] == user_input) | (df_users["使用者姓名"] == user_input)) & 
                        (df_users["使用者密碼"] == password_input)
                    ]
                    
                    if not matched_user.empty:
                        user_info = matched_user.iloc[0]
                        st.session_state["authenticated"] = True
                        st.session_state["is_admin"] = False
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
                                
                        st.success(f"✅ 歡迎 {st.session_state['user_name']}，正在進入系統...")
                        st.rerun()
                    else:
                        st.error("❌ 登入失敗：使用者編號或密碼錯誤。")
                else:
                    st.error(f"❌ 找不到使用者名單檔案 (`{USER_FILE}`)，且非管理者帳號！")
    st.stop()

# ---------------------------------------------------------
# 🛠️ 管理者畫面
# ---------------------------------------------------------
if st.session_state["is_admin"]:
    st.title("🛠️ 管理者後台 - 登入記錄管理")
    
    col_admin_info, col_logout = st.columns([3, 1])
    with col_admin_info:
        st.write(f"👤 當前身分：**{st.session_state['user_name']} ({st.session_state['user_id']})**")
    with col_logout:
        if st.button("🚪 安全登出", type="secondary"):
            st.session_state["authenticated"] = False
            st.session_state["is_admin"] = False
            st.session_state["user_id"] = ""
            st.session_state["user_name"] = ""
            st.rerun()
            
    st.divider()

    if not supabase:
        st