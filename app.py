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
                barcode = line.split('BARCODE:')[1].strip().upper()
                if barcode == 'NONE':
                    barcode = None
            elif 'CONFIDENCE:' in line:
                confidence = line.split('CONFIDENCE:')[1].strip().upper()
        
        return barcode, confidence
    except Exception as e:
        st.error(f"❌ Lỗi AI: {e}")
        return None, "LOW"
