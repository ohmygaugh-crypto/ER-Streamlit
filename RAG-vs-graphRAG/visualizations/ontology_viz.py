"""
Ontology Visualization Module
============================

Contains the 3D ontology visualization and related UI components
for knowledge graph ontology discovery visualization.
"""

import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import pandas as pd
from pathlib import Path


def create_ontology_visualization(ontology_data):
    """Create 3D visualization of discovered ontology"""
    if not ontology_data or not ontology_data.get('entities'):
        return None
    
    entities = ontology_data['entities']
    relationships = ontology_data.get('relationships', [])
    
    # Create NetworkX graph for layout
    G = nx.Graph()
    
    # Add nodes with attributes
    for name, entity in entities.items():
        G.add_node(name, 
                  type=entity['type'],
                  frequency=entity['frequency'],
                  confidence=entity['confidence'])
    
    # Add edges
    for rel in relationships:
        if rel['source'] in entities and rel['target'] in entities:
            G.add_edge(rel['source'], rel['target'],
                      relation_type=rel['relation_type'],
                      frequency=rel['frequency'])
    
    if len(G.nodes()) == 0:
        return None
    
    # Create 3D layout with type-based clustering
    pos_2d = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Create z-coordinates based on entity type
    type_z_map = {}
    unique_types = list(set(entity['type'] for entity in entities.values()))
    for i, entity_type in enumerate(unique_types):
        type_z_map[entity_type] = i * 2
    
    # Prepare 3D positions
    pos_3d = {}
    for node_id, (x, y) in pos_2d.items():
        entity_type = entities[node_id]['type']
        z = type_z_map.get(entity_type, 0)
        pos_3d[node_id] = (x, y, z)
    
    # Create edge traces
    edge_traces = []
    for edge in G.edges():
        x0, y0, z0 = pos_3d[edge[0]]
        x1, y1, z1 = pos_3d[edge[1]]
        
        edge_traces.append(go.Scatter3d(
            x=[x0, x1, None],
            y=[y0, y1, None],
            z=[z0, z1, None],
            mode='lines',
            line=dict(color='rgba(150,150,150,0.6)', width=2),
            hoverinfo='none',
            showlegend=False
        ))
    
    # Create node traces by type
    node_traces = []
    entity_colors = {
        'CUSTOMER': '#ff7f0e',
        'SYSTEM_COMPONENT': '#2ca02c',
        'TECHNOLOGY': '#d62728',
        'PERSON': '#9467bd',
        'ORG': '#e377c2',
        'FEATURE': '#17becf',
        'ISSUE': '#bcbd22',
        'METRIC': '#8c564b'
    }
    
    # Group nodes by type
    nodes_by_type = {}
    for name, entity in entities.items():
        entity_type = entity['type']
        if entity_type not in nodes_by_type:
            nodes_by_type[entity_type] = []
        nodes_by_type[entity_type].append((name, entity))
    
    # Create traces for each type
    for entity_type, nodes in nodes_by_type.items():
        color = entity_colors.get(entity_type, '#1f77b4')
        
        node_x = [pos_3d[name][0] for name, _ in nodes]
        node_y = [pos_3d[name][1] for name, _ in nodes]
        node_z = [pos_3d[name][2] for name, _ in nodes]
        node_text = [name for name, _ in nodes]
        node_sizes = [min(max(entity['frequency'] * 3, 8), 20) for _, entity in nodes]
        
        node_traces.append(go.Scatter3d(
            x=node_x,
            y=node_y,
            z=node_z,
            mode='markers+text',
            marker=dict(size=node_sizes, color=color, opacity=0.8),
            text=node_text,
            textposition='top center',
            name=entity_type.replace('_', ' ').title(),
            hovertemplate='%{text}<br>Type: ' + entity_type + '<br>Frequency: %{marker.size}<extra></extra>'
        ))
    
    # Create figure
    fig = go.Figure(data=edge_traces + node_traces)
    
    fig.update_layout(
        title='3D Ontology Graph: Discovered Entity Relationships',
        scene=dict(
            xaxis_title='Relationship Space X',
            yaxis_title='Relationship Space Y',
            zaxis_title='Entity Type Layers',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5))
        ),
        height=600,
        margin=dict(l=0, r=0, b=0, t=40),
        showlegend=True,
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig


def render_ontology_discovery_section(graph_rag):
    """Render the complete ontology discovery section"""
    st.markdown("## 🧠 Knowledge Ontology Discovery")
    st.markdown("**Discover hidden knowledge structures and entity relationships** from your enterprise documents.")
    
    # Get ontology data if available
    ontology_data = {}
    if hasattr(graph_rag, 'get_ontology_data'):
        ontology_data = graph_rag.get_ontology_data()
    
    # Show 3D ontology visualization
    st.markdown("### 🌐 3D Ontology Graph Visualization")
    st.markdown("**Interactive 3D view** of discovered entity relationships organized by type layers.")
    
    with st.spinner("Creating ontology visualization..."):
        ontology_fig = create_ontology_visualization(ontology_data)
    
    if ontology_fig:
        st.plotly_chart(ontology_fig, use_container_width=True)
        
        st.markdown("""
        **🌐 3D Ontology Insights:**
        - **Z-Layers**: Entity types are clustered by conceptual similarity
        - **Node Size**: Proportional to entity frequency in documents
        - **Colors**: Different entity types (customers, systems, technologies, etc.)
        - **Gray Lines**: Discovered relationships between entities
        - **Interactive**: Rotate to explore entity relationships across type layers
        """)
    else:
        st.info("No ontology data available yet. The visualization will appear when data is loaded.")
