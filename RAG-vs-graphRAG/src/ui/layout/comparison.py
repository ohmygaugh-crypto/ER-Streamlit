"""
Comparison Interface
Handles the main RAG vs GraphRAG comparison interface
"""
import streamlit as st
import time
import hashlib
from ...system.initialization import initialize_rag_systems
from ...data.loaders import load_sample_data
from ..visualizations import (
    render_traditional_rag_visualization,
    render_graph_rag_visualization,
    render_ontology_discovery_section
)


def render_comparison_interface(custom_question, openai_api_key, domain_hint=None):
    """Render the main comparison interface"""
    st.markdown("## 🎯 RAG vs GraphRAG Comparison")
    st.markdown("---")
    
    # Show different UI based on processing state
    if not st.session_state.data_loaded:
        render_method_preview(openai_api_key)
        handle_data_processing(openai_api_key, domain_hint)
    elif not st.session_state.get('data_processed', False):
        st.info("🔄 Data loaded but not processed. Click 'Process Data' to continue.")
        handle_data_processing(openai_api_key, domain_hint)
    else:
        # Data is processed, show query interface
        handle_query_execution(custom_question, openai_api_key)


def render_method_preview(openai_api_key):
    """Render preview of RAG methods when no data is loaded"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🔍 Traditional RAG
        - Vector similarity search
        - Document chunking  
        - Embedding-based retrieval
        """)
    
    with col2:
        st.markdown("""
        ### 🕸️ GraphRAG
        - Knowledge graph construction
        - Entity relationship mapping
        - Graph-enhanced retrieval
        """)
    
    # Show different messages based on state (moved here to be above Run Comparison button)
    if openai_api_key:
        st.info("💡 You can load sample data from the sidebar, or click 'Run Comparison' below to process data automatically")
    else:
        st.info("💡 1st Import your own data via sidebar OR enter API key'")


def handle_data_processing(openai_api_key, domain_hint=None):
    """Handle the data processing step (Step 1)"""
    # Disable button if already processing or processed
    processing_disabled = st.session_state.get('data_processed', False)
    button_text = "✅ Data Processed" if processing_disabled else "🔄 Process Data"
    
    if st.button(button_text, type="primary", disabled=processing_disabled):
        # Set processing flag immediately to prevent double-clicks
        st.session_state.data_processed = True
        
        # Handle data loading logic when Process Data is clicked
        if not st.session_state.data_loaded:
            if openai_api_key:
                # User has API key - load sample data automatically
                st.info("🔄 Loading sample data with API key...")
                
                # Reinitialize systems with API key for processing
                api_key_hash = hashlib.md5(openai_api_key.encode()).hexdigest()[:8]
                
                # Get fresh systems with API key
                trad_rag, graph_rag = initialize_rag_systems(api_key_hash, domain_hint)
                st.session_state.trad_rag = trad_rag
                st.session_state.graph_rag = graph_rag
                st.session_state.current_api_key = openai_api_key
                
                # Load sample data
                if load_sample_data(trad_rag, graph_rag):
                    st.session_state.data_loaded = True
                    st.rerun()  # Refresh to show question section
                else:
                    st.error("❌ Failed to load sample data")
                    return
            else:
                # No API key and no data - can't run comparison
                st.error("❌ Please either upload data via sidebar or enter an API key to use sample data")
                return
        else:
            # Data already loaded, processing complete
            st.rerun()


def handle_query_execution(custom_question, openai_api_key):
    """Handle the query execution step (Step 2)"""
    if st.button("🚀 Run Comparison", type="primary"):
        question = custom_question.strip()
        if not question:
            st.warning("Please enter a question.")
            return
        
        # Execute the comparison
        execute_rag_comparison(question)


def execute_rag_comparison(question):
    """Execute the actual RAG comparison"""
    st.markdown(f"**Question:** {question}")
    
    # Get current systems
    trad_rag = st.session_state.trad_rag
    graph_rag = st.session_state.graph_rag
    
    # Create columns for side-by-side comparison
    col1, col2 = st.columns(2)
    
    # Traditional RAG
    with col1:
        trad_result, trad_time = run_traditional_rag(trad_rag, question)
    
    # GraphRAG
    with col2:
        graph_result, graph_time = run_graph_rag(graph_rag, question)
    
    # Render visualizations
    render_comparison_visualizations(trad_rag, graph_rag, question, trad_result, graph_result)


def run_traditional_rag(trad_rag, question):
    """Run Traditional RAG and return results"""
    st.markdown('<div class="comparison-box traditional-rag">', unsafe_allow_html=True)
    st.markdown("## 🔍 Traditional RAG")
    
    with st.spinner("Running Traditional RAG..."):
        start_time = time.time()
        trad_result = trad_rag.answer_question(question)
        trad_time = time.time() - start_time
    
    st.markdown("### Answer:")
    st.write(trad_result['answer'])
    
    st.markdown("### Retrieved Context:")
    for i, chunk in enumerate(trad_result.get('retrieved_chunks', [])[:3]):
        with st.expander(f"Chunk {i+1} from {chunk.get('metadata', {}).get('filename', 'Unknown')}"):
            st.write(chunk.get('content', ''))
    
    # Metrics
    st.markdown("### Metrics:")
    st.metric("Confidence", f"{trad_result.get('confidence', 0):.2f}")
    st.metric("Response Time", f"{trad_time:.2f}s")
    st.metric("Chunks Retrieved", len(trad_result.get('retrieved_chunks', [])))
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    return trad_result, trad_time


def run_graph_rag(graph_rag, question):
    """Run GraphRAG and return results"""
    st.markdown('<div class="comparison-box graph-rag">', unsafe_allow_html=True)
    st.markdown("## 🕸️ GraphRAG")
    
    with st.spinner("Running GraphRAG..."):
        start_time = time.time()
        graph_result = graph_rag.answer_question(question)
        graph_time = time.time() - start_time
    
    st.markdown("### Answer:")
    st.write(graph_result['answer'])
    
    st.markdown("### Graph Insights:")
    for insight in graph_result.get('graph_insights', []):
        st.markdown(f"💡 {insight}")
    
    st.markdown("### Retrieved Context:")
    for i, chunk in enumerate(graph_result.get('retrieved_chunks', [])[:3]):
        with st.expander(f"Chunk {i+1} from {chunk.get('filename', 'Unknown')}"):
            st.write(chunk.get('content', ''))
            if chunk.get('source'):
                st.caption(f"Source: {chunk['source']}")
    
    # Metrics  
    st.markdown("### Metrics:")
    st.metric("Confidence", f"{graph_result.get('confidence', 0):.2f}")
    st.metric("Response Time", f"{graph_time:.2f}s")
    st.metric("Chunks Retrieved", len(graph_result.get('retrieved_chunks', [])))
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    return graph_result, graph_time


def render_comparison_visualizations(trad_rag, graph_rag, question, trad_result, graph_result):
    """Render the comparison visualizations"""
    # Advanced Visualizations
    st.markdown("---")
    st.markdown("## 🎯 Retrieval Method Visualization")
    st.markdown("**See how each approach finds relevant information differently**")
    
    # Side-by-side visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        render_traditional_rag_visualization(trad_rag, question, trad_result)
    
    with col2:
        render_graph_rag_visualization(trad_rag, graph_rag, question, trad_result, graph_result)

    # Ontology Discovery Section (Independent Feature)
    st.markdown("---")
    render_ontology_discovery_section(graph_rag)
