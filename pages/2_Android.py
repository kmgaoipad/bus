import os
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
from supabase import create_client, Client

st.set_page_config(page_title="Android校車驗證", page_icon="🤖", layout="centered")

# 權限保護：未登入者退回首頁
if not st.session_state.get("authenticated", False):
    st.warning("⚠️ 請先完成登入！")
    if st.button("返回登入頁面"):
        st.switch_page("bus.py")
    st.stop()

# 側邊欄導覽
with st.sidebar:
    st.write(f"👤 使用者：**{st.session_state.get('user_name', '')}**")
    if st.button("🏠 回主選單"):
        st.switch_page("bus.py")

USER_FILE = "校車驗證系統使用者名單.xlsx"
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

# Android 專用相機元件 (修正 components.html 參數)
def android_camera_scanner():
    scanner_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/streamlit-component-lib@1.4.0/dist/streamlit.min.js"></script>
        <style>
            #reader-wrapper {{ width: 100%; max-width: 320px; margin: 0 auto; text-align: center; }}
            #reader {{ width: 100%; height: 230px !important; border-radius: 10px; border: 2px solid #28a745; background-color: #000; overflow: hidden; }}
            #reader video {{ object-fit: cover !important; width: 100% !important; height: 100% !important; }}
            .btn-start {{ background-color: #28a745; color: white; border: none; padding: 12px 22px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; box-shadow: 0 3px 6px rgba(0,0,0,0.2); }}
            #status-msg {{ font-size: 13px; color: #333; margin-top: 6px; font-weight: bold; }}
        </style>
    </head>
    <body style="margin:0; padding:0; background:transparent;">
        <div id="reader-wrapper">
            <button id="start-btn" class="btn-start" onclick="activateAndroidCam()">🤖 開啟 Android 相機掃描</button>
            <div id="reader" style="display:none;"></div>
            <div id="status-msg"></div>
        </div>

        <script>
            let html5QrCode = null;
            let lastScannedCode = "";

            function activateAndroidCam() {{
                document.getElementById("start-btn").style.display = "none";
                document.getElementById("reader").style.display = "block";
                document.getElementById("status-msg").innerText = "🎯 請將 QR Code 對準鏡頭...";

                html5QrCode = new Html5Qrcode("reader");
                const config = {{ fps: 15, qrbox: {{ width: 180, height: 180 }} }};

                html5QrCode.start(
                    {{ facingMode: "environment" }},
                    config,
                    (decodedText) => {{
                        if (decodedText && decodedText.trim !== undefined && decodedText.trim() !== "") {{
                            let cleanText = decodedText.trim();
                            if (cleanText !== lastScannedCode) {{
                                lastScannedCode = cleanText;
                                document.getElementById("status-msg").innerText = "⚡ 辨識成功：" + cleanText;
                                sendToParent(cleanText);
                            }}
                        }}
                    }}
                ).catch(err => {{
                    html5QrCode.start(true, config, (decodedText) => {{
                        if (decodedText && decodedText.trim() !== "") sendToParent(decodedText.trim());
                    }}).catch(err2 => {{
                        document.getElementById("status-msg").innerText = "❌ 相機開啟失敗，請確認已允許 Chrome 相機權限。";
                    }});
                }});
            }}

            function sendToParent(val) {{
                if (window.Streamlit) {{
                    window.Streamlit.setComponentValue(val);
                }} else {{
                    window.parent.postMessage({{
                        type: "streamlit:setComponentValue",
                        value: val
                    }}, "*");
                }}
            }}
        </script>
    </body>
    </html>
    """
    return components.html(scanner_html, height=290)

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

st.title("🤖 Android 專用校車驗證系統")

category_options = ["-- 請選擇時段/類別 --"] + list(CATEGORY_CONFIG.keys())
selected_category = st.selectbox("1. 請先選擇搭乘時段/類別：", category_options, index=0)

if selected_category == "-- 請選擇時段/類別 --":
    st.warning("👈 請先選擇時段/類別。")
else:
    config = CATEGORY_CONFIG[selected_category]
    df, route_list = load_category_data(config["file"], config["filter"])

    if df is None:
        st.error(f"❌ 找不到類別【{selected_category}】對應的資料庫檔案 (`{config['file']}`)！")
    else:
        route_options = ["-- 請點此選擇路線 --"] + list(route_list)
        selected_route = st.selectbox("2. 請選擇車輛路線：", route_options, index=0)

        if selected_route == "-- 請點此選擇路線 --":
            st.warning("👈 請選擇當前路線以開啟核對功能。")
        else:
            if st.session_state.get("log_id") and supabase:
                try:
                    supabase.table("usage_logs").update({
                        "route_selected": f"[Android] {selected_category} - {selected_route}"
                    }).eq("id", st.session_state["log_id"]).execute()
                except Exception:
                    pass

            st.success(f"📌 當前選擇：**【{selected_category}】➔ {selected_route}**")

            input_mode = st.radio("3. 驗證方式：", ["📷 Android 相機對焦連刷", "⌨️ 手動輸入"], horizontal=True)

            seat_no = ""
            if input_mode == "📷 Android 相機對焦連刷":
                scanned_val = android_camera_scanner()
                if scanned_val:
                    seat_no = clean_seat_number(scanned_val)
            else:
                raw_input = st.text_input("輸入座號：", placeholder="例如：20402").strip()
                if raw_input:
                    seat_no = clean_seat_number(raw_input)

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