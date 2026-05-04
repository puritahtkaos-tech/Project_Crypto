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
import time
import google.generativeai as genai

# ==========================================
# 1. ตั้งค่า AI (เวอร์ชันแก้ Bug 404 และรองรับ Secret)
# ==========================================
ai_ready = False
ai_error_msg = ""
try:
    # ดึง API KEY จาก Secrets หรือใช้ค่าว่างถ้าไม่เจอ
    if "GEMINI_API_KEY" in st.secrets:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    else:
        API_KEY = "AIzaSyA_zC5g9GJjrx52ywy_LjP_r8MGX5sO9pI" # ใส่คีย์สำรองของคุณตรงนี้

    genai.configure(api_key=API_KEY)
    AI_MODEL = 'gemini-1.5-flash'
    ai_ready = True
except Exception as e:
    ai_ready = False
    ai_error_msg = str(e)

# ==========================================
# 2. ระบบฐานข้อมูลผู้ใช้ (JSON) & ระบบ Admin
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

def setup_admin():
    users = load_users()
    if "admin" not in users:
        users["admin"] = {
            "password": "admin",
            "wallet_thb": 999999999.0,
            "crypto_wallet": {"BTC-USD": 0.0, "ETH-USD": 0.0, "DOGE-USD": 0.0, "SOL-USD": 0.0, "ADA-USD": 0.0, "XRP-USD": 0.0, "BNB-USD": 0.0},
            "trade_history": [],
            "role": "admin"
        }
        save_users(users)

setup_admin()

def register_user(username, password):
    users = load_users()
    if username in users: return False, "❌ ชื่อผู้ใช้นี้มีอยู่แล้ว"
    users[username] = {
        "password": password, "wallet_thb": 0.0,
        "crypto_wallet": {"BTC-USD": 0.0, "ETH-USD": 0.0, "DOGE-USD": 0.0, "SOL-USD": 0.0, "ADA-USD": 0.0, "XRP-USD": 0.0, "BNB-USD": 0.0},
        "trade_history": [], "role": "user"
    }
    save_users(users)
    return True, "✅ สมัครสมาชิกสำเร็จ!"

def login_user(username, password):
    users = load_users()
    if username in users and users[username]["password"] == password:
        return True, users[username]
    return False, None

# ==========================================
# 3. Algorithms (Sorting & Search ใกล้เคียง)
# ==========================================
def partition(arr, low, high):
    pivot = arr[high]['price']
    i = low - 1
    for j in range(low, high):
        if arr[j]['price'] <= pivot:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i+1], arr[high] = arr[high], arr[i+1]
    return i + 1

def quick_sort(arr, low, high):
    if low < high:
        pi = partition(arr, low, high)
        quick_sort(arr, low, pi - 1)
        quick_sort(arr, pi + 1, high)

def jump_search_closest(arr, target):
    n = len(arr)
    if n == 0: return None
    step = int(math.sqrt(n))
    prev = 0
    while prev < n and arr[min(step, n)-1]['price'] < target:
        prev = step
        step += int(math.sqrt(n))
        if prev >= n: return arr[-1]
    while prev < min(step, n) and arr[prev]['price'] < target:
        prev += 1
    if prev == n: return arr[-1]
    if prev == 0: return arr[0]
    return arr[prev] if abs(arr[prev]['price'] - target) < abs(arr[prev-1]['price'] - target) else arr[prev-1]

@st.cache_data(ttl=300)
def fetch_data(ticker="BTC-USD", days=30):
    try:
        data = yf.Ticker(ticker).history(period=f"{days}d")
        return [{"date": d.strftime("%d/%m/%Y"), "open": int(r['Open']*35), "high": int(r['High']*35), "low": int(r['Low']*35), "price": int(r['Close']*35)} for d, r in data.iterrows()]
    except: return []

# ==========================================
# 4. UI Config & Authentication
# ==========================================
st.set_page_config(page_title="PRO CRYPTO SIM", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .login-box { background-color: #1a1c24; padding: 40px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); max-width: 450px; margin: auto; }
    </style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

def show_auth():
    st.markdown('<div style="text-align: center; padding: 40px 0;"><h1>🏦 PRO <span style="color:#f3ba2f">CRYPTO</span> SIM</h1><p style="color:#888">The Ultimate Trading Simulator</p></div>', unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        if st.session_state.auth_mode == 'login':
            st.markdown('<h2 style="text-align:center">🔐 เข้าสู่ระบบ</h2>', unsafe_allow_html=True)
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("เข้าสู่ระบบ", use_container_width=True, type="primary"):
                ok, data = login_user(u, p)
                if ok:
                    st.session_state.update({"logged_in": True, "username": u, "wallet_thb": data["wallet_thb"], "role": data.get("role", "user"), "crypto_wallet": data["crypto_wallet"], "trade_history": data["trade_history"]})
                    st.rerun()
                else: st.error("ชื่อผู้ใช้หรือรหัสผ่านผิด")
            if st.button("สมัครสมาชิกใหม่"): st.session_state.auth_mode = 'register'; st.rerun()
            
            st.markdown("<hr><p style='text-align:center; color:#888; font-size:12px'>Social Login (Mockup)</p>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            if c1.button("📘 Facebook", use_container_width=True): st.toast("ระบบ FB กำลังเชื่อมต่อ...")
            if c2.button("🟢 Line", use_container_width=True): st.toast("Line Login เร็วๆ นี้")
        else:
            st.markdown('<h2 style="text-align:center">📝 สมัครสมาชิก</h2>', unsafe_allow_html=True)
            nu = st.text_input("ตั้งชื่อผู้ใช้")
            np = st.text_input("ตั้งรหัสผ่าน", type="password")
            if st.button("ยืนยันสมัครสมาชิก", use_container_width=True, type="primary"):
                ok, msg = register_user(nu, np)
                if ok: st.success(msg); st.session_state.auth_mode = 'login'; st.rerun()
                else: st.error(msg)
            if st.button("กลับไปหน้า Login"): st.session_state.auth_mode = 'login'; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state.logged_in: show_auth(); st.stop()

# ==========================================
# 5. Main App
# ==========================================
def sync():
    users = load_users()
    if st.session_state.username in users:
        users[st.session_state.username].update({"wallet_thb": st.session_state.wallet_thb, "crypto_wallet": st.session_state.crypto_wallet, "trade_history": st.session_state.trade_history})
        save_users(users)

with st.sidebar:
    st.title("💰 เมนูควบคุม")
    st.write(f"👤: **{st.session_state.username}** ({st.session_state.role})")
    if st.session_state.role == 'admin':
        with st.expander("👑 Admin Panel"):
            all_u = load_users()
            target = st.selectbox("เลือก User:", list(all_u.keys()))
            amt = st.number_input("เสกเงิน (THB):", min_value=0.0)
            if st.button("🪄 เสกเงิน"):
                all_u[target]["wallet_thb"] += amt
                save_users(all_u)
                if target == st.session_state.username: st.session_state.wallet_thb += amt
                st.success("สำเร็จ!"); st.rerun()
    
    if st.button("🚪 Logout", use_container_width=True): st.session_state.logged_in = False; st.rerun()
    st.markdown("---")
    coins = {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Dogecoin (DOGE)": "DOGE-USD", "Solana (SOL)": "SOL-USD"}
    sel_coin = st.selectbox("เลือกเหรียญ:", list(coins.keys()))
    sel_tf = st.selectbox("ช่วงเวลา:", ["7 วัน", "1 เดือน", "1 ปี"])
    days = {"7 วัน": 7, "1 เดือน": 30, "1 ปี": 365}[sel_tf]
    if st.button("🔄 โหลดข้อมูล", use_container_width=True, type="primary"):
        st.session_state.raw_data = fetch_data(coins[sel_coin], days)
        st.session_state.sorted_data = [d.copy() for d in st.session_state.raw_data]
        st.session_state.is_sorted = False

st.title("📈 Pro Crypto Simulator")

if 'raw_data' in st.session_state and st.session_state.raw_data:
    t1, t2, t3, t4 = st.tabs(["📊 ตลาด", "💳 ฝาก-ถอน", "🤖 AI & Algo", "📜 ประวัติ"])
    now_p = st.session_state.raw_data[-1]['price']

    with t1:
        m1, m2, m3 = st.columns(3)
        m1.metric("ราคาปัจจุบัน", f"฿{now_p:,}")
        m2.metric("เงินสดของคุณ", f"฿{st.session_state.wallet_thb:,.2f}")
        m3.metric("เหรียญในมือ", f"{st.session_state.crypto_wallet.get(coins[sel_coin],0):.4f}")
        
        df = pd.DataFrame(st.session_state.raw_data)
        fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['price'])])
        st.plotly_chart(fig, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            b_amt = st.number_input("ซื้อกี่บาท:", min_value=0.0)
            if st.button("🟢 BUY", use_container_width=True):
                if 0 < b_amt <= st.session_state.wallet_thb:
                    qty = b_amt / now_p
                    st.session_state.wallet_thb -= b_amt
                    st.session_state.crypto_wallet[coins[sel_coin]] += qty
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%H:%M"), "ประเภท": "ซื้อ", "เหรียญ": sel_coin, "มูลค่า": b_amt})
                    sync(); st.success("ซื้อสำเร็จ"); st.rerun()
        with c2:
            s_qty = st.number_input("ขายกี่เหรียญ:", min_value=0.0)
            if st.button("🔴 SELL", use_container_width=True):
                if 0 < s_qty <= st.session_state.crypto_wallet.get(coins[sel_coin],0):
                    val = s_qty * now_p
                    st.session_state.wallet_thb += val
                    st.session_state.crypto_wallet[coins[sel_coin]] -= s_qty
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%H:%M"), "ประเภท": "ขาย", "เหรียญ": sel_coin, "มูลค่า": val})
                    sync(); st.success("ขายสำเร็จ"); st.rerun()

    with t2:
        st.markdown(f"### ยอดเงินคงเหลือ: ฿{st.session_state.wallet_thb:,.2f}")
        cd1, cd2 = st.columns(2)
        with cd1:
            st.write("**📥 ฝากเงิน (Scan QR)**")
            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=PromptPay_000", width=200)
            d_val = st.number_input("ยอดเงินฝาก:", min_value=0.0, key="d")
            slip = st.file_uploader("แนบสลิป")
            if st.button("✅ แจ้งฝาก", use_container_width=True):
                if d_val > 0 and slip:
                    with st.spinner("ตรวจสลิป..."): time.sleep(2)
                    st.session_state.wallet_thb += d_val
                    st.session_state.trade_history.append({"เวลา": "สแกน", "ประเภท": "ฝาก", "เหรียญ": "THB", "มูลค่า": d_val})
                    sync(); st.balloons(); st.rerun()
        with cd2:
            st.write("**📤 ถอนเงิน**")
            w_val = st.number_input("ยอดถอน:", min_value=0.0, key="w")
            st.text_input("เลขบัญชีรับเงิน")
            if st.button("🏧 ยืนยันถอน", use_container_width=True):
                if 0 < w_val <= st.session_state.wallet_thb:
                    st.session_state.wallet_thb -= w_val
                    st.session_state.trade_history.append({"เวลา": "ถอน", "ประเภท": "ถอน", "เหรียญ": "THB", "มูลค่า": w_val})
                    sync(); st.success("ถอนสำเร็จ"); st.rerun()

    with t3:
        if st.button("✨ AI วิเคราะห์ตลาด"):
            if ai_ready:
                with st.spinner("AI คิดอยู่..."):
                    model = genai.GenerativeModel(AI_MODEL)
                    ps = [d['price'] for d in st.session_state.raw_data[-10:]]
                    res = model.generate_content(f"วิเคราะห์ราคา {sel_coin} จากข้อมูลนี้: {ps} สรุปสั้นๆ ว่าควร ซื้อ/ขาย")
                    st.info(res.text)
            else: st.error(f"AI ไม่พร้อม: {ai_error_msg}")
        
        st.markdown("---")
        if st.button("📉 จัดเรียงราคา (Quick Sort)"):
            quick_sort(st.session_state.sorted_data, 0, len(st.session_state.sorted_data)-1)
            st.session_state.is_sorted = True
            st.success("เรียงเสร็จแล้ว ดูตารางด้านล่าง")
        if st.session_state.get('is_sorted'): st.dataframe(pd.DataFrame(st.session_state.sorted_data)[['date','price']])
        
        st.markdown("**🔍 ค้นหาราคาใกล้เคียง (Jump Search)**")
        target = st.number_input("ใส่ราคาที่อยากหา:")
        if st.button("🚀 ค้นหา"):
            if st.session_state.get('is_sorted'):
                res = jump_search_closest(st.session_state.sorted_data, target)
                st.success(f"ราคาที่ใกล้เคียงที่สุดคือ {res['price']:,} เมื่อวันที่ {res['date']}")
            else: st.warning("ต้องกดเรียงราคาก่อน!")

    with t4: st.table(st.session_state.trade_history[::-1])
else: st.info("👈 กดปุ่ม 'โหลดข้อมูล' ที่แถบด้านซ้ายเพื่อเริ่ม")