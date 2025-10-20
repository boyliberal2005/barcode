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

# Khởi tạo session state
for key, default in {
    'logged_in': False,
    'scanned_product': None,
    'barcode_data': None,
    'last_image_hash': None,
    'product_cache': None,
    'client': None,
    'sheet_name': 'Barcode_Data'
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Thông tin đăng nhập
HARDCODED_USER = "admin@123"
HARDCODED_PASS = "A@bcde6789"

# ==================== LAZY CONNECTION ====================

def get_client():
    """Lazy load Google Sheets client"""
    if st.session_state.client is None:
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
            st.session_state.client = gspread.authorize(creds)
        except Exception as e:
            st.error(f"Lỗi kết nối: {e}")
            return None
    return st.session_state.client

def load_products():
    """Load products CHỈ 1 LẦN"""
    if st.session_state.product_cache is not None:
        return st.session_state.product_cache
    
    client = get_client()
    if not client:
        return pd.DataFrame(columns=['Barcode', 'Tên SP', 'Thương hiệu'])
    
    try:
        spreadsheet = client.open(st.session_state.sheet_name)
        sheet = spreadsheet.worksheet("Product_List")
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df['Barcode'] = df['Barcode'].astype(str).str.strip()
        st.session_state.product_cache = df
        return df
    except:
        df = pd.DataFrame(columns=['Barcode', 'Tên SP', 'Thương hiệu'])
        st.session_state.product_cache = df
        return df

# ==================== BARCODE SCAN ====================

def scan_barcode_gemini(image):
    """Quét barcode bằng Gemini AI"""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key="AIzaSyA52qNG0pm7JD9E5Jhp_GhcwjdgXJd8sXQ")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([
            "Read the barcode number only. Return just the digits. If no barcode, return 'None'.",
            {"mime_type": "image/png", "data": img_bytes}
        ])
        barcode_text = response.text.strip()
        return None if barcode_text.lower() == 'none' else barcode_text
    except Exception as e:
        st.error(f"Lỗi quét: {e}")
        return None

def lookup_product(barcode, df):
    """Tra cứu sản phẩm"""
    barcode = str(barcode).strip()
    match = df[df['Barcode'] == barcode]
    if not match.empty:
        return {'name': match.iloc[0]['Tên SP'], 'brand': match.iloc[0]['Thương hiệu']}
    return {'name': 'Sản phẩm không xác định', 'brand': 'N/A'}

def send_to_sheet(data):
    """Gửi dữ liệu"""
    client = get_client()
    if not client:
        return False
    
    try:
        spreadsheet = client.open(st.session_state.sheet_name)
        try:
            sheet = spreadsheet.worksheet("Barcode_Data")
        except:
            sheet = spreadsheet.add_worksheet(title="Barcode_Data", rows=100, cols=10)
            sheet.append_row(["Barcode", "Tên SP", "Thương hiệu", "Số lượng", "Đơn vị", "Thời gian"])
        
        sheet.append_row([
            data['barcode'], data['product_name'], data['brand'],
            data['quantity'], data['unit'], data['timestamp']
        ])
        return True
    except Exception as e:
        st.error(f"Lỗi gửi: {e}")
        return False

def save_product(barcode, name, brand):
    """Lưu sản phẩm mới"""
    client = get_client()
    if not client:
        return False
    
    try:
        spreadsheet = client.open(st.session_state.sheet_name)
        try:
            sheet = spreadsheet.worksheet("Product_List")
        except:
            sheet = spreadsheet.add_worksheet(title="Product_List", rows=100, cols=10)
            sheet.append_row(["Barcode", "Tên SP", "Thương hiệu"])
        
        sheet.append_row([str(barcode).strip(), name, brand])
        st.session_state.product_cache = None  # Clear cache
        return True
    except Exception as e:
        st.error(f"Lỗi lưu: {e}")
        return False

def reset_form():
    """Reset form"""
    st.session_state.scanned_product = None
    st.session_state.barcode_data = None
    st.session_state.last_image_hash = None

# ==================== AUTH ====================

def check_login():
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
    st.session_state.client = None
    st.session_state.product_cache = None
    reset_form()
    st.rerun()

# ==================== MAIN APP ====================

if not st.session_state.logged_in:
    st.session_state.logged_in = check_login()

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

# ==================== LOGGED IN ====================

st.title("📦 Viva Star Coffee - Kiểm Hàng")
st.markdown("---")

if st.button("🚪 Đăng xuất"):
    logout()

# Load products (CHỈ 1 LẦN)
product_df = load_products()

# ==================== TABS ====================

tab1, tab2, tab3 = st.tabs(["📸 Quét Barcode", "📊 Xem Dữ Liệu", "🛠 Cập nhật Barcode"])

# ===== TAB 1 =====
with tab1:
    scan_method = st.radio("Phương thức:", ["📷 Chụp", "📁 Upload", "⌨️ Nhập"], horizontal=True)

    # Quét barcode
    if scan_method == "📷 Chụp":
        camera_image = st.camera_input("Chụp ảnh")
        if camera_image:
            image = Image.open(camera_image)
            current_hash = hash(camera_image.getvalue())
            
            if current_hash != st.session_state.last_image_hash:
                st.session_state.last_image_hash = current_hash
                with st.spinner("🤖 Đang quét..."):
                    barcode = scan_barcode_gemini(image)
                    if barcode:
                        st.session_state.barcode_data = barcode
                        st.session_state.scanned_product = lookup_product(barcode, product_df)
                        st.rerun()

    elif scan_method == "📁 Upload":
        uploaded = st.file_uploader("Chọn ảnh", type=['jpg', 'jpeg', 'png'])
        if uploaded:
            image = Image.open(uploaded)
            current_hash = hash(uploaded.getvalue())
            
            if current_hash != st.session_state.last_image_hash:
                st.session_state.last_image_hash = current_hash
                with st.spinner("🤖 Đang quét..."):
                    barcode = scan_barcode_gemini(image)
                    if barcode:
                        st.session_state.barcode_data = barcode
                        st.session_state.scanned_product = lookup_product(barcode, product_df)
                        st.rerun()

    else:  # Nhập thủ công
        manual = st.text_input("Nhập barcode:", max_chars=20)
        if st.button("🔍 Tra cứu"):
            if manual:
                st.session_state.barcode_data = manual
                st.session_state.scanned_product = lookup_product(manual, product_df)
                st.rerun()

    # Hiển thị form (nếu đã có barcode)
    if st.session_state.barcode_data and st.session_state.scanned_product:
        st.success(f"✅ Barcode: {st.session_state.barcode_data}")
        
        if st.session_state.scanned_product['name'] == 'Sản phẩm không xác định':
            st.warning("⚠️ Chưa có sản phẩm. Vui lòng thêm trong tab 'Cập nhật'.")
            if st.button("🔄 Quét lại"):
                reset_form()
                st.rerun()
        else:
            st.markdown("---")
            col1, col2 = st.columns(2)
            col1.metric("Tên", st.session_state.scanned_product['name'])
            col2.metric("Thương hiệu", st.session_state.scanned_product['brand'])
            
            st.markdown("---")
            
            # FORM - Không rerun khi nhập
            with st.form("input_form"):
                col1, col2 = st.columns([2, 1])
                qty = col1.number_input("Số lượng:", min_value=0.0, step=0.1, format="%.2f")
                unit = col2.selectbox("Đơn vị:", ["ml", "L", "g", "kg", "cái", "hộp", "chai"])
                
                col1, col2 = st.columns(2)
                rescan = col1.form_submit_button("🔄 Quét lại", use_container_width=True)
                submit = col2.form_submit_button("📤 Gửi", type="primary", use_container_width=True)
                
                if rescan:
                    reset_form()
                    st.rerun()
                
                if submit:
                    if qty > 0:
                        data = {
                            'barcode': st.session_state.barcode_data,
                            'product_name': st.session_state.scanned_product['name'],
                            'brand': st.session_state.scanned_product['brand'],
                            'quantity': qty,
                            'unit': unit,
                            'timestamp': datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        if send_to_sheet(data):
                            st.success("✅ Đã gửi!")
                            st.balloons()
                            reset_form()
                            st.rerun()
                    else:
                        st.warning("⚠️ Nhập số lượng > 0!")

# ===== TAB 2 =====
with tab2:
    st.subheader("📊 Dữ liệu đã lưu")
    
    today = date.today()
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Từ ngày:", value=today)
    end_date = col2.date_input("Đến ngày:", value=today)
    
    if st.button("🔄 Tải dữ liệu"):
        client = get_client()
        if client:
            try:
                spreadsheet = client.open(st.session_state.sheet_name)
                sheet = spreadsheet.worksheet("Barcode_Data")
                data = sheet.get_all_records()
                
                if data:
                    df = pd.DataFrame(data)
                    df['Thời gian'] = pd.to_datetime(df['Thời gian'], errors='coerce')
                    df = df.dropna(subset=['Thời gian'])
                    
                    mask = (df['Thời gian'].dt.date >= start_date) & (df['Thời gian'].dt.date <= end_date)
                    filtered = df[mask]
                    
                    if not filtered.empty:
                        st.dataframe(filtered, use_container_width=True)
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Tổng bản ghi", len(filtered))
                        col2.metric("Số sản phẩm", filtered['Barcode'].nunique())
                        col3.metric("Tổng SL", f"{filtered['Số lượng'].sum():.2f}")
                        
                        csv = filtered.to_csv(index=False)
                        st.download_button("📥 Tải CSV", csv, f"data_{start_date}_{end_date}.csv", "text/csv")
                    else:
                        st.info("📭 Không có dữ liệu!")
                else:
                    st.info("📭 Chưa có dữ liệu!")
            except Exception as e:
                st.error(f"Lỗi: {e}")

# ===== TAB 3 =====
with tab3:
    st.subheader("🛠 Cập nhật Barcode")
    
    with st.form("update_form"):
        barcode_in = st.text_input("Mã Barcode", max_chars=20)
        name_in = st.text_input("Tên sản phẩm")
        brand_in = st.text_input("Thương hiệu")
        save_btn = st.form_submit_button("💾 Lưu", type="primary")
        
        if save_btn:
            if barcode_in and name_in and brand_in:
                if save_product(barcode_in, name_in, brand_in):
                    st.success(f"✅ Đã lưu: {barcode_in}")
                    st.balloons()
            else:
                st.warning("⚠️ Nhập đầy đủ!")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #666;'>@2025 Viva Star Coffee</div>", unsafe_allow_html=True)
