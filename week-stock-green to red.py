%%writefile app.py
import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# =====================================================================
# 1. 密碼驗證功能 (Password Authentication)
# =====================================================================
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "592888":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 清除密碼輸入防外洩
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 尚未登入，顯示輸入框
        st.text_input(
            "請輸入密碼：", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # 密碼錯誤，重新顯示輸入框與錯誤訊息
        st.text_input(
            "請輸入密碼：", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 密碼錯誤，請重新輸入！")
        return False
    else:
        # 密碼正確
        return True

# 檢查密碼，若未通過則終止程式執行
if not check_password():
    st.stop()

# =====================================================================
# 2. 核心計算與篩選邏輯 (MACD Compute & Scan Functions)
# =====================================================================
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
            if len(df) < 35:
                continue

            df = compute_macd(df)
            df_periods = df.index.to_period("W")
            valid_mask = df_periods <= target_year_week

            if not valid_mask.any():
                continue

            target_idx = df[valid_mask].index[-1]
            idx_loc = df.index.get_loc(target_idx)

            if idx_loc < 1:
                continue

            recent = df.iloc[idx_loc-1 : idx_loc+1].copy()
            osc_val = recent['OSC'].values.flatten()
            green_to_red = (osc_val[-2] < 0) and (osc_val[-1] >= 0)

            if green_to_red:
                result.append(ticker)
        except Exception as e:
            pass
    return result

# =====================================================================
# 3. Streamlit 介面 (Streamlit UI)
# =====================================================================
st.title("📊 周K MACD 綠轉紅篩選器")

# 預設股票清單
default_tickers_list = ['0056.TW', '1301.TW', '1303.TW', '1308.TW', '1312A.TW', '1316.TW', '1319.TW', '1326.TW', '1336.TWO', '1416.TW', '1440.TW', '1504.TW', '1515.TW', '1519.TW', '1558.TW']
default_tickers_str = ", ".join(default_tickers_list)

tickers_input = st.text_area(
    "請輸入股票代號（支援空格、逗號、換行分隔）：",
    value=default_tickers_str,
    height=150
)

target_date = st.date_input("選擇基準日期：", value=datetime.today().date())

if st.button("🚀 開始篩選", type="primary"):
    with st.spinner("⏳ 正在下載資料並分析中，請稍候..."):
        # 整理輸入代號
        raw_input = tickers_input
        for char in [',', ';', '\n', '\t', '，', '；']:
            raw_input = raw_input.replace(char, ' ')

        cleaned_tickers = [t.strip() for t in raw_input.split(' ') if t.strip()]

        if not cleaned_tickers:
            st.error("❌ 請輸入至少一個股票代號！")
        else:
            # 自動為沒有字尾的台股代號加上 .TW
            formatted_tickers = [f"{t}.TW" if "." not in t else t for t in cleaned_tickers]
            target_date_str = target_date.strftime('%Y-%m-%d')

            try:
                results = scan_weekly_stocks_by_specific_date(formatted_tickers, target_date_str)

                st.success("🎉 篩選完成！")
                st.write(f"**📅 基準日期：** {target_date_str} (對應周K)")
                st.write(f"**🔍 掃描檔數：** {len(formatted_tickers)} 檔")

                st.markdown("---")
                if results:
                    st.subheader(f"✅ 符合條件的股票 ({len(results)} 檔) :")
                    st.code(", ".join(results))
                    st.info("📋 提示：您可以複製上方代號列並貼至您的軟體自選股中。")
                else:
                    st.warning("查無符合「周K MACD 綠柱轉紅柱」條件的股票。")
            except Exception as e:
                st.error(f"❌ 執行過程中發生錯誤: {str(e)}")
