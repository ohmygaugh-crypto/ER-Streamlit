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
import math


def get_graph_layout(G, nodes, layout_algo):
    """Generate node positions based on selected layout algorithm"""
    try:
        if layout_algo == "spring":
            return nx.spring_layout(G, k=3, iterations=200, seed=42)
        
        elif layout_algo == "circular":
            return nx.circular_layout(G)
        
        elif layout_algo == "shell":
            # Group nodes by type for shell layout
            chunk_nodes = [n['id'] for n in nodes if n['type'] == 'CHUNK']
            entity_nodes = [n['id'] for n in nodes if n['type'] != 'CHUNK']
            nlist = [chunk_nodes, entity_nodes] if chunk_nodes and entity_nodes else None
            return nx.shell_layout(G, nlist=nlist)
        
        elif layout_algo == "kamada_kawai":
            return nx.kamada_kawai_layout(G)
        
        elif layout_algo == "planar":
            if nx.is_planar(G):
                return nx.planar_layout(G)
            else:
                return nx.spring_layout(G, k=3, iterations=100, seed=42)
        
        elif layout_algo == "spiral":
            return create_spiral_layout(G, nodes)
        
        elif layout_algo == "random":
            return nx.random_layout(G, seed=42)
        
        elif layout_algo == "hierarchical":
            return create_hierarchical_layout(nodes)
        
        else:
            # Default fallback
            return nx.spring_layout(G, k=3, iterations=100, seed=42)
            
    except Exception as e:
        print(f"Layout error with {layout_algo}: {e}")
        return nx.spring_layout(G, k=3, iterations=100, seed=42)


def create_spiral_layout(G, nodes):
    """Create a spiral layout for nodes"""
    pos = {}
    node_list = list(G.nodes())
    center_x, center_y = 0, 0
    
    for i, node in enumerate(node_list):
        angle = i * 0.5  # Spiral spacing
        radius = 0.5 + i * 0.1  # Increasing radius
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        pos[node] = (x, y)
    
    return pos


def create_hierarchical_layout(nodes):
    """Create hierarchical tree-like layout"""
    chunk_nodes = [n for n in nodes if n['type'] == 'CHUNK']
    entity_nodes = [n for n in nodes if n['type'] != 'CHUNK']
    
    pos_2d = {}
    
    # Layer 1: Place chunks in a grid at the bottom
    chunk_cols = int(len(chunk_nodes) ** 0.5) + 1
    for i, node in enumerate(chunk_nodes):
        x = (i % chunk_cols) * 2 - chunk_cols
        y = -3 - (i // chunk_cols) * 0.5
        pos_2d[node['id']] = (x, y)
    
    # Layer 2: Place entities in organized clusters above chunks
    entity_types = {}
    for node in entity_nodes:
        node_type = node['type']
        if node_type not in entity_types:
            entity_types[node_type] = []
        entity_types[node_type].append(node['id'])
    
    # Arrange entity types in a semi-circle
    type_positions = [
        (-4, 2), (-2, 3), (0, 3.5), (2, 3), (4, 2),  # Top arc
        (-3, 1), (-1, 1.5), (1, 1.5), (3, 1)         # Middle arc
    ]
    
    for i, (entity_type, node_ids) in enumerate(entity_types.items()):
        if i < len(type_positions):
            base_x, base_y = type_positions[i]
            for j, node_id in enumerate(node_ids):
                # Cluster entities of same type together
                offset_x = (j % 3) * 0.3 - 0.3
                offset_y = (j // 3) * 0.2
                pos_2d[node_id] = (base_x + offset_x, base_y + offset_y)
    
    return pos_2d


def create_graph_traversal_visualization(trad_rag, graph_rag, query, trad_retrieved_chunks, graph_retrieved_chunks, layout_algo="hierarchical"):
    """Create 3D visualization showing chunks + 2D graph plane + GraphRAG gap-filling"""
    # Use GraphRAG's enhanced chunk embeddings instead of Traditional RAG's static ones
    enhanced_data = graph_rag.get_enhanced_chunk_embeddings()
    enhanced_chunks = enhanced_data.get('chunks', [])
    
    if not enhanced_chunks:
        # Fallback to Traditional RAG if no enhanced chunks
        if not hasattr(trad_rag, 'chunks_metadata') or not trad_rag.chunks_metadata:
            return None
        enhanced_chunks = [
            {
                'chunk_id': chunk['chunk_id'],
                'content': chunk['content'], 
                'filename': chunk['filename'],
                'entities': [],
                'embedding': trad_rag.embedding_model.encode([chunk['content']])[0]
            }
            for chunk in trad_rag.chunks_metadata
        ]
    
    print(f"🕸️ GraphRAG visualization using {len(enhanced_chunks)} enhanced chunks")
    
    # Get chunk embeddings and positions 
    all_embeddings = []
    chunk_info = []
    
    for chunk_meta in enhanced_chunks:
        embedding = chunk_meta['embedding']
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
    
    # 1. Add 2D Knowledge Graph Plane (at z=0) - showing chunks and entities
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
        
        # Choose layout algorithm based on user selection
        pos_2d = get_graph_layout(G, graph_data['nodes'], layout_algo)
        
        # Add graph edges on the z=0 plane
        for edge in G.edges():
            if edge[0] in pos_2d and edge[1] in pos_2d:
                x0, y0 = pos_2d[edge[0]]
                x1, y1 = pos_2d[edge[1]]
                fig.add_trace(go.Scatter3d(
                    x=[x0*3, x1*3], y=[y0*3, y1*3], z=[0, 0],
                    mode='lines',
                    line=dict(color='rgba(100,100,100,0.6)', width=2),
                    hoverinfo='none',
                    showlegend=False
                ))
        
        # Add chunk nodes on the z=0 plane
        chunk_nodes = [n for n in graph_data['nodes'] if n['type'] == 'CHUNK']
        if chunk_nodes:
            chunk_positions = [(pos_2d[n['id']], n) for n in chunk_nodes if n['id'] in pos_2d]
            if chunk_positions:
                fig.add_trace(go.Scatter3d(
                    x=[pos[0]*3 for pos, _ in chunk_positions],
                    y=[pos[1]*3 for pos, _ in chunk_positions],
                    z=[0 for _ in chunk_positions],
                    mode='markers',
                    marker=dict(size=12, color='#87CEEB', symbol='square', opacity=0.7),
                    name='Document Chunks',
                    hovertemplate='%{text}<extra></extra>',
                    text=[f"Chunk: {node['filename']}<br>{node['content']}" for _, node in chunk_positions],
                    legendgroup='graph'
                ))
        
        # Add entity nodes on the z=0 plane  
        node_colors = {
            'CUSTOMER': '#ff7f0e', 'SYSTEM_COMPONENT': '#2ca02c', 
            'TECHNOLOGY': '#d62728', 'PERSON': '#9467bd',
            'ORG': '#e377c2', 'FEATURE': '#17becf', 'CHUNK': '#87CEEB',
            'Company': '#e377c2', 'Person': '#9467bd', 'System': '#2ca02c',
            'Technology': '#d62728', 'Issue': '#ff4444', 'Decision': '#4444ff'
        }
        
        entity_nodes = [n for n in graph_data['nodes'] if n['type'] != 'CHUNK']
        for node in entity_nodes:
            if node['id'] in pos_2d:
                x, y = pos_2d[node['id']]
                color = node_colors.get(node['type'], '#1f77b4')
                display_name = node.get('name', node['id']).replace('entity_', '').replace('_', ' ')[:15]
                fig.add_trace(go.Scatter3d(
                    x=[x*3], y=[y*3], z=[0],
                    mode='markers+text',
                    marker=dict(size=10, color=color, opacity=0.8),
                    text=[display_name],
                    textposition='top center',
                    name=f"Graph: {node['type'].replace('_', ' ')}",
                    hovertemplate=f"{display_name}<br>Type: {node['type']}<extra></extra>",
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
    
    # Layout algorithm selector with descriptions
    layout_options = {
        "🌸 Spring Layout (Physics)": "spring",
        "🌳 Hierarchical Tree": "hierarchical", 
        "🎯 Circular Layout": "circular",
        "🔲 Shell Layout (Layered)": "shell",
        "🕸️ Kamada-Kawai (Balanced)": "kamada_kawai",
        "📊 Planar Layout": "planar",
        "🌀 Spiral Layout": "spiral",
        "🎨 Random Layout": "random"
    }
    
    layout_descriptions = {
        "spring": "Force-directed physics simulation - nodes attract/repel naturally",
        "hierarchical": "Structured layers: chunks at bottom, entities grouped by type above",
        "circular": "All nodes arranged in a perfect circle",
        "shell": "Layered shells: chunks in inner ring, entities in outer ring", 
        "kamada_kawai": "Balanced force-directed layout - good for showing relationships",
        "planar": "Flat layout avoiding edge crossings (if graph is planar)",
        "spiral": "Nodes arranged in an outward spiral pattern",
        "random": "Completely random positioning - good for comparison"
    }
    
    # Get graph data once for all tabs
    with st.spinner("Loading graph data..."):
        graph_data = graph_rag.get_graph_visualization_data()
        query_entities = graph_rag.extract_entities(question, "query") if hasattr(graph_rag, 'extract_entities') else []
    
    # Use tabs for instant layout switching without page refresh
    st.markdown("🎛️ **Choose Graph Layout Algorithm:**")
    
    layout_tabs = st.tabs([
        "🌳 Tree", "🌸 Physics", "🎯 Circle", "🔲 Shell", 
        "🕸️ Balanced", "📊 Planar", "🌀 Spiral", "🎨 Random"
    ])
    
    tab_to_layout = {
        0: "🌳 Hierarchical Tree",
        1: "🌸 Spring Layout (Physics)", 
        2: "🎯 Circular Layout",
        3: "🔲 Shell Layout (Layered)",
        4: "🕸️ Kamada-Kawai (Balanced)",
        5: "📊 Planar Layout",
        6: "🌀 Spiral Layout",
        7: "🎨 Random Layout"
    }
    
    # Create visualization in each tab
    for i, tab in enumerate(layout_tabs):
        with tab:
            selected_layout = tab_to_layout[i]
            layout_algo = layout_options[selected_layout]
            st.info(f"**{selected_layout}**: {layout_descriptions[layout_algo]}")
            
            # Create visualization for this specific layout
            if graph_data.get('nodes'):
                graph_viz = create_graph_traversal_visualization(
                    trad_rag, graph_rag, question, 
                    trad_result.get('retrieved_chunks', []), 
                    graph_result.get('retrieved_chunks', []),
                    layout_algo
                )
                st.plotly_chart(graph_viz, use_container_width=True)
            else:
                st.warning("No graph data available for visualization")
    
    # Add explanation below all tabs
    st.markdown("""
    **🕸️ GraphRAG Gap-Filling Magic:**
    - **2D Graph Plane (z=0)**: Entity relationship network as foundation
    - **🟢 Green Chunks**: Found by both methods (baseline similarity)
    - **🟠 Orange Chunks**: Traditional RAG only (pure similarity)
    - **💎 Red Diamonds**: GraphRAG gap-filling (relationship bridges!)
    - **Dashed Lines**: How graph entities connect to outlier chunks
    - **The Story**: GraphRAG uses relationships to reach relevant chunks that similarity search missed
    """)
