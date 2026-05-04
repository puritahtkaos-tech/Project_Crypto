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
# 1. ตั้งค่า AI
# ==========================================
try:
    API_KEY = st.secrets["GEMINI_API_KEY"] # ใส่ API KEY ใน st.secrets
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
        "crypto_wallet": {
            "BTC-USD": 0.0, "ETH-USD": 0.0, "DOGE-USD": 0.0,
            "SOL-USD": 0.0, "ADA-USD": 0.0, "XRP-USD": 0.0, "BNB-USD": 0.0
        },
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
# 3. Algorithm (Sorting & Searching แบบใหม่ หาค่าใกล้เคียงได้!)
# ==========================================
def partition(arr, low, high):
    pivot_value = arr[high]['price']
    i = low - 1
    for j in range(low, high):
        if arr[j]['price'] <= pivot_value: # เรียงจากน้อยไปมาก
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1

def random_quick_sort(arr, low, high):
    if low < high:
        pi = partition(arr, low, high)
        random_quick_sort(arr, low, pi - 1)
        random_quick_sort(arr, pi + 1, high)

# อัปเกรด Jump Search ให้หา "ค่าที่ใกล้เคียงที่สุด" แทนการหาแบบเป๊ะๆ
def jump_search_closest(arr, target_price):
    n = len(arr)
    if n == 0: return None
    
    step = int(math.sqrt(n))
    prev = 0
    
    # กระโดดหาช่วงข้อมูล
    while prev < n and arr[min(step, n) - 1]['price'] < target_price:
        prev = step
        step += int(math.sqrt(n))
        if prev >= n: 
            return arr[-1] # ถ้าค้นหาตัวเลขที่มากกว่าราคาสูงสุด ให้คืนค่าราคาสูงสุดไปเลย
            
    # ค้นหาแบบเส้นตรงในบล็อกที่เจอ
    while prev < min(step, n) and arr[prev]['price'] < target_price:
        prev += 1
        
    # เทียบหาค่าที่ใกล้เคียงที่สุด (ระหว่างตัวที่มากกว่า กับตัวที่น้อยกว่า)
    if prev == n: return arr[-1]
    if prev == 0: return arr[0]
    
    diff1 = abs(arr[prev]['price'] - target_price)
    diff2 = abs(arr[prev-1]['price'] - target_price)
    
    if diff1 <= diff2:
        return arr[prev]
    else:
        return arr[prev-1]

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
        background-color: #1a1c24;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        max-width: 450px;
        margin: auto;
    }
    .social-btn { margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'

# ==========================================
# 5. หน้า Login / Register (แบบไม่มีรูป แบรนด์เนมเท่ๆ)
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
                
            st.markdown("<hr><p style='text-align: center; color: #888;'>หรือเข้าสู่ระบบด้วย</p>", unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.button("🔵 FB", use_container_width=True)
            with c2: st.button("🟢 Line", use_container_width=True)
            with c3: st.button("👾 Discord", use_container_width=True)
            with c4: st.button("🔴 Google", use_container_width=True)
        
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
# 6. ส่วนหน้าหลักแอป (Dashboard)
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
    tab1, tab2, tab3, tab4 = st.tabs(["📊 ตลาด & ซื้อขาย", "💼 พอร์ตฟอลิโอ", "🤖 AI & ระบบค้นหา", "📜 ประวัติรายการ"])
    latest_price = st.session_state.raw_data[-1]['price']

    # --- TAB 1: ตลาด ---
    with tab1:
        df = pd.DataFrame(st.session_state.raw_data)
        fig = go.Figure(data=[go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['price'])])
        fig.update_layout(title=f"กราฟราคา {selected_coin} ({selected_tf} ย้อนหลัง)", xaxis_title="วันที่", yaxis_title="ราคา (บาท)", template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.info(f"💵 เงินสดพร้อมเทรด: {st.session_state.wallet_thb:,.2f} บาท")
            buy_amt = st.number_input("ยอดเงินที่ต้องการซื้อ (บาท)", min_value=0.0, step=1000.0)
            if st.button("🟢 ซื้อเหรียญ", use_container_width=True):
                if buy_amt > 0 and buy_amt <= st.session_state.wallet_thb:
                    qty = buy_amt / latest_price
                    st.session_state.wallet_thb -= buy_amt
                    st.session_state.crypto_wallet[current_ticker] += qty
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "🟢 ซื้อ", "เหรียญ": selected_coin, "ปริมาณ": f"{qty:.6f}", "ราคา": f"{latest_price:,.0f}", "มูลค่า": f"{buy_amt:,.2f}"})
                    sync_data(); st.success("ซื้อสำเร็จ!"); st.rerun()
                else: st.error("เงินไม่พอ!")

        with col2:
            st.warning(f"🪙 เหรียญที่มี: {st.session_state.crypto_wallet[current_ticker]:.6f} เหรียญ")
            sell_qty = st.number_input("จำนวนที่ต้องการขาย", min_value=0.0, step=0.001, format="%.6f")
            if st.button("🔴 ขายเหรียญ", use_container_width=True):
                if sell_qty > 0 and sell_qty <= st.session_state.crypto_wallet[current_ticker]:
                    money = sell_qty * latest_price
                    st.session_state.crypto_wallet[current_ticker] -= sell_qty
                    st.session_state.wallet_thb += money
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "🔴 ขาย", "เหรียญ": selected_coin, "ปริมาณ": f"{sell_qty:.6f}", "ราคา": f"{latest_price:,.0f}", "มูลค่า": f"{money:,.2f}"})
                    sync_data(); st.success("ขายสำเร็จ!"); st.rerun()
                else: st.error("เหรียญไม่พอ!")

    # --- TAB 2: พอร์ตโฟลิโอ ---
    with tab2:
        st.subheader("💼 สรุปกระเป๋าเงินของคุณ")
        total_crypto_value = 0
        portfolio_data = []
        
        for coin_name, ticker in coin_dict.items():
            amount = st.session_state.crypto_wallet.get(ticker, 0)
            if amount > 0:
                est_value = amount * latest_price if ticker == current_ticker else 0 
                portfolio_data.append({"เหรียญ": coin_name, "จำนวนที่มี": amount, "มูลค่าประเมิน (บาท)": f"{est_value:,.2f}" if est_value else "กดดูเหรียญเพื่อดูมูลค่า"})
                total_crypto_value += est_value
                
        col_a, col_b = st.columns(2)
        col_a.metric("เงินสดทั้งหมด (THB)", f"{st.session_state.wallet_thb:,.2f} ฿")
        col_b.metric("มูลค่าคริปโตที่เปิดดูอยู่", f"{total_crypto_value:,.2f} ฿")
        
        if portfolio_data: st.table(pd.DataFrame(portfolio_data))
        else: st.info("ยังไม่มีเหรียญในกระเป๋า เริ่มต้นเทรดกันเลย!")
            
        st.markdown("---")
        with st.expander("💸 ระบบ ฝาก-ถอน เงินสด"):
            c1, c2 = st.columns(2)
            with c1:
                d_amt = st.number_input("จำนวนเงินฝาก", min_value=0.0)
                if st.button("💵 ฝากเงิน"):
                    st.session_state.wallet_thb += d_amt
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "💵 ฝาก", "เหรียญ": "THB", "ปริมาณ": "-", "ราคา": "-", "มูลค่า": f"{d_amt:,.2f}"})
                    sync_data(); st.rerun()
            with c2:
                w_amt = st.number_input("จำนวนเงินถอน", min_value=0.0)
                if st.button("🏧 ถอนเงิน"):
                    if w_amt <= st.session_state.wallet_thb:
                        st.session_state.wallet_thb -= w_amt
                        st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"), "ประเภท": "🏧 ถอน", "เหรียญ": "THB", "ปริมาณ": "-", "ราคา": "-", "มูลค่า": f"-{w_amt:,.2f}"})
                        sync_data(); st.rerun()
                    else: st.error("เงินไม่พอถอน!")

    # --- TAB 3: AI & อัลกอริทึม (อัปเดตให้โชว์ตารางแล้ว!) ---
    with tab3:
        st.subheader("🤖 ให้ AI ช่วยวิเคราะห์ (Gemini)")
        if st.button("✨ กดเพื่อวิเคราะห์แนวโน้ม"):
            if ai_ready:
                prices = [d['price'] for d in st.session_state.raw_data[-14:]] 
                prompt = f"วิเคราะห์ราคา {selected_coin} จากข้อมูล 14 วันล่าสุดนี้: {prices} และสรุปสั้นๆ ว่าควรทำอย่างไร"
                try:
                    response = client.models.generate_content(model=AI_MODEL, contents=prompt)
                    st.info(response.text)
                except Exception as e:
                    st.error("AI อาจทำงานหนักไป ลองใหม่อีกครั้งครับ")
            else: st.error("⚠️ รบกวนตรวจสอบ API KEY ในคอมพิวเตอร์ของคุณ")

        st.markdown("---")
        st.subheader("📉 ค้นหาและเรียงลำดับราคา")
        
        # ส่วนแสดงผลจัดเรียง
        if st.button("1. จัดเรียงราคา (Quick Sort - จากน้อยไปมาก)"):
            random_quick_sort(st.session_state.sorted_data, 0, len(st.session_state.sorted_data)-1)
            st.session_state.is_sorted = True
            st.success("✅ จัดเรียงข้อมูลจาก น้อยไปมาก เสร็จสิ้น! ดูผลลัพธ์ด้านล่างได้เลยครับ")
        
        # เพิ่มการแสดงผลตารางตรงนี้!
        if st.session_state.get('is_sorted', False):
            with st.expander("📊 ดูตารางข้อมูลที่จัดเรียงแล้ว", expanded=True):
                # แสดงแค่คอลัมน์ วันที่ กับ ราคา ให้ดูง่ายๆ
                df_sorted = pd.DataFrame(st.session_state.sorted_data)[['date', 'price']]
                df_sorted.columns = ['วันที่', 'ราคา (บาท)']
                st.dataframe(df_sorted, use_container_width=True)

        st.markdown("---")
        # ส่วนค้นหาแบบใกล้เคียง
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
                if res: 
                    st.success(f"🎯 **เจอแล้ว!** ราคาที่ใกล้เคียง **{target:,}** ที่สุดคือ **{res['price']:,} บาท** (พบในวันที่ {res['date']})")
                else: 
                    st.error("❌ ไม่พบข้อมูล")

    # --- TAB 4: ประวัติ ---
    with tab4:
        if st.session_state.trade_history:
            st.table(pd.DataFrame(st.session_state.trade_history).iloc[::-1])
        else:
            st.write("ยังไม่มีประวัติการทำรายการใดๆ")

else:
    st.info("👈 เลือกเหรียญและระยะเวลาทางแถบเมนูด้านซ้าย แล้วกดปุ่ม 'โหลดข้อมูล' เพื่อเริ่มต้นใช้งาน!")