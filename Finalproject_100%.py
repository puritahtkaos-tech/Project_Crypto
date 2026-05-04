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
# 1. ตั้งค่า AI (เพิ่มระบบดักจับ Error แบบละเอียด)
# ==========================================
ai_ready = False
ai_error_msg = ""
try:
    # ลองดึงจาก Secrets ก่อน ถ้าไม่ได้ค่อยใช้อันสำรอง
    if "GEMINI_API_KEY" in st.secrets:
        API_KEY = st.secrets["GEMINI_API_KEY"]
    else:
        API_KEY = "AIzaSyA_J4TDD6bk7l3WQhHkEa1LqnxOQ7x3GPM" 

    client = genai.Client(api_key=API_KEY)
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
    # สร้างไอดี Admin อัตโนมัติถ้ายังไม่มี
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
    if username in users:
        return False, "❌ ชื่อผู้ใช้นี้มีอยู่แล้ว"
    users[username] = {
        "password": password,
        "wallet_thb": 0.0, # เริ่มต้น 0 บาท ต้องฝากเงิน
        "crypto_wallet": {
            "BTC-USD": 0.0, "ETH-USD": 0.0, "DOGE-USD": 0.0,
            "SOL-USD": 0.0, "ADA-USD": 0.0, "XRP-USD": 0.0, "BNB-USD": 0.0
        },
        "trade_history": [],
        "role": "user"
    }
    save_users(users)
    return True, "✅ สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ"

def login_user(username, password):
    users = load_users()
    if username in users and users[username]["password"] == password:
        return True, users[username]
    return False, None

# ==========================================
# 3. Algorithm
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

def jump_search_closest(arr, target_price):
    n = len(arr)
    if n == 0: return None
    step = int(math.sqrt(n))
    prev = 0
    while prev < n and arr[min(step, n) - 1]['price'] < target_price:
        prev = step
        step += int(math.sqrt(n))
        if prev >= n: return arr[-1]
    while prev < min(step, n) and arr[prev]['price'] < target_price:
        prev += 1
    if prev == n: return arr[-1]
    if prev == 0: return arr[0]
    diff1 = abs(arr[prev]['price'] - target_price)
    diff2 = abs(arr[prev-1]['price'] - target_price)
    return arr[prev] if diff1 <= diff2 else arr[prev-1]

@st.cache_data(ttl=300)
def fetch_real_crypto_data(ticker="BTC-USD", days=30):
    data = yf.Ticker(ticker)
    hist = data.history(period=f"{days}d")
    result = []
    for date, row in hist.iterrows():
        result.append({
            "date": date.strftime("%d/%m/%Y"), 
            "open": int(row['Open'] * 35),
            "high": int(row['High'] * 35),
            "low": int(row['Low'] * 35),
            "price": int(row['Close'] * 35)
        })
    return result

# ==========================================
# 4. ตั้งค่าหน้าเว็บ & UI
# ==========================================
st.set_page_config(page_title="Crypto Simulator", page_icon="🏦", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .login-box {
        background-color: #1a1c24; padding: 40px; border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5); max-width: 450px; margin: auto;
    }
    .social-btn {
        width: 100%; padding: 10px; margin: 5px 0; border-radius: 8px; border: none; font-weight: bold; cursor: pointer; color: white;
    }
    .btn-fb { background-color: #1877F2; }
    .btn-line { background-color: #00C300; }
    .btn-discord { background-color: #5865F2; }
    .btn-google { background-color: #DB4437; }
    </style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

# ==========================================
# 5. หน้า Login / Register (ปรับ UI Social Login)
# ==========================================
def show_auth_page():
    st.markdown("""
        <div style="text-align: center; padding: 40px 0px 20px 0px;">
            <h1 style="font-size: 50px; margin-bottom: 0px;">🏦 PRO <span style="color: #f3ba2f;">CRYPTO</span> SIM</h1>
            <p style="color: #888; font-size: 18px;">The Ultimate Trading Simulator & Market Analysis</p>
        </div>
    """, unsafe_allow_html=True)
    
    _, center_col, _ = st.columns([1, 2, 1])
    
    with center_col:
        st.markdown(f'<div class="login-box">', unsafe_allow_html=True)
        
        if st.session_state.auth_mode == 'login':
            st.markdown('<h2 style="text-align: center; color: white; margin-top: 0;">🔐 เข้าสู่ระบบ</h2>', unsafe_allow_html=True)
            user = st.text_input("ชื่อผู้ใช้ (Username)")
            pw = st.text_input("รหัสผ่าน (Password)", type="password")
            
            if st.button("เข้าสู่ระบบ", use_container_width=True, type="primary"):
                success, data = login_user(user, pw)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.wallet_thb = data["wallet_thb"]
                    st.session_state.role = data.get("role", "user")
                    
                    default_wallet = {"BTC-USD": 0.0, "ETH-USD": 0.0, "DOGE-USD": 0.0, "SOL-USD": 0.0, "ADA-USD": 0.0, "XRP-USD": 0.0, "BNB-USD": 0.0}
                    user_wallet = data.get("crypto_wallet", {})
                    for coin in default_wallet:
                        if coin not in user_wallet: user_wallet[coin] = 0.0
                    st.session_state.crypto_wallet = user_wallet
                    st.session_state.trade_history = data["trade_history"]
                    st.rerun()
                else:
                    st.error("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            
            if st.button("ยังไม่มีบัญชี? สมัครสมาชิกที่นี่", use_container_width=True):
                st.session_state.auth_mode = 'register'
                st.rerun()
                
            # --- Social Login Mockup ---
            st.markdown("<hr><p style='text-align: center; color: #888; font-size: 14px;'>เข้าสู่ระบบด้วยโซเชียลมีเดีย</p>", unsafe_allow_html=True)
            sc1, sc2 = st.columns(2)
            if sc1.button("📘 Facebook", use_container_width=True): st.warning("ระบบ Facebook กำลังขออนุญาต API จาก Meta")
            if sc2.button("🟩 Line", use_container_width=True): st.warning("ระบบ Line Login อยู่ระหว่างการพัฒนา")
            if sc1.button("👾 Discord", use_container_width=True): st.warning("เชื่อมต่อ Discord Server ล้มเหลว")
            if sc2.button("🔴 Google", use_container_width=True): st.warning("Google OAuth จำเป็นต้องใช้ HTTPS ยืนยันตัวตน")
        
        else:
            st.markdown('<h2 style="text-align: center; color: white; margin-top: 0;">📝 สมัครสมาชิก</h2>', unsafe_allow_html=True)
            new_user = st.text_input("ตั้งชื่อผู้ใช้")
            new_pw = st.text_input("ตั้งรหัสผ่าน", type="password")
            confirm_pw = st.text_input("ยืนยันรหัสผ่าน", type="password")
            
            if st.button("ยืนยันการสมัคร", use_container_width=True, type="primary"):
                if new_pw != confirm_pw: st.error("รหัสผ่านไม่ตรงกัน")
                elif len(new_user) < 3: st.error("ชื่อผู้ใช้สั้นเกินไป")
                else:
                    success, msg = register_user(new_user, new_pw)
                    if success:
                        st.success(msg)
                        st.session_state.auth_mode = 'login'
                        st.rerun()
                    else: st.error(msg)
            
            if st.button("มีบัญชีแล้ว? กลับไปหน้าเข้าสู่ระบบ", use_container_width=True):
                st.session_state.auth_mode = 'login'
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

if not st.session_state.logged_in:
    show_auth_page()
    st.stop()

# ==========================================
# 6. Dashboard & Admin System
# ==========================================
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
    st.markdown(f"👤 สวัสดี: **{st.session_state.username}**")
    
    # 👑 ระบบ Admin: เสกเงิน
    if st.session_state.get('role') == 'admin':
        st.markdown("---")
        st.markdown("👑 **Admin Panel**")
        all_users = load_users()
        target_user = st.selectbox("เลือกผู้ใช้ที่จะเพิ่มเงิน:", list(all_users.keys()))
        add_money = st.number_input("จำนวนเงิน (THB)", min_value=0.0, step=1000.0)
        if st.button("🪄 เสกเงินเข้าบัญชี", type="primary"):
            all_users[target_user]["wallet_thb"] += add_money
            save_users(all_users)
            if target_user == st.session_state.username:
                st.session_state.wallet_thb += add_money
            st.success(f"เพิ่มเงิน {add_money:,.2f} ให้ {target_user} สำเร็จ!")
            st.rerun()

    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        sync_data()
        st.session_state.logged_in = False
        st.rerun()
    
    st.markdown("---")
    
    coin_dict = {
        "Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", 
        "Dogecoin (DOGE)": "DOGE-USD", "Solana (SOL)": "SOL-USD", 
        "Cardano (ADA)": "ADA-USD", "Ripple (XRP)": "XRP-USD", "Binance (BNB)": "BNB-USD"
    }
    selected_coin = st.selectbox("1️⃣ เลือกเหรียญ:", list(coin_dict.keys()))
    current_ticker = coin_dict[selected_coin]
    
    timeframe_dict = {"7 วัน": 7, "1 เดือน": 30, "3 เดือน": 90, "6 เดือน": 180, "1 ปี": 365}
    selected_tf = st.selectbox("2️⃣ เลือกช่วงเวลา:", list(timeframe_dict.keys()))
    days_to_fetch = timeframe_dict[selected_tf]
    
    if st.button("🔄 โหลดข้อมูล / อัปเดตกราฟ", use_container_width=True, type="primary"):
        st.session_state.raw_data = fetch_real_crypto_data(current_ticker, days_to_fetch)
        st.session_state.sorted_data = [d.copy() for d in st.session_state.raw_data]
        st.session_state.is_sorted = False
        st.success("อัปเดตข้อมูลสำเร็จ!")

st.title("📈 Pro Crypto Simulator")

if 'raw_data' in st.session_state and len(st.session_state.raw_data) > 0:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 ตลาด & ซื้อขาย", "💼 ฝาก-ถอน & พอร์ต", "🤖 AI & ระบบค้นหา", "📜 ประวัติรายการ"])
    
    latest_price = st.session_state.raw_data[-1]['price']
    prev_price = st.session_state.raw_data[-2]['price'] if len(st.session_state.raw_data) > 1 else latest_price
    price_change = latest_price - prev_price
    percent_change = (price_change / prev_price) * 100 if prev_price > 0 else 0

    # --- TAB 1: ตลาด (UI ใหม่ สวยขึ้น มี Metric) ---
    with tab1:
        # แถบแสดงข้อมูลเหรียญแบบ Real-time ดึงดูดสายตา
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(label=f"ราคา {selected_coin}", value=f"฿{latest_price:,.2f}", delta=f"{price_change:,.2f} ({percent_change:.2f}%)")
        m2.metric(label="ปริมาณที่มีในกระเป๋า", value=f"{st.session_state.crypto_wallet[current_ticker]:.6f}")
        m3.metric(label="เงินสดพร้อมเทรด", value=f"฿{st.session_state.wallet_thb:,.2f}")
        m4.metric(label="สถานะตลาด", value="เปิด 24 ชม.", delta="ออนไลน์", delta_color="normal")

        df = pd.DataFrame(st.session_state.raw_data)
        fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['price'])])
        fig.update_layout(xaxis_title="วันที่", yaxis_title="ราคา (บาท)", template="plotly_dark", margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🛒 ทำรายการซื้อ-ขาย")
        col1, col2 = st.columns(2)
        with col1:
            st.success("🟢 ซื้อเหรียญ (Buy)")
            buy_amt = st.number_input("ใส่จำนวนเงิน (บาท) เพื่อซื้อ:", min_value=0.0, step=1000.0)
            if st.button("ยืนยันการซื้อ", use_container_width=True):
                if buy_amt > 0 and buy_amt <= st.session_state.wallet_thb:
                    qty = buy_amt / latest_price
                    st.session_state.wallet_thb -= buy_amt
                    st.session_state.crypto_wallet[current_ticker] += qty
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "🟢 ซื้อ", "เหรียญ": selected_coin, "ปริมาณ": f"{qty:.6f}", "ราคา": f"{latest_price:,.0f}", "มูลค่า": f"{buy_amt:,.2f}"})
                    sync_data(); st.success("ซื้อสำเร็จ!"); st.rerun()
                else: st.error("⚠️ เงินสดไม่พอ!")

        with col2:
            st.error("🔴 ขายเหรียญ (Sell)")
            sell_qty = st.number_input("ใส่จำนวนเหรียญที่ต้องการขาย:", min_value=0.0, step=0.001, format="%.6f")
            if st.button("ยืนยันการขาย", use_container_width=True):
                if sell_qty > 0 and sell_qty <= st.session_state.crypto_wallet[current_ticker]:
                    money = sell_qty * latest_price
                    st.session_state.crypto_wallet[current_ticker] -= sell_qty
                    st.session_state.wallet_thb += money
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "🔴 ขาย", "เหรียญ": selected_coin, "ปริมาณ": f"{sell_qty:.6f}", "ราคา": f"{latest_price:,.0f}", "มูลค่า": f"{money:,.2f}"})
                    sync_data(); st.success("ขายสำเร็จ!"); st.rerun()
                else: st.error("⚠️ เหรียญไม่พอ!")

    # --- TAB 2: ระบบฝาก-ถอน สมจริง ---
    with tab2:
        st.subheader("💳 ระบบจัดการเงินสด (Deposit & Withdraw)")
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### 📥 ฝากเงิน (PromptPay/Bank)")
            st.info("จำลองการฝากเงิน: โปรดสแกน QR Code จำลองด้านล่าง หรือโอนผ่านบัญชี")
            
            # โชว์ QR Code จำลอง (ใช้ API สร้าง QR อัตโนมัติจาก PromptPay Dummy)
            # หรือถ้าอยากเปลี่ยนเป็น QR ตัวเอง ให้เอารูป QR ตัวเองใส่ในโฟลเดอร์เดียวกับโค้ด แล้วแก้เป็น st.image("qr.png")
            st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=PromptPayDummy", width=200)
            st.write("ธนาคาร: กสิกรไทย (KBank) | เลขบัญชี: 123-4-56789-0")
            
            d_amt = st.number_input("ยอดเงินที่โอน (บาท):", min_value=0.0, step=500.0)
            slip = st.file_uploader("แนบสลิปการโอน (จำลอง)", type=['png', 'jpg'])
            if st.button("✅ แจ้งฝากเงิน", use_container_width=True):
                if d_amt > 0 and slip is not None:
                    st.session_state.wallet_thb += d_amt
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "💵 ฝาก", "เหรียญ": "THB", "ปริมาณ": "-", "ราคา": "-", "มูลค่า": f"{d_amt:,.2f}"})
                    sync_data()
                    st.success(f"แอดมินอนุมัติแล้ว! เงินเข้า {d_amt:,.2f} บาท")
                    st.rerun()
                else:
                    st.warning("กรุณากรอกยอดเงินและแนบสลิปเพื่อยืนยัน")

        with c2:
            st.markdown("#### 📤 ถอนเงิน (Withdraw)")
            st.write(f"**ยอดเงินถอนได้:** ฿{st.session_state.wallet_thb:,.2f}")
            w_bank = st.selectbox("เลือกธนาคารปลายทาง:", ["กสิกรไทย", "ไทยพาณิชย์", "กรุงเทพ", "กรุงไทย", "TrueMoney Wallet"])
            w_acc = st.text_input("เลขบัญชี / เบอร์โทรศัพท์:")
            w_amt = st.number_input("จำนวนเงินที่ต้องการถอน:", min_value=0.0, step=500.0)
            
            if st.button("🏧 ยืนยันการถอนเงิน", use_container_width=True):
                if w_amt <= 0: st.warning("ระบุจำนวนเงินที่ต้องการถอน")
                elif w_acc == "": st.warning("กรุณาระบุเลขบัญชีปลายทาง")
                elif w_amt <= st.session_state.wallet_thb:
                    st.session_state.wallet_thb -= w_amt
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "🏧 ถอน", "เหรียญ": "THB", "ปริมาณ": "-", "ราคา": "-", "มูลค่า": f"-{w_amt:,.2f}"})
                    sync_data()
                    st.success(f"ทำรายการถอน {w_amt:,.2f} บาท เข้าบัญชี {w_bank} สำเร็จ!")
                    st.rerun()
                else: st.error("เงินในระบบไม่พอ!")

    # --- TAB 3: AI & อัลกอริทึม (ระบบจับ Error ละเอียด) ---
    with tab3:
        st.subheader("🤖 ให้ AI ช่วยวิเคราะห์ (Gemini)")
        if st.button("✨ กดเพื่อวิเคราะห์แนวโน้ม"):
            if ai_ready:
                prices = [d['price'] for d in st.session_state.raw_data[-14:]] 
                prompt = f"วิเคราะห์ราคา {selected_coin} จากข้อมูล 14 วันล่าสุดนี้: {prices} และสรุปสั้นๆ ว่าควรทำอย่างไร"
                try:
                    with st.spinner("AI กำลังใช้ความคิด..."):
                        response = client.models.generate_content(model=AI_MODEL, contents=prompt)
                        st.info(response.text)
                except Exception as e:
                    # ถ้าพัง จะโชว์ Error แดงๆ ให้รู้สาเหตุเลย
                    st.error(f"❌ AI ทำงานล้มเหลว สาเหตุ: {str(e)}")
                    st.warning("💡 คำแนะนำ: ตรวจสอบว่า API KEY ถูกต้องไหม หรือโควต้าการใช้งานฟรีรายวันหมดหรือไม่")
            else: 
                st.error("⚠️ ระบบ AI ยังไม่พร้อมใช้งาน")
                if ai_error_msg: st.code(f"Error Log: {ai_error_msg}")

        st.markdown("---")
        st.subheader("📉 ค้นหาและเรียงลำดับราคา")
        if st.button("1. จัดเรียงราคา (Quick Sort - จากน้อยไปมาก)"):
            random_quick_sort(st.session_state.sorted_data, 0, len(st.session_state.sorted_data)-1)
            st.session_state.is_sorted = True
            st.success("✅ จัดเรียงข้อมูลเสร็จสิ้น!")
        
        if st.session_state.get('is_sorted', False):
            with st.expander("📊 ดูตารางข้อมูลที่จัดเรียงแล้ว", expanded=True):
                df_sorted = pd.DataFrame(st.session_state.sorted_data)[['date', 'price']]
                df_sorted.columns = ['วันที่', 'ราคา (บาท)']
                st.dataframe(df_sorted, use_container_width=True)

        st.markdown("**🔍 ค้นหาราคา (Jump Search - ค้นหาแบบใกล้เคียง)**")
        target_input = st.text_input("ป้อนราคาเป้าหมาย (ใส่ค่าประมาณได้ เช่น 2000000):")
        if st.button("🚀 ค้นหา"):
            if not st.session_state.get('is_sorted', False): 
                st.error("⚠️ ต้องกดปุ่ม 'จัดเรียงราคา' ด้านบนก่อนครับ!")
            elif not target_input.replace(",", "").isdigit(): 
                st.warning("⚠️ กรุณาพิมพ์เฉพาะตัวเลข")
            else:
                target = int(target_input.replace(",", ""))
                res = jump_search_closest(st.session_state.sorted_data, target)
                if res: st.success(f"🎯 **เจอแล้ว!** ราคาที่ใกล้เคียง **{target:,}** ที่สุดคือ **{res['price']:,} บาท** (วันที่ {res['date']})")
                else: st.error("❌ ไม่พบข้อมูล")

    # --- TAB 4: ประวัติ ---
    with tab4:
        if st.session_state.trade_history:
            st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
        else:
            st.write("ยังไม่มีประวัติการทำรายการใดๆ")