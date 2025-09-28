import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

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
# モデルを "gemini-1.5-flash-latest" に変更
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
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# ここに、あなたが作成したGoogleスプレッドシートの名前を正確に入力してください
# (例: SPREADSHEET_NAME = "外部脳日記")
SPREADSHEET_NAME = "外部脳日記"
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

# ----------------------------------------------------
# 機能の定義
# ----------------------------------------------------

# AIからのフィードバックを生成する関数
def get_ai_feedback(diary_text):
    prompt = f"""
あなたはユーザーの良き相談相手であり、思考を整理するアシスタントです。
以下の日記の内容に対して、ポジティブな視点で客観的なフィードバックやアドバイス、
面白い視点からの問いかけなどを150字程度で返してください。

---
{diary_text}
---
"""
    response = gemini_model.generate_content(prompt)
    return response.text

# Googleスプレッドシートに書き込む関数
def write_to_spreadsheet(date, diary, feedback):
    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.sheet1
        # 新しい行としてデータを追記
        worksheet.append_row([date, diary, feedback])
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"エラー: スプレッドシート '{SPREADSHEET_NAME}' が見つかりません。名前が正しいか、サービスアカウントに共有されているか確認してください。")
        return False
    except Exception as e:
        st.error(f"スプレッドシートへの書き込み中にエラーが発生しました: {e}")
        return False

# ----------------------------------------------------
# UIとメイン処理
# ----------------------------------------------------

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
            # 1. AIからのフィードバックを取得
            ai_feedback = get_ai_feedback(diary_entry)

            # 2. スプレッドシートに書き込み
            # 日付を文字列に変換
            date_str = selected_date.strftime('%Y-%m-%d')
            success = write_to_spreadsheet(date_str, diary_entry, ai_feedback)

            if success:
                st.success("記録が完了しました！")
                st.subheader("AIからのフィードバック:")
                st.write(ai_feedback)
    else:
        st.warning("日記が入力されていません。")