"""
Streamlit App: RAG vs GraphRAG Comparison
Enterprise Knowledge Management Demo
"""
import streamlit as st
import time
import os
from pathlib import Path
import sys
import glob

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

def load_sample_data(trad_rag, graph_rag):
    """Load and process sample enterprise data"""
    data_dir = Path(__file__).parent / "data"
    
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


def import_graph_data(uploaded_file, trad_rag, graph_rag):
    """Import previously exported graph data into Kuzu database"""
    try:
        # Read the uploaded JSON file
        import json
        data = json.load(uploaded_file)
        
        # Validate the data structure
        if not isinstance(data, dict) or 'chunks' not in data:
            st.error("❌ Invalid file format. Please upload a valid graph export JSON.")
            return False
        
        chunks = data.get('chunks', [])
        entities = data.get('entities', [])
        relationships = data.get('relationships', [])
        
        with st.spinner(f"🚀 Native Kuzu import: {len(chunks)} chunks, {len(entities)} entities, {len(relationships)} relationships..."):
            
            # Use native Kuzu JSON import
            success = graph_rag.import_from_kuzu_json(data)
            
            if not success:
                st.error("❌ Native Kuzu import failed")
                return False
            
            # Prepare Traditional RAG data from chunks
            st.info("🔄 Setting up Traditional RAG...")
            
            # Group chunks by document and create traditional RAG chunks
            from collections import defaultdict
            doc_groups = defaultdict(list)
            for chunk in chunks:
                doc_groups[chunk['filename']].append(chunk['content'])
            
            # Create documents for Traditional RAG
            trad_documents = []
            for filename, chunk_contents in doc_groups.items():
                full_content = '\n\n'.join(chunk_contents)
                trad_documents.append({
                    'filename': filename,
                    'content': full_content,
                    'filepath': filename
                })
            
            # Process for Traditional RAG
            trad_chunks = trad_rag.chunk_documents(trad_documents)
            trad_rag.create_embeddings(trad_chunks)
            
            # Store documents for GraphRAG
            graph_rag.documents = trad_documents
            
            # Rebuild entity mappings from imported data
            graph_rag.entity_mappings = {}
            for entity in entities:
                entity_name = entity['name'].lower().replace(' ', '_')
                if entity_name not in graph_rag.entity_mappings:
                    graph_rag.entity_mappings[entity_name] = []
                
                # Find chunks related to this entity through relationships (updated for native format)
                related_chunk_ids = [
                    rel['to'] for rel in relationships 
                    if rel['from'] == entity['id']  # Updated for native Kuzu format
                ]
                graph_rag.entity_mappings[entity_name].extend(related_chunk_ids)
            
            print(f"🔗 Rebuilt entity mappings for {len(graph_rag.entity_mappings)} entities")
        
        st.success(f"✅ Native Kuzu import successful: {len(chunks)} chunks, {len(entities)} entities, {len(relationships)} relationships!")
        return True
        
    except json.JSONDecodeError:
        st.error("❌ Invalid JSON file. Please check the file format.")
        return False
    except Exception as e:
        st.error(f"❌ Import error: {str(e)}")
        return False

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
    
    # Only initialize systems when explicitly needed (for imports or when user requests)
    # Don't auto-initialize just because API key is present
    
    if not st.session_state.systems_initialized:
        # Systems not initialized - initialize for imports only (no API calls)
        st.sidebar.info("🔄 Initializing systems (import-only, no API calls)...")
        
        # Create API key hash for cache invalidation
        import hashlib
        api_key_hash = hashlib.md5("none".encode()).hexdigest()[:8]  # Always use "none" for import-only mode
        
        # Initialize systems with fresh database (cached)
        trad_rag, graph_rag = initialize_rag_systems(api_key_hash)
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
    
    st.sidebar.markdown("---")
    
    # Data loading controls
    st.sidebar.markdown("### 📂 Data Loading")
    
    # Data loading interface
    if not st.session_state.data_loaded:
        # Primary option: API key workflow
        if openai_api_key:
            if st.sidebar.button("📋 Load Sample Enterprise Data", 
                               help="Load sample documents about engineering decisions, meetings, specs, and support tickets"):
                # Reinitialize systems with API key for processing
                st.sidebar.info("🔄 Initializing systems with API key for processing...")
                
                import hashlib
                api_key_hash = hashlib.md5(openai_api_key.encode()).hexdigest()[:8]
                
                # Get fresh systems with API key
                trad_rag, graph_rag = initialize_rag_systems(api_key_hash)
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
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    

    

    
    # Export functionality
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📤 Export Data**")
    
    if 'data_loaded' in st.session_state and st.session_state.data_loaded:
        trad_rag = st.session_state.trad_rag
        graph_rag = st.session_state.graph_rag
        
        # Export Kuzu Database (main export)
        if st.sidebar.button("📊 Export Graph Database", help="Download complete graph data as JSON"):
            with st.spinner("Exporting graph database..."):
                try:
                    export_data = graph_rag.export_kuzu_database()
                    if 'error' not in export_data:
                        import json
                        json_data = json.dumps(export_data, indent=2)
                        
                        st.sidebar.download_button(
                            label="⬇️ Download Graph Export",
                            data=json_data,
                            file_name=f"graph_export_{Path(graph_rag.db_path).name}.json",
                            mime="application/json",
                            help="Complete graph data: chunks, entities, relationships, embeddings"
                        )
                        
                        st.sidebar.success(f"✅ Ready! {len(export_data['chunks'])} chunks, {len(export_data['entities'])} entities")
                    else:
                        st.sidebar.error(f"Export failed: {export_data['error']}")
                except Exception as e:
                    st.sidebar.error(f"Export error: {str(e)}")
        
        # Export for specific databases
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("🌲 Pinecone", help="Export for Pinecone vector DB"):
                try:
                    # Create Pinecone-formatted data from graph export
                    export_data = graph_rag.export_kuzu_database()
                    pinecone_data = {
                        "vectors": [
                            {
                                "id": chunk["id"],
                                "values": chunk["embedding"],
                                "metadata": {
                                    "content": chunk["content"][:1000],
                                    "filename": chunk["filename"],
                                    "chunk_index": chunk["chunk_index"]
                                }
                            }
                            for chunk in export_data["chunks"]
                        ],
                        "metadata": {
                            "total_vectors": len(export_data["chunks"]),
                            "embedding_dimension": len(export_data["chunks"][0]["embedding"]) if export_data["chunks"] else 0
                        }
                    }
                    
                    import json
                    json_data = json.dumps(pinecone_data, indent=2)
                    st.sidebar.download_button(
                        label="⬇️ Pinecone JSON",
                        data=json_data,
                        file_name="pinecone_vectors.json",
                        mime="application/json"
                    )
                except Exception as e:
                    st.sidebar.error(f"Pinecone export error: {str(e)}")
        
        with col2:
            if st.button("🕸️ Neo4j", help="Export for Neo4j graph DB"):
                try:
                    export_data = graph_rag.export_kuzu_database()
                    
                    # Create Neo4j CSV data
                    import io
                    import csv
                    import zipfile
                    
                    # Create in-memory zip file
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        # Chunks CSV
                        chunks_csv = io.StringIO()
                        chunks_writer = csv.writer(chunks_csv)
                        chunks_writer.writerow(['chunk_id:ID', 'content', 'filename', 'chunk_index:int', ':LABEL'])
                        for chunk in export_data['chunks']:
                            chunks_writer.writerow([
                                chunk['id'],
                                chunk['content'].replace('"', '""'),
                                chunk['filename'],
                                chunk['chunk_index'],
                                'Chunk'
                            ])
                        zip_file.writestr('chunks.csv', chunks_csv.getvalue())
                        
                        # Entities CSV
                        entities_csv = io.StringIO()
                        entities_writer = csv.writer(entities_csv)
                        entities_writer.writerow(['entity_id:ID', 'name', 'type', ':LABEL'])
                        for entity in export_data['entities']:
                            entities_writer.writerow([
                                entity['id'],
                                entity['name'],
                                entity['type'],
                                'Entity'
                            ])
                        zip_file.writestr('entities.csv', entities_csv.getvalue())
                        
                        # Import script
                        import_script = f"""// Neo4j Import Script
LOAD CSV WITH HEADERS FROM 'file:///chunks.csv' AS row
CREATE (c:Chunk {{
    id: row.chunk_id,
    content: row.content,
    filename: row.filename,
    chunk_index: toInteger(row.chunk_index)
}});

LOAD CSV WITH HEADERS FROM 'file:///entities.csv' AS row
CREATE (e:Entity {{
    id: row.entity_id,
    name: row.name,
    type: row.type
}});

CREATE INDEX chunk_id_index FOR (c:Chunk) ON (c.id);
CREATE INDEX entity_id_index FOR (e:Entity) ON (e.id);
"""
                        zip_file.writestr('import_script.cypher', import_script)
                    
                    zip_buffer.seek(0)
                    st.sidebar.download_button(
                        label="⬇️ Neo4j ZIP",
                        data=zip_buffer.getvalue(),
                        file_name="neo4j_import.zip",
                        mime="application/zip"
                    )
                except Exception as e:
                    st.sidebar.error(f"Neo4j export error: {str(e)}")
    else:
        st.sidebar.info("📊 Load data first to enable exports")
    
    # Always show the main comparison interface
    st.markdown("## 🎯 RAG vs GraphRAG Comparison")
    
    # Demo scenarios and question input (moved from sidebar to main page)
    st.markdown("### 💭 Ask a Question")
    
    demo_scenarios = {
        "Cross-system Dependencies": "What technical issues are blocking our enterprise customers and how are they related?",
        "Customer Impact Analysis": "Which customers are affected by authentication service problems and what are the consequences?", 
        "Root Cause Investigation": "What is the root cause of dashboard performance issues and what systems are involved?",
        "Resource Planning": "What engineering resources and timeline are needed to resolve the current technical debt?",
        "Business Risk Assessment": "How do current technical problems impact customer satisfaction and business outcomes?"
    }
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_scenario = st.selectbox("🎯 Demo Scenarios", list(demo_scenarios.keys()), key="demo_scenario")
        custom_question = st.text_area("📝 Your Question:", 
                                      value=demo_scenarios[selected_scenario],
                                      height=100,
                                      key="main_question")
    
    with col2:
        st.markdown("**Options:**")
        show_graph_viz = st.checkbox("Show Knowledge Graph", value=True)
    
    st.markdown("---")
    
    # Show preview of what will be compared
    if not st.session_state.data_loaded:
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
    
    # Main content - Core RAG vs GraphRAG Comparison
    if st.button("🚀 Run Comparison", type="primary"):
        question = custom_question.strip()
        if not question:
            st.warning("Please enter a question.")
            return
        
        # Handle data loading logic when Run Comparison is clicked
        if not st.session_state.data_loaded:
            if openai_api_key:
                # User has API key - load sample data automatically
                st.info("🔄 Loading sample data with API key...")
                
                # Reinitialize systems with API key for processing
                import hashlib
                api_key_hash = hashlib.md5(openai_api_key.encode()).hexdigest()[:8]
                
                # Get fresh systems with API key
                trad_rag, graph_rag = initialize_rag_systems(api_key_hash)
                st.session_state.trad_rag = trad_rag
                st.session_state.graph_rag = graph_rag
                st.session_state.current_api_key = openai_api_key
                
                # Load sample data
                if load_sample_data(trad_rag, graph_rag):
                    st.session_state.data_loaded = True
                    st.success("✅ Sample data loaded successfully!")
                else:
                    st.error("❌ Failed to load sample data")
                    return
            else:
                # No API key and no data - can't run comparison
                st.error("❌ Please either upload data via sidebar or enter an API key to use sample data")
            return
        
        st.markdown(f"**Question:** {question}")
        
        # Get current systems
        trad_rag = st.session_state.trad_rag
        graph_rag = st.session_state.graph_rag
        
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
