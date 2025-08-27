# 🧠 Ontology Discovery for GraphRAG

## Overview

This implementation adds **lightweight ontology discovery** to your existing GraphRAG system, enabling automatic discovery of hidden knowledge structures from your enterprise documents. The system is **Kuzu-compatible** and **Streamlit-ready**.

## 🎯 Key Features

### 🔍 **Automatic Entity Discovery**
- **spaCy NER**: Discovers people, organizations, products, events, dates
- **Custom Patterns**: Domain-specific entities (systems, customers, technologies, metrics, issues, features)
- **Entity Consolidation**: Merges duplicate entities and ranks by frequency/confidence
- **Type Classification**: Automatically categorizes entities into meaningful types

### 🕸️ **Relationship Pattern Discovery**
- **Hierarchical**: "is-a", "part-of", "belongs-to" relationships
- **Functional**: "uses", "performs", "enables", "manages" relationships  
- **Causal**: "causes", "prevents", "affects", "triggers" relationships
- **Temporal**: "before", "after", "during", "while" relationships
- **Associative**: "related-to", "similar-to", "associated-with" relationships

### 🤖 **LLM Enhancement (Optional)**
- **Ontology Refinement**: Uses GPT-3.5 to validate and improve discovered patterns
- **Missing Relationships**: Suggests relationships based on domain knowledge
- **Type Optimization**: Recommends better entity type classifications
- **Hierarchy Suggestions**: Proposes ontological hierarchies

### 📊 **Rich Visualizations**
- **3D Ontology Graph**: Interactive Plotly visualization with type-based layers
- **Entity Statistics**: Frequency, confidence, and type distributions  
- **Relationship Matrix**: Tabular view of discovered relationships
- **Type Clustering**: Visual grouping by entity types

## 🚀 Usage

### In Your Streamlit App

```python
# The ontology discovery is already integrated!
# Just run your app and click "🔍 Discover Hidden Ontology"

streamlit run app.py
```

### Programmatic Usage

```python
from src.ontology_discovery import OntologyDiscovery

# Initialize discovery system
discovery = OntologyDiscovery(use_llm=True)  # Set False to disable LLM

# Discover ontology from documents
documents = ["Your document content here..."]
filenames = ["doc1.txt", "doc2.txt"]

ontology = discovery.discover_ontology(documents, filenames)

# Access results
print(f"Found {len(ontology['entities'])} entities")
print(f"Found {len(ontology['relationships'])} relationships")
```

### With GraphRAG Integration

```python
from src.graph_rag import GraphRAG

# Initialize GraphRAG (ontology discovery included automatically)
graph_rag = GraphRAG()

# Discover ontology first
ontology_data = graph_rag.discover_ontology("./data")

# Then build knowledge graph (uses discovered ontology)
graph_rag.load_documents("./data")

# Get ontology data for analysis
ontology = graph_rag.get_ontology_data()
```

## 📁 File Structure

```
RAG-vs-graphRAG/
├── src/
│   ├── ontology_discovery.py     # Main ontology discovery module
│   ├── graph_rag.py              # Enhanced GraphRAG with ontology
│   └── traditional_rag.py        # Traditional RAG (unchanged)
├── app.py                        # Streamlit app with ontology UI
├── test_ontology.py              # Test script
└── data/                         # Your enterprise documents
    ├── meeting_notes_q4_planning.txt
    ├── support_tickets_enterprise.txt
    ├── engineering_decisions_log.txt
    └── product_spec_auth_service.txt
```

## 🧪 Test Results

From your enterprise documents, the system discovered:

- **📊 202 entities** across 9 types
- **🔗 5 relationships** with linguistic patterns
- **🏷️ Entity types**: CUSTOMER, SYSTEM_COMPONENT, TECHNOLOGY, PERSON, ORG, FEATURE, ISSUE, METRIC, DATE
- **📈 Average frequency**: 1.93 mentions per entity

### Sample Discovered Entities:
- **Customers**: TechCorp Solutions, DataFlow Inc, CloudSync Solutions
- **Systems**: Authentication Service, Analytics Dashboard, Notification Service
- **People**: Mike Rodriguez, Sarah Chen, Lisa Thompson
- **Technologies**: Redis, JWT, Node.js, Docker, Kubernetes
- **Issues**: Performance issues, timeout errors, loading times

### Sample Discovered Relationships:
- "Authentication service" **CAUSES** "performance issues"
- "TechCorp Solutions" **USES** "analytics dashboard"
- "Mike Rodriguez" **MANAGES** "authentication service"
- "Redis implementation" **ENABLES** "session management"

## 🎨 Streamlit UI Features

### 📊 Ontology Statistics Dashboard
- Entity counts by type
- Relationship frequency analysis  
- Confidence metrics
- Average frequency indicators

### 🎯 Top Entities by Type
- Organized by entity categories
- Frequency and confidence scores
- Multi-column layout for easy scanning

### 🕸️ Relationship Patterns Table
- Source → Relationship → Target format
- Sortable by frequency and confidence
- Shows linguistic patterns used

### 🌐 3D Interactive Ontology Graph
- **Z-layers**: Entity types clustered by conceptual similarity
- **Node sizes**: Proportional to entity frequency
- **Colors**: Different entity types with consistent color coding
- **Edges**: Gray lines showing discovered relationships
- **Interactive**: Full 3D rotation and zoom capabilities

## 🔧 Configuration

### Entity Pattern Customization

Add your domain-specific patterns in `ontology_discovery.py`:

```python
self.entity_patterns = {
    'YOUR_DOMAIN_TYPE': [
        r'\b(your_pattern_here)\b',
        r'\b([A-Z][a-z]+\s+YourKeyword)\b',
    ]
}
```

### Relationship Pattern Customization

Add custom relationship patterns:

```python
self.relation_patterns = {
    RelationType.YOUR_TYPE: [
        r'(\w+(?:\s+\w+)*)\s+your_relationship_word\s+(\w+(?:\s+\w+)*)',
    ]
}
```

## 🌟 Integration with Your Existing UI Story

The ontology discovery perfectly complements your existing **3D visualization story**:

1. **📊 Vector Space** (left): Shows how Traditional RAG finds chunks by similarity
2. **🕸️ GraphRAG Gap-Filling** (right): Shows how GraphRAG bridges to missing chunks
3. **🧠 Ontology Discovery** (new): Shows the **hidden knowledge structure** that enables the bridging

This creates a complete narrative:
- **Similarity Search** → **Knowledge Graph** → **Hidden Ontology** → **Gap-Filling Magic**

## 🚀 Next Steps

1. **Run the system**: `streamlit run app.py`
2. **Click "Discover Hidden Ontology"** to analyze your documents
3. **Explore the 3D ontology visualization** to understand your knowledge structure
4. **Use the discovered patterns** to improve your GraphRAG performance
5. **Export ontology** for use in other systems: `graph_rag.export_ontology("ontology.json")`

## 💡 Benefits Over Manual Ontology Creation

- **Automated Discovery**: No manual ontology engineering required
- **Data-Driven**: Based on actual document content, not assumptions
- **Lightweight**: Runs efficiently in Streamlit without heavy infrastructure
- **Kuzu Compatible**: Works seamlessly with your existing graph database
- **Iterative**: Can be re-run as documents change to update ontology
- **Visual**: 3D visualization makes complex relationships understandable

The system transforms your **unstructured enterprise documents** into a **structured knowledge ontology** that reveals hidden patterns and enables more intelligent GraphRAG retrieval! 🎯
