"""
Data Importers
Handles importing data from various formats into the RAG systems
"""
import streamlit as st
import json
from collections import defaultdict
from pathlib import Path


def import_graph_data(uploaded_file, trad_rag, graph_rag):
    """Import previously exported graph data into Kuzu database"""
    try:
        # Read the uploaded JSON file
        data = json.load(uploaded_file)
        
        # Validate the data structure
        if not isinstance(data, dict) or 'chunks' not in data:
            st.error("❌ Invalid file format. Please upload a valid graph export JSON.")
            return False
        
        chunks = data.get('chunks', [])
        entities = data.get('entities', [])
        relationships = data.get('relationships', [])
        
        with st.spinner(f"🚀 Native Kuzu import: {len(chunks)} chunks, {len(entities)} entities, {len(relationships)} relationships..."):
            
            # Use native Kuzu JSON import
            success = graph_rag.import_from_kuzu_json(data)
            
            if not success:
                st.error("❌ Native Kuzu import failed")
                return False
            
            # Prepare Traditional RAG data from chunks
            st.info("🔄 Setting up Traditional RAG...")
            
            # Group chunks by document and create traditional RAG chunks
            doc_groups = defaultdict(list)
            for chunk in chunks:
                doc_groups[chunk['filename']].append(chunk['content'])
            
            # Create documents for Traditional RAG
            trad_documents = []
            for filename, chunk_contents in doc_groups.items():
                full_content = '\n\n'.join(chunk_contents)
                trad_documents.append({
                    'filename': filename,
                    'content': full_content,
                    'filepath': filename
                })
            
            # Process for Traditional RAG
            trad_chunks = trad_rag.chunk_documents(trad_documents)
            trad_rag.create_embeddings(trad_chunks)
            
            # Store documents for GraphRAG
            graph_rag.documents = trad_documents
            
            # Rebuild entity mappings from imported data
            graph_rag.entity_mappings = {}
            for entity in entities:
                entity_name = entity['name'].lower().replace(' ', '_')
                if entity_name not in graph_rag.entity_mappings:
                    graph_rag.entity_mappings[entity_name] = []
                
                # Find chunks related to this entity through relationships (updated for native format)
                related_chunk_ids = [
                    rel['to'] for rel in relationships 
                    if rel['from'] == entity['id']  # Updated for native Kuzu format
                ]
                graph_rag.entity_mappings[entity_name].extend(related_chunk_ids)
            
            print(f"🔗 Rebuilt entity mappings for {len(graph_rag.entity_mappings)} entities")
        
        st.success(f"✅ Native Kuzu import successful: {len(chunks)} chunks, {len(entities)} entities, {len(relationships)} relationships!")
        return True
        
    except json.JSONDecodeError:
        st.error("❌ Invalid JSON file. Please check the file format.")
        return False
    except Exception as e:
        st.error(f"❌ Import error: {str(e)}")
        return False
