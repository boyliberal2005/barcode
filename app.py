import streamlit as st
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import pandas as pd
import pytz
import io
import base64

# Cấu hình trang
st.set_page_config(
    page_title="Quét Barcode",
    page_icon="📦",
    layout="centered"
)

# CSS tùy chỉnh - Tối giản
st.markdown("""
    <style>
    .main {background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);}
    .stButton>button {width: 100%; background-color: #4CAF50; color: white; height: 3em; border-radius: 10px; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# Khởi tạo session state tối giản
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'scanned_product' not in st.session_state:
    st.session_state.scanned_product = None
if 'barcode_data' not in st.session_state:
    st.session_state.barcode_data = None

# Thông tin đăng nhập
HARDCODED_USER = "admin@123"
HARDCODED_PASS = "A@bcde6789"

# ==================== CACHE FUNCTIONS ====================

@st.cache_resource
def get_google_sheet_client():
    """Cache Google Sheets client - chỉ kết nối 1 lần"""
    try:
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scope
            )
        else:
            creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Lỗi kết nối: {e}")
        return None

@st.cache_data(ttl=300)  # Cache 5 phút
def get_product_list(_client, sheet_name):
    """Cache danh sách sản phẩm - tránh load lại liên tục"""
    try:
        spreadsheet = _client.open(sheet_name)
        sheet = spreadsheet.worksheet("Product_List")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Barcode'] = df['Barcode'].astype(str).str.strip()
        return df
    except gspread.exceptions.WorksheetNotFound:
        return pd.DataFrame(columns=['Barcode', 'Tên SP', 'Thương hiệu'])
    except Exception as e:
        st.error(f"Lỗi load Product_List: {e}")
        return pd.DataFrame(columns=['Barcode', 'Tên SP', 'Thương hiệu'])

def get_worksheet(_client, sheet_name, worksheet_name):
    """Lấy worksheet, tạo nếu chưa có"""
    try:
        spreadsheet = _client.open(sheet_name)
        try:
            return spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=10)
            if worksheet_name == "Barcode_Data":
                sheet.append_row(["Barcode", "Tên SP", "Thương hiệu", "Số lượng", "Đơn vị", "Thời gian"])
            elif worksheet_name == "Product_List":
                sheet.append_row(["Barcode", "Tên SP", "Thương hiệu"])
            return sheet
    except Exception as e:
        st.error(f"Lỗi worksheet: {e}")
        return None

# ==================== LAZY IMPORT ====================

def scan_barcode_pyzbar(image):
    """Lazy import pyzbar và cv2 chỉ khi cần"""
    try:
        import cv2
        import numpy as np
        from pyzbar import pyzbar
        
        img_array = np.array(image)
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        barcodes = pyzbar.decode(gray)
        if barcodes:
            return barcodes[0].data.decode('utf-8')
        
        # Thử với tiền xử lý nếu không quét được
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        barcodes = pyzbar.decode(gray)
        if barcodes:
            return barcodes[0].data.decode('utf-8')
        
        return None
    except Exception as e:
        return None

def scan_barcode_gemini(image):
    """Lazy import Gemini chỉ khi pyzbar thất bại"""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key="AIzaSyA52qNG0pm7JD9E5Jhp_GhcwjdgXJd8sXQ")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([
            "Read the barcode number only. Return just the digits (e.g., '8935049502142'). If no barcode, return 'None'.",
            {"mime_type": "image/png", "data": img_bytes}
        ])
        barcode_text = response.text.strip()
        if barcode_text.lower() != 'none':
            return barcode_text
        return None
    except Exception as e:
        return None

def scan_barcode(image):
    """Quét barcode: pyzbar trước, Gemini fallback"""
    result = scan_barcode_pyzbar(image)
    if result:
        return result
    with st.spinner("Dùng AI để quét..."):
        return scan_barcode_gemini(image)

# ==================== CORE FUNCTIONS ====================

def lookup_product_fast(barcode, df):
    """Tra cứu nhanh từ DataFrame đã cache"""
    barcode = str(barcode).strip()
    match = df[df['Barcode'] == barcode]
    if not match.empty:
        return {
            'name': match.iloc[0]['Tên SP'],
            'brand': match.iloc[0]['Thương hiệu']
        }
    return {'name': 'Sản phẩm không xác định', 'brand': 'N/A'}

def update_product(client, sheet_name, barcode, product_name, brand):
    """Cập nhật sản phẩm và clear cache"""
    sheet = get_worksheet(client, sheet_name, "Product_List")
    if not sheet:
        return False
    try:
        sheet.append_row([str(barcode).strip(), product_name, brand])
        # Clear cache để load lại data mới
        get_product_list.clear()
        return True
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return False

def send_to_sheet(client, sheet_name, data):
    """Gửi dữ liệu quét"""
    sheet = get_worksheet(client, sheet_name, "Barcode_Data")
    if not sheet:
        return False
    try:
        row = [
            data['barcode'], data['product_name'], data['brand'],
            data['quantity'], data['unit'], data['timestamp']
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Lỗi: {e}")
        return False

# ==================== AUTH ====================

def check_login():
    """Kiểm tra query params cho login"""
    logged_in = st.query_params.get("logged_in", None)
    if logged_in:
        try:
            return base64.b64decode(logged_in).decode("utf-8") == "true"
        except:
            return False
    return False

def set_logged_in():
    st.query_params["logged_in"] = base64.b64encode(b"true").decode("utf-8")
    st.session_state.logged_in = True

def logout():
    if "logged_in" in st.query_params:
        del st.query_params["logged_in"]
    st.session_state.logged_in = False
    st.session_state.scanned_product = None
    st.session_state.barcode_data = None
    st.rerun()

# ==================== MAIN APP ====================

# Kiểm tra login từ query params
if not st.session_state.logged_in:
    st.session_state.logged_in = check_login()

# Form đăng nhập
if not st.session_state.logged_in:
    st.title("🔒 Đăng Nhập")
    with st.form("login_form"):
        username = st.text_input("Tên người dùng")
        password = st.text_input("Mật khẩu", type="password")
        submit = st.form_submit_button("Đăng nhập", type="primary")
        
        if submit:
            if username == HARDCODED_USER and password == HARDCODED_PASS:
                set_logged_in()
                st.success("✅ Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("❌ Sai thông tin đăng nhập!")
    st.stop()

# ==================== APP CHÍNH ====================

st.title("📦 Viva Star Coffee - Kiểm Hàng")
st.markdown("---")

# Nút đăng xuất
if st.button("🚪 Đăng xuất"):
    logout()

# Sidebar
with st.sidebar:
    st.header("⚙️ Cấu hình")
    sheet_name = st.text_input("Tên Google Sheet", value="Barcode_Data")

# Kết nối Google Sheets (chỉ 1 lần)
client = get_google_sheet_client()
if not client:
    st.error("❌ Không thể kết nối Google Sheets!")
    st.stop()

# Load Product_List (cache 5 phút)
product_df = get_product_list(client, sheet_name)

# ==================== TABS ====================

tab1, tab2, tab3 = st.tabs(["📸 Quét Barcode", "📊 Xem Dữ Liệu", "🛠 Cập nhật Barcode"])

# ===== TAB 1: QUÉT BARCODE =====
with tab1:
    scan_method = st.radio(
        "Phương thức quét:",
        ["📷 Chụp ảnh", "📁 Upload ảnh", "⌨️ Nhập thủ công"],
        horizontal=True
    )

    image = None
    barcode = None

    if scan_method == "📷 Chụp ảnh":
        camera_image = st.camera_input("Chụp ảnh barcode")
        if camera_image:
            image = Image.open(camera_image)
            st.image(image, caption="Ảnh đã chụp", use_column_width=True)
            with st.spinner("Đang quét..."):
                barcode = scan_barcode(image)

    elif scan_method == "📁 Upload ảnh":
        uploaded_file = st.file_uploader("Chọn ảnh", type=['jpg', 'jpeg', 'png'])
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Ảnh đã upload", use_column_width=True)
            with st.spinner("Đang quét..."):
                barcode = scan_barcode(image)

    else:  # Nhập thủ công
        manual_barcode = st.text_input("Nhập mã barcode:", max_chars=20)
        if st.button("🔍 Tra cứu"):
            if manual_barcode:
                barcode = manual_barcode

    # Xử lý barcode vừa quét
    if barcode:
        st.session_state.barcode_data = barcode
        st.session_state.scanned_product = lookup_product_fast(barcode, product_df)
        st.success(f"✅ Barcode: {barcode}")
        
        if st.session_state.scanned_product['name'] == 'Sản phẩm không xác định':
            st.warning(f"⚠️ Barcode {barcode} chưa có. Vui lòng thêm trong tab 'Cập nhật Barcode'.")

    # Form nhập liệu nếu đã có sản phẩm
    if st.session_state.scanned_product and st.session_state.scanned_product['name'] != 'Sản phẩm không xác định':
        st.markdown("---")
        st.subheader("📦 Thông tin sản phẩm")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tên", st.session_state.scanned_product['name'])
        with col2:
            st.metric("Thương hiệu", st.session_state.scanned_product['brand'])
        
        st.info(f"🔢 Barcode: **{st.session_state.barcode_data}**")
        
        st.markdown("---")
        col1, col2 = st.columns([2, 1])
        with col1:
            quantity = st.number_input("Số lượng:", min_value=0.0, step=0.1, format="%.2f")
        with col2:
            unit = st.selectbox("Đơn vị:", ["ml", "L", "g", "kg", "cái", "hộp", "chai"])
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Quét lại", use_container_width=True):
                st.session_state.scanned_product = None
                st.session_state.barcode_data = None
                st.rerun()
        with col2:
            if st.button("📤 Gửi", type="primary", use_container_width=True):
                if quantity > 0:
                    data = {
                        'barcode': st.session_state.barcode_data,
                        'product_name': st.session_state.scanned_product['name'],
                        'brand': st.session_state.scanned_product['brand'],
                        'quantity': quantity,
                        'unit': unit,
                        'timestamp': datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d %H:%M:%S")
                    }
                    if send_to_sheet(client, sheet_name, data):
                        st.success("✅ Đã gửi!")
                        st.balloons()
                        st.session_state.scanned_product = None
                        st.session_state.barcode_data = None
                        st.rerun()
                else:
                    st.warning("⚠️ Nhập số lượng > 0!")

# ===== TAB 2: XEM DỮ LIỆU =====
with tab2:
    st.subheader("📊 Dữ liệu đã lưu")
    
    today = date.today()
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Từ ngày:", value=today)
    with col2:
        end_date = st.date_input("Đến ngày:", value=today)
    
    if st.button("🔄 Tải dữ liệu"):
        sheet = get_worksheet(client, sheet_name, "Barcode_Data")
        if sheet:
            with st.spinner("Đang tải..."):
                data = sheet.get_all_records()
                if data:
                    df = pd.DataFrame(data)
                    df['Thời gian'] = pd.to_datetime(df['Thời gian'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                    df = df.dropna(subset=['Thời gian'])
                    
                    mask = (df['Thời gian'].dt.date >= start_date) & (df['Thời gian'].dt.date <= end_date)
                    filtered_df = df[mask]
                    
                    if not filtered_df.empty:
                        st.dataframe(filtered_df, use_container_width=True)
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Tổng bản ghi", len(filtered_df))
                        with col2:
                            st.metric("Số sản phẩm", filtered_df['Barcode'].nunique())
                        with col3:
                            st.metric("Tổng SL", f"{filtered_df['Số lượng'].sum():.2f}")
                        
                        csv = filtered_df.to_csv(index=False)
                        st.download_button(
                            "📥 Tải CSV",
                            csv,
                            f"data_{start_date}_to_{end_date}.csv",
                            "text/csv"
                        )
                    else:
                        st.info("📭 Không có dữ liệu!")
                else:
                    st.info("📭 Chưa có dữ liệu!")

# ===== TAB 3: CẬP NHẬT BARCODE =====
with tab3:
    st.subheader("🛠 Cập nhật Barcode")
    
    barcode_input = st.text_input("Mã Barcode", max_chars=20)
    product_name = st.text_input("Tên sản phẩm")
    brand = st.text_input("Thương hiệu")
    
    if st.button("💾 Lưu", type="primary"):
        if barcode_input and product_name and brand:
            if update_product(client, sheet_name, barcode_input, product_name, brand):
                st.success(f"✅ Đã lưu: {barcode_input}")
                st.balloons()
            else:
                st.error("❌ Lỗi!")
        else:
            st.warning("⚠️ Nhập đầy đủ thông tin!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>@2025 Viva Star Coffee</div>",
    unsafe_allow_html=True
)
