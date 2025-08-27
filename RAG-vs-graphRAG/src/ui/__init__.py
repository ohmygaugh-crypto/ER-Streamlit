"""
User Interface Components
Handles all UI layout and visualization components
"""

# Import layout components
from .layout.sidebar import render_sidebar
from .layout.demo_scenarios import render_demo_scenarios, get_demo_scenarios  
from .layout.comparison import render_comparison_interface

# Import visualization components
from .visualizations import (
    render_traditional_rag_visualization,
    render_graph_rag_visualization,
    render_ontology_discovery_section
)

__all__ = [
    'render_sidebar',
    'render_demo_scenarios',
    'get_demo_scenarios',
    'render_comparison_interface',
    'render_traditional_rag_visualization',
    'render_graph_rag_visualization', 
    'render_ontology_discovery_section'
]
