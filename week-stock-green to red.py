import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 設定網頁標題與排版
st.set_page_config(
    page_title="周K MACD 篩選器 (受保護)",
    page_icon="📊",
    layout="centered"
)

# --- 密碼保護功能 ---
def check_password():
    """如果密碼正確則回傳 True，否則顯示輸入框並回傳 False"""
    def password_entered():
        if st.session_state["password"] == "592888":  # 👈 在這裡設定您的專屬密碼！
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 刪除暫存密碼以策安全
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 第一次進入，顯示輸入密碼畫面
        st.title("🔒 系統安全驗證")
        st.text_input(
            "請輸入密碼以存取周K MACD 綠轉紅篩選器：",
            type="password",
            on_change=password_entered,
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # 密碼輸入錯誤，重新顯示輸入框與錯誤訊息
        st.title("🔒 系統安全驗證")
        st.text_input(
            "請輸入密碼以存取周K MACD 綠轉紅篩選器：",
            type="password",
            on_change=password_entered,
            key="password"
        )
        st.error("❌ 密碼錯誤，請重新輸入！")
        return False
    else:
        # 密碼正確
        return True

# 只有密碼驗證通過，才顯示後續的 App 內容
if check_password():

    # --- 核心計算邏輯 ---
    def compute_macd(df, fast=12, slow=26, signal=9):
        df['EMA_fast'] = df['Close'].ewm(span=fast, adjust=False).mean()
        df['EMA_slow'] = df['Close'].ewm(span=slow, adjust=False).mean()
        df['DIF'] = df['EMA_fast'] - df['EMA_slow']
        df['MACD'] = df['DIF'].ewm(span=signal, adjust=False).mean()
        df['OSC'] = df['DIF'] - df['MACD']
        return df

    def scan_weekly_stocks_by_specific_date(ticker_list, target_date):
        result = []
        target_dt = pd.Timestamp(target_date)
        target_year_week = target_dt.to_period('W')
        start_date = (target_dt - pd.Timedelta(days=365*2)).strftime('%Y-%m-%d')
        end_date = (target_dt + pd.Timedelta(days=14)).strftime('%Y-%m-%d')

        for ticker in ticker_list:
            try:
                df = yf.download(ticker, start=start_date, end=end_date, interval="1wk", auto_adjust=False, progress=False)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.dropna(subset=["Close"])
                if len(df) < 35: continue
                df = compute_macd(df)
                df_periods = df.index.to_period('W')
                valid_mask = df_periods <= target_year_week
                if not valid_mask.any(): continue
                target_idx = df[valid_mask].index[-1]
                idx_loc = df.index.get_loc(target_idx)
                if idx_loc < 1: continue
                recent = df.iloc[idx_loc-1 : idx_loc+1].copy()
                osc_val = recent['OSC'].values.flatten()
                # 綠柱轉紅柱條件：前一周為綠柱 (<0)，當周轉為紅柱 (>=0)
                green_to_red = (osc_val[-2] < 0) and (osc_val[-1] >= 0)
                if green_to_red:
                    result.append(ticker)
            except:
                pass
        return result

    # --- App 主介面 ---
    st.title("📊 周K MACD 綠轉紅篩選器")
    st.write("歡迎回來！請輸入代號、設定日期，快速找出綠柱轉紅柱的潛力個股！")

    default_tickers = "2330, 1519, 2603, 2605"
    tickers_input = st.text_area(
        "輸入股票代號 (支援空格、逗號、換行分隔):",
        value=default_tickers,
        height=120
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        target_date = st.date_input("選擇基準日期:", datetime.now())
    with col2:
        st.write("")
        st.write("")
        run_button = st.button("🎯 開始篩選", use_container_width=True)

    if run_button:
        with st.spinner("⏳ 正在分析歷史數據，請稍候..."):
            raw_input = tickers_input
            for char in [',', ';', '\n', '\t', '，', '；']:
                raw_input = raw_input.replace(char, ' ')
            cleaned_tickers = [t.strip() for t in raw_input.split(' ') if t.strip()]

            if not cleaned_tickers:
                st.warning("⚠️ 請輸入至少一個股票代號！")
            else:
                formatted_tickers = [f"{t}.TW" if "." not in t else t for t in cleaned_tickers]
                results = scan_weekly_stocks_by_specific_date(formatted_tickers, target_date.strftime('%Y-%m-%d'))

                st.subheader("🎉 篩選結果")
                st.metric(label="掃描個股數量", value=f"{len(formatted_tickers)} 檔")

                if results:
                    st.success(f"✅ 符合條件的股票 ({len(results)} 檔):")
                    results_str = " , ".join(results)
                    st.code(results_str, language="text")
                    st.info("💡 提示：點擊上方結果框右上角的『📋』圖示即可快速複製！")
                else:
                    st.error("❌ 查無符合條件的周K綠轉紅個股。")
