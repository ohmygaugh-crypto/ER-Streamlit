# Development Cache System 🗄️

## Overview

To reduce API costs during development, we've implemented a caching system that saves:
- **Document chunks** (text splitting results)
- **Embeddings** (expensive API calls to embedding models)
- **Graph processing state** (entity extraction and relationship building)

## Quick Start

### 1. Enable Development Mode

The development cache is **enabled by default** in the Streamlit app. You'll see a checkbox in the sidebar:

```
🗄️ Development Mode (Cache Data) ✅
```

Keep this checked to avoid re-processing data unnecessarily.

### 2. How It Works

**First Run:**
```
🔄 Processing documents into chunks...
🔄 Generating embeddings...
💾 Saved 45 chunks to cache
💾 Saved embeddings for 45 chunks to cache
```

**Subsequent Runs:**
```
📁 Using cached chunks (45 chunks)
📁 Using cached embeddings for 45 chunks
```

## Cost Savings

### Traditional RAG
- ✅ **Chunks cached**: No re-processing of text splitting
- ✅ **Embeddings cached**: No repeated calls to `embedding_model.encode()`

### GraphRAG  
- ✅ **Graph processing cached**: Skips entire document processing pipeline
- ✅ **Entity extraction cached**: No repeated LLM calls for entity extraction
- ✅ **Embeddings cached**: Same as Traditional RAG

## Cache Management

### View Cache Status
```bash
python dev_cache_utils.py info
```

Output:
```
📊 Development Cache Information:
   Enabled: True
   Cache Directory: dev_cache
   Number of Files: 3
   Total Size: 2.4 MB
   Cached Files:
     - chunks_a1b2c3d4.pkl
     - embeddings_e5f6g7h8.pkl
     - graph_i9j0k1l2.pkl
```

### Clear Cache
```bash
python dev_cache_utils.py clear
```

### Check Cache Status
```bash
python dev_cache_utils.py status
```

## Technical Details

### Cache Key Generation
Cache keys are generated based on:
- **File paths and modification times** (detects file changes)
- **Chunking parameters** (chunk_size, chunk_overlap)
- **Model names** (different models = different cache)

### Cache Storage
- **Location**: `./dev_cache/` directory
- **Format**: Pickle files (`.pkl`)
- **Naming**: `{type}_{hash}.pkl` (e.g., `embeddings_a1b2c3.pkl`)

### Automatic Cache Invalidation
Cache is automatically invalidated when:
- Source files are modified (timestamp check)
- Chunking parameters change
- Model names change

## Production Mode

To disable caching (for production):

```python
# In your code
trad_rag = TraditionalRAG(dev_mode=False)
graph_rag = GraphRAG(dev_mode=False)
```

Or uncheck the "Development Mode" checkbox in the Streamlit sidebar.

## Expected Savings

With development cache enabled:

| Operation | First Run | Cached Run | Savings |
|-----------|-----------|------------|---------|
| Document Chunking | ~1s | ~0.1s | 90% faster |
| Embedding Generation | ~30s | ~0.1s | 99% faster |
| Graph Processing | ~60s | ~0.1s | 99% faster |

**Total**: From minutes to seconds on repeated runs! 🚀

## Troubleshooting

### Cache Not Working?
1. Check that `dev_mode=True` (default)
2. Ensure cache directory is writable
3. Run `python dev_cache_utils.py info` to verify

### Out of Disk Space?
```bash
python dev_cache_utils.py clear
```

### Want Fresh Data?
```bash
python dev_cache_utils.py clear
```
Then run your app again - it will regenerate and cache fresh data.

---

**💡 Pro Tip**: Leave development mode enabled during development, disable only for production deployments!
