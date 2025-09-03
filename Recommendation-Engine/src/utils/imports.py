"""
Centralized import checking for optional dependencies
"""

# Check for st_link_analysis availability
HAS_ST_LINK = False
ST_LINK_ANALYSIS = None
NODE_STYLE = None
EDGE_STYLE = None

try:
    from st_link_analysis import st_link_analysis, NodeStyle, EdgeStyle
    HAS_ST_LINK = True
    ST_LINK_ANALYSIS = st_link_analysis
    NODE_STYLE = NodeStyle
    EDGE_STYLE = EdgeStyle
except ImportError as e:
    HAS_ST_LINK = False

# Check for networkx availability
try:
    import networkx as nx
    HAS_NETWORKX = True
    NETWORKX = nx
except ImportError:
    HAS_NETWORKX = False
    NETWORKX = None

def check_st_link_analysis():
    """Runtime check for st_link_analysis availability"""
    try:
        import st_link_analysis
        return True, st_link_analysis
    except ImportError as e:
        return False, str(e)

def get_import_status():
    """Get status of all optional imports"""
    return {
        "st_link_analysis": HAS_ST_LINK,
        "networkx": HAS_NETWORKX
    }
