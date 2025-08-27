"""
Data Exporters
Handles exporting data to various formats (Kuzu, Pinecone, Neo4j)
"""
import streamlit as st
import json
import io
import csv
import zipfile
from pathlib import Path


def export_kuzu_database(graph_rag):
    """Export complete Kuzu database as JSON"""
    try:
        export_data = graph_rag.export_kuzu_database()
        if 'error' not in export_data:
            json_data = json.dumps(export_data, indent=2)
            
            st.sidebar.download_button(
                label="⬇️ Download Graph Export",
                data=json_data,
                file_name=f"graph_export_{Path(graph_rag.db_path).name}.json",
                mime="application/json",
                help="Complete graph data: chunks, entities, relationships, embeddings"
            )
            
            st.sidebar.success(f"✅ Ready! {len(export_data['chunks'])} chunks, {len(export_data['entities'])} entities")
            return True
        else:
            st.sidebar.error(f"Export failed: {export_data['error']}")
            return False
    except Exception as e:
        st.sidebar.error(f"Export error: {str(e)}")
        return False


def export_pinecone_format(graph_rag):
    """Export data in Pinecone-compatible format"""
    try:
        # Create Pinecone-formatted data from graph export
        export_data = graph_rag.export_kuzu_database()
        pinecone_data = {
            "vectors": [
                {
                    "id": chunk["id"],
                    "values": chunk["embedding"],
                    "metadata": {
                        "content": chunk["content"][:1000],
                        "filename": chunk["filename"],
                        "chunk_index": chunk["chunk_index"]
                    }
                }
                for chunk in export_data["chunks"]
            ],
            "metadata": {
                "total_vectors": len(export_data["chunks"]),
                "embedding_dimension": len(export_data["chunks"][0]["embedding"]) if export_data["chunks"] else 0
            }
        }
        
        json_data = json.dumps(pinecone_data, indent=2)
        st.sidebar.download_button(
            label="⬇️ Pinecone JSON",
            data=json_data,
            file_name="pinecone_vectors.json",
            mime="application/json"
        )
        return True
    except Exception as e:
        st.sidebar.error(f"Pinecone export error: {str(e)}")
        return False


def export_neo4j_format(graph_rag):
    """Export data in Neo4j-compatible format (CSV + Cypher script)"""
    try:
        export_data = graph_rag.export_kuzu_database()
        
        # Create in-memory zip file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Chunks CSV
            chunks_csv = io.StringIO()
            chunks_writer = csv.writer(chunks_csv)
            chunks_writer.writerow(['chunk_id:ID', 'content', 'filename', 'chunk_index:int', ':LABEL'])
            for chunk in export_data['chunks']:
                chunks_writer.writerow([
                    chunk['id'],
                    chunk['content'].replace('"', '""'),
                    chunk['filename'],
                    chunk['chunk_index'],
                    'Chunk'
                ])
            zip_file.writestr('chunks.csv', chunks_csv.getvalue())
            
            # Entities CSV
            entities_csv = io.StringIO()
            entities_writer = csv.writer(entities_csv)
            entities_writer.writerow(['entity_id:ID', 'name', 'type', ':LABEL'])
            for entity in export_data['entities']:
                entities_writer.writerow([
                    entity['id'],
                    entity['name'],
                    entity['type'],
                    'Entity'
                ])
            zip_file.writestr('entities.csv', entities_csv.getvalue())
            
            # Import script
            import_script = f"""// Neo4j Import Script
LOAD CSV WITH HEADERS FROM 'file:///chunks.csv' AS row
CREATE (c:Chunk {{
    id: row.chunk_id,
    content: row.content,
    filename: row.filename,
    chunk_index: toInteger(row.chunk_index)
}});

LOAD CSV WITH HEADERS FROM 'file:///entities.csv' AS row
CREATE (e:Entity {{
    id: row.entity_id,
    name: row.name,
    type: row.type
}});

CREATE INDEX chunk_id_index FOR (c:Chunk) ON (c.id);
CREATE INDEX entity_id_index FOR (e:Entity) ON (e.id);
"""
            zip_file.writestr('import_script.cypher', import_script)
        
        zip_buffer.seek(0)
        st.sidebar.download_button(
            label="⬇️ Neo4j ZIP",
            data=zip_buffer.getvalue(),
            file_name="neo4j_import.zip",
            mime="application/zip"
        )
        return True
    except Exception as e:
        st.sidebar.error(f"Neo4j export error: {str(e)}")
        return False
