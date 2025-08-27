"""
GraphRAG Implementation using Kuzu
Extracts entities, creates knowledge graph, and performs graph-enhanced retrieval
Enhanced with ontology discovery capabilities
"""
import os
import re
from typing import List, Dict, Any, Set, Tuple
from pathlib import Path
import pandas as pd
import kuzu
from sentence_transformers import SentenceTransformer

from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.graph_transformers import LLMGraphTransformer
from langchain_core.documents import Document
import tiktoken
import networkx as nx
from collections import defaultdict
import json
import numpy as np
# Caching removed - using export/import instead

# Import ontology discovery
try:
    from .ontology_discovery import OntologyDiscovery
except ImportError:
    from ontology_discovery import OntologyDiscovery

class GraphRAG:
    def __init__(self, db_path: str = "./graph_db", model_name: str = "all-MiniLM-L6-v2", dev_mode: bool = False):
        """Initialize GraphRAG with Kuzu database and NLP models"""
        self.db_path = db_path
        self.model_name = model_name
        
        # Initialize database
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        
        # Initialize models
        self.embedding_model = SentenceTransformer(model_name)
        

        
        # Initialize LLM
        self.llm = None
        self.llm_graph_transformer = None
        api_key = os.getenv("OPENAI_API_KEY")
        print(f"🔑 API Key Status: {'✅ Found' if api_key else '❌ Not Found'}")
        if api_key:
            print(f"🔑 API Key prefix: {api_key[:10]}...")
            self.llm = ChatOpenAI(temperature=0, model="gpt-4o")
            
            # Initialize LangChain Graph Transformer for enhanced entity extraction
            self.llm_graph_transformer = LLMGraphTransformer(
                llm=self.llm,
                allowed_nodes=["Person", "Company", "System", "Technology", "Issue", "Feature", "Decision"],
                allowed_relationships=[
                    ("Person", "WORKS_AT", "Company"),
                    ("Person", "LEADS", "System"),
                    ("Company", "USES", "System"),
                    ("System", "DEPENDS_ON", "Technology"),
                    ("Issue", "AFFECTS", "Company"),
                    ("Issue", "BLOCKS", "Feature"),
                    ("Decision", "ADDRESSES", "Issue"),
                    ("Person", "MAKES", "Decision")
                ],
                node_properties=["priority", "status", "date", "impact"]
            )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        
        # Create schema
        self._create_schema()
        
        # Initialize ontology discovery
        self.ontology_discovery = OntologyDiscovery(use_llm=bool(self.llm))
        
        # Storage for discovered ontology
        self.discovered_ontology = None
        
        # Entity resolution mappings
        self.entity_mappings = {}
    
    def _create_schema(self):
        """Create knowledge graph schema in Kuzu"""
        try:
            # Create node tables
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Document(id STRING, filename STRING, content STRING, PRIMARY KEY(id))")
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Chunk(id STRING, content STRING, filename STRING, chunk_index INT64, token_count INT64, embedding DOUBLE[], PRIMARY KEY(id))")
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Entity(id STRING, name STRING, type STRING, PRIMARY KEY(id))")
            self.conn.execute("CREATE NODE TABLE IF NOT EXISTS Concept(id STRING, name STRING, description STRING, importance DOUBLE, PRIMARY KEY(id))")
            
            # Create relationship tables
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS CONTAINS(FROM Document TO Chunk)")
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS MENTIONS(FROM Chunk TO Entity, frequency INT64)")
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS RELATES_TO(FROM Entity TO Entity, relationship_type STRING, confidence DOUBLE)")
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS ASSOCIATED_WITH(FROM Entity TO Concept, strength DOUBLE)")
            self.conn.execute("CREATE REL TABLE IF NOT EXISTS DEPENDS_ON(FROM Concept TO Concept, dependency_type STRING)")
            
            print("Knowledge graph schema created successfully")
        except Exception as e:
            print(f"Schema creation error (may already exist): {e}")
    
    def extract_entities_with_langchain(self, text: str, filename: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Extract entities and relationships using LangChain LLMGraphTransformer"""
        if not self.llm_graph_transformer:
            return [], []
        
        try:
            # Convert text to LangChain Document format
            documents = [Document(page_content=text, metadata={"filename": filename})]
            
            # Extract graph structure using LLM
            graph_documents = self.llm_graph_transformer.convert_to_graph_documents(documents)
            
            entities = []
            relationships = []
            
            if graph_documents:
                graph_doc = graph_documents[0]
                
                # Convert nodes to our entity format
                for node in graph_doc.nodes:
                    entities.append({
                        'name': node.id,
                        'type': node.type,
                        'properties': node.properties,
                        'filename': filename,
                        'context': text[:200] + "..."  # First 200 chars as context
                    })
                
                # Convert relationships to our format
                for rel in graph_doc.relationships:
                    relationships.append({
                        'source': rel.source.id,
                        'target': rel.target.id,
                        'relationship_type': rel.type,
                        'properties': rel.properties,
                        'confidence': 0.9,  # LangChain extractions are high confidence
                        'context': f"LLM extracted relationship from {filename}"
                    })
            
            print(f"LangChain extracted {len(entities)} entities and {len(relationships)} relationships from {filename}")
            return entities, relationships
            
        except Exception as e:
            print(f"❌ LangChain extraction failed for {filename}: {e}")
            print(f"❌ Error type: {type(e).__name__}")
            print(f"❌ Full error details: {str(e)}")
            # Don't fall back - we NEED the LLM results, not spaCy
            return [], []


    

    

    
    def resolve_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve entity variations to canonical forms"""
        resolved = []
        entity_groups = defaultdict(list)
        
        # Group similar entities
        for entity in entities:
            key = (entity['name'].lower().strip(), entity['type'])
            entity_groups[key].append(entity)
        
        # Create canonical entities
        for (name, entity_type), group in entity_groups.items():
            # Use most common context or first occurrence
            canonical = group[0].copy()
            canonical['frequency'] = len(group)
            canonical['contexts'] = [e['context'] for e in group[:3]]  # Keep top 3 contexts
            canonical['source_files'] = list(set(e['filename'] for e in group))
            
            resolved.append(canonical)
        
        return resolved
    
    def extract_relationships(self, entities: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """Extract relationships between entities using co-occurrence and patterns"""
        relationships = []
        
        # Co-occurrence based relationships
        for i, entity1 in enumerate(entities):
            for entity2 in entities[i+1:]:
                if entity1['name'] != entity2['name']:
                    # Check if entities co-occur in same context window
                    if self._entities_cooccur(entity1, entity2, text):
                        rel_type = self._determine_relationship_type(entity1, entity2, text)
                        if rel_type:
                            relationships.append({
                                'source': entity1['name'],
                                'target': entity2['name'],
                                'relationship_type': rel_type,
                                'confidence': 0.7,
                                'context': f"Co-occurrence in {entity1['filename']}"
                            })
        
        # Pattern-based relationships
        pattern_relationships = self._extract_pattern_relationships(text, entities)
        relationships.extend(pattern_relationships)
        
        return relationships
    
    def _entities_cooccur(self, entity1: Dict, entity2: Dict, text: str) -> bool:
        """Check if two entities occur within same context window"""
        # Simple implementation: check if both entities appear in same sentence/paragraph
        sentences = text.split('.')
        for sentence in sentences:
            if entity1['name'].lower() in sentence.lower() and entity2['name'].lower() in sentence.lower():
                return True
        return False
    
    def _determine_relationship_type(self, entity1: Dict, entity2: Dict, text: str) -> str:
        """Determine relationship type between entities"""
        type1, type2 = entity1['type'], entity2['type']
        
        # Customer-System relationships
        if type1 == 'CUSTOMER' and type2 == 'SYSTEM':
            return 'USES'
        elif type1 == 'SYSTEM' and type2 == 'CUSTOMER':
            return 'SERVES'
        
        # System-System relationships
        elif type1 == 'SYSTEM' and type2 == 'SYSTEM':
            return 'DEPENDS_ON'
        
        # Technology relationships
        elif type1 == 'TECHNOLOGY' or type2 == 'TECHNOLOGY':
            return 'IMPLEMENTED_WITH'
        
        return 'RELATED_TO'
    
    def _extract_pattern_relationships(self, text: str, entities: List[Dict]) -> List[Dict]:
        """Extract relationships using linguistic patterns"""
        relationships = []
        entity_names = [e['name'] for e in entities]
        
        # Dependency patterns
        dependency_patterns = [
            r'(\w+(?:\s+\w+)*)\s+(?:depends on|requires|needs)\s+(\w+(?:\s+\w+)*)',
            r'(\w+(?:\s+\w+)*)\s+(?:blocks|prevents)\s+(\w+(?:\s+\w+)*)',
            r'(\w+(?:\s+\w+)*)\s+(?:enables|allows)\s+(\w+(?:\s+\w+)*)'
        ]
        
        for pattern in dependency_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source, target = match.groups()
                if any(source.lower() in name.lower() for name in entity_names) and \
                   any(target.lower() in name.lower() for name in entity_names):
                    relationships.append({
                        'source': source.strip(),
                        'target': target.strip(),
                        'relationship_type': 'DEPENDS_ON',
                        'confidence': 0.8,
                        'context': match.group(0)
                    })
        
        return relationships
    
    def discover_ontology(self, data_dir: str) -> Dict[str, Any]:
        """Discover ontology from documents before building knowledge graph"""
        print("🔍 Discovering ontology from documents...")
        
        data_path = Path(data_dir)
        documents = []
        filenames = []
        
        # Load all documents
        for file_path in data_path.glob("*.txt"):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                documents.append(content)
                filenames.append(file_path.name)
        
        # Discover ontology
        self.discovered_ontology = self.ontology_discovery.discover_ontology(documents, filenames)
        
        print(f"✅ Ontology discovery complete: {self.discovered_ontology['statistics']}")
        return self.discovered_ontology

    def load_documents(self, data_dir: str, discover_ontology_first: bool = True) -> None:
        """Load documents and build knowledge graph"""
        print("Loading documents and building knowledge graph...")
        
        # TEMPORARILY DISABLED: Discover ontology first if requested (for debugging)
        # if discover_ontology_first and not self.discovered_ontology:
        #     self.discover_ontology(data_dir)
        print("🔧 Ontology discovery temporarily disabled for API key debugging")
        
        # Clear existing data
        try:
            self.conn.execute("MATCH (n) DETACH DELETE n")
            print("Cleared existing graph data")
        except:
            pass
        
        # Recreate schema
        self._create_schema()
        
        data_path = Path(data_dir)
        all_entities = []
        all_relationships = []
        
        # Process each document
        for file_path in data_path.glob("*.txt"):
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Store document
            doc_id = f"doc_{file_path.stem}"
            try:
                self.conn.execute(
                    "CREATE (:Document {id: $doc_id, filename: $filename, content: $content})",
                    parameters={"doc_id": doc_id, "filename": file_path.name, "content": content}
                )
            except:
                # Document might already exist, skip
                pass
            
            # Chunk document
            chunks = self.text_splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_path.stem}_chunk_{i}"
                embedding = self.embedding_model.encode(chunk).tolist()
                token_count = len(tiktoken.get_encoding("cl100k_base").encode(chunk))
                
                # Store chunk
                try:
                    self.conn.execute(
                        "CREATE (:Chunk {id: $chunk_id, content: $content, filename: $filename, chunk_index: $idx, token_count: $tokens, embedding: $embedding})",
                        parameters={
                            "chunk_id": chunk_id,
                            "content": chunk,
                            "filename": file_path.name,
                            "idx": i,
                            "tokens": token_count,
                            "embedding": embedding
                        }
                    )
                except:
                    # Chunk might already exist, skip
                    pass
                
                # Create document-chunk relationship
                try:
                    self.conn.execute(
                        "MATCH (d:Document {id: $doc_id}), (c:Chunk {id: $chunk_id}) CREATE (d)-[:CONTAINS]->(c)",
                        parameters={"doc_id": doc_id, "chunk_id": chunk_id}
                    )
                except:
                    # Relationship might already exist
                    pass
                
                # Extract entities and relationships from chunk using LangChain
                if self.llm_graph_transformer:
                    entities, chunk_relationships = self.extract_entities_with_langchain(chunk, file_path.name)
                    all_relationships.extend(chunk_relationships)
                else:
                    # Require LLM for proper entity extraction
                    print(f"❌ No LLM available - cannot extract entities for {file_path.name}")
                    print(f"❌ Set OPENAI_API_KEY to get proper LLM-generated relationships")
                    entities = []
                all_entities.extend(entities)
                
                # Store entity mentions
                for entity in entities:
                    entity_id = f"entity_{entity['name'].lower().replace(' ', '_')}"
                    
                    # Create entity if not exists
                    try:
                        self.conn.execute(
                            "CREATE (:Entity {id: $entity_id, name: $name, type: $type})",
                            parameters={
                                "entity_id": entity_id,
                                "name": entity['name'],
                                "type": entity['type']
                            }
                        )
                    except Exception as e:
                        # Entity might already exist, skip
                        pass
                    
                    # Create mention relationship
                    try:
                        self.conn.execute(
                            "MATCH (c:Chunk {id: $chunk_id}), (e:Entity {id: $entity_id}) CREATE (c)-[:MENTIONS {frequency: 1}]->(e)",
                            parameters={
                                "chunk_id": chunk_id,
                                "entity_id": entity_id
                            }
                        )
                    except Exception as e:
                        # Relationship might already exist
                        pass
            
            # LLM already extracted relationships from chunks, no need for document-level extraction
        
        # Resolve entities and create relationships
        resolved_entities = self.resolve_entities(all_entities)
        self._create_entity_relationships(all_relationships)
        
        print(f"Knowledge graph built with {len(resolved_entities)} entities and {len(all_relationships)} relationships")
    
    def _create_entity_relationships(self, relationships: List[Dict]) -> None:
        """Create relationships between entities in the graph"""
        for rel in relationships:
            source_id = f"entity_{rel['source'].lower().replace(' ', '_')}"
            target_id = f"entity_{rel['target'].lower().replace(' ', '_')}"
            
            try:
                # Check if entities exist first, create relationship only if both exist
                result = self.conn.execute(
                    "MATCH (s:Entity {id: $source_id}), (t:Entity {id: $target_id}) RETURN s.id, t.id",
                    parameters={"source_id": source_id, "target_id": target_id}
                )
                
                if result.has_next():
                    self.conn.execute(
                        "MATCH (s:Entity {id: $source_id}), (t:Entity {id: $target_id}) CREATE (s)-[:RELATES_TO {relationship_type: $rel_type, confidence: $conf}]->(t)",
                        parameters={
                            "source_id": source_id,
                            "target_id": target_id,
                            "rel_type": rel['relationship_type'],
                            "conf": rel['confidence']
                        }
                    )
            except Exception as e:
                print(f"Error creating relationship {rel['source']} -> {rel['target']}: {e}")
        
        print("✅ Graph data loaded successfully!")
    
    def graph_enhanced_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Perform graph-enhanced retrieval"""
        # Extract entities from query using LLM
        query_entities, _ = self.extract_entities_with_langchain(query, "query")
        
        # Find relevant chunks through entity connections
        relevant_chunks = []
        
        if query_entities:
            for entity in query_entities:
                entity_id = f"entity_{entity['name'].lower().replace(' ', '_')}"
                
                # Find chunks mentioning this entity or related entities
                try:
                    result = self.conn.execute(
                        """
                        MATCH (e:Entity {id: $entity_id})<-[:MENTIONS]-(c:Chunk)
                        RETURN c.id, c.content, c.filename, c.chunk_index
                        UNION
                        MATCH (e:Entity {id: $entity_id})-[:RELATES_TO]->(related:Entity)<-[:MENTIONS]-(c:Chunk)
                        RETURN c.id, c.content, c.filename, c.chunk_index
                        LIMIT $k
                        """,
                        parameters={"entity_id": entity_id, "k": k}
                    )
                    
                    while result.has_next():
                        record = result.get_next()
                        relevant_chunks.append({
                            'id': record[0],
                            'content': record[1],
                            'filename': record[2],
                            'chunk_index': record[3],
                            'source': 'graph_traversal'
                        })
                        
                except Exception as e:
                    print(f"Graph query error: {e}")
        
        # If no graph results, fall back to similarity search
        if not relevant_chunks:
            relevant_chunks = self._similarity_search_fallback(query, k)
        
        return relevant_chunks[:k]
    
    def _similarity_search_fallback(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Fallback similarity search when graph search fails"""
        query_embedding = self.embedding_model.encode(query).tolist()
        
        try:
            result = self.conn.execute(
                "MATCH (c:Chunk) RETURN c.id, c.content, c.filename, c.chunk_index, c.embedding LIMIT 100"
            )
            
            chunks_with_similarity = []
            while result.has_next():
                record = result.get_next()
                chunk_embedding = record[4]
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, chunk_embedding)
                
                chunks_with_similarity.append({
                    'id': record[0],
                    'content': record[1],
                    'filename': record[2],
                    'chunk_index': record[3],
                    'similarity': similarity,
                    'source': 'similarity_search'
                })
            
            # Sort by similarity and return top k
            chunks_with_similarity.sort(key=lambda x: x['similarity'], reverse=True)
            return chunks_with_similarity[:k]
            
        except Exception as e:
            print(f"Similarity search error: {e}")
            return []
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        import numpy as np
        vec1, vec2 = np.array(vec1), np.array(vec2)
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def answer_question(self, question: str, k: int = 5) -> Dict[str, Any]:
        """Answer question using GraphRAG approach"""
        # Get graph-enhanced retrieval results
        relevant_chunks = self.graph_enhanced_search(question, k)
        
        if not relevant_chunks:
            return {
                'answer': "No relevant information found in knowledge graph.",
                'retrieved_chunks': [],
                'method': 'graph_rag',
                'confidence': 0.0,
                'graph_insights': []
            }
        
        # Get additional graph insights
        graph_insights = self._get_graph_insights(question)
        
        # Prepare context
        context = "\n\n".join([chunk['content'] for chunk in relevant_chunks])
        
        # Generate answer
        answer = "LLM not available - please set OPENAI_API_KEY"
        confidence = 0.5
        
        if self.llm:
            try:
                # Enhanced prompt with graph context
                prompt = f"""Based on the following context from a knowledge graph, answer the question. The context includes information retrieved through entity relationships and dependencies.

Context from Knowledge Graph:
{context}

Additional Graph Insights:
{chr(10).join(graph_insights)}

Question: {question}

Provide a comprehensive answer that leverages the interconnected nature of the information:"""
                
                response = self.llm.invoke(prompt)
                answer = response.content
                confidence = 0.9  # Higher confidence due to graph context
                
            except Exception as e:
                answer = f"Error generating answer: {str(e)}"
                confidence = 0.0
        
        return {
            'answer': answer,
            'retrieved_chunks': relevant_chunks,
            'method': 'graph_rag',
            'confidence': confidence,
            'graph_insights': graph_insights,
            'context_used': context[:500] + "..." if len(context) > 500 else context
        }
    
    def _get_graph_insights(self, question: str) -> List[str]:
        """Get additional insights from graph structure"""
        insights = []
        
        try:
            # Find highly connected entities
            result = self.conn.execute(
                """
                MATCH (e:Entity)-[r:RELATES_TO]-()
                RETURN e.name, e.type, count(r) as connections
                ORDER BY connections DESC
                LIMIT 5
                """
            )
            
            connected_entities = []
            while result.has_next():
                record = result.get_next()
                connected_entities.append(f"{record[0]} ({record[1]}) - {record[2]} connections")
            
            if connected_entities:
                insights.append(f"Highly connected entities: {', '.join(connected_entities)}")
            
            # Find dependency chains
            result = self.conn.execute(
                """
                MATCH path = (a:Entity)-[:RELATES_TO {relationship_type: 'DEPENDS_ON'}*1..3]->(b:Entity)
                RETURN [node in nodes(path) | node.name] as dependency_chain
                LIMIT 3
                """
            )
            
            dependency_chains = []
            while result.has_next():
                record = result.get_next()
                chain = " -> ".join(record[0])
                dependency_chains.append(chain)
            
            if dependency_chains:
                insights.append(f"Dependency chains: {'; '.join(dependency_chains)}")
                
        except Exception as e:
            insights.append(f"Graph analysis error: {e}")
        
        return insights
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the GraphRAG system"""
        try:
            # Count nodes and relationships
            doc_count = self.conn.execute("MATCH (d:Document) RETURN count(d)").get_next()[0]
            chunk_count = self.conn.execute("MATCH (c:Chunk) RETURN count(c)").get_next()[0]
            entity_count = self.conn.execute("MATCH (e:Entity) RETURN count(e)").get_next()[0]
            rel_count = self.conn.execute("MATCH ()-[r:RELATES_TO]->() RETURN count(r)").get_next()[0]
            
            return {
                'documents': doc_count,
                'chunks': chunk_count,
                'entities': entity_count,
                'relationships': rel_count,
                'embedding_model': self.model_name,
                'status': 'Ready'
            }
        except Exception as e:
            return {'status': f'Error: {e}'}
    
    def get_graph_visualization_data(self) -> Dict[str, Any]:
        """Get data for graph visualization including chunks and entities"""
        try:
            nodes = []
            edges = []
            
            # Get all chunks as nodes
            try:
                chunk_result = self.conn.execute(
                    "MATCH (c:Chunk) RETURN c.id, c.content, c.filename LIMIT 30"
                )
                while chunk_result.has_next():
                    record = chunk_result.get_next()
                    chunk_id, content, filename = record
                    nodes.append({
                        'id': chunk_id,
                        'type': 'CHUNK',
                        'filename': filename,
                        'content': content[:100] + "..." if content else ""
                    })
            except Exception as e:
                print(f"Error getting chunks: {e}")
            
            # Get all entities as nodes  
            try:
                entity_result = self.conn.execute("MATCH (e:Entity) RETURN e.id, e.name, e.type LIMIT 50")
                while entity_result.has_next():
                    record = entity_result.get_next()
                    entity_id, entity_name, entity_type = record
                    nodes.append({
                        'id': entity_id,
                        'type': entity_type,
                        'name': entity_name
                    })
            except Exception as e:
                print(f"Error getting entities: {e}")
            
            # Get chunk-entity relationships (MENTIONS)
            try:
                mention_result = self.conn.execute(
                    "MATCH (c:Chunk)-[m:MENTIONS]->(e:Entity) RETURN c.id, e.id, 'MENTIONS'"
                )
                while mention_result.has_next():
                    record = mention_result.get_next()
                    chunk_id, entity_id, rel_type = record
                    edges.append({
                        'source': chunk_id,
                        'target': entity_id,
                        'relationship': rel_type,
                        'confidence': 0.9
                    })
            except Exception as e:
                print(f"Error getting chunk-entity relationships: {e}")
            
            # Get entity-entity relationships
            try:
                relationship_result = self.conn.execute(
                    "MATCH (e1:Entity)-[r]->(e2:Entity) WHERE e1.id <> e2.id RETURN e1.id, e2.id, label(r)"
                )
                while relationship_result.has_next():
                    record = relationship_result.get_next()
                    source_id, target_id, rel_type = record
                    edges.append({
                        'source': source_id,
                        'target': target_id,
                        'relationship': rel_type,
                        'confidence': 0.8
                    })
            except Exception as e:
                print(f"Error getting entity relationships: {e}")
            
            print(f"📊 Graph visualization: {len(nodes)} nodes ({sum(1 for n in nodes if n['type'] == 'CHUNK')} chunks, {sum(1 for n in nodes if n['type'] != 'CHUNK')} entities), {len(edges)} edges")
            return {
                'nodes': nodes,
                'edges': edges
            }
            
        except Exception as e:
            print(f"Graph visualization error: {e}")
            return {'nodes': [], 'edges': [], 'error': str(e)}

    def get_enhanced_chunk_embeddings(self) -> Dict[str, Any]:
        """Get chunk embeddings enhanced with entity information for visualization"""
        try:
            result = self.conn.execute(
                """
                MATCH (c:Chunk)
                OPTIONAL MATCH (c)-[:MENTIONS]->(e:Entity)
                RETURN c.id, c.content, c.filename, c.chunk_index, collect(e.name) as entities
                """
            )
            
            enhanced_chunks = []
            while result.has_next():
                record = result.get_next()
                chunk_id, content, filename, chunk_index, entities = record
                
                # Create enhanced content with entity information
                entity_text = " ".join(entities) if entities else ""
                enhanced_content = f"{content} [ENTITIES: {entity_text}]" if entities else content
                
                # Generate enhanced embedding
                embedding = self.embedding_model.encode([enhanced_content])[0]
                
                enhanced_chunks.append({
                    'chunk_id': chunk_id,
                    'content': content,
                    'filename': filename,
                    'chunk_index': chunk_index,
                    'entities': entities,
                    'enhanced_content': enhanced_content,
                    'embedding': embedding,
                    'token_count': len(tiktoken.get_encoding("cl100k_base").encode(content))
                })
            
            print(f"🕸️ GraphRAG enhanced embeddings for {len(enhanced_chunks)} chunks (with entity info)")
            return {'chunks': enhanced_chunks}
            
        except Exception as e:
            print(f"Error getting enhanced embeddings: {e}")
            return {'chunks': []}

    def get_ontology_data(self) -> Dict[str, Any]:
        """Get discovered ontology data for visualization"""
        if not self.discovered_ontology:
            return {'entities': {}, 'relationships': [], 'statistics': {}}
        return self.discovered_ontology

    def get_ontology_graph_data(self) -> Dict[str, Any]:
        """Get ontology data formatted for graph visualization"""
        if not self.discovered_ontology:
            return {'nodes': [], 'edges': []}
        
        # Convert entities to nodes
        nodes = []
        for name, entity in self.discovered_ontology['entities'].items():
            nodes.append({
                'id': name,
                'type': entity['type'],
                'frequency': entity['frequency'],
                'confidence': entity['confidence']
            })
        
        # Convert relationships to edges
        edges = []
        for rel in self.discovered_ontology['relationships']:
            edges.append({
                'source': rel['source'],
                'target': rel['target'],
                'relationship': rel['relation_type'],
                'frequency': rel['frequency'],
                'confidence': rel['confidence']
            })
        
        return {'nodes': nodes, 'edges': edges}

    def export_ontology(self, filepath: str, format: str = 'json'):
        """Export discovered ontology"""
        if self.discovered_ontology:
            self.ontology_discovery.export_ontology(filepath, format)
        else:
            print("No ontology discovered yet. Run discover_ontology() first.")
    
    def export_kuzu_database(self) -> Dict[str, Any]:
        """Export all data from Kuzu database for external use"""
        try:
            from datetime import datetime
            
            export_data = {
                "chunks": [],
                "entities": [],
                "relationships": [],
                "metadata": {
                    "export_timestamp": datetime.now().isoformat(),
                    "database_path": self.db_path
                }
            }
            
            # Export chunks
            try:
                result = self.conn.execute("MATCH (c:Chunk) RETURN c.id, c.content, c.filename, c.chunk_index, c.token_count, c.embedding")
                while result.has_next():
                    record = result.get_next()
                    export_data["chunks"].append({
                        "id": record[0],
                        "content": record[1],
                        "filename": record[2],
                        "chunk_index": record[3],
                        "token_count": record[4],
                        "embedding": record[5]
                    })
            except Exception as e:
                print(f"⚠️ No chunks found in database: {e}")
            
            # Export entities
            try:
                result = self.conn.execute("MATCH (e:Entity) RETURN e.id, e.name, e.type")
                while result.has_next():
                    record = result.get_next()
                    export_data["entities"].append({
                        "id": record[0],
                        "name": record[1],
                        "type": record[2]
                    })
            except Exception as e:
                print(f"⚠️ No entities found in database: {e}")
            
            # Export relationships in Kuzu JSON format (with from/to keys)
            try:
                # First check what relationships exist
                print("🔍 Checking for existing relationships...")
                
                # Check MENTIONS relationships
                mentions_result = self.conn.execute("MATCH (c:Chunk)-[m:MENTIONS]->(e:Entity) RETURN count(m) as mentions_count")
                if mentions_result.has_next():
                    mentions_count = mentions_result.get_next()[0]
                    print(f"   MENTIONS relationships: {mentions_count}")
                
                # Check RELATES_TO relationships  
                relates_result = self.conn.execute("MATCH (e1:Entity)-[r:RELATES_TO]->(e2:Entity) RETURN count(r) as relates_count")
                if relates_result.has_next():
                    relates_count = relates_result.get_next()[0]
                    print(f"   RELATES_TO relationships: {relates_count}")
                
                # Check ALL relationship types - using label() instead of type()
                try:
                    all_rels_result = self.conn.execute("MATCH ()-[r]->() RETURN label(r) as rel_type, count(r) as count")
                    print("   All relationship types in database:")
                    while all_rels_result.has_next():
                        record = all_rels_result.get_next()
                        print(f"     {record[0]}: {record[1]}")
                except:
                    print("   Could not get relationship type breakdown")
                
                # Export all relationships - using label() instead of type()
                result = self.conn.execute("""
                    MATCH (source)-[r]->(target)
                    RETURN source.id as from, target.id as to, label(r) as rel_type
                """)
                while result.has_next():
                    record = result.get_next()
                    rel_data = {
                        "from": record[0],
                        "to": record[1],
                        "rel_type": record[2]
                    }
                    export_data["relationships"].append(rel_data)
                    
                print(f"   Total relationships exported: {len(export_data['relationships'])}")
                    
            except Exception as e:
                print(f"⚠️ Error exporting relationships: {e}")
            
            print(f"📤 Exported Kuzu database:")
            print(f"   Chunks: {len(export_data['chunks'])}")
            print(f"   Entities: {len(export_data['entities'])}")
            print(f"   Relationships: {len(export_data['relationships'])}")
            
            return export_data
            
        except Exception as e:
            print(f"❌ Error exporting Kuzu database: {e}")
            return {"error": str(e)}
    
    def import_from_kuzu_json(self, json_data: Dict[str, Any]) -> bool:
        """Import data using native Kuzu COPY FROM JSON functionality"""
        try:
            import tempfile
            import json
            import os
            
            print("📥 Starting native Kuzu JSON import...")
            
            # Check Kuzu version and environment
            try:
                version_result = self.conn.execute("CALL kuzu_version() RETURN version")
                if version_result.has_next():
                    version = version_result.get_next()[0]
                    print(f"🔧 Kuzu Version: {version}")
            except:
                print("🔧 Kuzu Version: Unknown")
            
            # Install and load JSON extension
            try:
                self.conn.execute("INSTALL json")
                print("✅ Installed JSON extension")
            except Exception as e:
                print(f"⚠️ JSON extension install failed: {e}")
                print(f"⚠️ Error type: {type(e).__name__}")
            
            try:
                self.conn.execute("LOAD EXTENSION json")
                print("✅ Loaded JSON extension")
            except Exception as e:
                print(f"⚠️ JSON extension load: {e}")
                # If native JSON import fails, fall back to manual import
                print("📥 Falling back to manual import method...")
                return self._manual_import_fallback(json_data)
            
            # Test if JSON extension is working
            try:
                test_result = self.conn.execute("SELECT json_valid('{}') as test")
                if test_result.has_next():
                    print("✅ JSON extension is working")
                else:
                    print("⚠️ JSON extension test failed, using fallback")
                    return self._manual_import_fallback(json_data)
            except Exception as e:
                print(f"⚠️ JSON extension test failed: {e}, using fallback")
                return self._manual_import_fallback(json_data)
            
            # Clear existing data
            try:
                self.conn.execute("MATCH (n) DETACH DELETE n")
                print("✅ Cleared existing data")
            except:
                pass
            
            # Recreate schema
            self._create_schema()
            print("✅ Recreated schema")
            
            # Create temporary JSON files for each table
            with tempfile.TemporaryDirectory() as temp_dir:
                
                # Import chunks using COPY FROM JSON
                if json_data.get("chunks"):
                    chunks_file = os.path.join(temp_dir, "chunks.json")
                    with open(chunks_file, 'w') as f:
                        json.dump(json_data["chunks"], f)
                    
                    try:
                        self.conn.execute(f"COPY Chunk FROM '{chunks_file}'")
                        print(f"✅ Imported {len(json_data['chunks'])} chunks")
                    except Exception as e:
                        print(f"❌ Error importing chunks: {e}")
                        return False
                
                # Import entities using COPY FROM JSON
                if json_data.get("entities"):
                    entities_file = os.path.join(temp_dir, "entities.json")
                    with open(entities_file, 'w') as f:
                        json.dump(json_data["entities"], f)
                    
                    try:
                        self.conn.execute(f"COPY Entity FROM '{entities_file}'")
                        print(f"✅ Imported {len(json_data['entities'])} entities")
                    except Exception as e:
                        print(f"❌ Error importing entities: {e}")
                        return False
                
                # Import relationships using COPY FROM JSON
                if json_data.get("relationships"):
                    # Group relationships by type
                    rel_types = {}
                    for rel in json_data["relationships"]:
                        rel_type = rel.get("rel_type", "RELATED_TO")
                        if rel_type not in rel_types:
                            rel_types[rel_type] = []
                        rel_types[rel_type].append(rel)
                    
                    for rel_type, rels in rel_types.items():
                        # Check if relationship table exists, create if not
                        try:
                            # Try to create relationship table (will fail if exists, which is fine)
                            self.conn.execute(f"""
                                CREATE REL TABLE IF NOT EXISTS {rel_type}(
                                    FROM Entity TO Entity,
                                    confidence DOUBLE DEFAULT 1.0
                                )
                            """)
                        except:
                            pass  # Table might already exist
                        
                        # Create temporary file for this relationship type
                        rel_file = os.path.join(temp_dir, f"{rel_type}.json")
                        with open(rel_file, 'w') as f:
                            json.dump(rels, f)
                        
                        try:
                            self.conn.execute(f"COPY {rel_type} FROM '{rel_file}'")
                            print(f"✅ Imported {len(rels)} {rel_type} relationships")
                        except Exception as e:
                            print(f"❌ Error importing {rel_type} relationships: {e}")
            
            print("📥 Native Kuzu JSON import completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error in native Kuzu JSON import: {e}")
            print("📥 Falling back to manual import method...")
            return self._manual_import_fallback(json_data)
    
    def _manual_import_fallback(self, json_data: Dict[str, Any]) -> bool:
        """Fallback manual import when native JSON import fails"""
        try:
            print("📥 Starting manual import fallback...")
            
            chunks = json_data.get("chunks", [])
            entities = json_data.get("entities", [])
            relationships = json_data.get("relationships", [])
            
            # Import chunks manually
            for chunk in chunks:
                try:
                    self.conn.execute(
                        "CREATE (:Chunk {id: $chunk_id, content: $content, filename: $filename, chunk_index: $idx, token_count: $tokens, embedding: $embedding})",
                        parameters={
                            "chunk_id": chunk['id'],
                            "content": chunk['content'],
                            "filename": chunk['filename'],
                            "idx": chunk['chunk_index'],
                            "tokens": chunk['token_count'],
                            "embedding": chunk['embedding']
                        }
                    )
                except Exception as e:
                    print(f"Error importing chunk {chunk['id']}: {e}")
            
            print(f"✅ Manually imported {len(chunks)} chunks")
            
            # Import entities manually
            for entity in entities:
                try:
                    self.conn.execute(
                        "CREATE (:Entity {id: $entity_id, name: $name, type: $type})",
                        parameters={
                            "entity_id": entity['id'],
                            "name": entity['name'],
                            "type": entity['type']
                        }
                    )
                except Exception as e:
                    print(f"Error importing entity {entity['id']}: {e}")
            
            print(f"✅ Manually imported {len(entities)} entities")
            
            # Import relationships manually (handle both old and new formats)
            relationship_count = 0
            mentions_count = 0
            relates_to_count = 0
            
            for rel in relationships:
                try:
                    # Handle both formats: old (source_id/target_id) and new (from/to)
                    source_id = rel.get('from', rel.get('source_id'))
                    target_id = rel.get('to', rel.get('target_id'))
                    rel_type = rel.get('rel_type', rel.get('relationship_type', 'RELATED_TO'))
                    confidence = rel.get('confidence', rel.get('properties', {}).get('confidence', 1.0))
                    
                    if source_id and target_id:
                        # Handle different relationship types with proper node type matching
                        if rel_type == 'MENTIONS':
                            # MENTIONS: Chunk -> Entity
                            try:
                                self.conn.execute(
                                    f"MATCH (source:Chunk {{id: $source_id}}), (target:Entity {{id: $target_id}}) CREATE (source)-[:MENTIONS {{frequency: 1}}]->(target)",
                                    parameters={
                                        "source_id": source_id,
                                        "target_id": target_id
                                    }
                                )
                                mentions_count += 1
                            except Exception as e:
                                print(f"Error importing MENTIONS relationship {source_id}->{target_id}: {e}")
                        
                        elif rel_type == 'RELATES_TO':
                            # RELATES_TO: Entity -> Entity  
                            try:
                                self.conn.execute(
                                    f"MATCH (source:Entity {{id: $source_id}}), (target:Entity {{id: $target_id}}) CREATE (source)-[:RELATES_TO {{relationship_type: 'RELATED_TO', confidence: $conf}}]->(target)",
                                    parameters={
                                        "source_id": source_id,
                                        "target_id": target_id,
                                        "conf": confidence
                                    }
                                )
                                relates_to_count += 1
                            except Exception as e:
                                print(f"Error importing RELATES_TO relationship {source_id}->{target_id}: {e}")
                        
                        else:
                            # Other relationship types: try generic approach
                            try:
                                self.conn.execute(
                                    f"MATCH (source {{id: $source_id}}), (target {{id: $target_id}}) CREATE (source)-[:{rel_type} {{confidence: $conf}}]->(target)",
                                    parameters={
                                        "source_id": source_id,
                                        "target_id": target_id,
                                        "conf": confidence
                                    }
                                )
                            except Exception as e:
                                print(f"Error importing {rel_type} relationship {source_id}->{target_id}: {e}")
                        
                        relationship_count += 1
                        
                except Exception as e:
                    print(f"Error processing relationship: {e}")
            
            print(f"✅ Manually imported {relationship_count} relationships ({mentions_count} MENTIONS, {relates_to_count} RELATES_TO)")
            print("📥 Manual import fallback completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error in manual import fallback: {e}")
            return False
