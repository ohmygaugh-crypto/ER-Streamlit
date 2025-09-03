"""
Sidebar layout with data source controls and network parameters
"""
import streamlit as st
from typing import Dict, Any


def render_sidebar() -> Dict[str, Any]:
    """
    Render sidebar with all configuration options
    
    Returns:
        Dictionary with configuration parameters
    """
    st.sidebar.header("🔧 Configuration")
    
    # Data source section
    st.sidebar.subheader("📊 Data Source")
    use_mock = st.sidebar.toggle(
        "Use Mock Grocery Data", 
        value=True,
        help="Toggle between built-in mock data and uploaded CSV"
    )
    
    uploaded_file = None
    if not use_mock:
        uploaded_file = st.sidebar.file_uploader(
            "Upload Orders CSV",
            type=["csv"],
            help="CSV with columns: order_id, customer_id, order_timestamp, product_id, product_name, category, price, quantity"
        )
    
    st.sidebar.divider()
    
    # Network analysis parameters
    st.sidebar.subheader("🕸️ Network Filters")
    min_support = st.sidebar.slider(
        "Min Pair Support",
        min_value=0.0,
        max_value=0.05,
        value=0.005,
        step=0.001,
        format="%.3f",
        help="Minimum fraction of orders containing both items in a pair"
    )
    
    min_lift = st.sidebar.slider(
        "Min Lift",
        min_value=1.0,
        max_value=5.0,
        value=1.2,
        step=0.05,
        help="Minimum lift score (co-occurrence strength relative to independence)"
    )
    
    max_edges = st.sidebar.number_input(
        "Max Edges",
        min_value=100,
        max_value=20000,
        value=2500,
        step=100,
        help="Maximum number of edges to display (for performance)"
    )
    
    st.sidebar.divider()
    
    # Recommendation parameters
    st.sidebar.subheader("🎯 Recommendations")
    rec_k = st.sidebar.slider(
        "Number of Recommendations",
        min_value=1,
        max_value=15,
        value=5,
        help="How many recommendations to show"
    )
    
    margin_pct = st.sidebar.slider(
        "Assumed Margin %",
        min_value=0,
        max_value=90,
        value=35,
        help="Profit margin percentage for revenue uplift calculations"
    )
    
    st.sidebar.divider()
    
    # Visualization parameters
    st.sidebar.subheader("📈 Visualization")
    
    # Only show layout option if st_link_analysis is available
    try:
        from st_link_analysis import st_link_analysis
        layout_choice = st.sidebar.selectbox(
            "Graph Layout",
            options=["cose", "grid", "concentric", "breadthfirst", "circle"],
            index=0,
            help="Layout algorithm for network visualization"
        )
    except ImportError:
        layout_choice = "cose"
        st.sidebar.info("📦 Install st-link-analysis for interactive graph visualization")
    
    show_communities = st.sidebar.checkbox(
        "Show Communities",
        value=True,
        help="Color nodes by detected communities"
    )
    
    st.sidebar.divider()
    
    # Information section
    with st.sidebar.expander("ℹ️ About This Demo", expanded=False):
        st.markdown("""
        **Network Analytics for Retail Recommendations**
        
        This demo showcases how network analysis can power intelligent product recommendations for retail checkout flows.
        
        **Key Features:**
        - Market basket analysis with support, confidence, and lift
        - Interactive product co-purchase network
        - Explainable recommendations with "why" reasoning
        - Revenue uplift estimation
        - Community detection in product relationships
        
        **Use Cases:**
        - E-commerce cart add-ons
        - Grocery store checkout suggestions
        - Cross-selling optimization
        - Inventory planning insights
        """)
    
    return {
        "use_mock": use_mock,
        "uploaded_file": uploaded_file,
        "min_support": min_support,
        "min_lift": min_lift,
        "max_edges": max_edges,
        "rec_k": rec_k,
        "margin_pct": margin_pct,
        "layout_choice": layout_choice,
        "show_communities": show_communities
    }
