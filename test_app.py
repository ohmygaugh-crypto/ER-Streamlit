import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Test App - Minimal Version", 
    layout="wide"
)

st.title("🧪 Test App - Checking Basic Functionality")
st.write("If you can see this, basic Streamlit is working!")

# Test basic functionality
st.sidebar.header("Basic Test")
test_slider = st.sidebar.slider("Test Slider", 0.0, 1.0, 0.5)
st.write(f"Slider value: {test_slider}")

# Test pandas
df_test = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
st.dataframe(df_test)

st.success("✅ Basic Streamlit + Pandas working!")

# Now test the problematic import
try:
    from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle
    st.success("✅ st-link-analysis imported successfully!")
    
    # Test basic usage
    elements = {
        "nodes": [{"data": {"id": "1", "label": "Test"}}],
        "edges": []
    }
    st_link_analysis(elements)
    st.success("✅ st-link-analysis works!")
    
except Exception as e:
    st.error(f"❌ st-link-analysis error: {str(e)}")
    st.write("This might be the source of the hanging issue.")

st.write("If this loads completely, your main app should work too.")
