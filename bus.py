import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from streamlit_qrcode_scanner import qrcode_scanner

# 設定網頁標題與頁面圖示
st.set_page_config(page_title="校車掃碼驗證系統", page_icon="🚌", layout="centered")

# 讀取 Excel 檔案並快取
@st.cache_data
def load_data():
    file_path = '大放學12各路線名單.xlsx'
    xls = pd.ExcelFile(file_path)
    all_dfs = []
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df['路線名稱'] = sheet_name.strip()
        all_dfs.append(df)
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df['班級座號'] = combined_df['班級座號'].astype(str).str.strip()
    return combined_df, xls.sheet_names

# 透過原生 JS SpeechSynthesis 播放語音
def speak_js(text_to_speak):
    js_code = f"""
    <script>
        function speak() {{
            if ('speechSynthesis' in window) {{
                window.speechSynthesis.cancel(); // 停止先前的聲音
                var msg = new SpeechSynthesisUtterance('{text_to_speak}');
                msg.lang = 'zh-TW';
                msg.rate = 1.1; // 語速稍快
                msg.volume = 1.0;
                window.speechSynthesis.speak(msg);
            }}
        }}
        // 延遲 100ms 確保 DOM 載入後播放
        setTimeout(speak, 100);
    </script>
    """
    components.html(js_code, height=0, width=0)

st.title("🚌 校車掃碼 / 放學路線核對系統")
st.caption("請先選擇車輛路線，開啟鏡頭對準學生證/車票上的 QR Code 即可自動核對！")

# 語音權限解鎖區塊
if "audio_unlocked" not in st.session_state:
    st.session_state["audio_unlocked"] = False

if not st.session_state["audio_unlocked"]:
    st.info("💡 **提示：首次使用請先點擊下方按鈕以啟用語音播報功能。**")
    if st.button("🔊 點此啟用/測試語音功能"):
        st.session_state["audio_unlocked"] = True
        speak_js("語音功能已啟用")
        st.rerun()

try:
    df, route_list = load_data()

    # 1. 路線下拉選單（預設空白）
    options_with_placeholder = ["-- 請點此選擇路線 --"] + list(route_list)
    selected_route = st.selectbox("1. 請先選擇當前路線：", options_with_placeholder, index=0)

    # 檢查是否已選擇路線
    if selected_route == "-- 請點此選擇路線 --":
        st.warning("👈 請先在上方下拉選單選擇「當前路線」，選擇後方可開啟掃描或輸入功能！")
    else:
        st.success(f"📌 當前選擇路線：**{selected_route}**")
        st.divider()

        # 2. 輸入模式選擇
        input_mode = st.radio("2. 選擇驗證方式：", ["📷 鏡頭掃描 QR Code", "⌨️ 手動輸入座號"], horizontal=True)

        seat_no = ""

        if input_mode == "📷 鏡頭掃描 QR Code":
            st.write("▼ 請將 QR Code 對準下方鏡頭視窗：")
            qr_code_val = qrcode_scanner(key="bus_qr_scanner")
            
            if qr_code_val:
                seat_no = str(qr_code_val).strip()
                st.info(f"📲 讀取至座號：**{seat_no}**")
                
        else:
            seat_no = st.text_input("請輸入班級座號（例如：10337 或 30110）：").strip()

        # 3. 進行驗證與發聲
        if seat_no:
            student_records = df[df['班級座號'] == seat_no]
            
            st.divider()
            
            if not student_records.empty:
                student_info = student_records.iloc[0]
                actual_route = student_info['路線名稱']
                student_name = student_info['學生姓名']
                station_name = student_info['放學站名']
                station_no = student_info['放學站號']
                
                if selected_route == actual_route:
                    # 正確搭乘語音
                    speak_js("正確搭乘")
                    
                    st.success(f"✅ **准予上車！【{student_name}】搭乘此路線（{selected_route}）。**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("學生姓名", student_name)
                        st.metric("班級座號", seat_no)
                    with col2:
                        st.metric("放學站名", station_name)
                        st.metric("放學站號", station_no)
                else:
                    # 錯誤搭乘語音
                    speak_js("錯誤搭乘")
                    
                    st.error(f"🚫 **警告！【{student_name}】搭錯車了！**")
                    st.warning(f"⚠️ 該生**非**搭乘【{selected_route}】\n\n💡 **實際應搭乘路線：**【{actual_route}】\n**放學站名：** {station_name} (站號: {station_no})")
            else:
                speak_js("錯誤搭乘")
                st.error(f"❌ **查無此班級座號（{seat_no}）的搭乘紀錄，請確認 QR Code 內容是否正確。**")

except FileNotFoundError:
    st.error("❌ 找不到 `大放學12各路線名單.xlsx` 檔案，請確認 Excel 檔與 `bus.py` 放在同一資料夾！")