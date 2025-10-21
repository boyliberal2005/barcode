import streamlit as st
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import pytz
import io
import base64

# ==================== CONFIG ====================
VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')
HARDCODED_USER = "admin@123"
HARDCODED_PASS = "A@bcde6789"

st.set_page_config(
    page_title="Viva Star Coffee - Kiểm Hàng",
    page_icon="📦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# CSS hiện đại
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        height: 3.5em;
        border-radius: 12px;
        font-weight: 600;
        font-size: 16px;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
    }
    .stForm {
        background: rgba(255,255,255,0.95);
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    div[data-testid="metric-container"] {
        background: rgba(255,255,255,0.9);
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .stAlert {
        border-radius: 12px;
        border-left: 4px solid;
    }
    /* Hide camera controls overlay */
    [data-testid="stCameraInput"] > div > div {
        background: transparent !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== SESSION STATE ====================
defaults = {
    'logged_in': False,
    'product': None,
    'barcode': None,
    'img_hash': None,
    'products_df': None,
    'client': None,
    'sheet_name': 'Barcode_Data',
    'just_sent': False,
    'pending_confirm': False,
    'scanned_image': None,
    'camera_key': 0
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ==================== GOOGLE SHEETS ====================

def get_client():
    """Lazy load client"""
    if st.session_state.client is None:
        try:
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds_data = dict(st.secrets["gcp_service_account"]) if "gcp_service_account" in st.secrets else None
            
            if creds_data:
                creds = Credentials.from_service_account_info(creds_data, scopes=scope)
            else:
                creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
            
            st.session_state.client = gspread.authorize(creds)
        except Exception as e:
            st.error(f"❌ Lỗi kết nối Google Sheets: {e}")
            return None
    return st.session_state.client

def load_products():
    """Cache products in session"""
    if st.session_state.products_df is not None:
        return st.session_state.products_df
    
    client = get_client()
    if not client:
        return pd.DataFrame(columns=['Barcode', 'Tên SP', 'Thương hiệu'])
    
    try:
        sheet = client.open(st.session_state.sheet_name).worksheet("Product_List")
        df = pd.DataFrame(sheet.get_all_records())
        if not df.empty:
            df['Barcode'] = df['Barcode'].astype(str).str.strip()
        st.session_state.products_df = df
        return df
    except:
        df = pd.DataFrame(columns=['Barcode', 'Tên SP', 'Thương hiệu'])
        st.session_state.products_df = df
        return df

def get_or_create_sheet(client, sheet_name, worksheet_name, headers):
    """Get or create worksheet"""
    try:
        spreadsheet = client.open(sheet_name)
        try:
            return spreadsheet.worksheet(worksheet_name)
        except:
            sheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=20)
            sheet.append_row(headers)
            return sheet
    except Exception as e:
        st.error(f"❌ Lỗi worksheet: {e}")
        return None

# ==================== BARCODE OPERATIONS ====================

def scan_gemini(image):
    """Scan barcode with Gemini - returns (barcode, confidence)"""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key="AIzaSyA52qNG0pm7JD9E5Jhp_GhcwjdgXJd8sXQ")
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content([
            """Analyze this image and extract barcode number. Respond in this exact format:
BARCODE: [number or NONE]
CONFIDENCE: [HIGH/MEDIUM/LOW]

- HIGH: Barcode is clear, sharp, well-lit, fully visible
- MEDIUM: Barcode is readable but slightly blurry or partially obscured
- LOW: Barcode is very blurry, dark, or unclear

If no barcode detected, use BARCODE: NONE and CONFIDENCE: LOW""",
            {"mime_type": "image/png", "data": img_bytes.getvalue()}
        ])
        
        result = response.text.strip()
        
        # Parse response
        barcode = None
        confidence = "LOW"
        
        for line in result.split('\n'):
            if 'BARCODE:' in line:
                barcode_text = line.split('BARCODE:')[1].strip().upper()
                if barcode_text != 'NONE':
                    barcode = barcode_text
            elif 'CONFIDENCE:' in line:
                confidence = line.split('CONFIDENCE:')[1].strip().upper()
        
        return barcode, confidence
    except Exception as e:
        st.error(f"❌ Lỗi AI: {e}")
        return None, "LOW"

def lookup(barcode, df):
    """Quick product lookup"""
    match = df[df['Barcode'] == str(barcode).strip()]
    return {
        'name': match.iloc[0]['Tên SP'] if not match.empty else 'Chưa có thông tin',
        'brand': match.iloc[0]['Thương hiệu'] if not match.empty else 'N/A'
    }

def save_scan(data):
    """Save to Google Sheets"""
    client = get_client()
    if not client:
        return False
    
    try:
        sheet = get_or_create_sheet(
            client, 
            st.session_state.sheet_name, 
            "Barcode_Data",
            ["Barcode", "Tên SP", "Thương hiệu", "Số lượng", "Đơn vị", "Thời gian"]
        )
        
        if sheet:
            sheet.append_row([
                data['barcode'], data['name'], data['brand'],
                data['qty'], data['unit'], data['time']
            ])
            return True
    except Exception as e:
        st.error(f"❌ Lỗi lưu: {e}")
    return False

def save_product(barcode, name, brand):
    """Add new product"""
    client = get_client()
    if not client:
        return False
    
    try:
        sheet = get_or_create_sheet(
            client,
            st.session_state.sheet_name,
            "Product_List",
            ["Barcode", "Tên SP", "Thương hiệu"]
        )
        
        if sheet:
            sheet.append_row([str(barcode).strip(), name, brand])
            st.session_state.products_df = None  # Clear cache
            return True
    except Exception as e:
        st.error(f"❌ Lỗi lưu: {e}")
    return False

def reset():
    """Reset scan state"""
    st.session_state.product = None
    st.session_state.barcode = None
    st.session_state.img_hash = None
    st.session_state.just_sent = False
    st.session_state.pending_confirm = False
    st.session_state.scanned_image = None
    st.session_state.camera_key += 1  # Tăng key để force reset camera

# ==================== AUTH ====================

def check_auth():
    """Check login from query params"""
    token = st.query_params.get("logged_in", None)
    if token:
        try:
            return base64.b64decode(token).decode("utf-8") == "true"
        except:
            return False
    return False

def login():
    """Set login state"""
    st.query_params["logged_in"] = base64.b64encode(b"true").decode("utf-8")
    st.session_state.logged_in = True

def logout():
    """Clear session"""
    if "logged_in" in st.query_params:
        del st.query_params["logged_in"]
    for k in defaults.keys():
        st.session_state[k] = defaults[k]
    st.rerun()

# ==================== MAIN APP ====================

# Check auth
if not st.session_state.logged_in:
    st.session_state.logged_in = check_auth()

# Login screen
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: white;'>🔒 Đăng Nhập Hệ Thống</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: rgba(255,255,255,0.8);'>Viva Star Coffee - Quản lý kiểm hàng</p>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("👤 Tên đăng nhập", placeholder="Nhập tên đăng nhập")
        password = st.text_input("🔑 Mật khẩu", type="password", placeholder="Nhập mật khẩu")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit = st.form_submit_button("🚀 Đăng nhập", use_container_width=True)
        
        if submit:
            if username == HARDCODED_USER and password == HARDCODED_PASS:
                login()
                st.success("✅ Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("❌ Sai thông tin đăng nhập!")
    st.stop()

# ==================== MAIN INTERFACE ====================

# Header
col1, col2 = st.columns([4, 1])
with col1:
    st.title("📦 Viva Star Coffee")
    st.caption("Hệ thống kiểm hàng thông minh")
with col2:
    if st.button("🚪 Thoát", use_container_width=True):
        logout()

st.markdown("---")

# Load products
products_df = load_products()

# Auto-reset after send
if st.session_state.just_sent:
    reset()
    st.rerun()

# ==================== TABS ====================

tab1, tab2, tab3 = st.tabs(["📸 Quét Mã", "📊 Dữ Liệu", "➕ Thêm SP"])

# ===== TAB 1: SCAN =====
with tab1:
    scan_mode = st.radio(
        "Chọn phương thức quét:",
        ["📷 Camera", "📁 Upload", "⌨️ Nhập tay"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # Camera mode
    if scan_mode == "📷 Camera":
        st.info("""
        📸 **Hướng dẫn chụp barcode:**
        - 📏 Giữ điện thoại cách barcode 15-20cm
        - 💡 Đảm bảo đủ ánh sáng
        - 📐 Giữ điện thoại song song với barcode
        - 🎯 Đưa barcode vào giữa khung hình
        """)
        
        # CSS cho camera to hơn trên mobile
        st.markdown("""
        <style>
        /* Tăng kích thước camera trên mobile */
        [data-testid="stCameraInput"] {
            width: 100% !important;
        }
        [data-testid="stCameraInput"] video {
            width: 100% !important;
            height: 70vh !important;
            max-height: 600px !important;
            object-fit: cover !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2) !important;
        }
        /* Image preview cũng lớn */
        [data-testid="stCameraInput"] img {
            width: 100% !important;
            height: auto !important;
            max-height: 600px !important;
            object-fit: contain !important;
            border-radius: 16px !important;
        }
        /* Nút chụp lớn hơn và dễ nhìn */
        [data-testid="stCameraInput"] button {
            height: 70px !important;
            width: 70px !important;
            border-radius: 50% !important;
            background: #4CAF50 !important;
            border: 5px solid white !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
        }
        /* Container của camera */
        [data-testid="stCameraInput"] > div {
            background: rgba(0,0,0,0.05) !important;
            border-radius: 20px !important;
            padding: 10px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        cam = st.camera_input("📸 Nhấn để chụp", label_visibility="visible", key=f"camera_{st.session_state.camera_key}")
        
        if cam:
            h = hash(cam.getvalue())
            
            # Chỉ xử lý ảnh mới hoặc khi chưa có product
            if h != st.session_state.img_hash or not st.session_state.product:
                # Nếu đã có barcode và product từ lần quét trước, giữ nguyên
                if st.session_state.img_hash == h and st.session_state.product:
                    pass  # Không làm gì, giữ nguyên state
                else:
                    # Ảnh mới, xử lý quét
                    st.session_state.img_hash = h
                    img = Image.open(cam)
                    
                    # Lưu ảnh vào session state
                    st.session_state.scanned_image = img
                    
                    st.image(img, caption="✅ Ảnh đã chụp", use_container_width=True)
                    
                    with st.spinner("🤖 AI đang quét barcode..."):
                        barcode, confidence = scan_gemini(img)
                        
                        if confidence == "HIGH" and barcode:
                            st.success("✅ Ảnh rõ ràng! Đang xử lý...")
                            st.session_state.barcode = barcode
                            st.session_state.product = lookup(barcode, products_df)
                            st.rerun()
                        elif confidence == "MEDIUM" and barcode:
                            st.warning("⚠️ Ảnh hơi mờ nhưng có thể quét được")
                            st.session_state.pending_confirm = True
                            st.session_state.barcode = barcode
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ Quét ngay", use_container_width=True, type="primary", key="confirm_scan"):
                                    st.session_state.product = lookup(barcode, products_df)
                                    st.session_state.pending_confirm = False
                                    st.rerun()
                            with col2:
                                if st.button("🔄 Chụp lại", use_container_width=True, key="retake_cam"):
                                    reset()
                                    st.rerun()
                        else:
                            st.error("❌ Không tìm thấy barcode hoặc ảnh quá mờ. Vui lòng chụp lại!")
                            if st.button("🔄 Chụp lại", use_container_width=True, key="retry_cam"):
                                reset()
                                st.rerun()
    
    # Upload mode
    elif scan_mode == "📁 Upload":
        upload = st.file_uploader("📁 Chọn ảnh", type=['jpg', 'jpeg', 'png'], label_visibility="collapsed")
        
        if upload:
            h = hash(upload.getvalue())
            
            # Chỉ xử lý ảnh mới
            if h != st.session_state.img_hash or not st.session_state.product:
                if st.session_state.img_hash == h and st.session_state.product:
                    pass  # Giữ nguyên state
                else:
                    st.session_state.img_hash = h
                    img = Image.open(upload)
                    
                    # Lưu ảnh vào session state
                    st.session_state.scanned_image = img
                    
                    st.image(img, caption="Ảnh đã chọn", use_container_width=True)
                    
                    with st.spinner("🤖 AI đang quét..."):
                        barcode, confidence = scan_gemini(img)
                        
                        if barcode:
                            st.session_state.barcode = barcode
                            st.session_state.product = lookup(barcode, products_df)
                            st.rerun()
                        else:
                            st.error("❌ Không tìm thấy barcode. Vui lòng chọn ảnh khác!")
                            if st.button("🔄 Chọn lại", use_container_width=True, key="retry_upload"):
                                reset()
                                st.rerun()
    
    # Manual mode
    else:
        manual = st.text_input("⌨️ Nhập mã barcode", placeholder="Ví dụ: 8935049502142", max_chars=20)
        
        if st.button("🔍 Tra cứu", use_container_width=True):
            if manual:
                st.session_state.barcode = manual
                st.session_state.product = lookup(manual, products_df)
                st.rerun()
            else:
                st.warning("⚠️ Vui lòng nhập mã barcode!")
    
    # Show product form - QUAN TRỌNG: Phải nằm ngoài các điều kiện scan_mode
    if st.session_state.barcode and st.session_state.product and not st.session_state.pending_confirm:
        st.markdown("---")
        
        # Hiển thị ảnh đã quét nếu có
        if st.session_state.scanned_image:
            st.image(st.session_state.scanned_image, caption="📸 Ảnh đã quét", use_container_width=True)
            st.markdown("---")
        
        st.success(f"✅ **Mã vạch đã quét:** {st.session_state.barcode}")
        
        if st.session_state.product['name'] == 'Chưa có thông tin':
            st.warning("⚠️ **Sản phẩm chưa được thêm vào hệ thống**")
            st.info("💡 Vui lòng chuyển sang tab **'Thêm SP'** để thêm thông tin sản phẩm này")
            
            if st.button("🔄 Quét lại", use_container_width=True, key="rescan_unknown"):
                reset()
                st.rerun()
        
        else:
            # Product info
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📦 Tên sản phẩm", st.session_state.product['name'])
            with col2:
                st.metric("🏷️ Thương hiệu", st.session_state.product['brand'])
            
            st.markdown("---")
            
            # Input form
            with st.form("input_form", clear_on_submit=True):
                st.subheader("📝 Nhập thông tin kiểm hàng")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    qty = st.number_input(
                        "Số lượng",
                        min_value=0.0,
                        step=0.1,
                        format="%.2f",
                        value=1.0,
                        help="Nhập số lượng sản phẩm"
                    )
                with col2:
                    unit = st.selectbox(
                        "Đơn vị",
                        ["cái", "hộp", "chai", "kg", "g", "L", "ml"],
                        help="Chọn đơn vị tính"
                    )
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    rescan = st.form_submit_button("🔄 Quét lại", use_container_width=True)
                with col2:
                    submit = st.form_submit_button("✅ Xác nhận & Gửi", type="primary", use_container_width=True)
                
                if rescan:
                    reset()
                    st.rerun()
                
                if submit:
                    if qty > 0:
                        data = {
                            'barcode': st.session_state.barcode,
                            'name': st.session_state.product['name'],
                            'brand': st.session_state.product['brand'],
                            'qty': qty,
                            'unit': unit,
                            'time': datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        with st.spinner("⏳ Đang lưu dữ liệu..."):
                            if save_scan(data):
                                st.success("✅ Đã lưu thành công!")
                                st.balloons()
                                st.session_state.just_sent = True
                                st.rerun()
                            else:
                                st.error("❌ Không thể lưu. Vui lòng thử lại!")
                    else:
                        st.warning("⚠️ Số lượng phải lớn hơn 0!")

# ===== TAB 2: DATA =====
with tab2:
    st.subheader("📊 Dữ liệu đã quét")
    
    today = datetime.now(VN_TZ).date()
    
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("📅 Từ ngày", value=today, max_value=today)
    with col2:
        end = st.date_input("📅 Đến ngày", value=today, max_value=today)
    
    if st.button("🔄 Tải dữ liệu", use_container_width=True):
        client = get_client()
        
        if client:
            with st.spinner("⏳ Đang tải..."):
                try:
                    sheet = client.open(st.session_state.sheet_name).worksheet("Barcode_Data")
                    data = sheet.get_all_records()
                    
                    if data:
                        df = pd.DataFrame(data)
                        df['Thời gian'] = pd.to_datetime(df['Thời gian'], errors='coerce')
                        df = df.dropna(subset=['Thời gian'])
                        
                        mask = (df['Thời gian'].dt.date >= start) & (df['Thời gian'].dt.date <= end)
                        filtered = df[mask]
                        
                        if not filtered.empty:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("📋 Tổng bản ghi", len(filtered))
                            with col2:
                                st.metric("📦 Số sản phẩm", filtered['Barcode'].nunique())
                            with col3:
                                st.metric("📊 Tổng SL", f"{filtered['Số lượng'].sum():.1f}")
                            
                            st.markdown("---")
                            st.dataframe(filtered, use_container_width=True, hide_index=True)
                            
                            csv = filtered.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                "📥 Tải xuống CSV",
                                csv,
                                f"vivastar_data_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                        else:
                            st.info("📭 Không có dữ liệu trong khoảng thời gian này")
                    else:
                        st.info("📭 Chưa có dữ liệu nào được lưu")
                
                except Exception as e:
                    st.error(f"❌ Lỗi: {e}")

# ===== TAB 3: ADD PRODUCT =====
with tab3:
    st.subheader("➕ Thêm sản phẩm mới")
    st.caption("Thêm thông tin sản phẩm cho barcode chưa có trong hệ thống")
    
    with st.form("add_product_form", clear_on_submit=True):
        barcode_input = st.text_input(
            "📊 Mã Barcode",
            placeholder="Ví dụ: 8935049502142",
            max_chars=20,
            help="Nhập mã barcode đầy đủ"
        )
        
        name_input = st.text_input(
            "📦 Tên sản phẩm",
            placeholder="Ví dụ: Cà phê G7 3in1",
            help="Nhập tên đầy đủ của sản phẩm"
        )
        
        brand_input = st.text_input(
            "🏷️ Thương hiệu",
            placeholder="Ví dụ: Trung Nguyên",
            help="Nhập tên thương hiệu"
        )
        
        st.markdown("---")
        
        submit = st.form_submit_button("💾 Lưu sản phẩm", type="primary", use_container_width=True)
        
        if submit:
            if barcode_input and name_input and brand_input:
                with st.spinner("⏳ Đang lưu..."):
                    if save_product(barcode_input, name_input, brand_input):
                        st.success(f"✅ Đã thêm sản phẩm: **{name_input}**")
                        st.balloons()
                    else:
                        st.error("❌ Không thể lưu. Vui lòng thử lại!")
            else:
                st.warning("⚠️ Vui lòng điền đầy đủ tất cả thông tin!")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: rgba(0,0,0,0.8); background: rgba(0,0,0,0.05); padding: 1.5rem; border-radius: 12px;'>
        <p style='margin: 0; font-weight: 600; color: #000;'>🌟 <strong>Viva Star Coffee</strong> - Hệ thống kiểm hàng thông minh</p>
        <p style='margin: 0.5rem 0 0 0; font-size: 0.9em; color: rgba(0,0,0,0.6);'>© 2025 - Powered by AI Technology</p>
    </div>
    """,
    unsafe_allow_html=True
)
