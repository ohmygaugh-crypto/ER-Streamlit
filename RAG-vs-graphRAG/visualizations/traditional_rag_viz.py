"""
Traditional RAG Visualization Module
====================================

Contains the 3D vector space visualization and related UI components
for Traditional RAG retrieval method visualization.
"""

import streamlit as st
import plotly.graph_objects as go
import numpy as np
from sklearn.decomposition import PCA


def create_vector_space_visualization(trad_rag, query, retrieved_chunks):
    """Create 3D vector space visualization showing query and retrieved chunks"""
    if not hasattr(trad_rag, 'chunks_metadata') or not trad_rag.chunks_metadata:
        return None
    
    # Get all chunk embeddings
    all_embeddings = []
    all_labels = []
    all_colors = []
    all_sizes = []
    
    print(f"🔍 Traditional RAG visualization using {len(trad_rag.chunks_metadata)} chunks")
    
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


def render_traditional_rag_visualization(trad_rag, question, trad_result):
    """Render the complete Traditional RAG visualization section"""
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
