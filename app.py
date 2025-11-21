import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import glob
import time
import json

# ページの基本設定
st.set_page_config(page_title="Couple Ledger", page_icon="💰")

SPREADSHEET_NAME = "couple_ledger_db"

# --- Googleスプレッドシートへの接続 ---
@st.cache_resource
def get_spreadsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # --- 【ここが重要】クラウドかPCかを自動判断 ---
    # パターンA：クラウド上の「金庫（Secrets）」に鍵がある場合
    if "gcp_json" in st.secrets:
        key_dict = json.loads(st.secrets["gcp_json"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    
    # パターンB：自分のPCに「secret.json」ファイルがある場合
    else:
        json_files = glob.glob("*.json")
        if not json_files:
            st.error("⚠️ 鍵ファイルが見つかりません！")
            st.stop()
        creds = ServiceAccountCredentials.from_json_keyfile_name(json_files[0], scope)

    client = gspread.authorize(creds)
    return client.open(SPREADSHEET_NAME).sheet1

# --- データの読み込み ---
def load_data():
    sheet = get_spreadsheet()
    data = sheet.get_all_records()
    if not data:
        return pd.DataFrame(columns=["日付", "誰が", "種別", "金額", "メモ"])
    return pd.DataFrame(data)

# --- データの追加 ---
def add_data(date, user, action, amount, memo):
    sheet = get_spreadsheet()
    row = [str(date), user, action, amount, memo]
    sheet.append_row(row)

# --- データの削除 ---
def delete_data(index):
    sheet = get_spreadsheet()
    sheet.delete_rows(index + 2)

# ==========================================
# アプリ画面の構築
# ==========================================

st.sidebar.title("メニュー")
page = st.sidebar.radio("移動", ["📝 入力画面", "📊 通帳・履歴"])

try:
    df = load_data()
except Exception as e:
    st.error(f"エラー: {e}")
    st.stop()

# ------------------------------------------
# 画面1：入力画面
# ------------------------------------------
if page == "📝 入力画面":
    st.title("📝 新しい記録を追加")

    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        date = col1.date_input("日付", datetime.date.today())
        amount = col2.number_input("金額", min_value=0, step=100)

        user = st.radio("誰が？", ["松矢", "彼女"], horizontal=True)
        action = st.radio("種別", ["入金 (貯金)", "出費 (支払い)"], horizontal=True)
        memo = st.text_input("メモ")

        submitted = st.form_submit_button("保存する")

        if submitted:
            add_data(date, user, action, amount, memo)
            
            if action == "入金 (貯金)":
                st.success(f"{amount}円 を入金しました！")
            else:
                st.error(f"{amount}円 を支払いました。")
            
            time.sleep(1)
            st.rerun()

# ------------------------------------------
# 画面2：通帳・履歴画面
# ------------------------------------------
elif page == "📊 通帳・履歴":
    st.title("📊 通帳・履歴")

    if not df.empty:
        df["金額"] = pd.to_numeric(df["金額"], errors='coerce').fillna(0)

        total_income = df[df["種別"] == "入金 (貯金)"]["金額"].sum()
        total_expense = df[df["種別"] == "出費 (支払い)"]["金額"].sum()
        current_balance = total_income - total_expense

        st.metric("現在の共同貯金残高", f"¥{int(current_balance):,}")
        
        col1, col2 = st.columns(2)
        col1.metric("総入金額", f"¥{int(total_income):,}")
        col2.metric("総出費額", f"¥{int(total_expense):,}", delta=-total_expense)

        st.write("---")
        st.subheader("📜 履歴一覧")
        st.dataframe(df, use_container_width=True)

        with st.expander("データを削除する"):
            delete_index = st.number_input("削除する行No.", min_value=0, step=1)
            if st.button("削除実行"):
                if delete_index in df.index:
                    delete_data(delete_index)
                    st.success("削除しました")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("その番号はありません")
    else:
        st.info("データがありません")