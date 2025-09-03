"""
Streamlit App: Cart Add-On Recommendations (Network Analytics Demo)
Retail Recommendation Engine based on Network Analytics
"""
import streamlit as st
import sys
from pathlib import Path

# Add src to path for modular imports
sys.path.append(str(Path(__file__).parent / "src"))

# Import core modules
from src.core.data_generator import generate_mock_orders
from src.core.network_analyzer import NetworkAnalyzer
from src.core.recommender import RecommendationEngine
from src.data.processors import DataProcessor
from src.ui.layouts.sidebar import render_sidebar
from src.ui.layouts.view import render_main_view

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
    
    # Initialize session state components
    _initialize_session_state()
    
    # Render sidebar controls and get configuration
    config = render_sidebar()
    
    # Load data based on configuration
    orders_df = _load_data(config)
    
    # Render main view with data and configuration
    render_main_view(orders_df, config)


def _initialize_session_state():
    """Initialize session state components"""
    if 'processor' not in st.session_state:
        st.session_state.processor = DataProcessor()
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = NetworkAnalyzer()
    if 'recommender' not in st.session_state:
        st.session_state.recommender = RecommendationEngine()


def _load_data(config):
    """Load data based on configuration"""
    if config['use_mock']:
        return generate_mock_orders()
    else:
        uploaded_file = config.get('uploaded_file')
        if uploaded_file is not None:
            try:
                import pandas as pd
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


if __name__ == "__main__":
    main()
