import os
import pandas as pd
import streamlit as st
from streamlit_qrcode_scanner import qrcode_scanner

# 設定網頁標題與頁面圖示
st.set_page_config(page_title="KMSH校車驗證系統", page_icon="🚌", layout="centered")

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

# 定義時段類別對應的 Excel 檔案名稱
CATEGORY_FILES = {
    "上學": "上學各路線名單.xlsx",
    "大放學 (週一二四五)": "大放學12各路線名單.xlsx",
    "週一小放學 (第1梯)": "週1小放學1梯各路線名單.xlsx",
    "週一小放學 (第2梯)": "週1小放學2梯各路線名單.xlsx",
    "週二小放學 (第1梯)": "週2小放學1梯各路線名單.xlsx",
    "週二小放學 (第2梯)": "週2小放學2梯各路線名單.xlsx",
    "週三小放學": "週3小放學各路線名單.xlsx",
    "週四小放學 (第1梯)": "週4小放學1梯各路線名單.xlsx",
    "週四小放學 (第2梯)": "週4小放學2梯各路線名單.xlsx",
    "週五小放學": "週5小放學各路線名單.xlsx",
    "高國三週六課程": "週六課程各路線名單.xlsx"
}

# 讀取指定類別 Excel 檔案並快取
@st.cache_data
def load_category_data(file_path):
    if not os.path.exists(file_path):
        return None, None
        
    xls = pd.ExcelFile(file_path)
    all_dfs = []
    
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df['路線名稱'] = sheet_name.strip()
        all_dfs.append(df)
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    combined_df['班級座號'] = combined_df['班級座號'].astype(str).str.strip()
    return combined_df, xls.sheet_names

st.title("🚌 KMSH校車驗證系統")

# 1. 第一階層：選擇時段類別
category_options = ["-- 請選擇時段/類別 --"] + list(CATEGORY_FILES.keys())
selected_category = st.selectbox("1. 請先選擇搭乘時段/類別：", category_options, index=0)

if selected_category == "-- 請選擇時段/類別 --":
    st.warning("👈 請先選擇時段/類別（例如：上學、大放學、週一小放學...）。")
else:
    file_path = CATEGORY_FILES[selected_category]
    df, route_list = load_category_data(file_path)

    if df is None:
        st.error(f"❌ 找不到類別【{selected_category}】對應的資料庫檔案 (`{file_path}`)，請確認該 Excel 檔已上傳至 GitHub！")
    else:
        # 2. 第二階層：選擇該時段對應的路線
        route_options = ["-- 請點此選擇路線 --"] + list(route_list)
        selected_route = st.selectbox("2. 請選擇車輛路線：", route_options, index=0)

        if selected_route == "-- 請點此選擇路線 --":
            st.warning("👈 請選擇當前路線以開啟核對功能。")
        else:
            # 顯示當前類別與路線提示
            st.markdown(f'<div class="route-info">📌 當前選擇：<b>【{selected_category}】➔ {selected_route}</b></div>', unsafe_allow_html=True)

            # 3. 選擇驗證方式
            input_mode = st.radio("3. 驗證方式：", ["📷 鏡頭掃描", "⌨️ 手動輸入"], horizontal=True)

            seat_no = ""

            if input_mode == "📷 鏡頭掃描":
                qr_code_val = qrcode_scanner(key=f"bus_qr_scanner_{selected_category}_{selected_route}")
                if qr_code_val:
                    seat_no = str(qr_code_val).strip()
            else:
                seat_no = st.text_input("輸入座號：", placeholder="例如：10337").strip()

            # 4. 進行驗證與結果顯示
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