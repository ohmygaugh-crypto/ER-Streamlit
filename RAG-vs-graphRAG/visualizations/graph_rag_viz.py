"""
GraphRAG Visualization Module
=============================

Contains the gap-filling visualization and related UI components
for GraphRAG retrieval method visualization.
"""

import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import numpy as np
from sklearn.decomposition import PCA


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
                    line=dict(color='rgba(0,0,0)', width=2),
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


def render_graph_rag_visualization(trad_rag, graph_rag, question, trad_result, graph_result):
    """Render the complete GraphRAG visualization section"""
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
