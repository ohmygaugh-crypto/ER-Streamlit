"""
Centralized import management for optional dependencies
"""

# Optional import for interactive graph visualization
try:
    from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle
    HAS_ST_LINK = True
    ST_LINK_ANALYSIS = st_link_analysis
    NODE_STYLE = NodeStyle
    EDGE_STYLE = EdgeStyle
except ImportError:
    HAS_ST_LINK = False
    ST_LINK_ANALYSIS = None
    NODE_STYLE = None
    EDGE_STYLE = None


def check_st_link_analysis():
    """
    Runtime check for st_link_analysis availability
    
    Returns:
        tuple: (is_available, module_or_error)
    """
    try:
        from st_link_analysis import st_link_analysis
        return True, st_link_analysis
    except ImportError as e:
        return False, str(e)