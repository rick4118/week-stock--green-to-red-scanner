import yfinance as yf
import pandas as pd
from datetime import datetime
import ipywidgets as widgets
from IPython.display import display, clear_output

# =====================================================================
# 1. 核心計算與篩選邏輯 (MACD Compute & Scan Functions)
# =====================================================================

def compute_macd(df, fast=12, slow=26, signal=9):
    # 計算周 EMA、DIF、MACD 與柱狀體 OSC
    df['EMA_fast'] = df['Close'].ewm(span=fast, adjust=False).mean()
    df['EMA_slow'] = df['Close'].ewm(span=slow, adjust=False).mean()
    df['DIF'] = df['EMA_fast'] - df['EMA_slow']
    df['MACD'] = df['DIF'].ewm(span=signal, adjust=False).mean()
    df['OSC'] = df['DIF'] - df['MACD']
    return df

def scan_weekly_stocks_by_specific_date(ticker_list, target_date):
    """
    特定日期篩選函數 (周K等級 - 篩選 MACD 綠柱轉紅柱)
    """
    result = []
    target_dt = pd.Timestamp(target_date)
    target_year_week = target_dt.to_period('W')  # 取得目標年周 (例如 2026-W31)

    # 往前抓 2 年確保歷史資料充足；往後多抓 14 天包覆當周
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

            # 將索引轉換為 Period('W') 進行周別比對
            df_periods = df.index.to_period('W')
            valid_mask = df_periods <= target_year_week

            if not valid_mask.any():
                continue

            target_idx = df[valid_mask].index[-1]
            idx_loc = df.index.get_loc(target_idx)

            if idx_loc < 1:
                continue

            # 取出目標周及其前一周
            recent = df.iloc[idx_loc-1 : idx_loc+1].copy()
            osc_val = recent['OSC'].values.flatten()

            # 綠柱轉紅柱條件：前一周為綠柱 (<0)，當周轉為紅柱 (>=0)
            green_to_red = (osc_val[-2] < 0) and (osc_val[-1] >= 0)

            if green_to_red:
                result.append(ticker)

        except Exception as e:
            pass
    return result

# =====================================================================
# 2. 互動式 IPywidgets 介面 (Interactive UI Area)
# =====================================================================

# 預設一些初始股票清單
if 'tickers' not in globals():
    tickers = ['0056.TW', '1301.TW', '1303.TW', '1308.TW', '1312A.TW', '1316.TW', '1319.TW', '1326.TW', '1336.TWO', '1416.TW', '1440.TW', '1504.TW', '1515.TW', '1519.TW', '1558.TW']
if 'query_date' not in globals():
    query_date = "2026-08-01"

# 建立 UI 說明文字
instruction_label = widgets.HTML(
    value="""
    <div style='background-color: #fcf8e3; padding: 12px; border-radius: 6px; border-left: 5px solid #f0ad4e; margin-bottom: 10px;'>
        <h3 style='margin-top:0; color: #b24a00;'><b>📊 一體化周K MACD 綠轉紅篩選器</b></h3>
        <p style='margin-bottom:0;'>請在下方輸入代號（支援空格、逗號、換行分隔）與基準日期。程式將自動篩選出當周 <b>MACD 綠柱轉紅柱</b> 的股票！</p>
    </div>
    """
)

# 預設代號文字
default_tickers = ", ".join(tickers[:15])

tickers_input = widgets.Textarea(
    value=default_tickers,
    placeholder='例如: 2330.TW, 1519.TW, 2603.TW, 2605.TW',
    description='股票代號:',
    disabled=False,
    layout=widgets.Layout(width='95%', height='120px')
)

date_picker = widgets.DatePicker(
    description='基準日期:',
    value=pd.to_datetime(query_date).date(),
    disabled=False
)

run_button = widgets.Button(
    description='開始篩選',
    disabled=False,
    button_style='warning',
    tooltip='點擊開始執行篩選邏輯',
    icon='search'
)

output_area = widgets.Output()

# 按鈕點擊處理
def on_button_clicked(b):
    with output_area:
        clear_output()
        print("⏳ 正在下載最新資料並進行周K MACD「綠轉紅」篩選，請稍候...")

        # 整理輸入代號
        raw_input = tickers_input.value
        for char in [',', ';', '\n', '\t', '，', '；']:
            raw_input = raw_input.replace(char, ' ')

        cleaned_tickers = [t.strip() for t in raw_input.split(' ') if t.strip()]

        if not cleaned_tickers:
            print("❌ 請輸入至少一個股票代號！")
            return

        # 自動為沒有字尾的台股代號加上 .TW
        formatted_tickers = [f"{t}.TW" if "." not in t else t for t in cleaned_tickers]
        target_date_str = date_picker.value.strftime('%Y-%m-%d')

        try:
            # 執行邏輯運算
            results = scan_weekly_stocks_by_specific_date(formatted_tickers, target_date_str)

            clear_output()
            print(f"=== 篩選完成 ===")
            print(f"📅 基準日期：{target_date_str} (對應周K)")
            print(f"🔍 掃描檔數：{len(formatted_tickers)} 檔")
            print(f"--------------------------------------")

            if results:
                print(f"✅ 符合「周K MACD 綠柱轉紅柱」的股票 ({len(results)} 檔) :\n")
                print(", ".join(results))
                print("\n--------------------------------------")
                print("📋 提示：您可以直接複製上方代號列，貼至您的券商或軟體自選股中。")
            else:
                print(" 查無符合條件的股票。")

        except Exception as e:
            print(f"❌ 執行過程中發生錯誤: {str(e)}")

# 註冊事件
run_button.on_click(on_button_clicked)

# 顯示介面
ui_container = widgets.VBox([
    instruction_label,
    tickers_input,
    widgets.HBox([date_picker, run_button]),
    widgets.HTML(value="<hr>"),
    output_area
])

display(ui_container)
