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

# Cấu hình trang
st.set_page_config(
    page_title="Quét Barcode",
    page_icon="📦",
    layout="centered"
)

# [Keep your CSS and session state initialization unchanged]

# Hàm kết nối Google Sheets
def connect_google_sheet(sheet_name):
    """Kết nối với Google Sheets"""
    try:
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Đọc credentials từ Streamlit secrets
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scope
            )
        else:
            # Fallback for local development
            creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
        
        client = gspread.authorize(creds)
        sheet = client.open(sheet_name).sheet1
        return sheet
    except Exception as e:
        st.error(f"Lỗi kết nối Google Sheets: {e}")
        return None

# Hàm quét barcode từ ảnh
def scan_barcode(image):
    """Quét barcode từ ảnh"""
    img_array = np.array(image)
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    barcodes = pyzbar.decode(gray)
    if barcodes:
        return barcodes[0].data.decode('utf-8')
    return None

# Hàm tra cứu sản phẩm (unchanged)
def lookup_product(barcode):
    products = {
        '8935049502142': {'name': 'Coca Cola 330ml', 'brand': 'Coca Cola'},
        '8934673102384': {'name': 'Pepsi 330ml', 'brand': 'Pepsi'},
        '8936036021028': {'name': 'Mì Hảo Hảo', 'brand': 'Acecook'},
        '8934563144104': {'name': 'Nước suối Lavie 500ml', 'brand': 'Lavie'},
    }
    return products.get(barcode, {'name': 'Sản phẩm không xác định', 'brand': 'N/A'})

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

# [Keep your sidebar and main content unchanged, except for timestamp in the form]

# In the "Gửi lên Google Sheets" button section, update the timestamp:
with tab1:
    # [Previous code unchanged until the "Gửi lên Google Sheets" button]
    with col2:
        if st.button("📤 Gửi lên Google Sheets", type="primary", use_container_width=True):
            if quantity > 0:
                sheet = connect_google_sheet(sheet_name)  # Remove credentials_file argument
                if sheet:
                    data = {
                        'barcode': st.session_state.barcode_data,
                        'product_name': st.session_state.scanned_product['name'],
                        'brand': st.session_state.scanned_product['brand'],
                        'quantity': quantity,
                        'unit': unit,
                        'timestamp': datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y-%m-%d %H:%M:%S")
                    }
                    if send_to_google_sheet(sheet, data):
                        st.success("✅ Đã gửi dữ liệu thành công!")
                        st.balloons()
                        st.session_state.scanned_product = None
                        st.session_state.barcode_data = None
                    else:
                        st.error("❌ Gửi dữ liệu thất bại!")
            else:
                st.warning("⚠️ Vui lòng nhập số lượng > 0!")

# [Keep the rest of tab1, tab2, tab3, and footer unchanged]
