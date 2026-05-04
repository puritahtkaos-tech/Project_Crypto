import streamlit as st
import yfinance as yf
import pandas as pd
import random
import math
import datetime
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from google import genai

# ==========================================
# 1. ตั้งค่า AI (ดึงคีย์จากตู้เซฟ Streamlit Secrets)
# ==========================================
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
    AI_MODEL = 'gemini-1.5-flash'
    ai_ready = True
except Exception as e:
    ai_ready = False

# ==========================================
# 2. ระบบฐานข้อมูลผู้ใช้ (JSON)
# ==========================================
USER_DB_FILE = "users.json"

def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def register_user(username, password):
    users = load_users()
    if username in users:
        return False, "❌ ชื่อผู้ใช้นี้มีอยู่แล้ว"
    users[username] = {
        "password": password,
        "wallet_thb": 100000.0,
        "crypto_wallet": {"BTC-USD": 0.0, "ETH-USD": 0.0, "DOGE-USD": 0.0},
        "trade_history": []
    }
    save_users(users)
    return True, "✅ สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ"

def login_user(username, password):
    users = load_users()
    if username in users and users[username]["password"] == password:
        return True, users[username]
    return False, None

# ==========================================
# 3. Algorithm (Sorting & Searching)
# ==========================================
def partition(arr, low, high):
    pivot_value = arr[high]['price']
    i = low - 1
    for j in range(low, high):
        if arr[j]['price'] <= pivot_value:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1

def random_quick_sort(arr, low, high):
    if low < high:
        pi = partition(arr, low, high)
        random_quick_sort(arr, low, pi - 1)
        random_quick_sort(arr, pi + 1, high)

def jump_search(arr, target_price):
    n = len(arr)
    if n == 0: return None
    step = int(math.sqrt(n))
    prev = 0
    while arr[min(step, n) - 1]['price'] < target_price:
        prev = step
        step += int(math.sqrt(n))
        if prev >= n: return None 
    while prev < n and arr[prev]['price'] < target_price:
        prev += 1
        if prev == min(step, n): return None 
    if prev < n and arr[prev]['price'] == target_price:
        return arr[prev]
    return None

@st.cache_data(ttl=300)
def fetch_real_crypto_data(ticker="BTC-USD", days=30):
    data = yf.Ticker(ticker)
    hist = data.history(period=f"{days}d")
    result = []
    for date, row in hist.iterrows():
        result.append({
            "date": date.strftime("%d/%m/%Y"), # แก้เป็น วัน/เดือน/ปี ตามสั่ง
            "open": int(row['Open'] * 35),
            "high": int(row['High'] * 35),
            "low": int(row['Low'] * 35),
            "price": int(row['Close'] * 35)
        })
    return result

# ==========================================
# 4. ตั้งค่าหน้าเว็บ & UI (สไตล์ตามรูปตัวอย่าง)
# ==========================================
st.set_page_config(page_title="Crypto Simulator", page_icon="🏦", layout="wide")

# CSS สำหรับหน้า Login ให้เหมือนรูปตัวอย่าง
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .login-box {
        background-color: #1a1c24;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        max-width: 450px;
        margin: auto;
    }
    .main-title { text-align: center; color: #ffffff; margin-bottom: 30px; }
    </style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

# ==========================================
# 5. หน้า Login / Register (แบบ Single Box)
# ==========================================
def show_auth_page():
    _, center_col, _ = st.columns([1, 2, 1])
    
    with center_col:
        st.markdown(f'<div class="login-box">', unsafe_allow_html=True)
        
        if st.session_state.auth_mode == 'login':
            st.markdown('<h1 class="main-title">🔐 เข้าสู่ระบบ</h1>', unsafe_allow_html=True)
            user = st.text_input("ชื่อผู้ใช้ (Username)")
            pw = st.text_input("รหัสผ่าน (Password)", type="password")
            
            if st.button("เข้าสู่ระบบ", use_container_width=True, type="primary"):
                success, data = login_user(user, pw)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.wallet_thb = data["wallet_thb"]
                    st.session_state.crypto_wallet = data["crypto_wallet"]
                    st.session_state.trade_history = data["trade_history"]
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            
            if st.button("ยังไม่มีบัญชี? สมัครสมาชิกที่นี่", use_container_width=True):
                st.session_state.auth_mode = 'register'
                st.rerun()
        
        else:
            st.markdown('<h1 class="main-title">📝 สมัครสมาชิก</h1>', unsafe_allow_html=True)
            new_user = st.text_input("ตั้งชื่อผู้ใช้")
            new_pw = st.text_input("ตั้งรหัสผ่าน", type="password")
            confirm_pw = st.text_input("ยืนยันรหัสผ่าน", type="password")
            
            if st.button("ยืนยันการสมัคร", use_container_width=True, type="primary"):
                if new_pw != confirm_pw:
                    st.error("รหัสผ่านไม่ตรงกัน")
                elif len(new_user) < 3:
                    st.error("ชื่อผู้ใช้สั้นเกินไป")
                else:
                    success, msg = register_user(new_user, new_pw)
                    if success:
                        st.success(msg)
                        st.session_state.auth_mode = 'login'
                        st.rerun()
                    else:
                        st.error(msg)
            
            if st.button("มีบัญชีแล้ว? กลับไปหน้าเข้าสู่ระบบ", use_container_width=True):
                st.session_state.auth_mode = 'login'
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    show_auth_page()
    st.stop()

# ==========================================
# 6. ส่วนหน้าหลักแอป (Dashboard)
# ==========================================

# ฟังก์ชันเซฟข้อมูล
def sync_data():
    users = load_users()
    if st.session_state.username in users:
        users[st.session_state.username].update({
            "wallet_thb": st.session_state.wallet_thb,
            "crypto_wallet": st.session_state.crypto_wallet,
            "trade_history": st.session_state.trade_history
        })
        save_users(users)

with st.sidebar:
    st.title("💰 เมนูควบคุม")
    st.markdown(f"👤 สวัสดีคุณ: **{st.session_state.username}**")
    
    # เพิ่มปุ่ม Logout ตาม List ที่ให้แก้
    if st.button("🚪 ออกจากระบบ (Logout)", use_container_width=True):
        sync_data()
        st.session_state.logged_in = False
        st.rerun()
    
    st.markdown("---")
    coin_dict = {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Dogecoin (DOGE)": "DOGE-USD"}
    selected_coin = st.selectbox("เลือกเหรียญที่จะดู:", list(coin_dict.keys()))
    current_ticker = coin_dict[selected_coin]
    
    if st.button("🔄 ดึงข้อมูลตลาดล่าสุด", use_container_width=True):
        st.session_state.raw_data = fetch_real_crypto_data(current_ticker)
        st.session_state.sorted_data = [d.copy() for d in st.session_state.raw_data]
        st.success("อัปเดตข้อมูลแล้ว!")

st.title("📈 ระบบจำลองการเทรดคริปโต")

if 'raw_data' in st.session_state:
    tab1, tab2, tab3 = st.tabs(["📊 ตลาดและการซื้อขาย", "🤖 AI & Algorithm", "📜 ประวัติการเงิน"])
    latest_price = st.session_state.raw_data[-1]['price']

    with tab1:
        # กราฟแท่งเทียน
        df = pd.DataFrame(st.session_state.raw_data)
        fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['price'])])
        fig.update_layout(title=f"กราฟราคา {selected_coin} (30 วันล่าสุด)", xaxis_title="วันที่", yaxis_title="ราคา (บาท)")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"💵 เงินสดในบัญชี: {st.session_state.wallet_thb:,.2f} บาท")
            buy_amt = st.number_input("จำนวนเงินที่จะซื้อ (บาท)", min_value=0.0, step=1000.0)
            if st.button("🟢 ยืนยันการซื้อ"):
                if buy_amt > 0 and buy_amt <= st.session_state.wallet_thb:
                    qty = buy_amt / latest_price
                    st.session_state.wallet_thb -= buy_amt
                    st.session_state.crypto_wallet[current_ticker] += qty
                    st.session_state.trade_history.append({
                        "เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "ประเภท": "🟢 ซื้อ", "เหรียญ": selected_coin, "ปริมาณ": f"{qty:.6f}", "ราคา": f"{latest_price:,.0f}", "มูลค่า": f"{buy_amt:,.2f}"
                    })
                    sync_data()
                    st.success(f"ซื้อ {selected_coin} สำเร็จ!")
                    st.rerun()
                else: st.error("เงินไม่พอ!")

        with col2:
            st.warning(f"🪙 เหรียญที่คุณมี: {st.session_state.crypto_wallet[current_ticker]:.6f}")
            sell_qty = st.number_input("จำนวนเหรียญที่จะขาย", min_value=0.0, step=0.001, format="%.6f")
            if st.button("🔴 ยืนยันการขาย"):
                if sell_qty > 0 and sell_qty <= st.session_state.crypto_wallet[current_ticker]:
                    money = sell_qty * latest_price
                    st.session_state.crypto_wallet[current_ticker] -= sell_qty
                    st.session_state.wallet_thb += money
                    st.session_state.trade_history.append({
                        "เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "ประเภท": "🔴 ขาย", "เหรียญ": selected_coin, "ปริมาณ": f"{sell_qty:.6f}", "ราคา": f"{latest_price:,.0f}", "มูลค่า": f"{money:,.2f}"
                    })
                    sync_data()
                    st.success(f"ขายสำเร็จ ได้รับเงิน {money:,.2f} บาท")
                    st.rerun()
                else: st.error("เหรียญไม่พอ!")

        # ระบบฝาก/ถอนเงิน (เพิ่มตาม List)
        st.markdown("---")
        with st.expander("💸 ทำรายการ ฝาก/ถอน เงินสด"):
            c1, c2 = st.columns(2)
            with c1:
                d_amt = st.number_input("จำนวนเงินฝาก (บาท)", min_value=0.0)
                if st.button("💵 ยืนยันฝากเงิน"):
                    st.session_state.wallet_thb += d_amt
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "💵 ฝากเงิน", "เหรียญ": "THB", "ปริมาณ": "-", "ราคา": "-", "มูลค่า": f"{d_amt:,.2f}"})
                    sync_data(); st.rerun()
            with c2:
                w_amt = st.number_input("จำนวนเงินถอน (บาท)", min_value=0.0)
                if st.button("🏧 ยืนยันถอนเงิน"):
                    if w_amt <= st.session_state.wallet_thb:
                        st.session_state.wallet_thb -= w_amt
                        st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "🏧 ถอนเงิน", "เหรียญ": "THB", "ปริมาณ": "-", "ราคา": "-", "มูลค่า": f"-{w_amt:,.2f}"})
                        sync_data(); st.rerun()
                    else: st.error("เงินไม่พอถอน!")

    with tab2:
        st.subheader("🤖 AI Analyst (Gemini)")
        if st.button("วิเคราะห์แนวโน้มตลาด"):
            if ai_ready:
                prices = [d['price'] for d in st.session_state.raw_data]
                prompt = f"วิเคราะห์ราคา {selected_coin} จากข้อมูล 30 วันนี้: {prices} และสรุปสั้นๆ ว่าควร ซื้อ/ขาย/ถือ"
                response = client.models.generate_content(model=AI_MODEL, contents=prompt)
                st.write(response.text)
            else: st.error("กรุณาตั้งค่า API Key ใน Secrets")

        st.markdown("---")
        st.subheader("📉 Algorithm Tools")
        if st.button("จัดเรียงราคา (Quick Sort)"):
            random_quick_sort(st.session_state.sorted_data, 0, len(st.session_state.sorted_data)-1)
            st.dataframe(pd.DataFrame(st.session_state.sorted_data))
            st.session_state.is_sorted = True

    with tab3:
        st.subheader("📜 ประวัติรายการทั้งหมด (ฝาก/ถอน/เทรด)")
        if st.session_state.trade_history:
            st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1]) # แสดงอันล่าสุดก่อน
        else:
            st.write("ยังไม่มีประวัติรายการ")

else:
    st.warning("กรุณากดปุ่ม 'ดึงข้อมูลตลาดล่าสุด' ที่แถบด้านซ้ายก่อนครับ")