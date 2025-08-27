#!/usr/bin/env python3
"""
Debug script to verify Streamlit app works with ontology discovery
"""
import sys
from pathlib import Path
import streamlit as st

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_streamlit_integration():
    """Test the Streamlit integration"""
    st.title("🧪 Ontology Discovery Debug")
    
    try:
        from graph_rag import GraphRAG
        st.success("✅ GraphRAG import successful")
        
        # Initialize GraphRAG
        graph_rag = GraphRAG("./debug_graph_db")
        st.success("✅ GraphRAG initialized")
        
        # Check methods
        has_ontology_data = hasattr(graph_rag, 'get_ontology_data')
        has_discover_ontology = hasattr(graph_rag, 'discover_ontology')
        
        st.write(f"**get_ontology_data method:** {'✅ Available' if has_ontology_data else '❌ Missing'}")
        st.write(f"**discover_ontology method:** {'✅ Available' if has_discover_ontology else '❌ Missing'}")
        
        if has_ontology_data:
            # Test calling the method
            try:
                ontology_data = graph_rag.get_ontology_data()
                st.success(f"✅ get_ontology_data() works: {type(ontology_data)}")
                st.json(ontology_data)
            except Exception as e:
                st.error(f"❌ get_ontology_data() error: {e}")
        
        if st.button("🔍 Test Ontology Discovery"):
            if has_discover_ontology:
                with st.spinner("Testing ontology discovery..."):
                    try:
                        data_dir = Path(__file__).parent / "data"
                        if data_dir.exists():
                            ontology_data = graph_rag.discover_ontology(str(data_dir))
                            st.success("✅ Ontology discovery works!")
                            st.json(ontology_data['statistics'])
                        else:
                            st.warning("Data directory not found")
                    except Exception as e:
                        st.error(f"❌ Discovery failed: {e}")
            else:
                st.error("❌ discover_ontology method not available")
        
        # Cleanup button
        if st.button("🧹 Cleanup"):
            import shutil
            shutil.rmtree("./debug_graph_db", ignore_errors=True)
            st.success("✅ Cleanup complete")
            
    except Exception as e:
        st.error(f"❌ Import or initialization failed: {e}")
        import traceback
        st.code(traceback.format_exc())

if __name__ == "__main__":
    test_streamlit_integration()
