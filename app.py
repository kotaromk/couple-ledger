import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import glob
import time
import json

# --- 設定: スマホで見やすくするために layout="centered" を明示 ---
st.set_page_config(page_title="Couple Ledger", page_icon="💰", layout="centered")

# --- CSSハック: 余計な余白やヘッダーを消してアプリっぽくする ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            /* 上の余白を詰める */
            .block-container {
                padding-top: 1rem;
                padding-bottom: 1rem;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            /* スマホでボタンを押しやすくする */
            div.stButton > button:first-child {
                width: 100%;
                border-radius: 10px;
                height: 3em;
                font-weight: bold;
            }
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

SPREADSHEET_NAME = "couple_ledger_db"

# --- Googleスプレッドシートへの接続 ---
@st.cache_resource
def get_spreadsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # クラウドの金庫を確認
        if "gcp_json" in st.secrets:
            # 3つのクォート対策：前後の空白を削除してから読み込む
            json_str = st.secrets["gcp_json"].strip()
            # もし外側がクォートで囲まれていたら外す処理（念のため）
            if json_str.startswith("'") and json_str.endswith("'"):
                json_str = json_str[1:-1]
            
            key_dict = json.loads(json_str)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
            client = gspread.authorize(creds)
            return client.open(SPREADSHEET_NAME).sheet1
    except Exception:
        pass

    # PC内のファイルを確認
    json_files = glob.glob("*.json")
    if not json_files:
        st.error("⚠️ 鍵ファイルが見つかりません")
        st.stop()
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_files[0], scope)
    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1

# --- データ操作関数 ---
def load_data():
    sheet = get_spreadsheet()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["日付", "誰が", "種別", "金額", "メモ"])
    return pd.DataFrame(data)

def add_data(date, user, action, amount, memo):
    sheet = get_spreadsheet()
    row = [str(date), user, action, amount, memo]
    sheet.append_row(row)

def delete_data(index):
    sheet = get_spreadsheet()
    sheet.delete_rows(index + 2)

# ==========================================
# アプリ本体（タブデザインに変更）
# ==========================================

# データを読み込む
try:
    df = load_data()
except Exception as e:
    st.error(f"通信エラー: {e}")
    st.stop()

# --- タイトル ---
st.markdown("### 💑 Couple Ledger")

# --- タブの作成（ここがポイント！） ---
tab1, tab2 = st.tabs(["📝 入力", "📊 通帳"])

# ------------------------------------------
# タブ1：入力画面
# ------------------------------------------
with tab1:
    # スマホだとフォームで囲むとスッキリする
    with st.form("entry_form", clear_on_submit=True):
        # 日付と金額
        date = st.date_input("日付", datetime.date.today())
        amount = st.number_input("金額 (円)", min_value=0, step=100)

        # ボタン系は見やすく
        st.write("👤 誰が？")
        user = st.radio("ユーザー", ["こうたろう", "ここな"], horizontal=True, label_visibility="collapsed")
        
        st.write("📂 種別")
        action = st.radio("アクション", ["入金 (貯金)", "出費 (支払い)"], horizontal=True, label_visibility="collapsed")
        
        memo = st.text_input("メモ (任意)")

        # 保存ボタン（CSSで大きくしてあります）
        submitted = st.form_submit_button("保存する")

        if submitted:
            if amount == 0:
                st.warning("金額を入力してください")
            else:
                add_data(date, user, action, amount, memo)
                st.success("✅ 保存しました！")
                time.sleep(1)
                st.rerun()

# ------------------------------------------
# タブ2：通帳画面
# ------------------------------------------
with tab2:
    if not df.empty:
        # 計算
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)
        total_income = df[df["種別"] == "入金 (貯金)"]["金額"].sum()
        total_expense = df[df["種別"] == "出費 (支払い)"]["金額"].sum()
        current_balance = total_income - total_expense

        # 残高カード表示
        st.info(f"💰 **現在の残高: ¥{int(current_balance):,}**")
        
        # 内訳
        c1, c2 = st.columns(2)
        c1.caption("総入金")
        c1.write(f"¥{int(total_income):,}")
        c2.caption("総出費")
        c2.write(f"¥{int(total_expense):,}")

        st.write("---")
        
        # 履歴（スマホで見やすいように必要な列だけ表示）
        st.caption("📜 最近の履歴")
        # 日付、誰が、金額、メモだけ表示
        display_df = df[["日付", "誰が", "種別", "金額", "メモ"]].copy()
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # 削除機能
        with st.expander("ゴミ箱 (データ削除)"):
            # 削除は見ながら選べるようにセレクトボックスに変更
            # 行番号と内容をセットにして表示
            options = [f"No.{i}: {row['日付']} {row['金額']}円 ({row['メモ']})" for i, row in df.iterrows()]
            selected_option = st.selectbox("削除するデータを選択", options)
            
            if st.button("削除実行"):
                # No.X の数字部分を取り出す
                delete_index = int(selected_option.split(":")[0].replace("No.", ""))
                delete_data(delete_index)
                st.success("削除しました")
                time.sleep(1)
                st.rerun()

    else:
        st.info("データがありません。隣のタブから入力してください。")