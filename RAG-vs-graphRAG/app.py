"""
Streamlit App: RAG vs GraphRAG Comparison
Enterprise Knowledge Management Demo
"""
import streamlit as st
import time
import os
from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from traditional_rag import TraditionalRAG
from graph_rag import GraphRAG

# Import visualization modules
from visualizations import (
    render_traditional_rag_visualization,
    render_graph_rag_visualization,
    render_ontology_discovery_section
)

# Page config
st.set_page_config(
    page_title="RAG vs GraphRAG Comparison",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .method-header {
        font-size: 1.8rem;
        color: #ff7f0e;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .comparison-box {
        border: 2px solid #e6e6e6;
        border-radius: 10px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .traditional-rag {
        border-color: #ff7f0e;
    }
    .graph-rag {
        border-color: #2ca02c;
    }
    .insight-box {
        background-color: #f0f8ff;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def initialize_empty_systems():
    """Initialize empty RAG systems without any data"""
    # Initialize Traditional RAG (empty)
    trad_rag = TraditionalRAG()
    
    # Initialize GraphRAG with session-specific database path
    import time
    db_path = f"./graph_db_session_{int(time.time())}"
    graph_rag = GraphRAG(db_path=db_path)
    
    return trad_rag, graph_rag

def load_sample_data(trad_rag, graph_rag):
    """Load and process sample enterprise data"""
    data_dir = Path(__file__).parent / "data"
    
    with st.spinner("🔄 Loading sample enterprise documents..."):
        # Load into Traditional RAG
        documents = trad_rag.load_documents(str(data_dir))
        chunks = trad_rag.chunk_documents(documents)
        trad_rag.create_embeddings(chunks)
        
        # Load into GraphRAG
        graph_rag.load_documents(str(data_dir))
        
    st.success("✅ Sample data loaded successfully!")
    return True

# Clear cache when developing to ensure latest code is used
def clear_cache():
    """Clear Streamlit cache to reload updated classes"""
    pass  # Now handled in sidebar













def main():
    st.markdown('<h1 class="main-header">🔍 RAG vs GraphRAG: Enterprise Knowledge Base Enablement</h1>', 
                unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Configuration")
    
    # API Key input
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password", 
                                          help="Required for LLM-powered answers")
    
    # Initialize session state
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'systems_initialized' not in st.session_state:
        st.session_state.systems_initialized = False
    if 'current_api_key' not in st.session_state:
        st.session_state.current_api_key = None
    
    # Check if API key changed - reinitialize systems if needed
    api_key_changed = st.session_state.current_api_key != openai_api_key
    
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    elif "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    # Only initialize systems if we have an API key OR user specifically requests it
    if openai_api_key and (not st.session_state.systems_initialized or api_key_changed):
        st.sidebar.info("🔄 Initializing systems..." + (" (API key updated)" if api_key_changed else ""))
        
        trad_rag, graph_rag = initialize_empty_systems()
        st.session_state.trad_rag = trad_rag
        st.session_state.graph_rag = graph_rag
        st.session_state.systems_initialized = True
        st.session_state.current_api_key = openai_api_key
        
        # Clear data if API key changed to force reload with new key
        if api_key_changed and st.session_state.data_loaded:
            st.session_state.data_loaded = False
            st.sidebar.warning("🔄 API key changed - please reload data")
            
    elif st.session_state.systems_initialized:
        # Use existing systems
        trad_rag = st.session_state.trad_rag
        graph_rag = st.session_state.graph_rag
    else:
        # No API key and no systems - show placeholder
        trad_rag = None
        graph_rag = None
    
    st.sidebar.markdown("---")
    
    # Data loading controls
    st.sidebar.markdown("### 📂 Data Loading")
    
    # Data loading interface
    if not openai_api_key:
        st.sidebar.warning("⚠️ Please enter your OpenAI API key above to initialize the systems")
        
    elif not st.session_state.data_loaded:
        st.sidebar.info("🔄 Systems initialized but no data loaded")
        
        # Option 1: Load sample data
        if st.sidebar.button("📋 Load Sample Enterprise Data", 
                           help="Load sample documents about engineering decisions, meetings, specs, and support tickets"):
            if trad_rag and graph_rag and load_sample_data(trad_rag, graph_rag):
                st.session_state.data_loaded = True
                st.rerun()
        
        # Option 2: Upload custom data (placeholder for future)
        st.sidebar.markdown("🔮 **Coming Soon**: Upload your own documents")
        
    else:
        st.sidebar.success("✅ Data loaded successfully!")
        if st.sidebar.button("🗑️ Clear Data & Restart", 
                            help="Remove all data and start fresh"):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.cache_resource.clear()
            st.rerun()
    
    # Demo scenarios
    demo_scenarios = {
        "Cross-system Dependencies": "What technical issues are blocking our enterprise customers and how are they related?",
        "Customer Impact Analysis": "Which customers are affected by authentication service problems and what are the consequences?", 
        "Root Cause Investigation": "What is the root cause of dashboard performance issues and what systems are involved?",
        "Resource Planning": "What engineering resources and timeline are needed to resolve the current technical debt?",
        "Business Risk Assessment": "How do current technical problems impact customer satisfaction and business outcomes?"
    }
    
    selected_scenario = st.sidebar.selectbox("Demo Scenarios", list(demo_scenarios.keys()))
    custom_question = st.sidebar.text_area("Or ask your own question:", 
                                          value=demo_scenarios[selected_scenario])
    
    # System comparison toggle
    show_graph_viz = st.sidebar.checkbox("Show Knowledge Graph", value=True)
    
    # Add cache clear button in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Development Tools**")
    if st.sidebar.button("🔄 Clear Cache & Reload", help="Use this if you updated the code"):
        st.cache_resource.clear()
        st.rerun()
    
    # Only show main content if systems are initialized and data is loaded
    if not openai_api_key:
        st.info("🔑 Please enter your OpenAI API key in the sidebar to get started")
    elif not st.session_state.data_loaded:
        st.info("👈 Please load data from the sidebar to begin exploring RAG vs GraphRAG comparison")
        
        # Show empty state preview
        st.markdown("## 🎯 What You'll Explore")
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
        
        return
    
    # Main content - Core RAG vs GraphRAG Comparison
    if st.button("🚀 Run Comparison", type="primary"):
        question = custom_question.strip()
        if not question:
            st.warning("Please enter a question.")
            return
        
        st.markdown(f"**Question:** {question}")
        
        # Create columns for side-by-side comparison
        col1, col2 = st.columns(2)
        
        # Traditional RAG
        with col1:
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
        
        # GraphRAG
        with col2:
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

if __name__ == "__main__":
    main()
