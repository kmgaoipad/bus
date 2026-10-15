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

# 安全整理班級座號字串
def clean_seat_number(val):
    if val is None:
        return ""
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

# 專為 iOS Safari 與 Android 最佳化的極速連刷掃描組件 (解決黑屏問題)
def ios_safari_compatible_qr_scanner(key_name="safari_scanner"):
    scanner_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js"></script>
        <style>
            #scanner-wrapper {{
                width: 100%;
                max-width: 320px;
                margin: 0 auto;
                text-align: center;
                position: relative;
            }}
            #video-canvas-container {{
                width: 100%;
                height: 220px;
                border-radius: 10px;
                border: 2px solid #28a745;
                background-color: #000;
                overflow: hidden;
                position: relative;
            }}
            #webcam-video {{
                width: 100% !important;
                height: 100% !important;
                object-fit: cover !important;
                display: block;
            }}
            .scan-line {{
                position: absolute;
                top: 0; left: 0;
                width: 100%; height: 2px;
                background: #00ff00;
                box-shadow: 0 0 8px #00ff00;
                animation: scan 1.8s infinite linear;
            }}
            @keyframes scan {{
                0% {{ top: 5%; }}
                50% {{ top: 90%; }}
                100% {{ top: 5%; }}
            }}
            #status-msg {{
                font-size: 12px;
                color: #444;
                margin-top: 6px;
                font-weight: bold;
            }}
            .btn-start {{
                background-color: #28a745;
                color: white;
                border: none;
                padding: 10px 18px;
                font-size: 15px;
                font-weight: bold;
                border-radius: 6px;
                cursor: pointer;
                margin-bottom: 8px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            }}
        </style>
    </head>
    <body style="margin:0; padding:0; background:transparent;">
        <div id="scanner-wrapper">
            <button id="start-btn" class="btn-start" onclick="startSafariCamera()">📷 點此開啟鏡頭自動連刷</button>
            <div id="video-canvas-container" style="display:none;">
                <video id="webcam-video" autoplay playsinline muted></video>
                <div class="scan-line"></div>
            </div>
            <canvas id="hidden-canvas" style="display:none;"></canvas>
            <div id="status-msg"></div>
        </div>

        <script>
            const video = document.getElementById("webcam-video");
            const canvas = document.getElementById("hidden-canvas");
            const ctx = canvas.getContext("2d");
            const statusMsg = document.getElementById("status-msg");
            let lastScannedCode = "";
            let isScanning = false;

            function startSafariCamera() {{
                document.getElementById("start-btn").style.display = "none";
                document.getElementById("video-canvas-container").style.display = "block";
                statusMsg.innerText = "🔍 請將學生證 QR Code 對準鏡頭...";

                // iOS Safari 多層相機連線降級相容機制
                const constraintsList = [
                    {{ video: {{ facingMode: {{ exact: "environment" }} }} }},
                    {{ video: {{ facingMode: "environment" }} }},
                    {{ video: true }}
                ];

                tryStreamConstraints(constraintsList, 0);
            }}

            function tryStreamConstraints(list, index) {{
                if (index >= list.length) {{
                    statusMsg.innerText = "❌ 無法取得鏡頭影像，請確認 Safari / Chrome 已允許權限。";
                    return;
                }}

                navigator.mediaDevices.getUserMedia(list[index])
                .then(function(stream) {{
                    video.srcObject = stream;
                    video.setAttribute("playsinline", "true"); // 解決 iOS 全螢幕視訊問題
                    video.play();
                    isScanning = true;
                    requestAnimationFrame(scanProcess);
                }})
                .catch(function(err) {{
                    console.log("Constraint " + index + " failed, trying next...");
                    tryStreamConstraints(list, index + 1);
                }});
            }}

            function scanProcess() {{
                if (video.readyState === video.HAVE_ENOUGH_DATA && isScanning) {{
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    
                    if (typeof jsQR !== 'undefined') {{
                        const qrCode = jsQR(imgData.data, imgData.width, imgData.height, {{
                            inversionAttempts: "dontInvert"
                        }});
                        
                        if (qrCode && qrCode.data && qrCode.data.trim() !== "") {{
                            let cleanCode = qrCode.data.trim();
                            if (cleanCode !== lastScannedCode) {{
                                lastScannedCode = cleanCode;
                                statusMsg.innerText = "⚡ 讀取座號：" + cleanCode;
                                
                                window.parent.postMessage({{
                                    type: "streamlit:setComponentValue",
                                    value: cleanCode
                                }}, "*");
                            }}
                        }}
                    }}
                }}
                if (isScanning) {{
                    requestAnimationFrame(scanProcess);
                }}
            }}
        </script>
    </body>
    </html>
    """
    return components.html(scanner_html, height=290)

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
if "detected_seat" not in st.session_state:
    st.session_state["detected_seat"] = ""

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
        st.session_state["detected_seat"] = ""
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

st.title("🚌 KMSH校車驗證系統")

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
            if st.session_state["log_id"] and supabase:
                try:
                    supabase.table("usage_logs").update({
                        "route_selected": f"{selected_category} - {selected_route}"
                    }).eq("id", st.session_state["log_id"]).execute()
                except Exception:
                    pass

            st.markdown(f'<div class="route-info">📌 當前選擇：<b>【{selected_category}】➔ {selected_route}</b></div>', unsafe_allow_html=True)

            # 3. 驗證方式選擇
            input_mode = st.radio("3. 驗證方式：", ["📷 鏡頭對焦自動連刷", "⌨️ 手動輸入"], horizontal=True)

            if input_mode == "📷 鏡頭對焦自動連刷":
                scanned_val = ios_safari_compatible_qr_scanner(key_name=f"safari_scan_{selected_category}_{selected_route}")
                if scanned_val:
                    cleaned_str = clean_seat_number(scanned_val)
                    if cleaned_str and cleaned_str != st.session_state["detected_seat"]:
                        st.session_state["detected_seat"] = cleaned_str
            else:
                raw_input = st.text_input("輸入座號：", placeholder="例如：20402").strip()
                if raw_input:
                    st.session_state["detected_seat"] = clean_seat_number(raw_input)

            seat_no = st.session_state.get("detected_seat", "")

            # 4. 進行驗證與結果顯示
            if seat_no:
                st.divider()
                student_records = df[df['班級座號'] == seat_no]
                
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