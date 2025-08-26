"""
Traditional RAG Implementation
Chunks text, creates embeddings, and performs similarity search
"""
import os
from typing import List, Dict, Any
from pathlib import Path
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle
import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
import openai

class TraditionalRAG:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", chunk_size: int = 500, chunk_overlap: int = 50):
        """Initialize Traditional RAG with embedding model and chunking parameters"""
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(model_name)
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
        # Initialize FAISS index
        self.faiss_index = None
        self.chunks_metadata = []
        
        # Initialize LLM
        self.llm = None
        api_key = os.getenv("OPENAI_API_KEY")
        print(f"🔑 Traditional RAG API Key Status: {'✅ Found' if api_key else '❌ Not Found'}")
        if api_key:
            print(f"🔑 Traditional RAG API Key prefix: {api_key[:10]}...")
            self.llm = ChatOpenAI(temperature=0, model="gpt-4o")
    
    def load_documents(self, data_dir: str) -> List[Dict[str, Any]]:
        """Load all text documents from directory"""
        documents = []
        data_path = Path(data_dir)
        
        for file_path in data_path.glob("*.txt"):
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                documents.append({
                    'filename': file_path.name,
                    'content': content,
                    'filepath': str(file_path)
                })
        
        return documents
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split documents into chunks"""
        chunks = []
        
        for doc in documents:
            text_chunks = self.text_splitter.split_text(doc['content'])
            
            for i, chunk in enumerate(text_chunks):
                chunks.append({
                    'chunk_id': f"{doc['filename']}_chunk_{i}",
                    'content': chunk,
                    'filename': doc['filename'],
                    'filepath': doc['filepath'],
                    'chunk_index': i,
                    'token_count': len(tiktoken.get_encoding("cl100k_base").encode(chunk))
                })
        
        return chunks
    
    def create_embeddings(self, chunks: List[Dict[str, Any]]) -> None:
        """Create embeddings and store in FAISS index"""
        # Generate embeddings
        documents = [chunk['content'] for chunk in chunks]
        embeddings = self.embedding_model.encode(documents)
        
        # Create FAISS index
        dimension = embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add embeddings to index
        self.faiss_index.add(embeddings.astype('float32'))
        
        # Store metadata
        self.chunks_metadata = [{
            'content': chunk['content'],
            'filename': chunk['filename'],
            'chunk_id': chunk['chunk_id'],
            'chunk_index': chunk['chunk_index'],
            'token_count': chunk['token_count']
        } for chunk in chunks]
        
        print(f"Created embeddings for {len(chunks)} chunks")
    
    def similarity_search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Perform similarity search and return relevant chunks"""
        if self.faiss_index is None or not self.chunks_metadata:
            return []
        
        # Encode query
        query_embedding = self.embedding_model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        k = min(k, len(self.chunks_metadata))
        scores, indices = self.faiss_index.search(query_embedding.astype('float32'), k)
        
        retrieved_chunks = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.chunks_metadata):
                chunk_data = self.chunks_metadata[idx].copy()
                chunk_data['similarity_score'] = float(scores[0][i])
                retrieved_chunks.append({
                    'content': chunk_data['content'],
                    'metadata': {
                        'filename': chunk_data['filename'],
                        'chunk_id': chunk_data['chunk_id'],
                        'chunk_index': chunk_data['chunk_index'],
                        'token_count': chunk_data['token_count']
                    },
                    'similarity_score': chunk_data['similarity_score'],
                    'id': chunk_data['chunk_id']
                })
        
        return retrieved_chunks
    
    def answer_question(self, question: str, k: int = 5) -> Dict[str, Any]:
        """Answer question using traditional RAG approach"""
        # Retrieve relevant chunks
        relevant_chunks = self.similarity_search(question, k)
        
        if not relevant_chunks:
            return {
                'answer': "No relevant information found.",
                'retrieved_chunks': [],
                'method': 'traditional_rag',
                'confidence': 0.0
            }
        
        # Prepare context from chunks
        context = "\n\n".join([chunk['content'] for chunk in relevant_chunks])
        
        # Generate answer using LLM if available
        answer = "LLM not available - please set OPENAI_API_KEY"
        confidence = 0.5
        
        if self.llm:
            print("🤖 Traditional RAG using OpenAI API for answer generation")
            try:
                prompt = f"""Based on the following context, answer the question. If the context doesn't contain enough information, say so clearly.

Context:
{context}

Question: {question}

Answer:"""
                
                response = self.llm.invoke(prompt)
                answer = response.content
                confidence = 0.8  # Basic confidence score
                
            except Exception as e:
                print(f"❌ Traditional RAG API call failed: {e}")
                answer = f"Error generating answer: {str(e)}"
                confidence = 0.0
        else:
            print("⚠️  Traditional RAG: No API key available, returning fallback message")
        
        return {
            'answer': answer,
            'retrieved_chunks': relevant_chunks,
            'method': 'traditional_rag',
            'confidence': confidence,
            'context_used': context[:500] + "..." if len(context) > 500 else context
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the traditional RAG system"""
        if self.faiss_index is None:
            return {'status': 'Not initialized'}
        
        return {
            'total_chunks': len(self.chunks_metadata),
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'embedding_model': self.model_name,
            'index_size': self.faiss_index.ntotal,
            'status': 'Ready'
        }
