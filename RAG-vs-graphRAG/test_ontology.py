#!/usr/bin/env python3
"""
Test script for ontology discovery functionality
"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_ontology_discovery():
    """Test the ontology discovery system"""
    print("🧪 Testing Ontology Discovery System...")
    
    try:
        from ontology_discovery import OntologyDiscovery
        print("✅ OntologyDiscovery import successful")
        
        # Initialize system
        discovery = OntologyDiscovery(use_llm=False)  # Don't require API key for test
        print("✅ OntologyDiscovery initialized")
        
        # Test with sample documents
        documents = [
            "TechCorp Solutions is experiencing authentication service issues that affect their dashboard performance. Mike Rodriguez from Engineering is working on Redis implementation to resolve JWT timeout errors.",
            "DataFlow Inc requires session management improvements. The authentication service causes bottlenecks affecting real-time notifications. Sarah Chen from Product is coordinating with Customer Success.",
            "CloudSync Solutions reported performance issues with the analytics dashboard. The database query optimization is needed to improve loading times for enterprise customers."
        ]
        
        filenames = ["sample1.txt", "sample2.txt", "sample3.txt"]
        
        print("🔍 Running ontology discovery...")
        ontology = discovery.discover_ontology(documents, filenames)
        
        print(f"✅ Discovery complete!")
        print(f"📊 Statistics: {ontology['statistics']}")
        print(f"🏷️ Entity types found: {ontology['entity_types']}")
        print(f"📝 Sample entities: {list(ontology['entities'].keys())[:5]}")
        print(f"🔗 Sample relationships: {len(ontology['relationships'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_graph_rag_integration():
    """Test GraphRAG integration with ontology discovery"""
    print("\n🧪 Testing GraphRAG Integration...")
    
    try:
        from graph_rag import GraphRAG
        print("✅ GraphRAG import successful")
        
        # Initialize GraphRAG
        graph_rag = GraphRAG(db_path="./test_ontology_db")
        print("✅ GraphRAG initialized with ontology discovery")
        
        # Test ontology discovery
        data_dir = Path(__file__).parent / "data"
        if data_dir.exists():
            ontology_data = graph_rag.discover_ontology(str(data_dir))
            print(f"✅ Ontology discovered from real data: {ontology_data['statistics']}")
        else:
            print("⚠️ Data directory not found, skipping real data test")
        
        # Cleanup
        import shutil
        shutil.rmtree("./test_ontology_db", ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"❌ GraphRAG integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Ontology Discovery Tests...")
    
    # Test basic ontology discovery
    test1_passed = test_ontology_discovery()
    
    # Test GraphRAG integration
    test2_passed = test_graph_rag_integration()
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Ontology discovery is ready!")
        print("\nTo use in Streamlit:")
        print("1. Run: streamlit run app.py")
        print("2. Click 'Discover Hidden Ontology' button")
        print("3. Explore the 3D ontology visualization")
    else:
        print("\n❌ Some tests failed. Check errors above.")
        sys.exit(1)
