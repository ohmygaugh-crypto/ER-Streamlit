"""
Test script to verify RAG vs GraphRAG systems work correctly
"""
import sys
from pathlib import Path
import time

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from traditional_rag import TraditionalRAG
from graph_rag import GraphRAG

def test_traditional_rag():
    """Test Traditional RAG system"""
    print("🔍 Testing Traditional RAG...")
    
    try:
        # Initialize system
        trad_rag = TraditionalRAG()
        
        # Load and process documents
        data_dir = Path(__file__).parent / "data"
        documents = trad_rag.load_documents(str(data_dir))
        print(f"✅ Loaded {len(documents)} documents")
        
        chunks = trad_rag.chunk_documents(documents)
        print(f"✅ Created {len(chunks)} chunks")
        
        trad_rag.create_embeddings(chunks)
        print("✅ Created embeddings")
        
        # Test query
        test_question = "What customers are affected by authentication issues?"
        result = trad_rag.answer_question(test_question)
        
        print(f"✅ Question answered with confidence: {result['confidence']:.2f}")
        print(f"✅ Retrieved {len(result['retrieved_chunks'])} chunks")
        
        # Get stats
        stats = trad_rag.get_stats()
        print(f"✅ System stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Traditional RAG test failed: {e}")
        return False

def test_graph_rag():
    """Test GraphRAG system"""
    print("\n🕸️ Testing GraphRAG...")
    
    try:
        # Initialize system
        graph_rag = GraphRAG(db_path="./test_graph_db")
        
        # Load and process documents
        data_dir = Path(__file__).parent / "data"
        graph_rag.load_documents(str(data_dir))
        print("✅ Built knowledge graph")
        
        # Test query
        test_question = "What customers are affected by authentication issues?"
        result = graph_rag.answer_question(test_question)
        
        print(f"✅ Question answered with confidence: {result['confidence']:.2f}")
        print(f"✅ Retrieved {len(result['retrieved_chunks'])} chunks")
        print(f"✅ Graph insights: {len(result.get('graph_insights', []))}")
        
        # Get stats
        stats = graph_rag.get_stats()
        print(f"✅ System stats: {stats}")
        
        # Test graph visualization data
        viz_data = graph_rag.get_graph_visualization_data()
        print(f"✅ Graph visualization: {len(viz_data.get('nodes', []))} nodes, {len(viz_data.get('edges', []))} edges")
        
        return True
        
    except Exception as e:
        print(f"❌ GraphRAG test failed: {e}")
        return False

def compare_systems():
    """Compare both systems on the same question"""
    print("\n⚖️ Comparing Systems...")
    
    test_questions = [
        "What customers are affected by authentication issues?",
        "How do dashboard problems relate to customer satisfaction?",
        "What technical dependencies are blocking new features?"
    ]
    
    try:
        # Initialize both systems
        trad_rag = TraditionalRAG()
        data_dir = Path(__file__).parent / "data"
        documents = trad_rag.load_documents(str(data_dir))
        chunks = trad_rag.chunk_documents(documents)
        trad_rag.create_embeddings(chunks)
        
        graph_rag = GraphRAG(db_path="./test_graph_db")
        
        for question in test_questions:
            print(f"\n📋 Question: {question}")
            
            # Traditional RAG
            start_time = time.time()
            trad_result = trad_rag.answer_question(question)
            trad_time = time.time() - start_time
            
            print(f"🔍 Traditional RAG: {trad_result['confidence']:.2f} confidence, {trad_time:.2f}s")
            
            # GraphRAG
            start_time = time.time()
            graph_result = graph_rag.answer_question(question)
            graph_time = time.time() - start_time
            
            print(f"🕸️ GraphRAG: {graph_result['confidence']:.2f} confidence, {graph_time:.2f}s, {len(graph_result.get('graph_insights', []))} insights")
        
        return True
        
    except Exception as e:
        print(f"❌ Comparison test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing RAG vs GraphRAG Demo Systems")
    print("=" * 50)
    
    # Test individual systems
    trad_success = test_traditional_rag()
    graph_success = test_graph_rag()
    
    if trad_success and graph_success:
        # Compare systems
        compare_success = compare_systems()
        
        if compare_success:
            print("\n✅ All tests passed! Systems are ready for demo.")
            print("\nTo run the Streamlit demo:")
            print("1. Set OpenAI API key: export OPENAI_API_KEY='your-key'")
            print("2. Run: streamlit run app.py")
        else:
            print("\n⚠️ Comparison test failed, but individual systems work.")
    else:
        print("\n❌ Some tests failed. Check error messages above.")
    
    # Cleanup test database
    import shutil
    try:
        shutil.rmtree("./test_graph_db", ignore_errors=True)
        print("🧹 Cleaned up test database")
    except:
        pass

if __name__ == "__main__":
    main()
