# Add this to the existing CSS in the CONFIG section
st.markdown("""
    <style>
    /* Existing CSS remains unchanged */
    /* Add mobile-specific styles */
    @media (max-width: 600px) {
        .stSelectbox, .stNumberInput, .stTextInput {
            font-size: 16px !important;
        }
        .stSelectbox > div > div {
            padding: 12px !important;
            border-radius: 8px !important;
        }
        .stNumberInput input {
            padding: 12px !important;
            border-radius: 8px !important;
            font-size: 16px !important;
        }
        .stButton>button {
            height: 48px !important; /* Larger tap target */
            font-size: 16px !important;
            border-radius: 10px !important;
        }
        .stMetric {
            padding: 8px !important;
            margin-bottom: 8px !important;
        }
        .product-card {
            background: rgba(255,255,255,0.95);
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .stForm {
            padding: 1rem !important;
        }
        /* Hide unnecessary horizontal rules on mobile */
        hr {
            display: none !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Replace the entire Tab 2 (Nhập Kho) section with this
with tab2:
    st.subheader("📦 Nhập Kho")
    st.caption("Chọn sản phẩm và nhập số lượng để lưu kho")

    if products_df.empty or len(products_df) == 0:
        st.warning("⚠️ Chưa có sản phẩm nào trong hệ thống. Vui lòng thêm sản phẩm ở tab 'Thêm SP'")
    else:
        # Search method selector
        search_method = st.selectbox(
            "🔍 Chọn cách tìm kiếm",
            ["Tìm kiếm", "Lọc theo chữ cái", "Tất cả"],
            help="Chọn phương thức để tìm sản phẩm",
            key="search_method_select"
        )

        filtered_products = products_df.copy()

        # Search mode
        if search_method == "Tìm kiếm":
            search_query = st.text_input(
                "🔍 Tìm sản phẩm",
                placeholder="Nhập tên, barcode hoặc thương hiệu...",
                help="Gõ để tìm sản phẩm nhanh",
                key="search_input"
            )
            if search_query:
                search_query = search_query.lower().strip()
                filtered_products = products_df[
                    products_df['Tên SP'].str.lower().str.contains(search_query, na=False) |
                    products_df['Barcode'].str.lower().str.contains(search_query, na=False) |
                    products_df['Thương hiệu'].str.lower().str.contains(search_query, na=False)
                ]

        # Alphabet filter mode
        elif search_method == "Lọc theo chữ cái":
            alphabet = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
                        'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0-9']
            selected_letter = st.selectbox(
                "🔤 Chọn chữ cái đầu",
                ["Tất cả"] + alphabet,
                help="Chọn chữ cái để lọc sản phẩm",
                key="alphabet_select"
            )
            if selected_letter != "Tất cả":
                if selected_letter == '0-9':
                    filtered_products = products_df[
                        products_df['Tên SP'].str[0].str.match(r'^\d', na=False)
                    ]
                else:
                    filtered_products = products_df[
                        products_df['Tên SP'].str.upper().str.startswith(selected_letter, na=False)
                    ]
            if st.button("🗑️ Xóa bộ lọc", use_container_width=True, key="clear_filter"):
                st.session_state["alphabet_select"] = "Tất cả"
                st.rerun()

        # Display results
        if filtered_products.empty:
            st.info("📭 Không tìm thấy sản phẩm nào")
        else:
            st.success(f"✅ Tìm thấy **{len(filtered_products)}** sản phẩm")

            # Product selector
            product_options = filtered_products.apply(
                lambda x: f"{x['Tên SP']} ({x['Barcode']})", axis=1
            ).tolist()

            selected_product = st.selectbox(
                "📦 Chọn sản phẩm",
                options=product_options,
                help="Chọn sản phẩm để nhập kho",
                key="product_select"
            )

            if selected_product:
                # Extract barcode and show product info
                selected_barcode = selected_product.split('(')[-1].rstrip(')')
                product_info = filtered_products[filtered_products['Barcode'] == selected_barcode].iloc[0]

                # Display product info in a compact card
                st.markdown(
                    f"""
                    <div class='product-card'>
                        <p style='margin: 0; font-weight: bold; font-size: 1.1em;'>📦 {product_info['Tên SP']}</p>
                        <p style='margin: 0.5rem 0; color: #555;'>🏷️ {product_info['Thương hiệu']}</p>
                        <p style='margin: 0; color: #777; font-size: 0.9em;'>📊 Barcode: {product_info['Barcode']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Input form
                with st.form("warehouse_input_form", clear_on_submit=True):
                    st.subheader("📝 Nhập thông tin nhập kho")
                    
                    qty = st.number_input(
                        "Số lượng",
                        min_value=0.0,
                        step=0.5,
                        format="%.2f",
                        value=1.0,
                        help="Nhập số lượng sản phẩm",
                        key="qty_input"
                    )
                    unit = st.selectbox(
                        "Đơn vị",
                        ["cái", "hộp", "chai", "kg", "g", "L", "ml"],
                        help="Chọn đơn vị tính",
                        key="unit_select"
                    )

                    submit = st.form_submit_button("✅ Lưu nhập kho", type="primary", use_container_width=True)

                    if submit:
                        if qty > 0:
                            data = {
                                'barcode': product_info['Barcode'],
                                'name': product_info['Tên SP'],
                                'brand': product_info['Thương hiệu'],
                                'qty': qty,
                                'unit': unit,
                                'time': datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")
                            }
                            with st.spinner("⏳ Đang lưu dữ liệu..."):
                                if save_scan(data):
                                    st.success(f"✅ Đã nhập kho: **{product_info['Tên SP']}** - **{qty} {unit}**")
                                    st.balloons()
                                else:
                                    st.error("❌ Lỗi lưu dữ liệu. Vui lòng thử lại!")
                        else:
                            st.warning("⚠️ Số lượng phải lớn hơn 0!")
