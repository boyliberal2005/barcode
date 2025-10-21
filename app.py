# ===== TAB 2: NHẬP KHO =====
with tab2:
    st.subheader("📦 Nhập Kho")
    st.caption("Chọn sản phẩm từ danh sách và nhập số lượng")
    
    if products_df.empty or len(products_df) == 0:
        st.warning("⚠️ Chưa có sản phẩm nào trong hệ thống. Vui lòng thêm sản phẩm ở tab 'Thêm SP'")
    else:
        # Search method selector - Compact version
        col1, col2, col3 = st.columns(3)
        with col1:
            btn_search = st.button("🔍 Tìm kiếm", use_container_width=True, key="search_mode")
        with col2:
            btn_alphabet = st.button("🔤 Chữ cái", use_container_width=True, key="alphabet_mode")
        with col3:
            btn_all = st.button("📋 Tất cả", use_container_width=True, key="all_mode")
        
        # Determine search method from session state or button clicks
        if 'warehouse_search_method' not in st.session_state:
            st.session_state.warehouse_search_method = "all"
        
        if btn_search:
            st.session_state.warehouse_search_method = "search"
        elif btn_alphabet:
            st.session_state.warehouse_search_method = "alphabet"
        elif btn_all:
            st.session_state.warehouse_search_method = "all"
        
        search_method = st.session_state.warehouse_search_method
        
        st.markdown("---")
        
        filtered_products = products_df.copy()
        
        # Search mode
        if search_method == "search":
            search_query = st.text_input(
                "🔍 Tìm kiếm sản phẩm",
                placeholder="Nhập tên sản phẩm hoặc barcode...",
                help="Gõ tên hoặc mã barcode để tìm",
                key="warehouse_search_input"
            )
            
            if search_query:
                search_query = search_query.lower().strip()
                filtered_products = products_df[
                    products_df['Tên SP'].str.lower().str.contains(search_query, na=False) |
                    products_df['Barcode'].str.lower().str.contains(search_query, na=False) |
                    products_df['Thương hiệu'].str.lower().str.contains(search_query, na=False)
                ]
        
        # Alphabet mode - MOBILE OPTIMIZED
        elif search_method == "alphabet":
            # CSS cho alphabet buttons - compact và mobile-friendly
            st.markdown("""
            <style>
            div[data-testid="column"] button[kind="secondary"] {
                padding: 0.4rem 0.2rem !important;
                font-size: 0.9em !important;
                min-height: 2.5rem !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown("**🔤 Chọn chữ cái đầu:**")
            
            # Create alphabet in 3 rows - MOBILE OPTIMIZED
            alphabet = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 
                       'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R',
                       'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0-9']
            
            # Initialize selected letter in session state
            if 'selected_letter_warehouse' not in st.session_state:
                st.session_state.selected_letter_warehouse = None
            
            # Row 1: A-I (9 letters)
            cols1 = st.columns(9)
            for idx, letter in enumerate(alphabet[0:9]):
                with cols1[idx]:
                    if st.button(letter, key=f"letter_w_{letter}", use_container_width=True):
                        st.session_state.selected_letter_warehouse = letter
            
            # Row 2: J-R (9 letters)
            cols2 = st.columns(9)
            for idx, letter in enumerate(alphabet[9:18]):
                with cols2[idx]:
                    if st.button(letter, key=f"letter_w_{letter}", use_container_width=True):
                        st.session_state.selected_letter_warehouse = letter
            
            # Row 3: S-Z + 0-9 (10 letters)
            cols3 = st.columns(10)
            for idx, letter in enumerate(alphabet[18:28]):
                with cols3[idx]:
                    if st.button(letter, key=f"letter_w_{letter}", use_container_width=True):
                        st.session_state.selected_letter_warehouse = letter
            
            selected_letter = st.session_state.selected_letter_warehouse
            
            if selected_letter:
                st.info(f"📝 Hiển thị sản phẩm bắt đầu bằng: **{selected_letter}**")
                
                if selected_letter == '0-9':
                    filtered_products = products_df[
                        products_df['Tên SP'].str[0].str.match(r'^\d', na=False)
                    ]
                else:
                    filtered_products = products_df[
                        products_df['Tên SP'].str.upper().str.startswith(selected_letter, na=False)
                    ]
