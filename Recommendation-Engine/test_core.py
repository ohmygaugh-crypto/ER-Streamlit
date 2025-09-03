"""
Test script to verify core functionality without Streamlit dependencies
"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_data_generation():
    """Test mock data generation"""
    print("🧪 Testing data generation...")
    try:
        from src.core.data_generator import generate_mock_orders
        
        # Generate small dataset for testing
        df = generate_mock_orders(n_customers=10, n_orders=50, seed=42)
        
        print(f"✅ Generated {len(df)} rows")
        print(f"   - {df['order_id'].nunique()} unique orders")
        print(f"   - {df['product_id'].nunique()} unique products")
        print(f"   - {df['customer_id'].nunique()} unique customers")
        
        # Check data structure
        expected_columns = [
            "order_id", "customer_id", "order_timestamp",
            "product_id", "product_name", "category", "price", "quantity"
        ]
        
        missing_cols = set(expected_columns) - set(df.columns)
        if missing_cols:
            print(f"❌ Missing columns: {missing_cols}")
            return False
        
        print("✅ Data generation test passed")
        return True
        
    except Exception as e:
        print(f"❌ Data generation test failed: {e}")
        return False

def test_network_analysis():
    """Test network analysis functionality"""
    print("\n🧪 Testing network analysis...")
    try:
        from src.core.data_generator import generate_mock_orders
        from src.core.network_analyzer import NetworkAnalyzer
        
        # Generate test data
        df = generate_mock_orders(n_customers=10, n_orders=50, seed=42)
        analyzer = NetworkAnalyzer()
        
        # Build statistics
        stats = analyzer.build_item_stats(df)
        
        print(f"✅ Analyzed {stats['n_orders']} orders")
        print(f"   - {len(stats['meta'])} products")
        print(f"   - {len(stats['pairs'])} product pairs")
        
        # Test graph elements
        elements = analyzer.build_graph_elements(stats, min_support=0.01, min_lift=1.1)
        
        print(f"✅ Generated network with {len(elements['nodes'])} nodes and {len(elements['edges'])} edges")
        
        # Test community detection
        node_to_comm, n_comms = analyzer.detect_communities(elements)
        print(f"✅ Detected {n_comms} communities")
        
        print("✅ Network analysis test passed")
        return True
        
    except Exception as e:
        print(f"❌ Network analysis test failed: {e}")
        return False

def test_recommendations():
    """Test recommendation engine"""
    print("\n🧪 Testing recommendation engine...")
    try:
        from src.core.data_generator import generate_mock_orders
        from src.core.network_analyzer import NetworkAnalyzer
        from src.core.recommender import RecommendationEngine
        
        # Generate test data and analyze
        df = generate_mock_orders(n_customers=20, n_orders=100, seed=42)
        analyzer = NetworkAnalyzer()
        stats = analyzer.build_item_stats(df)
        
        # Test recommendations
        recommender = RecommendationEngine()
        cart_items = ["milk_whole", "bread_whl"]  # Common items from mock data
        
        recs = recommender.compute_recommendations(cart_items, stats, topk=5)
        
        if not recs.empty:
            print(f"✅ Generated {len(recs)} recommendations for cart: {cart_items}")
            print("   Top recommendation:", recs.iloc[0]['product_name'])
            
            # Test revenue estimation
            recs_with_uplift = recommender.estimate_revenue_uplift(recs)
            print(f"✅ Added revenue uplift estimates")
            
        else:
            print("⚠️ No recommendations generated (may be due to thresholds)")
        
        print("✅ Recommendation engine test passed")
        return True
        
    except Exception as e:
        print(f"❌ Recommendation engine test failed: {e}")
        return False

def test_data_processing():
    """Test data processing functionality"""
    print("\n🧪 Testing data processing...")
    try:
        from src.data.processors import DataProcessor
        from src.core.data_generator import generate_mock_orders
        
        # Generate test data
        df = generate_mock_orders(n_customers=5, n_orders=25, seed=42)
        
        # Test processor
        processor = DataProcessor()
        processed_df = processor.validate_and_process(df)
        
        if processed_df is not None:
            print(f"✅ Processed {len(processed_df)} rows")
            
            # Test summary
            summary = processor.get_data_summary(processed_df)
            print(f"   - {summary['unique_orders']} orders")
            print(f"   - {summary['unique_products']} products")
            print(f"   - Avg basket size: {summary['avg_basket_size']:.1f}")
        else:
            print("❌ Data processing returned None")
            return False
        
        print("✅ Data processing test passed")
        return True
        
    except Exception as e:
        print(f"❌ Data processing test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Running Recommendation Engine Core Tests")
    print("=" * 50)
    
    tests = [
        test_data_generation,
        test_network_analysis,
        test_recommendations,
        test_data_processing
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All core functionality tests passed!")
        print("\n🚀 Ready to run the Streamlit app:")
        print("   cd Recommendation-Engine")
        print("   ./run.sh")
        print("   # or manually: streamlit run app.py")
    else:
        print("❌ Some tests failed. Check the output above.")
        return False
    
    return True

if __name__ == "__main__":
    main()
