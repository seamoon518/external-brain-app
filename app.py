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
gemini_model = genai.GenerativeModel("gemini-2.5-flash") # ユーザー指定のモデル

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

# AIからのフィードバックを生成する関数
def get_ai_feedback(diary_text):
    prompt = f"""
あなたは優秀なコンサルタントです。以下の日記の内容を分析し、次の2つの点を満たすように、構造化して客観的なフィードバックを返してください。

1. **客観的な状況整理:**
   書かれている内容を感情を排して客観的に整理し、何が起きているのかを明確にしてください。

2. **具体的な解決策の提案:**
   もし日記に悩みや課題が含まれている場合は、それに対する具体的で実行可能な解決策や次の一歩を、箇条書きで端的に提示してください。悩みや課題がなければ、この項目は不要です。

---
[日記本文]
{diary_text}
---
"""
    response = gemini_model.generate_content(prompt)
    return response.text

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# Googleスプレッドシートに書き込む関数（更新機能を追加）
def update_or_create_diary_entry(date, diary, feedback):
    try:
        spreadsheet = client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.sheet1
        
        # A列（日付が入力されている列）の全データを取得
        dates_list = worksheet.col_values(1)
        
        # 同じ日付が既に存在するか検索
        if date in dates_list:
            # 存在する場合、その行番号を取得 (リストのインデックス+1)
            row_index = dates_list.index(date) + 1
            # その行のB列とC列を更新
            worksheet.update_cell(row_index, 2, diary)
            worksheet.update_cell(row_index, 3, feedback)
        else:
            # 存在しない場合、新しい行として追記
            worksheet.append_row([date, diary, feedback])
            
        return True
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"エラー: スプレッドシート '{SPREADSHEET_NAME}' が見つかりません。名前が正しいか、サービスアカウントに共有されているか確認してください。")
        return False
    except Exception as e:
        st.error(f"スプレッドシートへの書き込み中にエラーが発生しました: {e}")
        return False
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

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
            ai_feedback = get_ai_feedback(diary_entry)
            date_str = selected_date.strftime('%Y-%m-%d')
            
            # 更新された関数を呼び出す
            success = update_or_create_diary_entry(date_str, diary_entry, ai_feedback)

            if success:
                st.success("記録が完了しました！")
                st.subheader("AIからのフィードバック:")
                st.write(ai_feedback)
    else:
        st.warning("日記が入力されていません。")