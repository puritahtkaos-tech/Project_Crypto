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
# 1. ตั้งค่า AI (ใส่ API Key ของคุณ)
# ==========================================
API_KEY = "AIzaSyA_zC5g9GJjrx52ywy_LjP_r8MGX5sO9pI" 

try:
    import google.generativeai as genai
    genai.configure(api_key=API_KEY)
    AI_MODEL = 'gemini-pro'
    ai_ready = True
except Exception as e:
    ai_ready = False

# ==========================================
# 1.1 ระบบ Users (ล็อกอิน/สมัคร)
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
    return True, "✅ สมัครสำเร็จ!"

def login_user(username, password):
    users = load_users()
    if username in users and users[username]["password"] == password:
        return True, users[username]
    return False, None

# ==========================================
# 2. Algorithm (Sorting & Searching) - ห้ามแก้ เพื่อคะแนน!
# ==========================================
def partition(arr, low, high):
    rand_pivot = random.randint(low, high)
    arr[rand_pivot], arr[high] = arr[high], arr[rand_pivot]
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

# อัปเกรด: ดึงข้อมูลแบบละเอียด (Open, High, Low, Close) ทำกราฟแท่งเทียน
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
            "price": int(row['Close'] * 35) # ใช้ Close เป็นราคาหลัก
        })
    return result

# ==========================================
# 3. ตั้งค่าหน้าเว็บ (UI/UX) & กระเป๋าเงิน
# ==========================================
st.set_page_config(page_title="Crypto Exchange Simulator", page_icon="🏦", layout="wide")

INITIAL_CAPITAL = 100000.0

# --- Session State สำหรับ Login ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# --- ฟังก์ชันโหลด/บันทึกข้อมูลผู้ใช้ ---
def load_user_data(username):
    users = load_users()
    if username in users:
        return users[username]
    return None

def save_user_data(username, user_data):
    users = load_users()
    users[username] = user_data
    save_users(users)

# ==========================================
# 4. หน้า Login / Register
# ==========================================
def show_auth_page():
    st.markdown("""
    <style>
    .auth-container {
        max-width: 400px;
        margin: 50px auto;
        padding: 30px;
        background: #1a1a2e;
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🔐 เข้าสู่ระบบ")
        input_username = st.text_input("ชื่อผู้ใช้", key="login_user_input")
        input_password = st.text_input("รหัสผ่าน", type="password", key="login_pass_input")
        if st.button("🚀 ลงชื่อเข้าใช้", use_container_width=True):
            success, result = login_user(input_username, input_password)
            if success:
                st.session_state.logged_in = True
                st.session_state.username = input_username
                user_data = load_user_data(input_username)
                st.session_state.wallet_thb = user_data["wallet_thb"]
                st.session_state.crypto_wallet = user_data["crypto_wallet"]
                st.session_state.trade_history = user_data["trade_history"]
                st.rerun()
            else:
                st.error("❌ ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    
    with col2:
        st.subheader("📝 สมัครสมาชิก")
        reg_user = st.text_input("ชื่อผู้ใช้ใหม่", key="reg_user_input")
        reg_pass = st.text_input("รหัสผ่าน", type="password", key="reg_pass_input")
        reg_confirm = st.text_input("ยืนยันรหัสผ่าน", type="password", key="reg_confirm_input")
        if st.button("✅ สมัคร", use_container_width=True):
            if reg_pass != reg_confirm:
                st.error("❌ รหัสผ่านไม่ตรงกัน")
            elif len(reg_user) < 3 or len(reg_pass) < 3:
                st.error("❌ ชื่อผู้ใช้และรหัสผ่านต้องมีอย่างน้อย 3 ตัวอักษร")
            else:
                success, msg = register_user(reg_user, reg_pass)
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

# ==========================================
# 5. เริ่มต้นแอป
# ==========================================
if not st.session_state.logged_in:
    show_auth_page()
    st.stop()

# --- แสดงชื่อผู้ใช้ & ปุ่ม Logout ---
with st.sidebar:
    st.markdown("---")
    st.markdown(f"👤 **ผู้ใช้:** `{st.session_state.username}`")
    if st.button("🚪 ออกจากระบบ", use_container_width=True):
        # บันทึกข้อมูลก่อนออก
        user_data = load_user_data(st.session_state.username)
        if user_data:
            user_data["wallet_thb"] = st.session_state.wallet_thb
            user_data["crypto_wallet"] = st.session_state.crypto_wallet
            user_data["trade_history"] = st.session_state.trade_history
            save_user_data(st.session_state.username, user_data)
        
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()
    
    st.markdown("---")
    st.subheader("1. เลือกข้อมูลตลาด")
    coin_dict = {"Bitcoin (BTC)": "BTC-USD", "Ethereum (ETH)": "ETH-USD", "Dogecoin (DOGE)": "DOGE-USD"}
    selected_coin = st.selectbox("เลือกเหรียญ:", list(coin_dict.keys()))
    current_ticker = coin_dict[selected_coin]
    
    if st.button("🔄 โหลดข้อมูล (30 วันล่าสุด)", use_container_width=True):
        with st.spinner("กำลังดึงข้อมูล..."):
            raw_data = fetch_real_crypto_data(current_ticker, 30)
            st.session_state.raw_data = raw_data
            st.session_state.sorted_data = [d.copy() for d in raw_data]
            st.success("✅ อัปเดตข้อมูลล่าสุดแล้ว!")
    
    st.markdown("---")
    if st.button("🔴 Reset พอร์ต (เริ่มใหม่)", use_container_width=True):
        st.session_state.wallet_thb = INITIAL_CAPITAL
        st.session_state.crypto_wallet = {"BTC-USD": 0.0, "ETH-USD": 0.0, "DOGE-USD": 0.0}
        st.session_state.trade_history = []
        # บันทึกลง database
        user_data = load_user_data(st.session_state.username)
        if user_data:
            user_data["wallet_thb"] = INITIAL_CAPITAL
            user_data["crypto_wallet"] = {"BTC-USD": 0.0, "ETH-USD": 0.0, "DOGE-USD": 0.0}
            user_data["trade_history"] = []
            save_user_data(st.session_state.username, user_data)
        st.rerun()

# --- หน้าจอหลัก ---
st.title("🏦 Crypto Exchange Simulator & AI")

if 'raw_data' in st.session_state:
    tab1, tab2, tab3 = st.tabs(["📊 Trading & Dashboard", "🤖 Algorithm & AI Analyst", "📜 History"])
    
    latest_price = st.session_state.raw_data[-1]['price']

    # =========================
    # แท็บ 1: หน้าเทรด กราฟแท่งเทียน และ P&L
    # =========================
    with tab1:
        col_g1, col_g2 = st.columns([2, 1])
        
        with col_g1:
            st.subheader(f"📈 กราฟแท่งเทียน (Candlestick) {selected_coin}")
            df_chart = pd.DataFrame(st.session_state.raw_data)
            df_chart['MA 5 Days'] = df_chart['price'].rolling(window=5).mean()
            
            # สร้างกราฟแท่งเทียนสุดโปร
            fig_candle = go.Figure(data=[go.Candlestick(x=df_chart['date'],
                            open=df_chart['open'], high=df_chart['high'],
                            low=df_chart['low'], close=df_chart['price'],
                            name="Candlestick")])
            fig_candle.add_trace(go.Scatter(x=df_chart['date'], y=df_chart['MA 5 Days'], opacity=0.7, line=dict(color='blue', width=2), name='MA 5 Days'))
            fig_candle.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=350, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig_candle, use_container_width=True)
            
        with col_g2:
            st.subheader("💼 สรุปพอร์ตการลงทุน")
            crypto_value = st.session_state.crypto_wallet[current_ticker] * latest_price
            thb_value = st.session_state.wallet_thb
            total_value = crypto_value + thb_value
            profit_loss = total_value - INITIAL_CAPITAL
            profit_percent = (profit_loss / INITIAL_CAPITAL) * 100
            
            # แสดงกำไร/ขาดทุน
            st.metric("📊 มูลค่าพอร์ตรวม (Net Worth)", f"{total_value:,.2f} ฿", f"{profit_percent:,.2f}% กำไร/ขาดทุน")
            
            df_pie = pd.DataFrame({"Assets": ["เงินสด (THB)", f"คริปโต"], "Value": [thb_value, crypto_value]})
            fig_pie = px.pie(df_pie, values='Value', names='Assets', hole=0.5, color_discrete_sequence=['#00CC96', '#636EFA'])
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200)
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("---")
        
        # ระบบซื้อขาย
        col_w1, col_w2, col_w3 = st.columns(3)

        col_w1.metric("💰 เงินสดพร้อมเทรด", f"{st.session_state.wallet_thb:,.2f} ฿")
        col_w2.metric(f"🪙 เหรียญ {selected_coin[:3]}", f"{st.session_state.crypto_wallet[current_ticker]:.6f}")
        col_w3.metric("📉 ราคาตลาดตอนนี้", f"{latest_price:,.2f} ฿/Coin")

        # --- ฝากเงิน/ถอนเงิน ---
        with st.expander("💸 ฝากเงิน / ถอนเงิน", expanded=False):
            tab_deposit, tab_withdraw = st.columns(2)
            with tab_deposit:
                deposit_amt = st.number_input("จำนวนเงินที่ต้องการฝาก (บาท)", min_value=0.0, step=1000.0, key="deposit_amt")
                if st.button("💵 ยืนยันฝากเงิน", key="deposit_btn"):
                    if deposit_amt > 0:
                        st.session_state.wallet_thb += deposit_amt
                        st.session_state.trade_history.append({
                            "เวลา": datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
                            "ประเภท": "💵 ฝากเงิน",
                            "เหรียญ": "THB",
                            "ปริมาณ": f"-",
                            "ราคา": f"-",
                            "มูลค่า (บาท)": f"{deposit_amt:,.2f}"
                        })
                        # update db
                        user_data = load_user_data(st.session_state.username)
                        if user_data:
                            user_data["wallet_thb"] = st.session_state.wallet_thb
                            user_data["trade_history"] = st.session_state.trade_history
                            save_user_data(st.session_state.username, user_data)
                        st.success(f"ฝากเงินสำเร็จ +{deposit_amt:,.2f} บาท")
                        st.rerun()
                    else:
                        st.warning("กรุณากรอกจำนวนเงินที่ถูกต้อง")
            with tab_withdraw:
                withdraw_amt = st.number_input("จำนวนเงินที่ต้องการถอน (บาท)", min_value=0.0, step=1000.0, key="withdraw_amt")
                if st.button("🏧 ยืนยันถอนเงิน", key="withdraw_btn"):
                    if withdraw_amt > 0 and withdraw_amt <= st.session_state.wallet_thb:
                        st.session_state.wallet_thb -= withdraw_amt
                        st.session_state.trade_history.append({
                            "เวลา": datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
                            "ประเภท": "🏧 ถอนเงิน",
                            "เหรียญ": "THB",
                            "ปริมาณ": f"-",
                            "ราคา": f"-",
                            "มูลค่า (บาท)": f"-{withdraw_amt:,.2f}"
                        })
                        # update db
                        user_data = load_user_data(st.session_state.username)
                        if user_data:
                            user_data["wallet_thb"] = st.session_state.wallet_thb
                            user_data["trade_history"] = st.session_state.trade_history
                            save_user_data(st.session_state.username, user_data)
                        st.success(f"ถอนเงินสำเร็จ -{withdraw_amt:,.2f} บาท")
                        st.rerun()
                    elif withdraw_amt > st.session_state.wallet_thb:
                        st.error("ยอดเงินไม่พอถอน!")
                    else:
                        st.warning("กรุณากรอกจำนวนเงินที่ถูกต้อง")

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.success("**🟢 ซื้อเหรียญ (Buy)**")
            buy_amount = st.number_input("จำนวนเงินที่ใช้ซื้อ (บาท):", min_value=0.0, step=1000.0)
            if st.button("🚀 ยืนยันการซื้อ", use_container_width=True, key="buy_btn"):
                if buy_amount > 0 and buy_amount <= st.session_state.wallet_thb:
                    coin_received = buy_amount / latest_price
                    st.session_state.wallet_thb -= buy_amount
                    st.session_state.crypto_wallet[current_ticker] += coin_received
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m %H:%M:%S"), "ประเภท": "🟢 ซื้อ", "เหรียญ": selected_coin, "ปริมาณ": f"{coin_received:.6f}", "ราคา": f"{latest_price:,.2f}", "มูลค่า (บาท)": f"{buy_amount:,.2f}"})
                    # บันทึกลง database
                    user_data = load_user_data(st.session_state.username)
                    if user_data:
                        user_data["wallet_thb"] = st.session_state.wallet_thb
                        user_data["crypto_wallet"] = st.session_state.crypto_wallet
                        user_data["trade_history"] = st.session_state.trade_history
                        save_user_data(st.session_state.username, user_data)
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ ยอดเงินไม่พอ")

        with col_t2:
            st.error("**🔴 ขายเหรียญ (Sell)**")
            sell_amount = st.number_input("จำนวนเหรียญที่ขาย:", min_value=0.0, step=0.0001, format="%.6f")
            if st.button("💥 ยืนยันการขาย", use_container_width=True, key="sell_btn"):
                if sell_amount > 0 and sell_amount <= st.session_state.crypto_wallet[current_ticker]:
                    thb_received = sell_amount * latest_price
                    st.session_state.crypto_wallet[current_ticker] -= sell_amount
                    st.session_state.wallet_thb += thb_received
                    st.session_state.trade_history.append({"เวลา": datetime.datetime.now().strftime("%d/%m %H:%M:%S"), "ประเภท": "🔴 ขาย", "เหรียญ": selected_coin, "ปริมาณ": f"{sell_amount:.6f}", "ราคา": f"{latest_price:,.2f}", "มูลค่า (บาท)": f"{thb_received:,.2f}"})
                    # บันทึกลง database
                    user_data = load_user_data(st.session_state.username)
                    if user_data:
                        user_data["wallet_thb"] = st.session_state.wallet_thb
                        user_data["crypto_wallet"] = st.session_state.crypto_wallet
                        user_data["trade_history"] = st.session_state.trade_history
                        save_user_data(st.session_state.username, user_data)
                    st.snow()
                    st.rerun()
                else:
                    st.error("❌ เหรียญไม่พอขาย")

    # =========================
    # แท็บ 2: Algorithm + AI Analyst
    # =========================
    with tab2:
        st.subheader("🧠 ผู้ช่วยวิเคราะห์ตลาด (AI Market Analyst)")
        if st.button("🤖 ให้ AI วิเคราะห์ว่าควร ซื้อ/ขาย/ถือ", use_container_width=True):
            if ai_ready and API_KEY != "ใส่_API_KEY_ของคุณที่นี่":
                with st.spinner("AI กำลังอ่านกราฟและสแกนเทรนด์..."):
                    try:
                        import google.generativeai as genai
                        prices_only = [d['price'] for d in st.session_state.raw_data]
                        prompt = f"คุณเป็นนักเทรดคริปโตระดับโลก ข้อมูลราคา {selected_coin} 30 วันย้อนหลังคือ (บาท): {prices_only} ราคาล่าสุดคือ {prices_only[-1]} จงวิเคราะห์แนวโน้ม 3 บรรทัด และสรุปตอนท้ายว่าตอนนี้ควร ซื้อ (Buy), ขาย (Sell), หรือ ถือ (Hold)"
                        model = genai.GenerativeModel(AI_MODEL)
                        response = model.generate_content(prompt)
                        st.info(response.text)
                    except Exception as e:
                        st.warning(f"⚠️ AI ขัดข้อง: {str(e)} กรุณาตรวจสอบ API Key หรืออินเทอร์เน็ต")
            else:
                st.error("⚠️ ยังไม่ได้ใส่ API Key หรือ API Key ไม่ถูกต้อง")
                
        st.markdown("---")
        
        col_algo1, col_algo2 = st.columns(2)
        with col_algo1:
            st.subheader("📉 คัดแยกข้อมูล (Quick Sort)")
            if st.button("เรียงราคา 'น้อยไปมาก'"):
                random_quick_sort(st.session_state.sorted_data, 0, len(st.session_state.sorted_data) - 1)
                st.session_state.is_sorted = True
                st.success("✅ เรียงเสร็จสิ้น!")
            
            if st.session_state.get('is_sorted', False):
                st.dataframe(pd.DataFrame(st.session_state.sorted_data)[['date', 'price']], height=250)
                
        with col_algo2:
            st.subheader("🔍 ค้นหาราคา (Jump Search)")
            target_input = st.text_input("ป้อนราคาเป้าหมายที่ต้องการค้นหา:")
            if st.button("🚀 ค้นหา"):
                if not st.session_state.get('is_sorted', False):
                    st.error("⚠️ ต้องกดปุ่ม 'เรียงราคา' ทางซ้ายมือก่อนครับ!")
                else:
                    target_input_clean = target_input.replace(",", "")
                    if not target_input_clean.isdigit():
                        st.warning("⚠️ กรุณาพิมพ์เฉพาะตัวเลข")
                    else:
                        target_price = int(target_input_clean)
                        result = jump_search(st.session_state.sorted_data, target_price)
                        if result:
                            st.success(f"🎯 **เจอแล้ว!** ราคา {target_price:,} บาท อยู่ในวันที่ {result['date']}")
                        else:
                            st.error(f"❌ **ไม่พบ** ราคา {target_price:,} บาท")

    # =========================
    # แท็บ 3: ประวัติการเทรด
    # =========================
    with tab3:
        st.subheader("📜 ประวัติการทำรายการ (Statement)")
        if len(st.session_state.trade_history) == 0:
            st.info("คุณยังไม่ได้ทำการซื้อขายใดๆ")
        else:
            df_history = pd.DataFrame(st.session_state.trade_history)
            st.dataframe(df_history.iloc[::-1], use_container_width=True, hide_index=True)

else:
    st.info("👈 กรุณากดปุ่ม **'โหลดข้อมูล'** ที่แผงควบคุมด้านซ้ายมือเพื่อเริ่มต้นระบบ")