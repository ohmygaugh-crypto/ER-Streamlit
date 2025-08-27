"""
Demo Scenarios
Handles demo questions and scenario selection
"""
import streamlit as st


def get_demo_scenarios():
    """Get predefined demo scenarios"""
    return {
        "Cross-system Dependencies": "What technical issues are blocking our enterprise customers and how are they related?",
        "Customer Impact Analysis": "Which customers are affected by authentication service problems and what are the consequences?", 
        "Root Cause Investigation": "What is the root cause of dashboard performance issues and what systems are involved?",
        "Resource Planning": "What engineering resources and timeline are needed to resolve the current technical debt?",
        "Business Risk Assessment": "How do current technical problems impact customer satisfaction and business outcomes?"
    }


def render_demo_scenarios():
    """Render the demo scenarios and question input section"""
    st.markdown("### 💭 Ask a Question")
    
    demo_scenarios = get_demo_scenarios()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected_scenario = st.selectbox("🎯 Demo Scenarios", list(demo_scenarios.keys()), key="demo_scenario")
        custom_question = st.text_area("📝 Your Question:", 
                                      value=demo_scenarios[selected_scenario],
                                      height=100,
                                      key="main_question")
    
    with col2:
        st.markdown("**Options:**")
        show_graph_viz = st.checkbox("Show Knowledge Graph", value=True)
    
    return custom_question, show_graph_viz
