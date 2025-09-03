"""
AI-powered scenario generation for custom uploaded documents
"""

import os
from typing import List, Dict, Tuple, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage


class ScenarioGenerator:
    """Generate relevant demo scenarios based on uploaded document content"""
    
    def __init__(self):
        """Initialize the scenario generator"""
        self.llm = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.llm = ChatOpenAI(temperature=0.7, model="gpt-4o-mini")  # Using mini for cost efficiency
    
    def analyze_documents_and_generate_scenarios(
        self, 
        document_chunks: List[str], 
        filenames: List[str],
        max_chunks_to_analyze: int = 20
    ) -> Tuple[List[Dict[str, str]], str]:
        """
        Analyze document content and generate relevant demo scenarios
        
        Args:
            document_chunks: List of text chunks from uploaded documents
            filenames: List of source filenames
            max_chunks_to_analyze: Limit chunks analyzed to control cost
            
        Returns:
            Tuple of (scenarios_list, content_summary)
            scenarios_list: List of {"name": str, "question": str} dicts
            content_summary: Brief description of the document content
        """
        if not self.llm:
            print("❌ No API key available for scenario generation")
            return self._get_generic_scenarios(), "Custom uploaded documents"
        
        try:
            # Sample chunks to analyze (limit for cost control)
            sample_chunks = document_chunks[:max_chunks_to_analyze]
            
            # Create content summary for analysis
            content_preview = "\n\n".join([
                f"File: {filename}\nContent sample: {chunk[:500]}..."
                for filename, chunk in zip(filenames * len(sample_chunks), sample_chunks)
            ])[:3000]  # Limit total content length
            
            # Generate scenarios using LLM
            scenarios, summary = self._generate_scenarios_with_llm(content_preview, filenames)
            
            if scenarios:
                print(f"✅ Generated {len(scenarios)} AI scenarios for uploaded content")
                return scenarios, summary
            else:
                print("⚠️ AI scenario generation failed, using generic scenarios")
                return self._get_generic_scenarios(), "Custom uploaded documents"
                
        except Exception as e:
            print(f"❌ Error generating scenarios: {e}")
            return self._get_generic_scenarios(), "Custom uploaded documents"
    
    def _generate_scenarios_with_llm(self, content_preview: str, filenames: List[str]) -> Tuple[List[Dict[str, str]], str]:
        """Use LLM to generate scenarios based on content"""
        
        system_prompt = """You are an expert at analyzing documents and creating relevant demo scenarios for knowledge graph analysis.

Your task is to:
1. Analyze the provided document content
2. Generate 4 relevant demo scenarios that would showcase knowledge graph connections in this specific content
3. Create a corresponding analytical question for each scenario
4. Provide a brief content summary

Focus on scenarios that would demonstrate:
- Entity relationships and dependencies
- Cross-document connections
- Complex information patterns
- Knowledge discovery opportunities

Return ONLY a JSON response in this exact format:
{
  "content_summary": "Brief description of what these documents contain",
  "scenarios": [
    {"name": "Scenario Name 1", "question": "Analytical question about the content?"},
    {"name": "Scenario Name 2", "question": "Another analytical question?"},
    {"name": "Scenario Name 3", "question": "Third analytical question?"},
    {"name": "Scenario Name 4", "question": "Fourth analytical question?"}
  ]
}"""

        user_prompt = f"""Analyze these document excerpts and generate relevant demo scenarios:

FILENAMES: {', '.join(filenames)}

CONTENT PREVIEW:
{content_preview}

Generate 4 demo scenarios that would be most relevant for exploring knowledge graph connections in this specific content."""

        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            result_text = response.content.strip()
            
            # Parse JSON response
            import json
            result = json.loads(result_text)
            
            scenarios = result.get("scenarios", [])
            summary = result.get("content_summary", "Custom uploaded documents")
            
            return scenarios, summary
            
        except Exception as e:
            print(f"❌ LLM scenario generation error: {e}")
            return [], "Custom uploaded documents"
    
    def _get_generic_scenarios(self) -> List[Dict[str, str]]:
        """Fallback generic scenarios when AI generation fails"""
        return [
            {
                "name": "Information Dependencies",
                "question": "What information elements are interconnected in these documents?"
            },
            {
                "name": "Cross-Document Relationships", 
                "question": "How do concepts relate across different documents?"
            },
            {
                "name": "Key Entity Analysis",
                "question": "What are the most important entities and their relationships?"
            },
            {
                "name": "Knowledge Discovery",
                "question": "What hidden patterns can be discovered in this content?"
            }
        ]
    
    def get_static_scenarios_for_domain(self, domain_hint: Optional[str] = None) -> List[Dict[str, str]]:
        """Get static scenarios based on domain hint (for sample data)"""
        if not domain_hint:
            domain_hint = "business"  # Default
        
        domain_scenarios = {
            'medical': [
                {"name": "Drug Interaction Analysis", "question": "What drug interactions and contraindications exist?"},
                {"name": "Patient Treatment Pathways", "question": "How do different treatments connect for patient care?"}, 
                {"name": "Clinical Research Dependencies", "question": "What relationships exist between research findings?"},
                {"name": "Symptom-Disease Relationships", "question": "How do symptoms relate to potential diagnoses?"}
            ],
            'legal': [
                {"name": "Case Precedent Analysis", "question": "How do legal precedents influence current cases?"},
                {"name": "Regulatory Compliance Chains", "question": "What regulatory requirements are interconnected?"},
                {"name": "Contract Dependencies", "question": "How do different contract terms relate to each other?"},
                {"name": "Legal Entity Relationships", "question": "What relationships exist between legal entities?"}
            ],
            'business': [
                {"name": "Cross-system Dependencies", "question": "What technical issues are blocking our enterprise customers and how are they related?"},
                {"name": "Customer Support Issues", "question": "How do customer problems relate to product features?"},
                {"name": "Product Roadmap Planning", "question": "What feature dependencies exist in our development pipeline?"},
                {"name": "Vendor Relationship Mapping", "question": "How do vendor relationships impact our operations?"}
            ],
            'academic': [
                {"name": "Research Citation Networks", "question": "How do academic papers build upon each other?"},
                {"name": "Methodology Dependencies", "question": "What research methods are interconnected?"},
                {"name": "Author Collaboration Patterns", "question": "How do researchers collaborate across institutions?"},
                {"name": "Field Evolution Analysis", "question": "How have research fields evolved over time?"}
            ]
        }
        
        # Find best matching domain
        for domain_key in domain_scenarios:
            if domain_key in domain_hint.lower():
                return domain_scenarios[domain_key]
        
        # Default to business scenarios
        return domain_scenarios['business']

    def analyze_full_documents_and_generate_scenarios(self, documents: List[str], filenames: List[str], max_content_length: int = 8000) -> Tuple[List[Dict[str, str]], str]:
        """
        Analyzes FULL document content (before chunking) and generates AI-powered demo scenarios.
        This provides better context for scenario generation than using pre-chunked content.
        
        Args:
            documents: List of full document text content
            filenames: List of source filenames
            max_content_length: Maximum content length to analyze (token limit)
            
        Returns:
            Tuple of (scenarios_list, content_summary)
        """
        if not self.llm:
            print("❌ No API key available for scenario generation")
            return self._get_generic_scenarios(), "Custom uploaded documents"

        try:
            # Combine full documents for comprehensive analysis
            content_for_analysis = "\n\n=== DOCUMENT SEPARATOR ===\n\n".join(documents)
            
            # Limit content length to prevent exceeding token limits but allow more content
            if len(content_for_analysis) > max_content_length:
                content_for_analysis = content_for_analysis[:max_content_length] + "..."

            # Use the same method as the existing working implementation
            scenarios, summary = self._generate_scenarios_with_llm(content_for_analysis, filenames)
            
            if scenarios:
                print(f"✅ Generated {len(scenarios)} AI scenarios from full document analysis:")
                for i, scenario in enumerate(scenarios, 1):
                    print(f"   {i}. {scenario.get('name', 'Unknown')}: {scenario.get('question', 'No question')}")
                return scenarios, summary
            else:
                print(f"⚠️ AI scenario generation failed, using generic scenarios")
                return self._get_generic_scenarios(), "AI scenario generation failed."
        except Exception as e:
            print(f"❌ Error generating AI scenarios from full documents: {e}")
            return self._get_generic_scenarios(), f"AI scenario generation failed: {str(e)}"
