"""
Data Loaders
Handles loading and processing of sample data
"""
import streamlit as st
from pathlib import Path
from ..system.initialization import check_graph_database_content


def load_sample_data(trad_rag, graph_rag):
    """Load and process sample enterprise data"""
    data_dir = Path(__file__).parent.parent.parent / "data"
    
    # Check if GraphRAG database already has data
    chunk_count, entity_count = check_graph_database_content(graph_rag)
    
    if chunk_count > 0 or entity_count > 0:
        st.info(f"📊 Database already contains data: {chunk_count} chunks, {entity_count} entities")
        st.success("✅ Using existing processed data!")
        
        # Still load Traditional RAG since it's not persistent
        with st.spinner("🔄 Loading data for Traditional RAG..."):
            documents = trad_rag.load_documents(str(data_dir))
            chunks = trad_rag.chunk_documents(documents)
            trad_rag.create_embeddings(chunks)
        
        return True
    else:
        # Database is empty, need to process data
        with st.spinner("🔄 Loading sample enterprise documents..."):
            # Load into Traditional RAG
            documents = trad_rag.load_documents(str(data_dir))
            chunks = trad_rag.chunk_documents(documents)
            trad_rag.create_embeddings(chunks)
            
            # Load into GraphRAG
            graph_rag.load_documents(str(data_dir))
            
        st.success("✅ Sample data loaded successfully!")
        return True
