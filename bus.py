import streamlit as st
import pandas as pd
from streamlit_qrcode_scanner import qrcode_scanner

# 設定網頁標題與頁面圖示
st.set_page_config(page_title="校車掃碼驗證系統", page_icon="🚌", layout="centered")

# 大幅壓縮邊距與限制鏡頭高度的 CSS
st.markdown("""
    <style>
        /* 壓縮頂部與整體邊距 */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }
        h1 {
            font-size: 1.3rem !important;
            margin-bottom: 0.2rem !important;
        }
        .stCaption {
            margin-bottom: 0.4rem !important;
        }
        hr {
            margin-top: 0.3rem !important;
            margin-bottom: 0.3rem !important;
        }
        /* 限制掃描相機高度，避免把結果推到底部 */
        iframe[title*="qrcode_scanner"] {
            max-height: 220px !important;
        }
        /* 緊湊型 Metric 卡片 */
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
        /* 警告與成功訊息框壓縮 */
        .stAlert {
            padding: 8px 12px !important;
            margin-bottom: 0.4rem !important;
        }
    </style>
""", unsafe_allow_html=True)

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

st.title("🚌 校車放學路線核對")

try:
    df, route_list = load_data()

    # 1. 路線下拉選單（預設空白）
    options_with_placeholder = ["-- 請點此選擇路線 --"] + list(route_list)
    selected_route = st.selectbox("1. 請選擇當前路線：", options_with_placeholder, index=0)

    # 檢查是否已選擇路線
    if selected_route == "-- 請點此選擇路線 --":
        st.warning("👈 請先選擇當前路線以開啟功能。")
    else:
        st.success(f"📌 當前路線：**{selected_route}**")

        # 建立專用容器：讓【驗證結果】強制顯示在【鏡頭/輸入區】的上方！
        result_container = st.container()
        input_container = st.container()

        seat_no = ""

        with input_container:
            # 2. 輸入模式選擇
            input_mode = st.radio("2. 驗證方式：", ["📷 鏡頭掃描", "⌨️ 手動輸入"], horizontal=True)

            if input_mode == "📷 鏡頭掃描":
                qr_code_val = qrcode_scanner(key="bus_qr_scanner")
                if qr_code_val:
                    seat_no = str(qr_code_val).strip()
            else:
                seat_no = st.text_input("輸入班級座號：", placeholder="例如：10337").strip()

        # 3. 進行驗證，並將結果輸出至頂部的 result_container
        if seat_no:
            student_records = df[df['班級座號'] == seat_no]
            
            with result_container:
                st.divider()
                if not student_records.empty:
                    student_info = student_records.iloc[0]
                    actual_route = student_info['路線名稱']
                    student_name = student_info['學生姓名']
                    station_name = student_info['放學站名']
                    station_no = student_info['放學站號']
                    
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
                    st.error(f"❌ **查無此座號（{seat_no}）紀錄。**")
                st.divider()

except FileNotFoundError:
    st.error("❌ 找不到 `大放學12各路線名單.xlsx` 檔案！")