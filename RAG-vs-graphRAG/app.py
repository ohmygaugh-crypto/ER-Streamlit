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
def initialize_systems():
    """Initialize both RAG systems"""
    data_dir = Path(__file__).parent / "data"
    
    # Initialize Traditional RAG
    trad_rag = TraditionalRAG()
    documents = trad_rag.load_documents(str(data_dir))
    chunks = trad_rag.chunk_documents(documents)
    trad_rag.create_embeddings(chunks)
    
    # Initialize GraphRAG with unique database path
    import time
    db_path = f"./graph_db_{int(time.time())}"
    graph_rag = GraphRAG(db_path=db_path)
    graph_rag.load_documents(str(data_dir))
    
    return trad_rag, graph_rag

# Clear cache when developing to ensure latest code is used
def clear_cache():
    """Clear Streamlit cache to reload updated classes"""
    if st.button("🔄 Clear Cache & Reload", help="Use this if you updated the code"):
        st.cache_resource.clear()
        st.rerun()













def main():
    st.markdown('<h1 class="main-header">🔍 RAG vs GraphRAG: Enterprise Knowledge Base Enablement</h1>', 
                unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Configuration")
    
    # API Key input
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password", 
                                          help="Required for LLM-powered answers")
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key
    
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
    
    # Initialize systems
    with st.spinner("Initializing RAG systems..."):
        try:
            trad_rag, graph_rag = initialize_systems()
            st.sidebar.success("✅ Systems initialized!")
            
            # Check if GraphRAG has ontology methods (for debugging)
            if not hasattr(graph_rag, 'get_ontology_data'):
                st.sidebar.warning("⚠️ GraphRAG missing ontology methods. Click 'Clear Cache & Reload' above.")
            
        except Exception as e:
            st.error(f"Error initializing systems: {e}")
            st.stop()
    
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
