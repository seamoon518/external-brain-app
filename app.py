import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd # pandasをインポート

# ----------------------------------------------------
# 画面のタイトル設定
# ----------------------------------------------------
st.set_page_config(
    page_title="外部脳日記アプリ",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 外部脳日記アプリ")
st.caption("AIがあなたの思考と記憶をサポートします。")

# ----------------------------------------------------
# 認証情報の設定
# ----------------------------------------------------

# Gemini APIへの接続設定
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# Googleスプレッドシートへの接続設定
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scopes
)
client = gspread.authorize(creds)

# 接続するスプレッドシートの名前を指定
SPREADSHEET_NAME = "外部脳日記"

# ----------------------------------------------------
# 機能の定義
# ----------------------------------------------------

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# スプレッドシートから全ての日記を読み込む関数（キャッシュ付き）
@st.cache_data(ttl=600) # 10分間キャッシュ
def load_diaries_from_sheet():
    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.sheet1
        # スプレッドシートの全データを取得し、DataFrameに変換
        data = worksheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=['Date', 'Diary', 'Feedback'])
        df = pd.DataFrame(data)
        # 列名を指定
        df.columns = ['Date', 'Diary', 'Feedback']
        return df
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"エラー: スプレッドシート '{SPREADSHEET_NAME}' が見つかりません。")
        return pd.DataFrame() # 空のDataFrameを返す
    except Exception as e:
        st.error(f"スプレッドシートの読み込み中にエラーが発生しました: {e}")
        return pd.DataFrame()

# AIからのフィードバックを生成する関数
def get_ai_feedback(diary_text):
    prompt = f"""
あなたは優秀なコンサルタントです。以下の日記の内容を分析し、次の2つの点を満たすように、構造化して客観的なフィードバックを返してください。
1. **客観的な状況整理:** 書かれている内容を感情を排して客観的に整理し、何が起きているのかを明確にしてください。
2. **具体的な解決策の提案:** もし日記に悩みや課題が含まれている場合は、それに対する具体的で実行可能な解決策や次の一歩を、箇条書きで端的に提示してください。悩みや課題がなければ、この項目は不要です。
---
[日記本文]
{diary_text}
---
"""
    response = gemini_model.generate_content(prompt)
    return response.text

# Googleスプレッドシートに書き込む/更新する関数
def update_or_create_diary_entry(date, diary, feedback):
    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.sheet1
        dates_list = worksheet.col_values(1)
        if date in dates_list:
            row_index = dates_list.index(date) + 1
            worksheet.update_cell(row_index, 2, diary)
            worksheet.update_cell(row_index, 3, feedback)
        else:
            worksheet.append_row([date, diary, feedback])
        st.cache_data.clear() # データ更新後にキャッシュをクリア
        return True
    except Exception as e:
        st.error(f"スプレッドシートへの書き込み中にエラーが発生しました: {e}")
        return False
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

# ----------------------------------------------------
# UIとメイン処理
# ----------------------------------------------------

# アプリ起動時に全日記データを読み込む
all_diaries_df = load_diaries_from_sheet()

selected_date = st.date_input(
    "どの日の日記を記録しますか？",
    datetime.now()
)

diary_entry = st.text_area(
    "ここに日記を書いてください...",
    height=300,
    key=f"diary_text_{selected_date}"
)

if st.button("記録する"):
    if diary_entry:
        with st.spinner("AIがフィードバックを生成し、データベースに記録しています..."):
            ai_feedback = get_ai_feedback(diary_entry)
            date_str = selected_date.strftime('%Y-%m-%d')
            success = update_or_create_diary_entry(date_str, diary_entry, ai_feedback)
            if success:
                st.success("記録が完了しました！")
                st.subheader("AIからのフィードバック:")
                st.write(ai_feedback)
    else:
        st.warning("日記が入力されていません。")

