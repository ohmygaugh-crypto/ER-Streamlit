"""
Session State Management
Handles Streamlit session state initialization and management
"""
import streamlit as st
import os
import hashlib
from .initialization import initialize_rag_systems


def manage_session_state():
    """Initialize and manage Streamlit session state"""
    # Initialize session state
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'systems_initialized' not in st.session_state:
        st.session_state.systems_initialized = False
    if 'current_api_key' not in st.session_state:
        st.session_state.current_api_key = None
    if 'using_custom_data' not in st.session_state:
        st.session_state.using_custom_data = False
    if 'custom_scenarios' not in st.session_state:
        st.session_state.custom_scenarios = []
    if 'content_summary' not in st.session_state:
        st.session_state.content_summary = ""
    if 'current_domain_hint' not in st.session_state:
        st.session_state.current_domain_hint = ""
    if 'data_processed' not in st.session_state:
        st.session_state.data_processed = False


def handle_api_key_setup(openai_api_key, domain_hint=None):
    """Handle API key setup and system initialization"""
    # Store domain hint in session state (using different key to avoid widget conflict)
    st.session_state.current_domain_hint = domain_hint or ""
    
    # Check if API key changed - reinitialize systems if needed
    api_key_changed = st.session_state.current_api_key != openai_api_key
    
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    elif "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    # Only initialize systems when explicitly needed (for imports or when user requests)
    # Don't auto-initialize just because API key is present
    
    if not st.session_state.systems_initialized:
        # Systems not initialized - initialize for imports only (no API calls)
        st.sidebar.info("🔄 Initializing systems (import-only, no API calls)...")
        
        # Create API key hash for cache invalidation
        api_key_hash = hashlib.md5("none".encode()).hexdigest()[:8]  # Always use "none" for import-only mode
        
        # Initialize systems with fresh database (cached)
        trad_rag, graph_rag = initialize_rag_systems(api_key_hash, domain_hint)
        st.session_state.trad_rag = trad_rag
        st.session_state.graph_rag = graph_rag
        st.session_state.systems_initialized = True
        st.session_state.current_api_key = None  # No API key used yet
        
    else:
        # Use existing systems
        trad_rag = st.session_state.trad_rag
        graph_rag = st.session_state.graph_rag
        
        # Check if API key changed and notify user
        if api_key_changed and openai_api_key:
            st.sidebar.success("✅ API key detected!")
            st.sidebar.info("💡 Load sample data to use the API key for processing")
        elif api_key_changed and not openai_api_key:
            st.sidebar.info("🔑 API key removed - import-only mode")
    
    return trad_rag, graph_rag


def clear_session_state():
    """Clear all session state and restart"""
    # Clear specific state variables while preserving others like widget states
    keys_to_clear = [
        'data_loaded', 'systems_initialized', 'current_api_key',
        'using_custom_data', 'custom_scenarios', 'content_summary',
        'trad_rag', 'graph_rag', 'data_processed'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
