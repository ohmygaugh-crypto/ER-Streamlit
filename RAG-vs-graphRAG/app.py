"""
Streamlit App: RAG vs GraphRAG Comparison
Enterprise Knowledge Management Demo - Refactored
"""
import streamlit as st
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

# Import system components
from src.system.initialization import initialize_app
from src.system.session_state import manage_session_state, handle_api_key_setup

# Import UI components
from src.ui.layout.sidebar import render_sidebar
from src.ui.layout.demo_scenarios import render_demo_scenarios
from src.ui.layout.comparison import render_comparison_interface


def main():
    """Main application entry point"""
    # Initialize app configuration
    initialize_app()
    
    # Display main header
    st.markdown('<h1 class="main-header">🔍 RAG vs GraphRAG: Enterprise Knowledge Base Enablement</h1>', 
                unsafe_allow_html=True)
    
    # Initialize session state
    manage_session_state()
    
    # Handle API key and system initialization
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password", 
                                          help="Required for LLM-powered answers",
                                          key="main_api_key")
    
    # Optional domain hint for LLM ontology extraction
    domain_hint = st.sidebar.text_input("Domain/Industry (optional)", 
                                       placeholder="e.g., medical, legal, business",
                                       help="Hint to guide entity extraction. Leave blank for auto-detection.",
                                       key="domain_hint")
    
    trad_rag, graph_rag = handle_api_key_setup(openai_api_key, domain_hint)
    
    # Render sidebar with data loading and export functionality
    render_sidebar(openai_api_key, trad_rag, graph_rag, domain_hint)
    
    # Render main content: demo scenarios and question input
    custom_question, show_graph_viz = render_demo_scenarios()
    
    # Render comparison interface
    render_comparison_interface(custom_question, openai_api_key, domain_hint)


if __name__ == "__main__":
    main()
