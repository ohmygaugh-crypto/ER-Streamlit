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
import spacy
from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import networkx as nx
from collections import defaultdict
import json

# Import ontology discovery
try:
    from .ontology_discovery import OntologyDiscovery
except ImportError:
    from ontology_discovery import OntologyDiscovery

class GraphRAG:
    def __init__(self, db_path: str = "./graph_db", model_name: str = "all-MiniLM-L6-v2"):
        """Initialize GraphRAG with Kuzu database and NLP models"""
        self.db_path = db_path
        self.model_name = model_name
        
        # Initialize database
        self.db = kuzu.Database(db_path)
        self.conn = kuzu.Connection(self.db)
        
        # Initialize models
        self.embedding_model = SentenceTransformer(model_name)
        
        # Load spacy model for NER
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Please install spacy English model: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Initialize LLM
        self.llm = None
        if os.getenv("OPENAI_API_KEY"):
            self.llm = ChatOpenAI(temperature=0)
        
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
    
    def extract_entities(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Extract entities using spaCy NER and custom patterns"""
        entities = []
        
        if not self.nlp:
            return self._extract_entities_fallback(text, filename)
        
        doc = self.nlp(text)
        
        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ['PERSON', 'ORG', 'PRODUCT', 'EVENT', 'DATE']:
                entities.append({
                    'name': ent.text.strip(),
                    'type': ent.label_,
                    'context': ent.sent.text if ent.sent else "",
                    'filename': filename
                })
        
        # Extract custom enterprise entities
        custom_entities = self._extract_custom_entities(text, filename)
        entities.extend(custom_entities)
        
        return entities
    
    def _extract_entities_fallback(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Fallback entity extraction using regex patterns"""
        entities = []
        
        # Customer names (capitalized words ending with Inc, Corp, Solutions, etc.)
        customer_pattern = r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Inc|Corp|Solutions|Systems|Technologies|Ltd|LLC))\b'
        for match in re.finditer(customer_pattern, text):
            entities.append({
                'name': match.group(1),
                'type': 'CUSTOMER',
                'context': text[max(0, match.start()-50):match.end()+50],
                'filename': filename
            })
        
        # Technical systems
        system_pattern = r'\b([A-Z][a-zA-Z]+\s+(?:Service|System|Database|API|Dashboard|App|Engine))\b'
        for match in re.finditer(system_pattern, text):
            entities.append({
                'name': match.group(1),
                'type': 'SYSTEM',
                'context': text[max(0, match.start()-50):match.end()+50],
                'filename': filename
            })
        
        return entities
    
    def _extract_custom_entities(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Extract domain-specific entities"""
        entities = []
        
        # Enhanced patterns for better entity extraction
        tech_patterns = {
            'TECHNOLOGY': r'\b(Redis|JWT|API|microservice|database|authentication|session|Docker|Kubernetes|Node\.js|JavaScript|Python|GraphRAG|RAG|LLM|AI)\b',
            'METRIC': r'\b(\d+(?:\.\d+)?(?:%|ms|seconds?|minutes?|hours?|req/min|users?|MB|GB|KB))\b',
            'SYSTEM_COMPONENT': r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\s+(?:service|component|module|system|engine|gateway|dashboard|app|application))\b',
            'CUSTOMER': r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Inc|Corp|Solutions|Systems|Technologies|Ltd|LLC))\b',
            'PERSON': r'\b([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)\s+\((?:Product|Engineering|Customer|Data|VP|CEO|CTO)\b',
            'FEATURE': r'\b(real-time notifications?|analytics dashboard|mobile app|API rate limiting|session management)\b',
            'ISSUE': r'\b(performance issues?|loading times?|timeout errors?|crashes?|bottlenecks?)\b'
        }
        
        for entity_type, pattern in tech_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entity_name = match.group(1) if entity_type != 'PERSON' else match.group(0).split('(')[0].strip()
                entities.append({
                    'name': entity_name,
                    'type': entity_type,
                    'context': text[max(0, match.start()-50):match.end()+50],
                    'filename': filename
                })
        
        return entities
    
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
        
        # Discover ontology first if requested
        if discover_ontology_first and not self.discovered_ontology:
            self.discover_ontology(data_dir)
        
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
                
                # Extract entities from chunk
                entities = self.extract_entities(chunk, file_path.name)
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
            
            # Extract relationships from full document
            doc_entities = self.extract_entities(content, file_path.name)
            doc_relationships = self.extract_relationships(doc_entities, content)
            all_relationships.extend(doc_relationships)
        
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
    
    def graph_enhanced_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Perform graph-enhanced retrieval"""
        # Extract entities from query
        query_entities = self.extract_entities(query, "query")
        
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
        """Get data for graph visualization"""
        try:
            # First try to get entities with relationships
            result = self.conn.execute(
                """
                MATCH (s:Entity)-[r:RELATES_TO]->(t:Entity)
                RETURN s.name, s.type, t.name, t.type, r.relationship_type, r.confidence
                LIMIT 50
                """
            )
            
            nodes = set()
            edges = []
            
            has_relationships = False
            while result.has_next():
                has_relationships = True
                record = result.get_next()
                source, source_type, target, target_type, rel_type, confidence = record
                
                nodes.add((source, source_type))
                nodes.add((target, target_type))
                
                edges.append({
                    'source': source,
                    'target': target,
                    'relationship': rel_type,
                    'confidence': confidence
                })
            
            # If no relationships found, get all entities and create basic connections
            if not has_relationships:
                entity_result = self.conn.execute(
                    "MATCH (e:Entity) RETURN e.name, e.type LIMIT 20"
                )
                
                entity_list = []
                while entity_result.has_next():
                    record = entity_result.get_next()
                    entity_list.append((record[0], record[1]))
                    nodes.add((record[0], record[1]))
                
                # Create basic connections between entities of different types
                for i, (name1, type1) in enumerate(entity_list):
                    for name2, type2 in entity_list[i+1:]:
                        if type1 != type2:  # Only connect different types
                            edges.append({
                                'source': name1,
                                'target': name2,
                                'relationship': 'MENTIONS',
                                'confidence': 0.5
                            })
                            if len(edges) >= 20:  # Limit edges for visualization
                                break
                    if len(edges) >= 20:
                        break
            
            node_list = [{'id': name, 'type': node_type} for name, node_type in nodes]
            
            return {
                'nodes': node_list,
                'edges': edges
            }
            
        except Exception as e:
            print(f"Graph visualization error: {e}")
            return {'nodes': [], 'edges': [], 'error': str(e)}

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
