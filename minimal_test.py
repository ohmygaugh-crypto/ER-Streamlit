import streamlit as st

st.title("🔬 Minimal Test - Step by Step")
st.write("Step 1: Basic Streamlit ✅")

# Test each import individually
try:
    import pandas as pd
    st.write("Step 2: Pandas import ✅")
except Exception as e:
    st.error(f"Pandas failed: {e}")

try:
    import numpy as np
    st.write("Step 3: NumPy import ✅")
except Exception as e:
    st.error(f"NumPy failed: {e}")

try:
    import jellyfish
    st.write("Step 4: Jellyfish import ✅")
except Exception as e:
    st.error(f"Jellyfish failed: {e}")

try:
    import networkx as nx
    st.write("Step 5: NetworkX import ✅")
except Exception as e:
    st.error(f"NetworkX failed: {e}")

st.write("Step 6: About to test st-link-analysis...")

# This is the suspected culprit
try:
    from st_link_analysis import st_link_analysis
    st.write("Step 7: st-link-analysis import ✅")
except Exception as e:
    st.error(f"st-link-analysis failed: {e}")

try:
    from st_link_analysis import NodeStyle, EdgeStyle
    st.write("Step 8: NodeStyle/EdgeStyle import ✅")
except Exception as e:
    st.error(f"NodeStyle/EdgeStyle failed: {e}")

st.success("🎉 All imports successful! The issue is elsewhere.")
st.balloons()
