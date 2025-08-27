"""
System Initialization
Handles RAG system setup and configuration
"""
import streamlit as st
import time
import os
from pathlib import Path

# Import core RAG systems
from ..core.traditional_rag import TraditionalRAG
from ..core.graph_rag import GraphRAG


@st.cache_resource
def initialize_rag_systems(api_key_hash: str):
    """Initialize RAG systems with fresh database (cache keyed by API key)"""
    import time
    
    print(f"🔧 Initializing fresh RAG systems (API key: {'✅' if api_key_hash != 'none' else '❌'})...")
    
    # Always create a new database for clean JSON imports
    db_path = f"./graph_db_session_{int(time.time())}"
    
    # Initialize Traditional RAG (empty)
    trad_rag = TraditionalRAG(dev_mode=False)
    
    # Initialize GraphRAG with fresh database
    graph_rag = GraphRAG(db_path=db_path, dev_mode=False)
    
    return trad_rag, graph_rag


def check_graph_database_content(graph_rag):
    """Check if the GraphRAG database already contains data"""
    try:
        # Try to count existing chunks
        result = graph_rag.conn.execute("MATCH (c:Chunk) RETURN count(c) as chunk_count")
        chunk_count = 0
        if result.has_next():
            chunk_count = result.get_next()[0]
        
        # Try to count existing entities
        result = graph_rag.conn.execute("MATCH (e:Entity) RETURN count(e) as entity_count")
        entity_count = 0
        if result.has_next():
            entity_count = result.get_next()[0]
            
        return chunk_count, entity_count
    except Exception as e:
        return 0, 0


def initialize_app():
    """Initialize the Streamlit app configuration"""
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
