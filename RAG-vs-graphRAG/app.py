"""
Streamlit App: RAG vs GraphRAG Comparison
Enterprise Knowledge Management Demo
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import networkx as nx
from streamlit_agraph import agraph, Node, Edge, Config
import time
import os
from pathlib import Path
import sys
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from traditional_rag import TraditionalRAG
from graph_rag import GraphRAG

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



def create_vector_space_visualization(trad_rag, query, retrieved_chunks):
    """Create 3D vector space visualization showing query and retrieved chunks"""
    if not hasattr(trad_rag, 'chunks_metadata') or not trad_rag.chunks_metadata:
        return None
    
    # Get all chunk embeddings
    all_embeddings = []
    all_labels = []
    all_colors = []
    all_sizes = []
    
    # Generate embeddings for all chunks
    for i, chunk_meta in enumerate(trad_rag.chunks_metadata):
        embedding = trad_rag.embedding_model.encode([chunk_meta['content']])[0]
        all_embeddings.append(embedding)
        
        # Check if this chunk was retrieved
        is_retrieved = any(ret['id'] == chunk_meta['chunk_id'] for ret in retrieved_chunks)
        
        if is_retrieved:
            all_labels.append(f"Retrieved: {chunk_meta['filename'][:20]}...")
            all_colors.append('#ff7f0e')  # Orange for retrieved
            all_sizes.append(12)
        else:
            all_labels.append(f"Not retrieved: {chunk_meta['filename'][:20]}...")
            all_colors.append('#d3d3d3')  # Gray for not retrieved
            all_sizes.append(8)
    
    # Add query embedding
    query_embedding = trad_rag.embedding_model.encode([query])[0]
    all_embeddings.append(query_embedding)
    all_labels.append(f"Query: {query[:30]}...")
    all_colors.append('#2ca02c')  # Green for query
    all_sizes.append(15)
    
    # Reduce dimensionality to 3D using PCA
    embeddings_array = np.array(all_embeddings)
    pca = PCA(n_components=3)
    embeddings_3d = pca.fit_transform(embeddings_array)
    
    # Create 3D scatter plot
    fig = go.Figure()
    
    # Plot non-retrieved chunks
    non_retrieved_mask = np.array(all_colors) == '#d3d3d3'
    if np.any(non_retrieved_mask):
        fig.add_trace(go.Scatter3d(
            x=embeddings_3d[non_retrieved_mask, 0],
            y=embeddings_3d[non_retrieved_mask, 1],
            z=embeddings_3d[non_retrieved_mask, 2],
            mode='markers',
            name='Not Retrieved',
            marker=dict(size=6, color='#d3d3d3', opacity=0.6),
            text=[all_labels[i] for i in range(len(all_labels)) if non_retrieved_mask[i]],
            hovertemplate='%{text}<extra></extra>'
        ))
    
    # Plot retrieved chunks with connecting lines to query
    retrieved_mask = np.array(all_colors) == '#ff7f0e'
    if np.any(retrieved_mask):
        # Add retrieved chunks
        fig.add_trace(go.Scatter3d(
            x=embeddings_3d[retrieved_mask, 0],
            y=embeddings_3d[retrieved_mask, 1],
            z=embeddings_3d[retrieved_mask, 2],
            mode='markers',
            name='Retrieved by RAG',
            marker=dict(size=10, color='#ff7f0e', symbol='circle'),
            text=[all_labels[i] for i in range(len(all_labels)) if retrieved_mask[i]],
            hovertemplate='%{text}<extra></extra>'
        ))
        
        # Add connecting lines from query to retrieved chunks
        query_pos = embeddings_3d[-1]  # Query is last in array
        for i, is_retrieved in enumerate(retrieved_mask[:-1]):  # Exclude query itself
            if is_retrieved:
                chunk_pos = embeddings_3d[i]
                fig.add_trace(go.Scatter3d(
                    x=[query_pos[0], chunk_pos[0]],
                    y=[query_pos[1], chunk_pos[1]],
                    z=[query_pos[2], chunk_pos[2]],
                    mode='lines',
                    line=dict(color='#ff7f0e', width=3, dash='dot'),
                    showlegend=False,
                    hoverinfo='skip'
                ))
    
    # Plot query as a diamond
    query_mask = np.array(all_colors) == '#2ca02c'
    if np.any(query_mask):
        fig.add_trace(go.Scatter3d(
            x=embeddings_3d[query_mask, 0],
            y=embeddings_3d[query_mask, 1],
            z=embeddings_3d[query_mask, 2],
            mode='markers+text',
            name='Query',
            marker=dict(size=15, color='#2ca02c', symbol='diamond'),
            text=['QUERY'],
            textposition='top center',
            hovertemplate=f'Query: {query}<extra></extra>'
        ))
    
    fig.update_layout(
        title='3D Vector Space: Traditional RAG Retrieval',
        scene=dict(
            xaxis_title=f'PC1 ({pca.explained_variance_ratio_[0]:.1%})',
            yaxis_title=f'PC2 ({pca.explained_variance_ratio_[1]:.1%})',
            zaxis_title=f'PC3 ({pca.explained_variance_ratio_[2]:.1%})',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
        ),
        height=500,
        margin=dict(l=0, r=0, b=0, t=40)
    )
    
    return fig

def create_graph_traversal_visualization(trad_rag, graph_rag, query, trad_retrieved_chunks, graph_retrieved_chunks):
    """Create 3D visualization showing chunks + 2D graph plane + GraphRAG gap-filling"""
    if not hasattr(trad_rag, 'chunks_metadata') or not trad_rag.chunks_metadata:
        return None
    
    # Get chunk embeddings and positions (similar to vector space)
    all_embeddings = []
    chunk_info = []
    
    for chunk_meta in trad_rag.chunks_metadata:
        embedding = trad_rag.embedding_model.encode([chunk_meta['content']])[0]
        all_embeddings.append(embedding)
        
        # Determine if chunk was retrieved by each method
        trad_retrieved = any(ret['id'] == chunk_meta['chunk_id'] for ret in trad_retrieved_chunks)
        graph_retrieved = any(ret['id'] == chunk_meta['chunk_id'] for ret in graph_retrieved_chunks)
        
        chunk_info.append({
            'id': chunk_meta['chunk_id'],
            'content': chunk_meta['content'][:100] + "...",
            'filename': chunk_meta['filename'],
            'trad_retrieved': trad_retrieved,
            'graph_retrieved': graph_retrieved,
            'embedding': embedding
        })
    
    # Add query embedding
    query_embedding = trad_rag.embedding_model.encode([query])[0]
    all_embeddings.append(query_embedding)
    
    # Project to 3D space
    embeddings_array = np.array(all_embeddings)
    pca = PCA(n_components=3)
    embeddings_3d = pca.fit_transform(embeddings_array)
    
    # Separate query position
    query_pos = embeddings_3d[-1]
    chunk_positions = embeddings_3d[:-1]
    
    # Update chunk info with 3D positions
    for i, chunk in enumerate(chunk_info):
        chunk['pos'] = chunk_positions[i]
    
    # Create the visualization
    fig = go.Figure()
    
    # 1. Add 2D Knowledge Graph Plane (at z=0)
    graph_data = graph_rag.get_graph_visualization_data()
    if graph_data.get('nodes') and graph_data.get('edges'):
        # Create 2D graph layout
        G = nx.Graph()
        for node in graph_data['nodes']:
            G.add_node(node['id'], type=node['type'])
        for edge in graph_data['edges']:
            if edge['source'] in [n['id'] for n in graph_data['nodes']] and \
               edge['target'] in [n['id'] for n in graph_data['nodes']]:
                G.add_edge(edge['source'], edge['target'])
        
        pos_2d = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        # Add graph edges on the z=0 plane
        for edge in G.edges():
            if edge[0] in pos_2d and edge[1] in pos_2d:
                x0, y0 = pos_2d[edge[0]]
                x1, y1 = pos_2d[edge[1]]
                fig.add_trace(go.Scatter3d(
                    x=[x0*2, x1*2], y=[y0*2, y1*2], z=[0, 0],
                    mode='lines',
                    line=dict(color='rgba(100,100,100,0.3)', width=2),
                    hoverinfo='none',
                    showlegend=False
                ))
        
        # Add graph nodes on the z=0 plane
        node_colors = {
            'CUSTOMER': '#ff7f0e', 'SYSTEM_COMPONENT': '#2ca02c', 
            'TECHNOLOGY': '#d62728', 'PERSON': '#9467bd',
            'ORG': '#e377c2', 'FEATURE': '#17becf'
        }
        
        for node in graph_data['nodes']:
            if node['id'] in pos_2d:
                x, y = pos_2d[node['id']]
                color = node_colors.get(node['type'], '#1f77b4')
                fig.add_trace(go.Scatter3d(
                    x=[x*2], y=[y*2], z=[0],
                    mode='markers+text',
                    marker=dict(size=8, color=color, opacity=0.8),
                    text=[node['id'].replace('entity_', '').replace('_', ' ')[:15]],
                    textposition='top center',
                    name=f"Graph: {node['type'].replace('_', ' ')}",
                    hovertemplate=f"{node['id']}<br>Type: {node['type']}<extra></extra>",
                    legendgroup='graph'
                ))
    
    # 2. Add floating chunks in 3D space
    # Chunks only retrieved by Traditional RAG
    trad_only_chunks = [c for c in chunk_info if c['trad_retrieved'] and not c['graph_retrieved']]
    if trad_only_chunks:
        fig.add_trace(go.Scatter3d(
            x=[c['pos'][0] for c in trad_only_chunks],
            y=[c['pos'][1] for c in trad_only_chunks],
            z=[c['pos'][2] for c in trad_only_chunks],
            mode='markers',
            marker=dict(size=10, color='#ff7f0e', symbol='circle'),
            name='Traditional RAG Only',
            hovertemplate='%{text}<br>Traditional RAG found this<extra></extra>',
            text=[f"{c['filename']}: {c['content']}" for c in trad_only_chunks]
        ))
    
    # Chunks retrieved by both methods  
    both_chunks = [c for c in chunk_info if c['trad_retrieved'] and c['graph_retrieved']]
    if both_chunks:
        fig.add_trace(go.Scatter3d(
            x=[c['pos'][0] for c in both_chunks],
            y=[c['pos'][1] for c in both_chunks], 
            z=[c['pos'][2] for c in both_chunks],
            mode='markers',
            marker=dict(size=12, color='#32CD32', symbol='circle'),
            name='Found by Both',
            hovertemplate='%{text}<br>Found by both methods<extra></extra>',
            text=[f"{c['filename']}: {c['content']}" for c in both_chunks]
        ))
    
    # 3. GRAPHRAG GAP-FILLING: Chunks only found by GraphRAG (the magic!)
    graph_only_chunks = [c for c in chunk_info if not c['trad_retrieved'] and c['graph_retrieved']]
    if graph_only_chunks:
        fig.add_trace(go.Scatter3d(
            x=[c['pos'][0] for c in graph_only_chunks],
            y=[c['pos'][1] for c in graph_only_chunks],
            z=[c['pos'][2] for c in graph_only_chunks],
            mode='markers',
            marker=dict(size=14, color='#DC143C', symbol='diamond', line=dict(width=2, color='#FFD700')),
            name='GraphRAG Gap-Filling',
            hovertemplate='%{text}<br><b>GraphRAG found this through entity relationships!</b><extra></extra>',
            text=[f"{c['filename']}: {c['content']}" for c in graph_only_chunks]
        ))
        
        # Add connection lines from graph plane to gap-filling chunks
        for chunk in graph_only_chunks:
            # Find the nearest graph entity (simplified)
            if graph_data.get('nodes') and pos_2d:
                nearest_entity = list(pos_2d.keys())[0]  # Simplified - could be more sophisticated
                if nearest_entity in pos_2d:
                    graph_x, graph_y = pos_2d[nearest_entity]
                    fig.add_trace(go.Scatter3d(
                        x=[graph_x*2, chunk['pos'][0]],
                        y=[graph_y*2, chunk['pos'][1]], 
                        z=[0, chunk['pos'][2]],
                        mode='lines',
                        line=dict(color='#DC143C', width=4, dash='dash'),
                        showlegend=False,
                        hoverinfo='none'
                    ))
    
    # 4. Add ignored chunks (gray)
    ignored_chunks = [c for c in chunk_info if not c['trad_retrieved'] and not c['graph_retrieved']]
    if ignored_chunks:
        fig.add_trace(go.Scatter3d(
            x=[c['pos'][0] for c in ignored_chunks],
            y=[c['pos'][1] for c in ignored_chunks],
            z=[c['pos'][2] for c in ignored_chunks],
            mode='markers',
            marker=dict(size=6, color='#D3D3D3', opacity=0.4),
            name='Not Retrieved',
            hovertemplate='%{text}<br>Not retrieved by either method<extra></extra>',
            text=[f"{c['filename']}: {c['content']}" for c in ignored_chunks]
        ))
    
    # 5. Add query position
    fig.add_trace(go.Scatter3d(
        x=[query_pos[0]], y=[query_pos[1]], z=[query_pos[2]],
        mode='markers+text',
        marker=dict(size=16, color='#2E8B57', symbol='diamond'),
        text=['QUERY'],
        name='Query',
        textposition='top center',
        hovertemplate=f'Query: {query}<extra></extra>'
    ))
    
    # Update layout
    fig.update_layout(
        title='GraphRAG Gap-Filling: How Knowledge Graph Finds Missing Chunks',
        scene=dict(
            xaxis_title='Semantic Space X',
            yaxis_title='Semantic Space Y',
            zaxis_title='Chunk Elevation',
            camera=dict(eye=dict(x=1.2, y=1.2, z=1.2)),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.8)
        ),
        height=500,
        margin=dict(l=0, r=0, b=0, t=40),
        showlegend=True,
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig

def create_retrieval_comparison_visualization(trad_chunks, graph_chunks, query):
    """Create side-by-side comparison of what each method retrieved"""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Traditional RAG Retrieved', 'GraphRAG Retrieved'),
        specs=[[{"type": "scatter"}, {"type": "scatter"}]]
    )
    
    # Traditional RAG chunks
    trad_files = [chunk.get('metadata', {}).get('filename', 'Unknown') for chunk in trad_chunks]
    trad_chunks_count = {}
    for file in trad_files:
        trad_chunks_count[file] = trad_chunks_count.get(file, 0) + 1
    
    if trad_chunks_count:
        fig.add_trace(
            go.Bar(
                x=list(trad_chunks_count.keys()),
                y=list(trad_chunks_count.values()),
                name='Traditional RAG',
                marker_color='#ff7f0e',
                text=list(trad_chunks_count.values()),
                textposition='auto'
            ),
            row=1, col=1
        )
    
    # GraphRAG chunks
    graph_files = [chunk.get('filename', 'Unknown') for chunk in graph_chunks]
    graph_chunks_count = {}
    for file in graph_files:
        graph_chunks_count[file] = graph_chunks_count.get(file, 0) + 1
    
    if graph_chunks_count:
        fig.add_trace(
            go.Bar(
                x=list(graph_chunks_count.keys()),
                y=list(graph_chunks_count.values()),
                name='GraphRAG',
                marker_color='#2ca02c',
                text=list(graph_chunks_count.values()),
                textposition='auto'
            ),
            row=1, col=2
        )
    
    fig.update_layout(
        title=f'Retrieval Sources Comparison for: "{query[:50]}..."',
        showlegend=False,
        height=400
    )
    
    fig.update_xaxes(title_text="Document", row=1, col=1)
    fig.update_xaxes(title_text="Document", row=1, col=2)
    fig.update_yaxes(title_text="Chunks Retrieved", row=1, col=1)
    fig.update_yaxes(title_text="Chunks Retrieved", row=1, col=2)
    
    return fig

def main():
    st.markdown('<h1 class="main-header">🔍 RAG vs GraphRAG: Enterprise Knowledge Management</h1>', 
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
    
    # Initialize systems
    with st.spinner("Initializing RAG systems..."):
        try:
            trad_rag, graph_rag = initialize_systems()
            st.sidebar.success("✅ Systems initialized!")
        except Exception as e:
            st.error(f"Error initializing systems: {e}")
            st.stop()
    
    # Main content
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
            st.markdown("### 📊 3D Vector Space: Traditional RAG")
            st.markdown("**Interactive 3D view** showing document chunks in vector space with connecting lines to retrieved chunks.")
            
            with st.spinner("Creating 3D vector space visualization..."):
                vector_fig = create_vector_space_visualization(trad_rag, question, trad_result.get('retrieved_chunks', []))
            
            if vector_fig:
                st.plotly_chart(vector_fig, use_container_width=True)
                
                st.markdown("""
                **🔍 3D Traditional RAG:**
                - **💎 Green Diamond**: Your query position in 3D space
                - **🟠 Orange Spheres**: Selected chunks (closest in vector space)
                - **⚪ Dotted Lines**: Direct similarity connections to query
                - **⚫ Gray Dots**: Ignored chunks (distant in semantic space)
                - **🔄 Rotate & Zoom**: Explore the 3D clustering patterns
                """)
            else:
                st.warning("Could not create vector space visualization")
        
        with col2:
            st.markdown("### 🕸️ GraphRAG Gap-Filling: Knowledge Graph + Chunks") 
            st.markdown("**2D graph plane + 3D floating chunks** showing how GraphRAG bridges to find missing information.")
            
            with st.spinner("Creating GraphRAG gap-filling visualization..."):
                graph_data = graph_rag.get_graph_visualization_data()
                query_entities = graph_rag.extract_entities(question, "query") if hasattr(graph_rag, 'extract_entities') else []
            
            if graph_data.get('nodes'):
                graph_viz = create_graph_traversal_visualization(
                    trad_rag, graph_rag, question, 
                    trad_result.get('retrieved_chunks', []), 
                    graph_result.get('retrieved_chunks', [])
                )
                st.plotly_chart(graph_viz, use_container_width=True)
                
                st.markdown("""
                **🕸️ GraphRAG Gap-Filling Magic:**
                - **2D Graph Plane (z=0)**: Entity relationship network as foundation
                - **🟢 Green Chunks**: Found by both methods (baseline similarity)
                - **🟠 Orange Chunks**: Traditional RAG only (pure similarity)
                - **💎 Red Diamonds**: GraphRAG gap-filling (relationship bridges!)
                - **Dashed Lines**: How graph entities connect to outlier chunks
                - **The Story**: GraphRAG uses relationships to reach relevant chunks that similarity search missed
                """)
            else:
                st.warning("No graph data available for visualization")
        
        # Graph statistics below both visualizations
        if graph_data.get('nodes'):
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🏷️ Entities", len(graph_data['nodes']))
            with col2:
                st.metric("🔗 Relationships", len(graph_data['edges']))
            with col3:
                entity_types = len(set(node['type'] for node in graph_data['nodes']))
                st.metric("📁 Entity Types", entity_types)
            with col4:
                rel_types = len(set(edge['relationship'] for edge in graph_data['edges']))
                st.metric("🔀 Relationship Types", rel_types)
        
        # Retrieval source comparison (simplified)
        st.markdown("---")
        st.markdown("### 📈 Source Document Analysis")
        
        trad_files = set(chunk.get('metadata', {}).get('filename', 'Unknown') for chunk in trad_result.get('retrieved_chunks', []))
        graph_files = set(chunk.get('filename', 'Unknown') for chunk in graph_result.get('retrieved_chunks', []))
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            st.markdown("**📊 Traditional RAG Sources:**")
            for file in sorted(trad_files):
                st.markdown(f"• {file}")
        
        with col2:
            st.markdown("**🕸️ GraphRAG Sources:**")  
            for file in sorted(graph_files):
                st.markdown(f"• {file}")
        
        with col3:
            # Highlight unique sources
            only_trad = trad_files - graph_files
            only_graph = graph_files - trad_files
            both = trad_files & graph_files
            
            st.markdown("**🔍 Source Comparison:**")
            if both:
                st.markdown(f"**Both found:** {len(both)} documents")
            if only_trad:
                st.markdown(f"**Only Traditional:** {len(only_trad)} documents")
            if only_graph:
                st.markdown(f"**Only GraphRAG:** {len(only_graph)} documents")
                
            if only_graph:
                st.success(f"GraphRAG found {len(only_graph)} additional source(s) through entity relationships!")
    
    # System statistics
    st.markdown("---")
    st.markdown("## 📈 System Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Traditional RAG Stats")
        trad_stats = trad_rag.get_stats()
        for key, value in trad_stats.items():
            st.text(f"{key}: {value}")
    
    with col2:
        st.markdown("### GraphRAG Stats")
        graph_stats = graph_rag.get_stats()
        for key, value in graph_stats.items():
            st.text(f"{key}: {value}")
    
    # Key Insights
    st.markdown("---")
    st.markdown("## 💡 Key Insights")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🎯 **Traditional RAG Limitations**")
        st.markdown("""
        - **Isolated Chunks**: Only finds semantically similar text
        - **No Relationships**: Misses connections between entities
        - **Limited Context**: Can't trace dependencies across documents
        - **Surface-Level**: Provides answers without deeper insights
        """)
    
    with col2:
        st.markdown("### 🕸️ **GraphRAG Advantages**")
        st.markdown("""
        - **Entity Resolution**: Links "TechCorp" → "auth service" → "dashboard issues"
        - **Multi-hop Reasoning**: Follows relationships across multiple documents
        - **Hidden Patterns**: Reveals that customer churn risk stems from technical debt
        - **Business Intelligence**: Maps technical decisions to customer impact
        """)

if __name__ == "__main__":
    main()
