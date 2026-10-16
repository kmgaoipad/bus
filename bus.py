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

# CSS 樣式設定
st.markdown("""
    <style>
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        h1 {
            font-size: 1.4rem !important;
            margin-bottom: 0.3rem !important;
        }
        iframe[title*="qrcode_scanner"] {
            max-height: 220px !important;
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
            margin-bottom: 0.4rem;
            display: inline-block;
            width: 100%;
        }
        [data-testid="stMetric"] {
            background-color: #f8f9fa;
            padding: 4px 8px !important;
            border-radius: 6px;
            border: 1px solid #e9ecef;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.1rem !important;
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
    st.title("🔒 KMSH 校車驗證系統 - 登入")
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
        st.error("❌ 未設定或無法連線至 Supabase 資料庫，無法讀取記錄。")
        st.stop()

    try:
        response = supabase.table("usage_logs").select("*").order("id", desc=True).execute()
        records = response.data
    except Exception as e:
        st.error(f"讀取記錄失敗：{e}")
        st.stop()

    if not records:
        st.info("目前尚無任何登入記錄。")
        st.stop()

    st.subheader(f"📋 登入紀錄列表（共 {len(records)} 筆）")

    if st.button("🗑️ 刪除全部記錄", type="primary"):
        try:
            all_ids = [r["id"] for r in records]
            supabase.table("usage_logs").delete().in_("id", all_ids).execute()
            st.success("已成功清空所有登入記錄！")
            st.rerun()
        except Exception as e:
            st.error(f"刪除失敗：{e}")

    st.write("")

    if "selected_delete_ids" not in st.session_state:
        st.session_state["selected_delete_ids"] = set()

    h1, h2, h3, h4, h5 = st.columns([0.6, 2.5, 2.5, 2.5, 1])
    h1.write("**選取**")
    h2.write("**使用者資訊**")
    h3.write("**登入時間**")
    h4.write("**選擇路線**")
    h5.write("**操作**")
    st.divider()

    for row in records:
        rec_id = row["id"]
        c1, c2, c3, c4, c5 = st.columns([0.6, 2.5, 2.5, 2.5, 1])
        
        is_chk = c1.checkbox("", key=f"chk_{rec_id}")
        if is_chk:
            st.session_state["selected_delete_ids"].add(rec_id)
        else:
            st.session_state["selected_delete_ids"].discard(rec_id)
            
        c2.write(row.get("user_email", "未知"))
        
        raw_time = row.get("login_time", "無記錄")
        formatted_time = raw_time.replace("T", " ")[:19] if raw_time else "無紀錄"
        c3.write(formatted_time)
        
        c4.write(row.get("route_selected", "未選擇"))
        
        if c5.button("❌ 刪除", key=f"del_btn_{rec_id}"):
            try:
                supabase.table("usage_logs").delete().eq("id", rec_id).execute()
                st.success(f"已刪除 ID: {rec_id} 的記錄")
                st.rerun()
            except Exception as e:
                st.error(f"刪除失敗：{e}")

    st.divider()

    if st.button("🗑️ 刪除勾選項目（部份刪除）", type="secondary"):
        selected_ids = list(st.session_state["selected_delete_ids"])
        if selected_ids:
            try:
                supabase.table("usage_logs").delete().in_("id", selected_ids).execute()
                st.session_state["selected_delete_ids"].clear()
                st.success(f"已成功刪除 {len(selected_ids)} 筆記錄！")
                st.rerun()
            except Exception as e:
                st.error(f"刪除失敗：{e}")
        else:
            st.warning("⚠️ 請先勾選要刪除的記錄。")

    st.stop()

# ---------------------------------------------------------
# 🚌 一般使用者：主系統畫面
# ---------------------------------------------------------

col_title, col_user_info = st.columns([2, 1])

with col_title:
    st.title("🚌 KMSH校車驗證系統")

with col_user_info:
    st.write(f"👤 **{st.session_state['user_name']}** ({st.session_state['user_id']})")
    if st.button("🚪 安全登出", type="secondary", use_container_width=True):
        if st.session_state["log_id"] and supabase:
            try:
                supabase.table("usage_logs").update({
                    "logout_time": datetime.now().isoformat()
                }).eq("id", st.session_state["log_id"]).execute()
            except Exception:
                pass
                
        st.session_state["authenticated"] = False
        st.session_state["is_admin"] = False
        st.session_state["user_id"] = ""
        st.session_state["user_name"] = ""
        st.session_state["log_id"] = None
        st.rerun()

st.divider()

# 1. 選擇時段類別
category_options = ["-- 請選擇時段/類別 --"] + list(CATEGORY_CONFIG.keys())
selected_category = st.selectbox("1. 請先選擇搭乘時段/類別：", category_options, index=0)

if selected_category == "-- 請選擇時段/類別 --":
    st.warning("👈 請先選擇時段/類別。")
else:
    config = CATEGORY_CONFIG[selected_category]
    df, route_list = load_category_data(config["file"], config["filter"])

    if df is None:
        st.error(f"❌ 找不到類別【{selected_category}】對應的資料庫檔案 (`{config['file']}`)，請確認檔案已上傳！")
    else:
        # 2. 選擇車輛路線
        route_options = ["-- 請點此選擇路線 --"] + list(route_list)
        selected_route = st.selectbox("2. 請選擇車輛路線：", route_options, index=0)

        if selected_route == "-- 請點此選擇路線 --":
            st.warning("👈 請選擇當前路線以開啟核對功能。")
        else:
            # 紀錄選擇路線至紀錄表
            if st.session_state["log_id"] and supabase:
                try:
                    supabase.table("usage_logs").update({
                        "route_selected": f"{selected_category} - {selected_route}"
                    }).eq("id", st.session_state["log_id"]).execute()
                except Exception:
                    pass

            st.markdown(f'<div class="route-info">📌 當前選擇：<b>【{selected_category}】➔ {selected_route}</b></div>', unsafe_allow_html=True)

            # 3. 驗證方式選擇
            input_mode = st.radio("3. 驗證方式：", ["📷 鏡頭掃描", "⌨️ 手動輸入"], horizontal=True)

            seat_no = ""

            if input_mode == "📷 鏡頭掃描":
                qr_code_val = qrcode_scanner(key=f"bus_qr_scanner_{selected_category}_{selected_route}")
                if qr_code_val:
                    seat_no = clean_seat_number(qr_code_val)
            else:
                raw_input = st.text_input("輸入座號：", placeholder="例如：20402").strip()
                seat_no = clean_seat_number(raw_input)

            # 4. 進行驗證與結果顯示
            if seat_no:
                student_records = df[df['班級座號'] == seat_no]
                st.divider()
                
                if not student_records.empty:
                    student_info = student_records.iloc[0]
                    actual_route = student_info['路線名稱']
                    student_name = student_info['學生姓名']
                    
                    station_name = student_info.get('放學站名') or student_info.get('上學站名') or "未設定"
                    station_no = student_info.get('放學站號') or student_info.get('上學站號') or "未設定"
                    
                    if selected_route == actual_route:
                        st.success(f"✅ **准予上車！【{student_name}】**")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("姓名", student_name)
                        col2.metric("座號", seat_no)
                        col3.metric("站名", f"{station_name} ({station_no})")
                    else:
                        st.error(f"🚫 **警告！【{student_name}】搭錯車！**")
                        st.warning(f"⚠️ 應搭乘：**【{actual_route}】** ｜ 站名：{station_name} ({station_no})")
                else:
                    st.error(f"❌ **查無此座號（{seat_no}）在【{selected_category}】的名單紀錄。**")