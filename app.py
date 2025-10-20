import streamlit as st
from pyzbar import pyzbar
import cv2
import numpy as np
from PIL import Image
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

# Cấu hình trang
st.set_page_config(
    page_title="Quét Barcode",
    page_icon="📦",
    layout="centered"
)

# CSS tùy chỉnh
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        height: 3em;
        border-radius: 10px;
        font-weight: bold;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    </style>
""", unsafe_allow_html=True)

# Khởi tạo session state
if 'scanned_product' not in st.session_state:
    st.session_state.scanned_product = None
if 'barcode_data' not in st.session_state:
    st.session_state.barcode_data = None

# Header
st.title("📦 Quét Barcode Sản Phẩm")
st.markdown("---")

# Hàm kết nối Google Sheets
def connect_google_sheet(credentials_file, sheet_name):
    """Kết nối với Google Sheets"""
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        return sheet
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        return None

# Hàm quét barcode từ ảnh
def scan_barcode(image):
    """Quét barcode từ ảnh"""
    # Chuyển đổi PIL Image sang numpy array
    img_array = np.array(image)
    
    # Chuyển sang grayscale nếu là ảnh màu
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Quét barcode
    barcodes = pyzbar.decode(gray)
    
    if barcodes:
        return barcodes[0].data.decode('utf-8')
    return None

# Hàm tra cứu sản phẩm (database giả)
def lookup_product(barcode):
    """Tra cứu thông tin sản phẩm từ barcode"""
    # Database mẫu - trong thực tế có thể kết nối API hoặc database
    products = {
        '8935049502142': {'name': 'Coca Cola 330ml', 'brand': 'Coca Cola'},
        '8934673102384': {'name': 'Pepsi 330ml', 'brand': 'Pepsi'},
        '8936036021028': {'name': 'Mì Hảo Hảo', 'brand': 'Acecook'},
        '8934563144104': {'name': 'Nước suối Lavie 500ml', 'brand': 'Lavie'},
    }
    
    if barcode in products:
        return products[barcode]
    else:
        return {'name': 'Sản phẩm không xác định', 'brand': 'N/A'}

# Hàm gửi dữ liệu lên Google Sheets
def send_to_google_sheet(sheet, data):
    """Gửi dữ liệu lên Google Sheets"""
    try:
        row = [
            data['barcode'],
            data['product_name'],
            data['brand'],
            data['quantity'],
            data['unit'],
            data['timestamp']
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Lỗi gửi dữ liệu: {e}")
        return False

# Sidebar - Cấu hình Google Sheets
with st.sidebar:
    st.header("⚙️ Cấu hình")
    
    st.subheader("Google Sheets")
    credentials_file = st.text_input(
        "Đường dẫn file credentials JSON",
        value="credentials.json",
        help="File JSON từ Google Cloud Console"
    )
    sheet_name = st.text_input(
        "Tên Google Sheet",
        value="Barcode_Data",
        help="Tên của Google Sheet bạn muốn lưu dữ liệu"
    )
    
    st.markdown("---")
    st.subheader("📖 Hướng dẫn")
    with st.expander("Cách thiết lập Google Sheets"):
        st.markdown("""
        **Bước 1:** Tạo Google Cloud Project
        1. Vào [Google Cloud Console](https://console.cloud.google.com/)
        2. Tạo project mới
        3. Enable Google Sheets API và Google Drive API
        
        **Bước 2:** Tạo Service Account
        1. Vào IAM & Admin → Service Accounts
        2. Tạo service account mới
        3. Tạo key (JSON) và tải về
        4. Đổi tên file thành `credentials.json`
        
        **Bước 3:** Chia sẻ Google Sheet
        1. Tạo Google Sheet mới
        2. Thêm header: Barcode | Tên SP | Thương hiệu | Số lượng | Đơn vị | Thời gian
        3. Share với email từ service account
        """)

# Main content
tab1, tab2, tab3 = st.tabs(["📸 Quét Barcode", "📊 Xem Dữ Liệu", "ℹ️ Hướng Dẫn"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Chọn cách quét")
        scan_method = st.radio(
            "Phương thức quét:",
            ["📷 Chụp ảnh", "📁 Upload ảnh", "⌨️ Nhập thủ công"],
            horizontal=True
        )
    
    # Phương thức quét
    if scan_method == "📷 Chụp ảnh":
        camera_image = st.camera_input("Chụp ảnh barcode")
        
        if camera_image:
            image = Image.open(camera_image)
            st.image(image, caption="Ảnh đã chụp", use_column_width=True)
            
            with st.spinner("Đang quét barcode..."):
                barcode = scan_barcode(image)
                
            if barcode:
                st.session_state.barcode_data = barcode
                st.session_state.scanned_product = lookup_product(barcode)
                st.success(f"✅ Đã quét được barcode: {barcode}")
            else:
                st.error("❌ Không tìm thấy barcode trong ảnh!")
    
    elif scan_method == "📁 Upload ảnh":
        uploaded_file = st.file_uploader(
            "Chọn ảnh barcode",
            type=['jpg', 'jpeg', 'png'],
            help="Hỗ trợ JPG, JPEG, PNG"
        )
        
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Ảnh đã upload", use_column_width=True)
            
            with st.spinner("Đang quét barcode..."):
                barcode = scan_barcode(image)
                
            if barcode:
                st.session_state.barcode_data = barcode
                st.session_state.scanned_product = lookup_product(barcode)
                st.success(f"✅ Đã quét được barcode: {barcode}")
            else:
                st.error("❌ Không tìm thấy barcode trong ảnh!")
    
    else:  # Nhập thủ công
        manual_barcode = st.text_input("Nhập mã barcode:", max_chars=20)
        
        if st.button("🔍 Tra cứu"):
            if manual_barcode:
                st.session_state.barcode_data = manual_barcode
                st.session_state.scanned_product = lookup_product(manual_barcode)
                st.success(f"✅ Đã tra cứu barcode: {manual_barcode}")
            else:
                st.warning("⚠️ Vui lòng nhập mã barcode!")
    
    # Hiển thị thông tin sản phẩm và form nhập liệu
    if st.session_state.scanned_product:
        st.markdown("---")
        st.subheader("📦 Thông tin sản phẩm")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tên sản phẩm", st.session_state.scanned_product['name'])
        with col2:
            st.metric("Thương hiệu", st.session_state.scanned_product['brand'])
        
        st.info(f"🔢 Barcode: **{st.session_state.barcode_data}**")
        
        st.markdown("---")
        st.subheader("📝 Nhập số lượng")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            quantity = st.number_input(
                "Số lượng:",
                min_value=0.0,
                step=0.1,
                format="%.2f"
            )
        
        with col2:
            unit = st.selectbox(
                "Đơn vị:",
                ["ml", "L", "g", "kg", "cái", "hộp", "chai"]
            )
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Quét lại", use_container_width=True):
                st.session_state.scanned_product = None
                st.session_state.barcode_data = None
                st.rerun()
        
        with col2:
            if st.button("📤 Gửi lên Google Sheets", type="primary", use_container_width=True):
                if quantity > 0:
                    # Kết nối Google Sheets
                    sheet = connect_google_sheet(credentials_file, sheet_name)
                    
                    if sheet:
                        # Chuẩn bị dữ liệu
                        data = {
                            'barcode': st.session_state.barcode_data,
                            'product_name': st.session_state.scanned_product['name'],
                            'brand': st.session_state.scanned_product['brand'],
                            'quantity': quantity,
                            'unit': unit,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Gửi dữ liệu
                        if send_to_google_sheet(sheet, data):
                            st.success("✅ Đã gửi dữ liệu thành công!")
                            st.balloons()
                            
                            # Reset
                            st.session_state.scanned_product = None
                            st.session_state.barcode_data = None
                        else:
                            st.error("❌ Gửi dữ liệu thất bại!")
                else:
                    st.warning("⚠️ Vui lòng nhập số lượng > 0!")

with tab2:
    st.subheader("📊 Dữ liệu đã lưu")
    
    if st.button("🔄 Tải dữ liệu từ Google Sheets"):
        sheet = connect_google_sheet(credentials_file, sheet_name)
        
        if sheet:
            try:
                # Lấy tất cả dữ liệu
                data = sheet.get_all_records()
                
                if data:
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Thống kê
                    st.markdown("---")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Tổng số bản ghi", len(df))
                    with col2:
                        st.metric("Số sản phẩm", df['Barcode'].nunique())
                    with col3:
                        if 'Số lượng' in df.columns:
                            total_qty = df['Số lượng'].sum()
                            st.metric("Tổng số lượng", f"{total_qty:.2f}")
                else:
                    st.info("📭 Chưa có dữ liệu nào!")
            except Exception as e:
                st.error(f"Lỗi tải dữ liệu: {e}")

with tab3:
    st.subheader("📖 Hướng dẫn sử dụng")
    
    st.markdown("""
    ### 🚀 Bắt đầu nhanh
    
    **Bước 1: Cài đặt thư viện**
    ```bash
    pip install streamlit pyzbar pillow opencv-python gspread oauth2client pandas
    ```
    
    **Bước 2: Thiết lập Google Sheets API**
    1. Làm theo hướng dẫn trong sidebar
    2. Đặt file `credentials.json` cùng thư mục với app
    3. Tạo Google Sheet với header như sau:
       - Barcode | Tên SP | Thương hiệu | Số lượng | Đơn vị | Thời gian
    
    **Bước 3: Chạy ứng dụng**
    ```bash
    streamlit run app.py
    ```
    
    ### 📱 Sử dụng trên điện thoại
    1. Deploy lên Streamlit Cloud (miễn phí)
    2. Truy cập link từ điện thoại
    3. Cho phép truy cập camera
    4. Quét và gửi dữ liệu!
    
    ### 🎯 Tính năng
    - ✅ Quét barcode từ camera hoặc ảnh
    - ✅ Nhập thủ công mã barcode
    - ✅ Nhập số lượng linh hoạt (ml, g, kg, cái...)
    - ✅ Tự động gửi lên Google Sheets
    - ✅ Xem dữ liệu và thống kê
    - ✅ Giao diện đẹp, dễ sử dụng
    
    ### 🔧 Lưu ý kỹ thuật
    - Cần cài **zbar** trên hệ thống:
      - Windows: Tải [zbar-0.10-setup.exe](http://zbar.sourceforge.net/download.html)
      - Mac: `brew install zbar`
      - Linux: `sudo apt-get install libzbar0`
    
    ### 💡 Mẹo
    - Chụp ảnh barcode rõ nét, đủ sáng
    - Đặt barcode nằm ngang
    - Khoảng cách vừa phải với camera
    """)
    
    st.markdown("---")
    st.info("💬 Có thắc mắc? Hãy kiểm tra file README hoặc liên hệ support!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>Made with ❤️ using Streamlit</div>",
    unsafe_allow_html=True
)