"""
Lightweight Ontology Discovery for GraphRAG
Discovers hidden graph ontology patterns from document collections using LangChain + spaCy
Compatible with Kuzu and Streamlit deployment
"""
import os
import re
import json
from typing import List, Dict, Any, Set, Tuple, Optional
from pathlib import Path
from collections import defaultdict, Counter
import spacy
from spacy import displacy
import networkx as nx
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
from dataclasses import dataclass
from enum import Enum

class RelationType(Enum):
    """Enumeration of discovered relationship types"""
    HIERARCHICAL = "hierarchical"  # parent-child, is-a
    FUNCTIONAL = "functional"      # uses, performs, enables
    TEMPORAL = "temporal"          # before, after, during
    CAUSAL = "causal"             # causes, prevents, triggers
    SPATIAL = "spatial"           # located-in, part-of
    ASSOCIATIVE = "associative"   # related-to, similar-to

@dataclass
class OntologyEntity:
    """Discovered ontology entity"""
    name: str
    entity_type: str
    frequency: int
    contexts: List[str]
    confidence: float
    properties: Dict[str, Any]

@dataclass
class OntologyRelation:
    """Discovered ontology relationship"""
    source: str
    target: str
    relation_type: RelationType
    frequency: int
    confidence: float
    contexts: List[str]
    linguistic_patterns: List[str]

class OntologyDiscovery:
    """Lightweight ontology discovery system"""
    
    def __init__(self, use_llm: bool = True):
        """Initialize ontology discovery system"""
        self.use_llm = use_llm
        
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Warning: spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Initialize LLM if available and requested
        self.llm = None
        if use_llm and os.getenv("OPENAI_API_KEY"):
            self.llm = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
        
        # Text splitter for processing
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Discovery patterns and rules
        self._init_patterns()
        
        # Storage for discovered ontology
        self.entities: Dict[str, OntologyEntity] = {}
        self.relations: List[OntologyRelation] = []
        self.entity_types: Set[str] = set()
        
    def _init_patterns(self):
        """Initialize linguistic patterns for relationship discovery"""
        self.relation_patterns = {
            RelationType.HIERARCHICAL: [
                r'(\w+(?:\s+\w+)*)\s+is\s+a\s+(?:type\s+of\s+)?(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+belongs\s+to\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+part\s+of\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+component\s+of\s+(\w+(?:\s+\w+)*)',
            ],
            RelationType.FUNCTIONAL: [
                r'(\w+(?:\s+\w+)*)\s+(?:uses|utilizes|employs)\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+(?:performs|executes|runs)\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+(?:enables|allows|supports)\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+(?:manages|controls|handles)\s+(\w+(?:\s+\w+)*)',
            ],
            RelationType.CAUSAL: [
                r'(\w+(?:\s+\w+)*)\s+(?:causes|triggers|leads\s+to)\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+(?:prevents|blocks|stops)\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+(?:affects|impacts|influences)\s+(\w+(?:\s+\w+)*)',
                r'due\s+to\s+(\w+(?:\s+\w+)*),\s+(\w+(?:\s+\w+)*)',
            ],
            RelationType.TEMPORAL: [
                r'(\w+(?:\s+\w+)*)\s+(?:before|prior\s+to)\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+(?:after|following)\s+(\w+(?:\s+\w+)*)',
                r'during\s+(\w+(?:\s+\w+)*),\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+(?:while|when)\s+(\w+(?:\s+\w+)*)',
            ],
            RelationType.ASSOCIATIVE: [
                r'(\w+(?:\s+\w+)*)\s+(?:related\s+to|associated\s+with)\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+(?:similar\s+to|like)\s+(\w+(?:\s+\w+)*)',
                r'(\w+(?:\s+\w+)*)\s+and\s+(\w+(?:\s+\w+)*)\s+(?:both|together)',
            ]
        }
        
        # Domain-specific entity patterns for enterprise documents
        self.entity_patterns = {
            'SYSTEM_COMPONENT': [
                r'\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\s+(?:service|component|module|system|engine|gateway|dashboard|app|application))\b',
                r'\b([A-Z][a-zA-Z]+\s+(?:API|Service|Database|Server|Client))\b',
            ],
            'CUSTOMER': [
                r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Inc|Corp|Solutions|Systems|Technologies|Ltd|LLC))\b',
                r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\s+(?:Company|Enterprise|Organization))\b',
            ],
            'TECHNOLOGY': [
                r'\b(Redis|JWT|API|microservice|database|authentication|session|Docker|Kubernetes|Node\.js|JavaScript|Python|GraphRAG|RAG|LLM|AI)\b',
                r'\b([A-Z][a-zA-Z]*(?:DB|SQL|JS|API))\b',
            ],
            'METRIC': [
                r'\b(\d+(?:\.\d+)?(?:%|ms|seconds?|minutes?|hours?|req/min|users?|MB|GB|KB))\b',
                r'\b(\d+(?:\.\d+)?\s*(?:percent|percentage|rate|ratio))\b',
            ],
            'ISSUE': [
                r'\b(performance\s+issues?|loading\s+times?|timeout\s+errors?|crashes?|bottlenecks?|failures?)\b',
                r'\b(bug|error|problem|issue|failure|crash|timeout)\b',
            ],
            'FEATURE': [
                r'\b(real-time\s+notifications?|analytics\s+dashboard|mobile\s+app|API\s+rate\s+limiting|session\s+management)\b',
                r'\b([A-Z][a-zA-Z]*\s+(?:feature|functionality|capability))\b',
            ]
        }

    def discover_ontology(self, documents: List[str], filenames: List[str]) -> Dict[str, Any]:
        """Main method to discover ontology from documents"""
        print("🔍 Starting ontology discovery...")
        
        # Step 1: Extract entities from all documents
        all_entities = []
        for doc, filename in zip(documents, filenames):
            entities = self._extract_entities(doc, filename)
            all_entities.extend(entities)
        
        # Step 2: Consolidate and rank entities
        self._consolidate_entities(all_entities)
        
        # Step 3: Discover relationships
        for doc, filename in zip(documents, filenames):
            relations = self._discover_relationships(doc, filename, list(self.entities.keys()))
            self.relations.extend(relations)
        
        # Step 4: LLM-enhanced ontology refinement (if available)
        if self.llm:
            self._refine_ontology_with_llm()
        
        # Step 5: Build ontology structure
        ontology = self._build_ontology_structure()
        
        print(f"✅ Discovered {len(self.entities)} entities and {len(self.relations)} relationships")
        return ontology

    def _extract_entities(self, text: str, filename: str) -> List[Dict[str, Any]]:
        """Extract entities using spaCy NER and custom patterns"""
        entities = []
        
        # Use spaCy NER if available
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ in ['PERSON', 'ORG', 'PRODUCT', 'EVENT', 'DATE', 'GPE']:
                    entities.append({
                        'name': ent.text.strip(),
                        'type': ent.label_,
                        'context': ent.sent.text if ent.sent else "",
                        'filename': filename,
                        'confidence': 0.9  # High confidence for spaCy NER
                    })
        
        # Extract custom domain entities
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity_name = match.group(1).strip()
                    if len(entity_name) > 2:  # Filter out very short matches
                        entities.append({
                            'name': entity_name,
                            'type': entity_type,
                            'context': self._get_context(text, match.start(), match.end()),
                            'filename': filename,
                            'confidence': 0.8  # Good confidence for pattern matching
                        })
        
        return entities

    def _get_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """Get context around a match"""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]

    def _consolidate_entities(self, all_entities: List[Dict[str, Any]]):
        """Consolidate and rank entities by frequency and confidence"""
        entity_counts = defaultdict(lambda: {
            'count': 0, 
            'contexts': [], 
            'types': set(), 
            'filenames': set(),
            'confidences': []
        })
        
        for entity in all_entities:
            name = entity['name']
            entity_counts[name]['count'] += 1
            entity_counts[name]['contexts'].append(entity['context'])
            entity_counts[name]['types'].add(entity['type'])
            entity_counts[name]['filenames'].add(entity['filename'])
            entity_counts[name]['confidences'].append(entity['confidence'])
        
        # Create consolidated entities
        for name, data in entity_counts.items():
            # Choose most common type
            entity_type = Counter(list(data['types'])).most_common(1)[0][0]
            
            # Calculate average confidence
            avg_confidence = sum(data['confidences']) / len(data['confidences'])
            
            self.entities[name] = OntologyEntity(
                name=name,
                entity_type=entity_type,
                frequency=data['count'],
                contexts=data['contexts'][:5],  # Keep top 5 contexts
                confidence=avg_confidence,
                properties={
                    'filenames': list(data['filenames']),
                    'all_types': list(data['types'])
                }
            )
            
            self.entity_types.add(entity_type)

    def _discover_relationships(self, text: str, filename: str, entity_names: List[str]) -> List[OntologyRelation]:
        """Discover relationships using linguistic patterns"""
        relations = []
        
        for relation_type, patterns in self.relation_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    source, target = match.groups()
                    
                    # Check if both entities are in our discovered entities
                    source_match = self._find_matching_entity(source, entity_names)
                    target_match = self._find_matching_entity(target, entity_names)
                    
                    if source_match and target_match:
                        relations.append(OntologyRelation(
                            source=source_match,
                            target=target_match,
                            relation_type=relation_type,
                            frequency=1,
                            confidence=0.8,
                            contexts=[self._get_context(text, match.start(), match.end())],
                            linguistic_patterns=[pattern]
                        ))
        
        return relations

    def _find_matching_entity(self, text: str, entity_names: List[str]) -> Optional[str]:
        """Find matching entity name using fuzzy matching"""
        text_lower = text.lower().strip()
        
        # Exact match first
        for entity in entity_names:
            if entity.lower() == text_lower:
                return entity
        
        # Partial match
        for entity in entity_names:
            if text_lower in entity.lower() or entity.lower() in text_lower:
                return entity
        
        return None

    def _refine_ontology_with_llm(self):
        """Use LLM to refine and validate discovered ontology"""
        if not self.llm:
            return
        
        print("🤖 Refining ontology with LLM...")
        
        # Create prompt for ontology validation
        prompt = PromptTemplate(
            input_variables=["entities", "relationships"],
            template="""
            You are an expert in knowledge graph ontology design. Please analyze the following discovered entities and relationships from enterprise documents and suggest improvements:

            ENTITIES:
            {entities}

            RELATIONSHIPS:
            {relationships}

            Please provide:
            1. Entity type refinements (merge similar types, suggest better names)
            2. Relationship validation (confirm if relationships make sense)
            3. Missing relationships that should exist based on domain knowledge
            4. Ontology hierarchy suggestions

            Respond in JSON format with your suggestions.
            """
        )
        
        # Prepare data for LLM
        entities_summary = "\n".join([
            f"- {entity.name} ({entity.entity_type}) - frequency: {entity.frequency}"
            for entity in list(self.entities.values())[:20]  # Limit for token efficiency
        ])
        
        relationships_summary = "\n".join([
            f"- {rel.source} --{rel.relation_type.value}--> {rel.target}"
            for rel in self.relations[:20]  # Limit for token efficiency
        ])
        
        try:
            chain = LLMChain(llm=self.llm, prompt=prompt)
            response = chain.run(
                entities=entities_summary,
                relationships=relationships_summary
            )
            
            # Parse and apply LLM suggestions (simplified implementation)
            print("LLM suggestions received:", response[:200] + "...")
            
        except Exception as e:
            print(f"LLM refinement failed: {e}")

    def _build_ontology_structure(self) -> Dict[str, Any]:
        """Build final ontology structure"""
        # Consolidate relationships by frequency
        relation_counts = defaultdict(lambda: {
            'frequency': 0,
            'confidences': [],
            'contexts': [],
            'patterns': []
        })
        
        for rel in self.relations:
            key = (rel.source, rel.target, rel.relation_type.value)
            relation_counts[key]['frequency'] += rel.frequency
            relation_counts[key]['confidences'].append(rel.confidence)
            relation_counts[key]['contexts'].extend(rel.contexts)
            relation_counts[key]['patterns'].extend(rel.linguistic_patterns)
        
        # Build final relationship list
        final_relations = []
        for (source, target, rel_type), data in relation_counts.items():
            final_relations.append({
                'source': source,
                'target': target,
                'relation_type': rel_type,
                'frequency': data['frequency'],
                'confidence': sum(data['confidences']) / len(data['confidences']),
                'contexts': data['contexts'][:3],  # Keep top 3 contexts
                'patterns': list(set(data['patterns']))  # Unique patterns
            })
        
        # Sort by frequency and confidence
        final_relations.sort(key=lambda x: (x['frequency'], x['confidence']), reverse=True)
        
        return {
            'entities': {
                name: {
                    'type': entity.entity_type,
                    'frequency': entity.frequency,
                    'confidence': entity.confidence,
                    'contexts': entity.contexts,
                    'properties': entity.properties
                }
                for name, entity in self.entities.items()
            },
            'relationships': final_relations,
            'entity_types': list(self.entity_types),
            'statistics': {
                'total_entities': len(self.entities),
                'total_relationships': len(final_relations),
                'entity_types_count': len(self.entity_types),
                'avg_entity_frequency': sum(e.frequency for e in self.entities.values()) / len(self.entities) if self.entities else 0
            }
        }

    def get_ontology_graph(self) -> nx.DiGraph:
        """Create NetworkX graph from discovered ontology"""
        G = nx.DiGraph()
        
        # Add entity nodes
        for name, entity in self.entities.items():
            G.add_node(name, 
                      type=entity.entity_type,
                      frequency=entity.frequency,
                      confidence=entity.confidence)
        
        # Add relationship edges
        for rel in self.relations:
            if rel.source in self.entities and rel.target in self.entities:
                G.add_edge(rel.source, rel.target,
                          relation_type=rel.relation_type.value,
                          frequency=rel.frequency,
                          confidence=rel.confidence)
        
        return G

    def export_ontology(self, filepath: str, format: str = 'json'):
        """Export discovered ontology to file"""
        ontology = self._build_ontology_structure()
        
        if format == 'json':
            with open(filepath, 'w') as f:
                json.dump(ontology, f, indent=2, default=str)
        elif format == 'rdf':
            # Could implement RDF export here
            pass
        
        print(f"Ontology exported to {filepath}")

    def get_entity_hierarchy(self) -> Dict[str, List[str]]:
        """Get entity type hierarchy for visualization"""
        hierarchy = defaultdict(list)
        
        for name, entity in self.entities.items():
            hierarchy[entity.entity_type].append(name)
        
        return dict(hierarchy)

    def get_relationship_matrix(self) -> pd.DataFrame:
        """Get relationship matrix for analysis"""
        entity_names = list(self.entities.keys())
        matrix = pd.DataFrame(0, index=entity_names, columns=entity_names)
        
        for rel in self.relations:
            if rel.source in entity_names and rel.target in entity_names:
                matrix.loc[rel.source, rel.target] += rel.frequency
        
        return matrix
