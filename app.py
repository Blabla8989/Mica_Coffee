import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. CẤU HÌNH MENU ---
MENU = {
    "Cà phê đen": 15,
    "Cà phê sữa": 20,
    "Bạc sỉu": 25,
    "Cà phê sữa tươi": 25,
    "Cà phê muối": 25,
    "Matcha latte": 30,
    "Matcha latte kem muối": 35,
    "Nước suối": 10,
    "Bò cụng Thái": 20,
    "Nước ngọt có ga": 15,
    "Cacao latte": 20,
    "Cacao latte kem muối": 25,
    "Cam vắt": 20,
    "Soda chanh": 20,
    "Chanh muối": 15,
    "Chanh đá": 15,
    "Đá me": 15,
    "Lipton (nóng/đá)": 15,
    "Trà tắc": 15,
    "Khác (Tự nhập)": 0
}

DB_FILE = 'mica_coffee.db'

# --- 2. XỬ LÝ DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_amount REAL,
            note TEXT,
            payment_method TEXT, 
            is_debt INTEGER DEFAULT 0,
            is_paid INTEGER DEFAULT 1,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            item_name TEXT,
            quantity INTEGER,
            price REAL,
            total REAL,
            FOREIGN KEY(order_id) REFERENCES orders(order_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            amount REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_order(cart_items, note, payment_method, is_debt):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    total_amount = sum(item['total'] for item in cart_items)
    is_paid = 0 if is_debt else 1
    
    final_payment_method = "Nợ" if is_debt else payment_method
    
    # --- SỬA LỖI THỜI GIAN: Lấy giờ hiện tại của máy tính ---
    now_vn = datetime.now() 
    
    c.execute('''
        INSERT INTO orders (total_amount, note, payment_method, is_debt, is_paid, timestamp) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (total_amount, note, final_payment_method, 1 if is_debt else 0, is_paid, now_vn))
    
    new_order_id = c.lastrowid
    for item in cart_items:
        c.execute('INSERT INTO order_items (order_id, item_name, quantity, price, total) VALUES (?, ?, ?, ?, ?)',
                  (new_order_id, item['name'], item['qty'], item['price'], item['total']))
    conn.commit()
    conn.close()

def save_expense(desc, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # --- SỬA LỖI THỜI GIAN ---
    now_vn = datetime.now()
    
    c.execute('INSERT INTO expenses (description, amount, timestamp) VALUES (?, ?, ?)', (desc, amount, now_vn))
    conn.commit()
    conn.close()

def pay_debt(order_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE orders SET is_paid = 1, payment_method = 'Tiền mặt' WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()

def get_data():
    conn = sqlite3.connect(DB_FILE)
    orders = pd.read_sql_query("SELECT * FROM orders ORDER BY order_id DESC", conn)
    items = pd.read_sql_query("SELECT * FROM order_items", conn)
    expenses = pd.read_sql_query("SELECT * FROM expenses ORDER BY id DESC", conn)
    conn.close()
    
    # Chuyển đổi chuỗi thời gian sang dạng datetime chuẩn
    if not orders.empty:
        orders['timestamp'] = pd.to_datetime(orders['timestamp'])
        orders['date'] = orders['timestamp'].dt.date
        orders['month'] = orders['timestamp'].dt.month
        orders['year'] = orders['timestamp'].dt.year
    
    if not expenses.empty:
        expenses['timestamp'] = pd.to_datetime(expenses['timestamp'])
        expenses['date'] = expenses['timestamp'].dt.date
        
    return orders, items, expenses

# --- 3. GIAO DIỆN CHÍNH ---
if 'cart' not in st.session_state:
    st.session_state.cart = []

st.set_page_config(page_title="MICA Quản Lý", page_icon="☕", layout="wide")
init_db()

tab_pos, tab_expense, tab_report = st.tabs(["🛒 BÁN HÀNG", "💸 NHẬP CHI PHÍ", "📊 BÁO CÁO & SỔ NỢ"])

# ================= TAB 1: BÁN HÀNG =================
with tab_pos:
    col_input, col_cart = st.columns([1, 1.5])
    with col_input:
        st.info("👇 Chọn món")
        selected_item = st.selectbox("Menu:", list(MENU.keys()))
        if selected_item == "Khác (Tự nhập)":
            final_name = st.text_input("Tên món:")
            default_price = 0
        else:
            final_name = selected_item
            default_price = MENU[selected_item]
        
        c1, c2 = st.columns(2)
        with c1:
            price_k = st.number_input("Giá (nghìn):", value=default_price, step=1)
        with c2:
            qty = st.number_input("Số lượng:", min_value=1, value=1)
            
        if st.button("➕ Thêm vào giỏ", use_container_width=True):
            if price_k > 0:
                real_price = price_k * 1000
                st.session_state.cart.append({
                    "name": final_name, "qty": qty, 
                    "price": real_price, "total": real_price * qty
                })
                st.rerun()

    with col_cart:
        st.warning("🛒 Đơn hàng hiện tại")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df, use_container_width=True, hide_index=True,
                         column_config={"name":"Tên", "qty":"SL", "price":"Giá", "total":"Thành tiền"})
            total_bill = sum(item['total'] for item in st.session_state.cart)
            st.markdown(f"### Tổng tiền: :red[{total_bill:,.0f} đ]")
            st.markdown("---")
            
            note_input = st.text_area("📝 Ghi chú", height=68, placeholder="Bàn số, ít đá, mang về...")
            payment_method = st.radio("Hình thức thanh toán:", ["Tiền mặt", "Chuyển khoản"], horizontal=True)
            is_debt_checkbox = st.checkbox("GHI SỔ NỢ (Khách chưa trả tiền)")
            
            if is_debt_checkbox:
                st.error("⚠️ Đơn này sẽ KHÔNG tính vào doanh thu cho đến khi được trả.")
            
            b1, b2 = st.columns(2)
            if b1.button("Hủy đơn"):
                st.session_state.cart = []
                st.rerun()
            
            btn_label = "LƯU SỔ NỢ" if is_debt_checkbox else "THANH TOÁN XONG"
            btn_type = "secondary" if is_debt_checkbox else "primary"
            
            if b2.button(f"✅ {btn_label}", type=btn_type, use_container_width=True):
                save_order(st.session_state.cart, note_input, payment_method, is_debt_checkbox)
                st.session_state.cart = []
                if is_debt_checkbox: st.toast("Đã ghi nợ!")
                else: st.balloons(); st.success("Đã thanh toán!")
                st.rerun()
        else:
            st.write("Giỏ hàng trống.")

# ================= TAB 2: NHẬP CHI PHÍ =================
with tab_expense:
    st.header("Ghi chép chi phí")
    with st.form("expense_form", clear_on_submit=True):
        e_desc = st.text_input("Nội dung chi (VD: Mua đá, sữa...)")
        e_amount_k = st.number_input("Số tiền chi (nghìn đồng):", min_value=0, step=5)
        if st.form_submit_button("Lưu chi phí"):
            if e_amount_k > 0 and e_desc:
                save_expense(e_desc, e_amount_k * 1000)
                st.success(f"Đã lưu: {e_desc}")
                st.rerun()
            else:
                st.warning("Nhập thiếu thông tin!")
    
    _, _, expenses = get_data()
    if not expenses.empty:
        today = datetime.now().date()
        daily_ex = expenses[expenses['date'] == today]
        if not daily_ex.empty:
            st.subheader("Chi phí hôm nay")
            st.dataframe(daily_ex[['timestamp', 'description', 'amount']], hide_index=True, use_container_width=True,
                         column_config={"timestamp": st.column_config.DatetimeColumn("Giờ", format="H:mm"), "amount": st.column_config.NumberColumn("Tiền", format="%d đ")})

# ================= TAB 3: BÁO CÁO & SỔ NỢ =================
with tab_report:
    orders, items, expenses = get_data()
    
    if orders.empty:
        st.info("Chưa có dữ liệu bán hàng.")
    else:
        today = datetime.now().date()
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # --- PHẦN 1: CHỈ SỐ HÔM NAY ---
        st.subheader(f"📊 Kết quả Hôm nay ({today.strftime('%d/%m')})")
        
        daily_orders = orders[orders['date'] == today]
        
        # 1. Doanh thu THỰC (Chỉ tính đơn đã trả tiền)
        paid_orders = daily_orders[daily_orders['is_paid'] == 1]
        rev_today = paid_orders['total_amount'].sum()
        
        # 2. Chi tiết Tiền mặt vs Chuyển khoản
        cash_revenue = paid_orders[paid_orders['payment_method'] == 'Tiền mặt']['total_amount'].sum()
        transfer_revenue = paid_orders[paid_orders['payment_method'] == 'Chuyển khoản']['total_amount'].sum()
        
        # 3. Nợ phát sinh
        debt_orders = daily_orders[daily_orders['is_paid'] == 0]
        debt_today = debt_orders['total_amount'].sum()
        
        # 4. Chi phí
        if not expenses.empty:
            daily_expenses = expenses[expenses['date'] == today]
            cost_today = daily_expenses['amount'].sum()
        else:
            cost_today = 0
            
        net_profit = rev_today - cost_today
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("DOANH THU (Đã thu)", f"{rev_today:,.0f} đ")
        m2.metric("Chi phí", f"{cost_today:,.0f} đ", delta_color="inverse")
        m3.metric("LÃI RÒNG", f"{net_profit:,.0f} đ")
        m4.metric("Nợ chưa thu (Hôm nay)", f"{debt_today:,.0f} đ", delta_color="off")
        
        st.info(f"💰 **CHI TIẾT TIỀN VỀ:** Tiền mặt: **{cash_revenue:,.0f} đ** | Chuyển khoản: **{transfer_revenue:,.0f} đ**")
        
        st.divider()

        # --- PHẦN 2: TAB CON ---
        sub_tab1, sub_tab2 = st.tabs(["📝 Danh sách đơn & Nợ", "📅 Thống kê Tháng"])

        with sub_tab1:
            filter_status = st.radio("Lọc đơn:", ["Tất cả", "Tiền mặt", "Chuyển khoản", "Nợ chưa trả"], horizontal=True)
            
            if filter_status == "Nợ chưa trả":
                view_orders = daily_orders[daily_orders['is_paid'] == 0]
            elif filter_status == "Tiền mặt":
                view_orders = daily_orders[(daily_orders['is_paid'] == 1) & (daily_orders['payment_method'] == 'Tiền mặt')]
            elif filter_status == "Chuyển khoản":
                view_orders = daily_orders[(daily_orders['is_paid'] == 1) & (daily_orders['payment_method'] == 'Chuyển khoản')]
            else:
                view_orders = daily_orders

            if view_orders.empty:
                st.info("Không có đơn hàng nào.")
            else:
                view_orders = view_orders.sort_values('order_id', ascending=False)
                for i, row in view_orders.iterrows():
                    o_id = row['order_id']
                    is_debt = row['is_debt'] == 1
                    is_paid = row['is_paid'] == 1
                    pay_method = row['payment_method']
                    note_txt = f" | 📝 {row['note']}" if row['note'] else ""
                    
                    if is_debt and not is_paid:
                        status_icon = "🔴 NỢ"
                        display_amount = f"{row['total_amount']:,.0f} đ (Chưa tính DT)"
                    elif pay_method == 'Chuyển khoản':
                        status_icon = "🏦 CK"
                        display_amount = f"{row['total_amount']:,.0f} đ"
                    else:
                        status_icon = "💵 TM"
                        display_amount = f"{row['total_amount']:,.0f} đ"

                    # Format giờ hiển thị
                    time_str = row['timestamp'].strftime('%H:%M')

                    expander_label = f"#{o_id} | {time_str} | {display_amount} | {status_icon}{note_txt}"
                    
                    with st.expander(expander_label):
                        sub_items = items[items['order_id'] == o_id]
                        st.dataframe(sub_items[['item_name', 'quantity', 'total']], 
                                   hide_index=True, use_container_width=True,
                                   column_config={"item_name":"Món", "quantity":"SL", "total": st.column_config.NumberColumn("Tiền", format="%d đ")})
                        
                        if is_debt and not is_paid:
                            st.warning("Đơn này chưa tính tiền vào doanh thu.")
                            if st.button(f"💸 Khách trả nợ đơn #{o_id}"):
                                pay_debt(o_id)
                                st.success("Đã cập nhật!")
                                st.rerun()

        with sub_tab2:
            monthly_orders = orders[(orders['month'] == current_month) & (orders['year'] == current_year)]
            
            if monthly_orders.empty:
                st.info(f"Tháng {current_month} chưa có dữ liệu.")
            else:
                monthly_paid = monthly_orders[monthly_orders['is_paid'] == 1]
                m_rev = monthly_paid['total_amount'].sum()
                m_count = len(monthly_paid)
                m_debt = monthly_orders[monthly_orders['is_paid'] == 0]['total_amount'].sum()
                
                c1, c2, c3 = st.columns(3)
                c1.metric(f"Doanh thu Thực thu T{current_month}", f"{m_rev:,.0f} đ")
                c2.metric("Số đơn đã bán", f"{m_count} đơn")
                c3.metric("Nợ treo chưa thu", f"{m_debt:,.0f} đ", delta_color="inverse")
                
                st.subheader("Biểu đồ doanh thu thực tế theo ngày")
                chart_data = monthly_paid.groupby('date')['total_amount'].sum().reset_index()
                chart_data.columns = ['Ngày', 'Doanh Thu']
                st.bar_chart(chart_data, x='Ngày', y='Doanh Thu', color='#4CAF50')