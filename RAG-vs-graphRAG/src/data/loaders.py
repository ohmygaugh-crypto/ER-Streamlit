"""
Data Loaders
Handles loading and processing of sample data
"""
import streamlit as st
import glob
import os
from pathlib import Path
from typing import List, Dict
from ..system.initialization import check_graph_database_content
from ..core.scenario_generator import ScenarioGenerator


def load_sample_data(trad_rag, graph_rag):
    """Load and process sample enterprise data"""
    import os
    data_dir = Path(__file__).parent.parent.parent / "sample_data"
    
    # Check if GraphRAG database already has data
    chunk_count, entity_count = check_graph_database_content(graph_rag)
    
    if chunk_count > 0 or entity_count > 0:
        st.info(f"📊 Database already contains data: {chunk_count} chunks, {entity_count} entities")
        st.success("✅ Using existing processed data!")
        
        # Still load Traditional RAG since it's not persistent
        with st.spinner("🔄 Loading data for Traditional RAG..."):
            documents = trad_rag.load_documents(str(data_dir))
            chunks = trad_rag.chunk_documents(documents)
            trad_rag.create_embeddings(chunks)
        
        return True
    else:
        # Database is empty, need to process data
        # FIRST: Generate AI scenarios from full document content (BEFORE chunking)
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            with st.spinner("🤖 Analyzing full documents and generating AI scenarios..."):
                try:
                    scenario_generator = ScenarioGenerator()
                    
                    # Read FULL documents for comprehensive scenario generation
                    full_documents = []
                    filenames = []
                    for file_path in glob.glob(str(data_dir / "*.txt")):
                        filename = Path(file_path).name
                        filenames.append(filename)
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            full_documents.append(content)
                    
                    # Generate scenarios from complete document context
                    scenarios, content_summary = scenario_generator.analyze_full_documents_and_generate_scenarios(
                        documents=full_documents,
                        filenames=filenames,
                        max_content_length=8000  # Analyze more content for better scenarios
                    )
                    
                    if scenarios:
                        # Store AI-generated scenarios BEFORE processing
                        st.session_state.custom_scenarios = scenarios
                        st.session_state.content_summary = f"Sample enterprise data: {content_summary}"
                        st.session_state.using_custom_data = True  # Trigger AI scenario display
                        
                        # Show the generated scenarios to user
                        st.success(f"🤖 Generated {len(scenarios)} AI scenarios from full document analysis:")
                        for i, scenario in enumerate(scenarios, 1):
                            st.info(f"   **{i}. {scenario.get('name', 'Unknown')}**: {scenario.get('question', 'No question')}")
                    else:
                        st.info("💡 Using static scenarios (AI generation had issues)")
                        
                except Exception as e:
                    st.warning(f"⚠️ AI scenario generation failed: {str(e)}, using static scenarios")
        else:
            st.info("💡 No API key - using static domain-based scenarios")
        
        # THEN: Process documents for RAG systems (AFTER scenario generation)
        with st.spinner("🔄 Loading sample enterprise documents..."):
            # Load into Traditional RAG
            documents = trad_rag.load_documents(str(data_dir))
            chunks = trad_rag.chunk_documents(documents)
            trad_rag.create_embeddings(chunks)
            
            # Load into GraphRAG
            graph_rag.load_documents(str(data_dir))
            
        st.success("✅ Sample data loaded successfully!")
        
        return True


def process_uploaded_files(uploaded_files, trad_rag, graph_rag) -> Dict:
    """
    Process uploaded files and generate AI-powered demo scenarios
    
    Returns:
        Dict with 'success', 'scenarios', 'content_summary' keys
    """
    if not uploaded_files:
        return {"success": False, "error": "No files uploaded"}
    
    try:
        # FIRST: Generate AI scenarios from full document content (before chunking)
        with st.spinner("🤖 Analyzing full document content and generating relevant demo scenarios..."):
            scenario_generator = ScenarioGenerator()
            
            # Read all uploaded documents for comprehensive analysis
            full_documents = []
            filenames = []
            documents = []
            
            for uploaded_file in uploaded_files:
                content = uploaded_file.read().decode('utf-8')
                filename = uploaded_file.name
                
                filenames.append(filename)
                full_documents.append(content)
                documents.append({
                    'content': content,
                    'filename': filename
                })
            
            # Generate scenarios from complete document context FIRST
            scenarios, content_summary = scenario_generator.analyze_full_documents_and_generate_scenarios(
                documents=full_documents,
                filenames=filenames,
                max_content_length=8000  # Analyze more content for better scenarios
            )
            
            # Add "Custom" option
            scenarios.append({
                "name": "Custom Question",
                "question": "Ask your own question about the uploaded content"
            })
            
            # Show the generated scenarios to user
            st.success(f"🤖 Generated {len(scenarios)-1} AI scenarios from uploaded documents:")
            for i, scenario in enumerate(scenarios[:-1], 1):  # Exclude "Custom" option from display
                st.info(f"   **{i}. {scenario.get('name', 'Unknown')}**: {scenario.get('question', 'No question')}")
        
        # THEN: Process documents for RAG systems
        with st.spinner("📄 Processing uploaded files for RAG systems..."):
            # Process Traditional RAG
            chunks = trad_rag.chunk_documents_from_content(documents)
            trad_rag.create_embeddings(chunks)
            
            # Process GraphRAG
            graph_rag.load_documents_from_content(documents)
        

        
        st.success("✅ Files processed and scenarios generated!")
        
        return {
            "success": True,
            "scenarios": scenarios,
            "content_summary": content_summary,
            "file_count": len(uploaded_files)
        }
        
    except Exception as e:
        st.error(f"❌ Error processing files: {str(e)}")
        return {"success": False, "error": str(e)}
