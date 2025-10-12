import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from io import StringIO

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
# 定数設定
# ----------------------------------------------------
SPREADSHEET_NAME = "外部脳日記"
DRIVE_FOLDER_ID = "1y55LVN8McbzGgA_2zUUoVz6WdWt7HhXd"


# ----------------------------------------------------
# 認証情報の設定
# ----------------------------------------------------
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scopes
)

# Gemini APIへの接続設定
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# Googleサービスへの接続クライアント
gspread_client = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

# ----------------------------------------------------
# 機能の定義
# ----------------------------------------------------

@st.cache_data(ttl=600)
def load_diaries_from_sheet():
    try:
        spreadsheet = gspread_client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.sheet1
        data = worksheet.get_all_records()
        if not data: return pd.DataFrame(columns=['Date', 'Diary', 'Feedback'])
        df = pd.DataFrame(data)
        df.columns = ['Date', 'Diary', 'Feedback']
        return df
    except Exception as e:
        st.error(f"日記スプレッドシートの読み込みエラー: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_drive_files_context(folder_id):
    context = ""
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        items = results.get('files', [])
        if not items: return "参照可能なファイルは見つかりませんでした。"
        for item in items:
            file_id, file_name, mime_type = item['id'], item['name'], item['mimeType']
            content = f"ファイル名: {file_name}\n内容:\n"
            if mime_type == 'application/vnd.google-apps.document':
                request = drive_service.files().export_media(fileId=file_id, mimeType='text/plain')
                content += request.execute().decode('utf-8')
            elif 'text' in mime_type:
                request = drive_service.files().get_media(fileId=file_id)
                content += request.execute().decode('utf-8')
            else:
                content += "（サポートされていないファイル形式です）"
            context += content + "\n---\n"
        return context
    except HttpError as error:
        st.error(f"Google Driveへのアクセスエラー: {error}")
        return "Google Driveのファイル取得に失敗しました。フォルダがサービスアカウントに共有されているか確認してください。"

# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
# AIからのフィードバックを生成する関数（プロンプトを調整）
def get_ai_feedback(diary_text, past_diaries_context, drive_context):
    prompt = f"""
あなたは非常に優秀なコンサルタントです。以下のすべての情報を統合的に分析し、クライアントにフィードバックを提供してください。

### 1. 参考情報（クライアントの知識ベース）
{drive_context}

### 2. 過去の経緯（直近の活動記録）
{past_diaries_context}

### 3. 今日の報告（日記）
{diary_text}

### あなたのタスク
上記の全ての情報を踏まえ、以下の2つの項目について、**全体で300字程度（1分以内で読める長さ）**で簡潔にまとめてください。

1.  **現状の整理:**
    過去の経緯も踏まえ、今日の報告内容がどのような状況にあるのかを客観的に整理してください。

2.  **解決策の提案:**
    もし今日の報告に悩みや課題が含まれていれば、その解決に向けた具体的な次の一歩を提案してください。
"""
    response = gemini_model.generate_content(prompt)
    return response.text
# ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

def update_or_create_diary_entry(date, diary, feedback):
    try:
        spreadsheet = gspread_client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.sheet1
        dates_list = worksheet.col_values(1)
        if date in dates_list:
            row_index = dates_list.index(date) + 1
            worksheet.update_cell(row_index, 2, diary)
            worksheet.update_cell(row_index, 3, feedback)
        else:
            worksheet.append_row([date, diary, feedback])
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"スプレッドシートへの書き込みエラー: {e}")
        return False

# ----------------------------------------------------
# UIとメイン処理
# ----------------------------------------------------
all_diaries_df = load_diaries_from_sheet()

selected_date = st.date_input("どの日付の日記を記録・閲覧しますか？", datetime.now())
date_str = selected_date.strftime('%Y-%m-%d')

diary_for_date = ""
if not all_diaries_df.empty:
    all_diaries_df['Date'] = all_diaries_df['Date'].astype(str)
    result_df = all_diaries_df[all_diaries_df['Date'] == date_str]
    if not result_df.empty:
        diary_for_date = result_df.iloc[0]['Diary']

diary_entry = st.text_area("ここに日記を書いてください...", value=diary_for_date, height=300)

if st.button("記録する"):
    if diary_entry:
        with st.spinner("関連情報を分析し、AIがフィードバックを生成しています..."):
            drive_context = get_drive_files_context(DRIVE_FOLDER_ID)
            
            past_diaries_context = "過去の日記はありません。"
            if not all_diaries_df.empty:
                recent_diaries = all_diaries_df[all_diaries_df['Date'] != date_str].tail(5)
                if not recent_diaries.empty:
                    past_diaries_context = ""
                    for index, row in recent_diaries.iterrows():
                        past_diaries_context += f"日付: {row['Date']}\n日記: {row['Diary']}\n---\n"

            ai_feedback = get_ai_feedback(diary_entry, past_diaries_context, drive_context)
            
            success = update_or_create_diary_entry(date_str, diary_entry, ai_feedback)
            if success:
                st.success("記録が完了しました！")
                st.subheader("AIからのフィードバック:")
                st.write(ai_feedback)
    else:
        st.warning("日記が入力されていません。")