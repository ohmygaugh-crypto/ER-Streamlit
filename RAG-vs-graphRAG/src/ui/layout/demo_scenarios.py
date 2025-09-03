"""
Demo Scenarios
Handles demo questions and scenario selection
"""
import streamlit as st
from ...core.scenario_generator import ScenarioGenerator


def get_demo_scenarios_for_domain(domain_hint=None):
    """Get static demo scenarios based on domain hint"""
    scenario_generator = ScenarioGenerator()
    scenarios = scenario_generator.get_static_scenarios_for_domain(domain_hint)
    
    # Convert to dict format for backwards compatibility
    return {scenario["name"]: scenario["question"] for scenario in scenarios}


def render_demo_scenarios():
    """Render the demo scenarios and question input section"""
    
    # Only show if data has been processed
    if not st.session_state.get('data_processed', False):
        st.info("📄 Upload data and click 'Process Data' to generate relevant question scenarios")
        return "", False
    
    st.markdown("### 💭 Ask a Question")
    
    # Check if we have custom AI-generated scenarios
    if hasattr(st.session_state, 'using_custom_data') and st.session_state.using_custom_data:
        # Use AI-generated scenarios for custom uploaded data
        if hasattr(st.session_state, 'custom_scenarios') and st.session_state.custom_scenarios:
            scenarios = st.session_state.custom_scenarios
            
            # Show content summary
            if hasattr(st.session_state, 'content_summary'):
                st.info(f"🤖 AI-generated scenarios for: {st.session_state.content_summary}")
            
            # Convert to dict format
            demo_scenarios = {scenario["name"]: scenario["question"] for scenario in scenarios}
        else:
            # Fallback to generic scenarios
            demo_scenarios = {
                "Information Dependencies": "What information elements are interconnected in these documents?",
                "Cross-Document Relationships": "How do concepts relate across different documents?",
                "Custom Question": "Ask your own question about the uploaded content"
            }
    else:
        # Use static domain-based scenarios for sample data
        # Get domain hint from the widget (if provided) or session state
        domain_hint = st.session_state.get('domain_hint', '') or getattr(st.session_state, 'current_domain_hint', 'business')
        
        demo_scenarios_list = get_demo_scenarios_for_domain(domain_hint)
        
        # Debug: Check what we're getting
        # st.write(f"Debug: domain_hint='{domain_hint}', type={type(demo_scenarios_list)}, content={demo_scenarios_list[:2] if isinstance(demo_scenarios_list, list) else demo_scenarios_list}")
        
        # Defensive coding: ensure we have the right format
        if isinstance(demo_scenarios_list, list) and demo_scenarios_list:
            # Check if first item is a dict with expected keys
            if isinstance(demo_scenarios_list[0], dict) and "name" in demo_scenarios_list[0] and "question" in demo_scenarios_list[0]:
                demo_scenarios = {scenario["name"]: scenario["question"] for scenario in demo_scenarios_list}
            else:
                # Fallback if format is wrong
                demo_scenarios = {"Cross-system Dependencies": "What technical issues are blocking our enterprise customers and how are they related?"}
        else:
            # Fallback if list is empty or wrong type
            demo_scenarios = {"Cross-system Dependencies": "What technical issues are blocking our enterprise customers and how are they related?"}
        
        # Debug: Show what domain hint is being used
        # st.write(f"🔍 Debug: Using domain hint: '{domain_hint}', Available scenarios: {len(demo_scenarios_list)}")  # Uncomment for debugging
        
        # Always add "Custom Question" option for sample data too
        demo_scenarios["Custom Question"] = "Ask your own question about the content"
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_scenario = st.selectbox("🎯 Demo Scenarios", list(demo_scenarios.keys()), key="demo_scenario")
        
        # Handle custom question scenario
        if selected_scenario == "Custom Question":
            custom_question = st.text_area("📝 Your Question:", 
                                          value="",
                                          placeholder="Enter your own question about the content...",
                                          height=100,
                                          key="main_question")
        else:
            custom_question = st.text_area("📝 Your Question:", 
                                          value=demo_scenarios[selected_scenario],
                                          height=100,
                                          key="main_question")
    
    with col2:
        st.markdown("**Options:**")
        show_graph_viz = st.checkbox("Show Knowledge Graph", value=True)
    
    return custom_question, show_graph_viz
