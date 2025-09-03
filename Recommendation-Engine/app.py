"""
Streamlit App: Cart Add-On Recommendations (Network Analytics Demo)
Retail Recommendation Engine based on Network Analytics
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
import json
import math
import uuid
from collections import defaultdict, Counter
import sys
from pathlib import Path

# Add src to path for modular imports
sys.path.append(str(Path(__file__).parent / "src"))

# Optional dependencies with graceful fallback
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

# st_link_analysis import handled in src.utils.imports

# Import our modules
from src.core.data_generator import generate_mock_orders
from src.core.network_analyzer import NetworkAnalyzer
from src.core.recommender import RecommendationEngine
from src.data.processors import DataProcessor
from src.ui.layouts.sidebar import render_sidebar
from src.ui.components.graph_viz import render_network_graph
from src.ui.components.cart_simulator import render_cart_simulator

# ----------------------
# CONFIG
# ----------------------
st.set_page_config(
    page_title="Cart Add‑On Recommendations (Network Demo)", 
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point"""
    
    st.title("🛒 Cart Add‑On Recommendations • Network Analytics Demo")
    
    # Initialize session state
    if 'processor' not in st.session_state:
        st.session_state.processor = DataProcessor()
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = NetworkAnalyzer()
    if 'recommender' not in st.session_state:
        st.session_state.recommender = RecommendationEngine()
    
    # Render sidebar controls and get configuration
    config = render_sidebar()
    
    # Load and process data
    orders_df = load_data(config)
    
    if orders_df is not None and not orders_df.empty:
        # Display data preview
        st.markdown("### 📊 Orders Preview")
        sample_size = min(10, len(orders_df))
        st.dataframe(orders_df.sample(sample_size).sort_values("order_id"))
        
        # Process data and build network
        with st.spinner("🔄 Computing item co‑occurrences and network metrics…"):
            stats = st.session_state.analyzer.build_item_stats(orders_df)
            elements = st.session_state.analyzer.build_graph_elements(
                stats, 
                config['min_support'], 
                config['min_lift'], 
                config['max_edges']
            )
        
        n_orders = stats["n_orders"]
        n_products = len(stats["meta"])
        n_pairs = len(stats["pairs"])
        
        st.success(f"✅ Processed {n_orders} orders • {n_products} products • {n_pairs} pairs")
        
        # Layout: Graph visualization and cart simulator
        left_col, right_col = st.columns([2, 1])
        
        with left_col:
            render_network_graph(elements, config, stats)
        
        with right_col:
            render_cart_simulator(stats, config)
        
        # Explanation section
        render_explanation()
    
    else:
        st.warning("⚠️ No data available. Please check your data source configuration.")


def load_data(config):
    """Load data based on configuration"""
    if config['use_mock']:
        return generate_mock_orders()
    else:
        uploaded_file = config.get('uploaded_file')
        if uploaded_file is not None:
            try:
                df_raw = pd.read_csv(uploaded_file)
                processed_df = st.session_state.processor.validate_and_process(df_raw)
                return processed_df
            except Exception as e:
                st.error(f"❌ Error processing uploaded file: {str(e)}")
                st.info("🔄 Falling back to mock data...")
                return generate_mock_orders()
        else:
            st.info("📁 Upload a CSV file or switch to Mock data to proceed.")
            return None


def render_explanation():
    """Render the explanation/documentation section"""
    st.divider()
    
    with st.expander("📚 How this demo works", expanded=False):
        st.markdown("""
        ### 🔗 Network Definition
        - **Nodes** represent **products**; **edges** connect products frequently bought together
        - **Edge attributes**: 
          - **Support** (fraction of orders containing both items A & B)
          - **Confidence** (P(B|A) - probability of buying B given A is in cart)
          - **Lift** (co-occurrence strength relative to independence)
        - Graph filters by minimum **pair support** and **lift**; edge count capped for performance

        ### 🎯 Recommendation Algorithm
        - For cart items S, each candidate item t gets scored by:
          ```
          score(t) = Σ[s∈S] lift(s,t) × log(1 + co_count(s,t))
          ```
        - We report the strongest contributing edge as the **"why this item"** explanation
        - Recommendations ranked by aggregated score from all cart items

        ### 💰 Revenue Uplift Estimation
        - **Acceptance probability** estimated by normalizing scores (capped at 60% for demo)
        - **Expected margin uplift** = acceptance_prob × item_price × margin_percentage
        - Adjust *Margin %* slider to simulate different business scenarios

        ### 🏘️ Community Detection
        - When NetworkX is available, detects connected components as product communities
        - Communities represent natural product groupings (e.g., breakfast items, cooking essentials)
        - Nodes colored by community membership in visualization

        ### 📊 Data Requirements
        Upload CSV with columns: `order_id, customer_id, order_timestamp, product_id, product_name, category, price, quantity`
        
        The app auto-maps common aliases (e.g., `sku`→`product_id`, `item_name`→`product_name`)
        """)
    
    st.caption("💡 **Tip**: Use threshold sliders to reveal market basket structure, then leverage those insights for targeted cart add‑ons!")


if __name__ == "__main__":
    main()
