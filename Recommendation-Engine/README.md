# 🛒 Recommendation Engine: Network Analytics for Retail

A sophisticated Streamlit application that demonstrates the power of network analytics for retail recommendation systems. This app showcases how co-purchase patterns can drive intelligent cart add-on suggestions with explainable AI and revenue impact estimation.

## 🎯 Executive Summary

This demo app showcases **network analytics for online retail recommendation systems**. In real-world grocery or retail checkout flows, suggesting relevant add-on products at the right moment benefits both customers (better experience, relevant suggestions) and businesses (increased revenue and basket size).

### What We're Demonstrating
- **Win-Win Scenario**: Smarter, data-driven product recommendations that increase cart value while staying relevant
- **Network Analytics**: Move beyond "black box" recommender models by visualizing product relationships and surfacing metrics like support, confidence, and lift
- **Business Value**: Demonstrate potential incremental revenue uplift from targeted recommendations

## 🚀 Features

### 🔗 Network Analysis
- **Market Basket Analysis**: Computes support, confidence, and lift for product pairs
- **Interactive Network Visualization**: Products as nodes, co-purchase relationships as edges
- **Community Detection**: Identifies natural product groupings (e.g., breakfast items, cooking essentials)
- **Explainable Recommendations**: Clear "why this item" explanations based on network relationships

### 🎯 Smart Recommendations
- **Cart-Aware Scoring**: Aggregates signals from all items currently in cart
- **Revenue Impact**: Estimates acceptance probability and margin uplift
- **Real-time Updates**: Recommendations update instantly as cart contents change
- **Export Capabilities**: Download recommendations and network data for further analysis

### 📊 Data Flexibility
- **Built-in Mock Data**: Realistic grocery dataset with intentional co-purchase patterns
- **CSV Upload Support**: Bring your own transaction data with automatic column mapping
- **Data Validation**: Robust handling of different CSV formats and data quality issues

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd Recommendation-Engine
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Using uv (recommended)
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Or using standard venv
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   # Using uv (recommended)
   uv pip install -r requirements.txt
   
   # Or using pip
   pip install -r requirements.txt
   ```

4. **Optional: Install interactive graph visualization:**
   ```bash
   pip install st-link-analysis
   ```

## 🚀 Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

## 📊 How It Works

### Network Construction
1. **Basket Analysis**: Groups transaction data by order to create market baskets
2. **Co-occurrence Calculation**: Computes how frequently product pairs appear together
3. **Metric Computation**: Calculates support, confidence, and lift for each pair
4. **Network Filtering**: Applies thresholds to focus on significant relationships

### Recommendation Algorithm
For a cart with items S, each candidate item t gets scored by:
```
score(t) = Σ[s∈S] lift(s,t) × log(1 + co_count(s,t))
```

This aggregates evidence from all cart items, emphasizing both relationship strength (lift) and frequency (co-count).

### Revenue Estimation
- **Acceptance Probability**: Normalized from recommendation scores (capped at 60% for demo)
- **Margin Calculation**: Item price × configured margin percentage
- **Expected Uplift**: Acceptance probability × estimated margin

## 📁 Project Structure

```
Recommendation-Engine/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── src/
    ├── core/                       # Core business logic
    │   ├── data_generator.py       # Mock data generation
    │   ├── network_analyzer.py     # Market basket analysis
    │   └── recommender.py          # Recommendation engine
    ├── data/                       # Data processing
    │   └── processors.py           # CSV validation and mapping
    └── ui/                         # User interface components
        ├── components/             # Reusable UI components
        │   ├── cart_simulator.py   # Cart interface
        │   └── graph_viz.py        # Network visualization
        └── layouts/                # Page layouts
            └── sidebar.py          # Configuration sidebar
```

## 🔧 Configuration Options

### Data Source
- **Mock Data**: Built-in grocery dataset with realistic co-purchase patterns
- **CSV Upload**: Support for custom transaction data with flexible column mapping

### Network Parameters
- **Min Support**: Minimum fraction of orders containing both items (default: 0.005)
- **Min Lift**: Minimum lift score for relationships (default: 1.2)
- **Max Edges**: Performance limit for network visualization (default: 2500)

### Recommendation Settings
- **Number of Recommendations**: How many suggestions to show (1-15)
- **Margin Percentage**: For revenue uplift calculations (0-90%)

## 📈 Use Cases

### E-commerce
- **Checkout Optimization**: Suggest complementary items during checkout
- **Cross-selling**: Identify products that naturally sell together
- **Inventory Planning**: Understand product relationships for stocking decisions

### Retail Analytics
- **Market Basket Analysis**: Discover hidden product relationships
- **Customer Behavior**: Understand shopping patterns and preferences
- **Revenue Optimization**: Quantify impact of recommendation strategies

### Business Intelligence
- **Explainable AI**: Provide clear reasoning for recommendations
- **Performance Metrics**: Track recommendation acceptance and revenue impact
- **Strategic Insights**: Identify product communities and market opportunities

## 🔍 Data Requirements

For custom CSV uploads, include these columns (automatic mapping will attempt to match variations):

| Required Column | Description | Aliases |
|----------------|-------------|---------|
| `order_id` | Unique order identifier | `orderid`, `basket_id`, `txn_id` |
| `customer_id` | Customer identifier | `customerid`, `user_id`, `account_id` |
| `order_timestamp` | Order date/time | `timestamp`, `order_date`, `datetime` |
| `product_id` | Product identifier | `sku`, `item_id`, `product_code` |
| `product_name` | Product display name | `item_name`, `name`, `title` |
| `category` | Product category | `dept`, `department`, `aisle` |
| `price` | Item price | `unit_price`, `item_price`, `amount` |
| `quantity` | Quantity purchased | `qty`, `count`, `units` |

## 🤝 Contributing

This project demonstrates network analytics capabilities for retail recommendations. To extend or customize:

1. **Add New Algorithms**: Implement additional recommendation algorithms in `src/core/recommender.py`
2. **Enhance Visualizations**: Extend graph visualization in `src/ui/components/graph_viz.py`
3. **Custom Data Sources**: Add new data processors in `src/data/processors.py`
4. **Business Logic**: Modify network analysis in `src/core/network_analyzer.py`

## 📝 License

This project is part of a demonstration portfolio showcasing network analytics capabilities for retail and e-commerce applications.

## 🆘 Troubleshooting

### Common Issues

**Graph visualization not showing:**
- Install `st-link-analysis`: `pip install st-link-analysis`
- Check browser console for JavaScript errors

**No recommendations appearing:**
- Lower the minimum support and lift thresholds
- Ensure cart has items that appear in the network
- Check data quality and co-purchase patterns

**CSV upload failing:**
- Verify column names match expected format
- Check for missing required columns
- Ensure data has sufficient orders and products

### Performance Tips

- Limit max edges for large datasets (< 5000 recommended)
- Use higher support thresholds to focus on strong relationships
- Consider sampling large datasets for interactive exploration

---

**💡 Pro Tip**: Start with the mock data to understand the interface, then upload your own transaction data to see real insights from your business!
