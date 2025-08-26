"""
Visualization Package for RAG vs GraphRAG Comparison
===================================================

This package contains modular visualization components for the RAG comparison app.
Each module handles specific visualization functionality to keep the main app clean.
"""

from .traditional_rag_viz import (
    create_vector_space_visualization,
    render_traditional_rag_visualization
)

from .graph_rag_viz import (
    create_graph_traversal_visualization,
    render_graph_rag_visualization
)

from .ontology_viz import (
    create_ontology_visualization,
    render_ontology_discovery_section
)

__all__ = [
    'create_vector_space_visualization',
    'render_traditional_rag_visualization',
    'create_graph_traversal_visualization', 
    'render_graph_rag_visualization',
    'create_ontology_visualization',
    'render_ontology_discovery_section'
]
