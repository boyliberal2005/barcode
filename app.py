import streamlit as st
from pyzbar import pyzbar
import cv2
import numpy as np
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import pytz
import google.generativeai as genai
import io

# Cấu hình Gemini API
genai.configure(api_key="AIzaSyA52qNG0pm7JD9E5Jhp_GhcwjdgXJd8sXQ")
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
def connect_google_sheet(sheet_name, worksheet_name):
    """Kết nối với Google Sheets và trả về worksheet, tạo nếu chưa tồn tại"""
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
        client = gspread.authorize(creds)
        spreadsheet = client.open(sheet_name)
        
        # Kiểm tra worksheet tồn tại
        try:
            sheet = spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            st.warning(f"Worksheet '{worksheet_name}' không tồn tại. Đang tạo mới...")
            sheet = spreadsheet.add_worksheet(title=worksheet_name, rows=100, cols=10)
            # Thêm header tùy theo worksheet
            if worksheet_name == "Barcode_Data":
                sheet.append_row(["Barcode", "Tên SP", "Thương hiệu", "Số lượng", "Đơn vị", "Thời gian"])
            elif worksheet_name == "Product_List":
                sheet.append_row(["Barcode", "Tên SP", "Thương hiệu"])
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Sheet '{sheet_name}' không tồn tại. Vui lòng tạo sheet với tên chính xác!")
        return None
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets ({worksheet_name}): {e}")
        return None

# Hàm quét barcode bằng pyzbar
def scan_barcode_pyzbar(image):
    """Quét barcode bằng pyzbar với tiền xử lý nâng cao"""
    try:
        img_array = np.array(image)
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )
        edges = cv2.Canny(thresh, 100, 200)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            roi = gray[y:y+h, x:x+w]
            if roi.size == 0:
                roi = gray
        else:
            roi = gray

        barcodes = pyzbar.decode(roi)
        if not barcodes:
            barcodes = pyzbar.decode(gray)

        if barcodes:
            return barcodes[0].data.decode('utf-8')
        return None
    except Exception as e:
        st.error(f"Lỗi pyzbar: {e}")
        return None

# Hàm quét barcode bằng Gemini AI
def scan_barcode_gemini(image):
    """Quét barcode bằng Gemini AI"""
    try:
        img_bytes = io.BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes = img_bytes.getvalue()
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([
            "Detect and read the barcode in this image. Return only the barcode value as plain text (e.g., '8935049502142'). If no barcode, return 'None'.",
            {"mime_type": "image/png", "data": img_bytes}
        ])
        barcode_text = response.text.strip()
        if barcode_text.lower() != 'none':
            return barcode_text
        return None
    except Exception as e:
        st.error(f"Lỗi Gemini AI: {e}")
        return None

# Hàm quét barcode chính
def scan_barcode(image):
    """Quét barcode: pyzbar trước, Gemini fallback"""
    pyzbar_result = scan_barcode_pyzbar(image)
    if pyzbar_result:
        return pyzbar_result
    st.info("Đang sử dụng AI Gemini để quét barcode thông minh hơn...")
    return scan_barcode_gemini(image)

# Hàm tra cứu sản phẩm từ Google Sheet
def lookup_product(barcode, sheet):
    """Tra cứu thông tin sản phẩm từ barcode trong Google Sheet"""
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'Barcode' in df.columns:
            match = df[df['Barcode'] == barcode]
            if not match.empty:
                return {
                    'name': match.iloc[0]['Tên SP'],
                    'brand': match.iloc[0]['Thương hiệu']
                }
        return {'name': 'Sản phẩm không xác định', 'brand': 'N/A'}
    except Exception as e:
        st.error(f"Lỗi tra cứu sản phẩm: {e}")
        return {'name': 'Sản phẩm không xác định', 'brand': 'N/A'}

# Hàm thêm hoặc cập nhật sản phẩm vào Google Sheet
def update_product(sheet, barcode, product_name, brand):
    """Thêm hoặc cập nhật sản phẩm trong Google Sheet"""
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty and 'Barcode' in df.columns:
            match = df[df['Barcode'] == barcode]
            if not match.empty:
                row_index = match.index[0] + 2
                sheet.update_cell(row_index, 2, product_name)
                sheet.update_cell(row_index, 3, brand)
                return True
        sheet.append_row([barcode, product_name, brand])
        return True
    except Exception as e:
        st.error(f"Lỗi cập nhật sản phẩm: {e}")
        return False

# Hàm gửi dữ liệu quét lên Google Sheet
def send_to_google_sheet(sheet, data):
    """Gửi dữ liệu quét lên Google Sheet"""
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
            4. Share Google Sheet với email từ service account
            
            **Bước 3:** Cấu hình Sheet
            - Tạo sheet "Barcode_Data" với hai worksheet:
              - "Barcode_Data": Header: Barcode, Tên SP, Thương hiệu, Số lượng, Đơn vị, Thời gian
              - "Product_List": Header: Barcode, Tên SP, Thương hiệu
        """)

# Main content
try:
    tab1, tab2, tab3 = st.tabs(["📸 Quét Barcode", "📊 Xem Dữ Liệu", "🛠 Cập nhật Barcode"])
except Exception as e:
    st.error(f"Lỗi khi tạo tabs: {e}")
    st.stop()

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Chọn cách quét")
        scan_method = st.radio(
            "Phương thức quét:",
            ["📷 Chụp ảnh", "📁 Upload ảnh", "⌨️ Nhập thủ công"],
            horizontal=True
        )

    if scan_method == "📷 Chụp ảnh":
        st.info("""
            **Mẹo quét barcode:**
            - Đặt barcode ở trung tâm khung hình.
            - Đảm bảo ánh sáng tốt, tránh bóng hoặc phản chiếu.
            - Giữ camera ổn định để tránh mờ.
        """)
        camera_image = st.camera_input("Chụp ảnh barcode")
        if camera_image:
            image = Image.open(camera_image)
            st.image(image, caption="Ảnh đã chụp", use_column_width=True)
            with st.spinner("Đang quét barcode..."):
                barcode = scan_barcode(image)
            if barcode:
                st.session_state.barcode_data = barcode
                product_sheet = connect_google_sheet(sheet_name, "Product_List")
                if product_sheet:
                    st.session_state.scanned_product = lookup_product(barcode, product_sheet)
                    st.success(f"✅ Đã quét được barcode: {barcode}")
                else:
                    st.error("❌ Lỗi kết nối sheet Product_List!")
            else:
                st.error("❌ Không tìm thấy barcode trong ảnh! Vui lòng thử lại.")

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
                product_sheet = connect_google_sheet(sheet_name, "Product_List")
                if product_sheet:
                    st.session_state.scanned_product = lookup_product(barcode, product_sheet)
                    st.success(f"✅ Đã quét được barcode: {barcode}")
                else:
                    st.error("❌ Lỗi kết nối sheet Product_List!")
            else:
                st.error("❌ Không tìm thấy barcode trong ảnh! Vui lòng thử lại.")

    else:  # Nhập thủ công
        manual_barcode = st.text_input("Nhập mã barcode:", max_chars=20)
        if st.button("🔍 Tra cứu"):
            if manual_barcode:
                st.session_state.barcode_data = manual_barcode
                product_sheet = connect_google_sheet(sheet_name, "Product_List")
                if product_sheet:
                    st.session_state.scanned_product = lookup_product(manual_barcode, product_sheet)
                    st.success(f"✅ Đã tra cứu barcode: {manual_barcode}")
                else:
                    st.error("❌ Lỗi kết nối sheet Product_List!")
            else:
                st.warning("⚠️ Vui lòng nhập mã barcode!")

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
                    data_sheet = connect_google_sheet(sheet_name, "Barcode_Data")
                    if data_sheet:
                        data = {
                            'barcode': st.session_state.barcode_data,
                            'product_name': st.session_state.scanned_product['name'],
                            'brand': st.session_state.scanned_product['brand'],
                            'quantity': quantity,
                            'unit': unit,
                            'timestamp': datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d %H:%M:%S")
                        }
                        if send_to_google_sheet(data_sheet, data):
                            st.success("✅ Đã gửi dữ liệu thành công!")
                            st.balloons()
                            st.session_state.scanned_product = None
                            st.session_state.barcode_data = None
                        else:
                            st.error("❌ Gửi dữ liệu thất bại!")
                    else:
                        st.error("❌ Lỗi kết nối sheet Barcode_Data!")
                else:
                    st.warning("⚠️ Vui lòng nhập số lượng > 0!")

with tab2:
    st.subheader("📊 Dữ liệu đã lưu")
    if st.button("🔄 Tải dữ liệu từ Google Sheets"):
        data_sheet = connect_google_sheet(sheet_name, "Barcode_Data")
        if data_sheet:
            try:
                data = data_sheet.get_all_records()
                if data:
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
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
    st.subheader("🛠 Cập nhật Barcode")
    st.markdown("Nhập thông tin để thêm hoặc cập nhật sản phẩm.")
    barcode_input = st.text_input("Mã Barcode", max_chars=20)
    product_name = st.text_input("Tên sản phẩm")
    brand = st.text_input("Thương hiệu")
    if st.button("💾 Lưu sản phẩm", type="primary"):
        if barcode_input and product_name and brand:
            product_sheet = connect_google_sheet(sheet_name, "Product_List")
            if product_sheet:
                if update_product(product_sheet, barcode_input, product_name, brand):
                    st.success(f"✅ Đã lưu/cập nhật barcode: {barcode_input}")
                    st.balloons()
                else:
                    st.error("❌ Lỗi khi lưu sản phẩm!")
            else:
                st.error("❌ Lỗi kết nối sheet Product_List!")
        else:
            st.warning("⚠️ Vui lòng nhập đầy đủ thông tin!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>Made with ❤️ using Streamlit</div>",
    unsafe_allow_html=True
)
