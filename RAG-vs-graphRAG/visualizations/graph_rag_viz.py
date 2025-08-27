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


def find_most_relevant_graph_node(graph_rag, query, graph_data):
    """Find the most relevant graph node for the query entry point"""
    try:
        # Extract entities from query
        query_entities = graph_rag.extract_entities(query, "query") if hasattr(graph_rag, 'extract_entities') else []
        
        if not query_entities or not graph_data.get('nodes'):
            return None
            
        # Find matching entities in the graph
        graph_entity_ids = [node['id'] for node in graph_data['nodes'] if node['type'] != 'CHUNK']
        
        for entity in query_entities:
            entity_id = f"entity_{entity['name'].lower().replace(' ', '_')}"
            if entity_id in graph_entity_ids:
                return entity_id
                
        # If no direct match, return the first entity node as fallback
        if graph_entity_ids:
            return graph_entity_ids[0]
            
    except Exception as e:
        print(f"Error finding relevant graph node: {e}")
    
    return None


def create_graph_traversal_visualization(trad_rag, graph_rag, query, trad_retrieved_chunks, graph_retrieved_chunks, layout_algo="hierarchical"):
    """Create 3D visualization showing chunks + 2D graph plane + GraphRAG gap-filling with query positioned at relevant graph node"""
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
    
    # Find the most relevant graph node for query positioning
    query_entry_node = find_most_relevant_graph_node(graph_rag, query, graph_data)
    
    # Initialize pos_2d as empty dict to avoid UnboundLocalError
    pos_2d = {}
    
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
        
        # Add graph edges on the z=0 plane - use original edge data, not NetworkX edges
        edges_drawn = 0
        mentions_edges = 0
        relates_edges = 0
        missing_source_nodes = []
        missing_target_nodes = []
        
        print(f"🔗 Debug: Total edges in graph_data: {len(graph_data['edges'])}")
        print(f"🔗 Debug: Total nodes with positions: {len(pos_2d)}")
        
        for edge in graph_data['edges']:
            source_id = edge['source']
            target_id = edge['target']
            relationship = edge.get('relationship', 'UNKNOWN')
            
            # Debug missing nodes and relationship types
            if source_id not in pos_2d:
                missing_source_nodes.append(source_id)
            if target_id not in pos_2d:
                missing_target_nodes.append(target_id)
            
            # Debug first few relationships
            if len(missing_source_nodes) + len(missing_target_nodes) < 3:
                print(f"🔗 Debug edge: {source_id} -[{relationship}]-> {target_id}")
            
            if source_id in pos_2d and target_id in pos_2d:
                x0, y0 = pos_2d[source_id]
                x1, y1 = pos_2d[target_id]
                
                # Different colors for different relationship types
                edge_color = 'rgba(100,100,100,0.6)'  # Default gray
                edge_width = 2
                if relationship == 'MENTIONS':
                    edge_color = 'rgba(65,105,225,0.8)'  # Blue for chunk-entity
                    edge_width = 3
                    mentions_edges += 1
                elif relationship == 'RELATES_TO':
                    edge_color = 'rgba(255,140,0,0.7)'  # Orange for entity-entity
                    edge_width = 2
                    relates_edges += 1
                
                fig.add_trace(go.Scatter3d(
                    x=[x0*3, x1*3], y=[y0*3, y1*3], z=[0, 0],
                    mode='lines',
                    line=dict(color=edge_color, width=edge_width),
                    hoverinfo='none',
                    showlegend=False
                ))
                edges_drawn += 1
        
        print(f"🔗 Debug: Edges drawn: {edges_drawn} (MENTIONS: {mentions_edges}, RELATES_TO: {relates_edges})")
        if missing_source_nodes:
            print(f"🔗 Debug: Missing source nodes: {missing_source_nodes[:5]}...")
        if missing_target_nodes:
            print(f"🔗 Debug: Missing target nodes: {missing_target_nodes[:5]}...")
        
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
        
        # Add connection lines showing query entry → graph traversal → gap-filling chunks
        for chunk in graph_only_chunks:
            if query_entry_node and query_entry_node in pos_2d:
                # Show path: query entry node → gap-filling chunk
                entry_x, entry_y = pos_2d[query_entry_node]
                fig.add_trace(go.Scatter3d(
                    x=[entry_x*3, chunk['pos'][0]],
                    y=[entry_y*3, chunk['pos'][1]], 
                    z=[0, chunk['pos'][2]],
                    mode='lines',
                    line=dict(color='#DC143C', width=4, dash='dash'),
                    showlegend=False,
                    hoverinfo='none'
                ))
                
                # Add intermediate connection showing graph traversal
                fig.add_trace(go.Scatter3d(
                    x=[entry_x*3, entry_x*3, chunk['pos'][0]],
                    y=[entry_y*3, entry_y*3, chunk['pos'][1]], 
                    z=[0, 0.3, chunk['pos'][2]],
                    mode='lines',
                    line=dict(color='#FFD700', width=2, dash='dot'),  # Gold dotted line
                    showlegend=False,
                    hoverinfo='none'
                ))
            else:
                # Fallback: Find the nearest graph entity (simplified)
                if graph_data.get('nodes') and pos_2d:
                    nearest_entity = list(pos_2d.keys())[0]  
                    if nearest_entity in pos_2d:
                        graph_x, graph_y = pos_2d[nearest_entity]
                        fig.add_trace(go.Scatter3d(
                            x=[graph_x*3, chunk['pos'][0]],
                            y=[graph_y*3, chunk['pos'][1]], 
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
    
    # 5. Add query position - either at relevant graph node or floating if no match
    if query_entry_node and query_entry_node in pos_2d:
        # Position query at the relevant graph node
        graph_x, graph_y = pos_2d[query_entry_node]
        query_x, query_y, query_z = graph_x * 3, graph_y * 3, 0.5  # Slightly elevated above graph plane
        
        # Add query at graph node position
        fig.add_trace(go.Scatter3d(
            x=[query_x], y=[query_y], z=[query_z],
            mode='markers+text',
            marker=dict(size=18, color='#2E8B57', symbol='diamond', 
                       line=dict(width=3, color='#FFD700')),  # Gold outline
            text=['QUERY'],
            name='Query Entry Point',
            textposition='top center',
            hovertemplate=f'Query: {query}<br>Connected to: {query_entry_node}<extra></extra>'
        ))
        
        # Add connection from query to the graph node below
        fig.add_trace(go.Scatter3d(
            x=[query_x, graph_x * 3],
            y=[query_y, graph_y * 3], 
            z=[query_z, 0],
            mode='lines',
            line=dict(color='#2E8B57', width=6, dash='solid'),
            showlegend=False,
            hoverinfo='none'
        ))
        
        # Add visual indicator for the connected graph node
        fig.add_trace(go.Scatter3d(
            x=[graph_x * 3], y=[graph_y * 3], z=[0],
            mode='markers',
            marker=dict(size=15, color='#2E8B57', symbol='circle', 
                       line=dict(width=3, color='#FFD700')),
            name='Query Entry Node',
            showlegend=False,
            hovertemplate=f'Query Entry: {query_entry_node}<extra></extra>'
        ))
        
    else:
        # Fallback: position query in 3D space if no relevant graph node found
        fig.add_trace(go.Scatter3d(
            x=[query_pos[0]], y=[query_pos[1]], z=[query_pos[2]],
            mode='markers+text',
            marker=dict(size=16, color='#2E8B57', symbol='diamond'),
            text=['QUERY (No Graph Match)'],
            name='Query',
            textposition='top center',
            hovertemplate=f'Query: {query}<extra></extra>'
        ))
    
    # Update layout
    fig.update_layout(
        title='GraphRAG Gap-Filling: Query Entry Point → Graph Traversal → Missing Chunks',
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
                st.plotly_chart(graph_viz, use_container_width=True, key=f"graph_viz_{layout_algo}")
            else:
                st.warning("No graph data available for visualization")
    
    # Add explanation below all tabs
    st.markdown("""
    **🕸️ GraphRAG Gap-Filling Magic:**
    - **2D Graph Plane (z=0)**: Entity relationship network as foundation
    - **💎 Green Query Diamond**: Query positioned at relevant graph entity (not isolated!)
    - **🟢 Green Chunks**: Found by both methods (baseline similarity)
    - **🟠 Orange Chunks**: Traditional RAG only (pure similarity)
    - **💎 Red Diamonds**: GraphRAG gap-filling (relationship bridges!)
    - **Solid Green Line**: Query connection to graph entry point
    - **Red Dashed Lines**: Direct path from query entry to gap-filling chunks
    - **Gold Dotted Lines**: Graph traversal paths showing intermediate steps
    - **The Story**: Query starts from relevant graph node, enabling relationship traversal to find missed chunks
    """)
