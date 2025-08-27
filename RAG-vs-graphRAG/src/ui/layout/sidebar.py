"""
Sidebar Layout
Handles sidebar configuration, data loading, and export functionality
"""
import streamlit as st
import hashlib
from ...system.initialization import initialize_rag_systems
from ...system.session_state import clear_session_state
from ...data.loaders import load_sample_data
from ...data.importers import import_graph_data
from ...data.exporters import export_kuzu_database, export_pinecone_format, export_neo4j_format


def render_sidebar(openai_api_key, trad_rag, graph_rag, domain_hint=None):
    """Render the complete sidebar"""
    st.sidebar.title("Configuration")
    st.sidebar.markdown("---")
    
    # Data loading controls
    render_data_loading_section(openai_api_key, trad_rag, graph_rag, domain_hint)
    
    # Export functionality
    render_export_section(trad_rag, graph_rag)


def render_data_loading_section(openai_api_key, trad_rag, graph_rag, domain_hint=None):
    """Render the data loading section"""
    st.sidebar.markdown("### 📂 Data Loading")
    
    # Data loading interface
    if not st.session_state.data_loaded:
        # Primary option: API key workflow
        if openai_api_key:
            if st.sidebar.button("📋 Load Sample Enterprise Data", 
                               help="Load sample documents about engineering decisions, meetings, specs, and support tickets"):
                # Reinitialize systems with API key for processing
                st.sidebar.info("🔄 Initializing systems with API key for processing...")
                
                api_key_hash = hashlib.md5(openai_api_key.encode()).hexdigest()[:8]
                
                # Get fresh systems with API key and domain hint
                trad_rag, graph_rag = initialize_rag_systems(api_key_hash, domain_hint)
                st.session_state.trad_rag = trad_rag
                st.session_state.graph_rag = graph_rag
                st.session_state.current_api_key = openai_api_key
                
                if load_sample_data(trad_rag, graph_rag):
                    st.session_state.data_loaded = True
                    st.rerun()
        else:
            st.sidebar.info("💡 Enter API key above, then click 'Run Comparison' to auto-load sample data")
        
        # Alternative option: Import data
        st.sidebar.markdown("**OR**")
        uploaded_file = st.sidebar.file_uploader(
            "📤 Upload JSON 'Knowledge Graph' Array", 
            type=['json'],
            help="Upload a previously exported, or kuzudb compatible, graph database JSON file (no API key needed)"
        )
        
        if uploaded_file is not None:
            if st.sidebar.button("⏏️ Import Uploaded Data"):
                if trad_rag and graph_rag and import_graph_data(uploaded_file, trad_rag, graph_rag):
                    st.session_state.data_loaded = True
                    st.rerun()
                else:
                    st.sidebar.error("Failed to import data. Please try again.")
                    
    else:
        st.sidebar.success("✅ Data loaded successfully!")
        if st.sidebar.button("🗑️ Clear Data & Restart", 
                            help="Remove all data and start fresh"):
            clear_session_state()


def render_export_section(trad_rag, graph_rag):
    """Render the export functionality section"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📤 Export Data**")
    
    if 'data_loaded' in st.session_state and st.session_state.data_loaded:
        # Export Kuzu Database (main export)
        if st.sidebar.button("📊 Export Graph Database", help="Download complete graph data as JSON"):
            with st.spinner("Exporting graph database..."):
                export_kuzu_database(graph_rag)
        
        # Export for specific databases
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("🌲 Pinecone", help="Export for Pinecone vector DB"):
                export_pinecone_format(graph_rag)
        
        with col2:
            if st.button("🕸️ Neo4j", help="Export for Neo4j graph DB"):
                export_neo4j_format(graph_rag)
    else:
        st.sidebar.info("📊 Load data first to enable exports")
