import streamlit as st
import time

st.title("🔍 st-link-analysis Debug Test")
st.write("Testing the custom component step by step...")

# Test 1: Basic import
try:
    st.write("Step 1: Importing st-link-analysis...")
    from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle
    st.success("✅ Import successful!")
except Exception as e:
    st.error(f"❌ Import failed: {e}")
    st.stop()

# Test 2: Create minimal elements
st.write("Step 2: Creating minimal test data...")
try:
    elements = {
        "nodes": [
            {"data": {"id": "1", "label": "TEST", "name": "Node1"}},
            {"data": {"id": "2", "label": "TEST", "name": "Node2"}}
        ],
        "edges": [
            {"data": {"id": "e1", "source": "1", "target": "2", "label": "CONNECTS"}}
        ]
    }
    st.success("✅ Test data created!")
except Exception as e:
    st.error(f"❌ Data creation failed: {e}")
    st.stop()

# Test 3: Create styles
st.write("Step 3: Creating node and edge styles...")
try:
    node_styles = [NodeStyle("TEST", "#FF7F3E", "name")]
    edge_styles = [EdgeStyle("CONNECTS", directed=False)]
    st.success("✅ Styles created!")
except Exception as e:
    st.error(f"❌ Style creation failed: {e}")
    st.stop()

# Test 4: Try to render (this is where it might hang)
st.write("Step 4: About to render component... (this might hang)")
st.write("⏳ If this hangs, the issue is in component rendering, not imports")

try:
    # Add a timeout mechanism
    with st.spinner("Rendering component..."):
        result = st_link_analysis(
            elements, 
            layout="grid",  # Use simple layout
            node_styles=node_styles,
            edge_styles=edge_styles,
            height=400
        )
    st.success("🎉 Component rendered successfully!")
    st.write(f"Component result: {result}")
    
except Exception as e:
    st.error(f"❌ Component rendering failed: {e}")
    st.write("This indicates the issue is in the component's frontend build/execution")

st.balloons()
st.write("If you see balloons, everything worked!")
