import os
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from supabase import create_client, Client

# 設定網頁標題與頁面圖示
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

# 安全整理班級座號字串（徹底防禦 DeltaGenerator 與特殊物件）
def clean_seat_number(val):
    if val is None:
        return ""
    # 只處理字串、整數、浮點數，其餘 Streamlit 元件物件一律傳回空字串
    if not isinstance(val, (str, int, float)):
        return ""
    
    val_str = str(val).strip()
    if not val_str or "DeltaGenerator" in val_str or "object at" in val_str:
        return ""
        
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
    return val_str

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

# 原生 JS 實時自動動態掃描元件 (無需按 Take Photo)
def real_time_auto_qr_scanner(key="live_qr_scanner"):
    scanner_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js"></script>
        <style>
            #container {{
                position: relative;
                width: 100%;
                max-width: 320px;
                margin: 0 auto;
                text-align: center;
            }}
            #video {{
                width: 100%;
                height: 220px;
                object-fit: cover;
                border-radius: 8px;
                border: 2px solid #007bff;
            }}
            #canvas {{
                display: none;
            }}
            .scan-line {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 2px;
                background: #00ff00;
                box-shadow: 0 0 8px #00ff00;
                animation: scan 2s infinite linear;
            }}
            @keyframes scan {{
                0% {{ top: 0%; }}
                50% {{ top: 95%; }}
                100% {{ top: 0%; }}
            }}
        </style>
    </head>
    <body style="margin:0; padding:0; background:transparent;">
        <div id="container">
            <video id="video" playsinline></video>
            <div class="scan-line"></div>
            <canvas id="canvas"></canvas>
        </div>
        <script>
            const video = document.getElementById("video");
            const canvas = document.getElementById("canvas");
            const ctx = canvas.getContext("2d");
            let isScanning = true;

            // 存取手機/電腦原生的後置攝影鏡頭
            navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: "environment" }} }})
            .then(function(stream) {{
                video.srcObject = stream;
                video.setAttribute("playsinline", true);
                video.play();
                requestAnimationFrame(tick);
            }}).catch(function(err) {{
                console.error("Camera Access Error: ", err);
            }});

            function tick() {{
                if (video.readyState === video.HAVE_ENOUGH_DATA && isScanning) {{
                    canvas.height = video.videoHeight;
                    canvas.width = video.videoWidth;
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    var imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    
                    // jsQR 自動辨識
                    var code = jsQR(imageData.data, imageData.width, imageData.height, {{
                        inversionAttempts: "dontInvert",
                    }});

                    if (code && code.data && code.data.trim() !== "") {{
                        let seatNo = code.data.trim();
                        // 抓取到座號後，即刻將數值傳回 Streamlit，無須點擊任何按鈕
                        window.parent.postMessage({{
                            type: "streamlit:setComponentValue",
                            value: seatNo
                        }}, "*");
                    }}
                }}
                if (isScanning) {{
                    requestAnimationFrame(tick);
                }}
            }}
        </script>
    </body>
    </html>
    """
    return components.html(scanner_html, height=230)

# CSS 樣式設定
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        h1 {
            font-size: 1.4rem !important;
            margin-bottom: 0.3rem !important;
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
                            
                    st.success(f"✅ 歡迎 {st.session_state['user_name']}，正在進入系統...")
                    st.rerun()
                else:
                    st.error("❌ 登入失敗：使用者編號或密碼錯誤，請重新確認。")
    st.stop()

# ---------------------------------------------------------
# 🚌 主系統畫面
# ---------------------------------------------------------

with st.sidebar:
    st.write(f"👤 當前使用者：**{st.session_state['user_name']} ({st.session_state['user_id']})**")
    if st.button("🚪 安全登出"):
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

CATEGORY_CONFIG = {
    "上學": {"file": "上學各路線名單.xlsx", "filter": None},
    "大放學 (第1梯)": {"file": "大放學12各路線名單.xlsx", "filter": "大放1"},
    "大放學 (第2梯)": {"file": "大放學12各路線名單.xlsx", "filter": "大放2"},
    "週一小放學 (第1梯)": {"file": "週1小放學1梯各路線名單.xlsx", "filter": None},
    "週一小放學 (第2梯)": {"file": "週1小放學2梯各路線名單.xlsx", "filter": None},
    "週二小放學 (第1梯)": {"file": "週2小放學1梯各路線名單.xlsx", "filter": None},
    "週二小放學 (第2梯)": {"file": "週2小放學2梯各路線名單.xlsx", "filter": None},
    "週三小放學": {"file": "週3小放學各路線名單.xlsx", "filter": None},
    "週四小放學 (第1梯)": {"file": "週4小放學1梯各路線名單.xlsx", "filter": None},
    "週四小放學 (第2梯)": {"file": "週4小放學2梯各路線名單.xlsx", "filter": None},
    "週五小放學": {"file": "週5小放學各路線名單.xlsx", "filter": None},
    "高國三週六課程": {"file": "週六課程各路線名單.xlsx", "filter": None}
}

@