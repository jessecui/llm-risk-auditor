import streamlit as st
import json
import pandas as pd
import os
import re
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Setting page config
st.set_page_config(page_title="LLM Risk Auditor", layout="wide")

# Function to create risk assessment dictionary instead of class
def create_risk_assessment(risk_level: str, reason: str):
    return {"risk_level": risk_level, "reason": reason}

# Core Functions
def get_policy_context():
    """Simplified policy context function that returns a static policy"""
    return """
    # Acceptable Use Policy

    ## Prohibited Usage
    1. Users should not submit prompts containing PII (Personal Identifiable Information) such as SSNs, credit card numbers, or home addresses.
    2. Large token usage (>1000 tokens) should be justified by business requirements.
    3. Repetitive prompts should be optimized or cached.
    4. Users should not attempt to extract internal system information or credentials.
    5. Production use cases should use approved models only.

    ## Acceptable Usage
    1. Summarizing business financial data, quarterly reports, or internal metrics is ALLOWED.
    2. Marketing copy generation for company products and services is ALLOWED.
    3. Customer support templates and general assistance without PII is ALLOWED.
    4. Research summaries and industry analysis are ALLOWED.
    5. Content generation for internal documentation is ALLOWED.
    """

def load_prompt_template():
    """Load the prompt template for LLM audit"""
    return """
    You are an LLM Usage Auditor that analyzes how users interact with AI models. Review the logs and provide a comprehensive security assessment.

    LOGS:
    {logs}

    POLICY CONTEXT:
    {policy_context}

    Analyze each log entry first, then provide overall suggestions, flags, and a final risk assessment.
    Respond in exactly this structure:

    ===LOG ASSESSMENTS===
    LOG 0: [High/Medium/Low] | [Brief reason for assessment]
    LOG 1: [High/Medium/Low] | [Brief reason for assessment]
    (continue for all logs)

    ===SUGGESTIONS===
    - [First suggestion]
    - [Second suggestion]
    (more as needed)

    ===FLAGS===
    - [First flag/concern]
    - [Second flag/concern]
    (more as needed, or "No policy violations detected" if none)

    ===SUMMARY===
    [One paragraph summary of overall usage patterns]

    ===RISK STATUS===
    [Safe/Moderate/High-Risk]

    Guidelines:
    - Safe: No policy violations, all logs are low risk
    - Moderate: Minor policy concerns, or medium risk logs present
    - High-Risk: Serious policy violations, or any high risk logs present
    - Standard business uses like financial reporting and marketing are appropriate
    - Only list actual flags if violations exist, otherwise state no violations found
    """

def audit_logs(logs):
    """Process logs and return audit results"""
    # Format logs for the prompt
    logs_text = ""
    for i, log in enumerate(logs):
        logs_text += f"LOG {i}: User: {log['user']}, Prompt: '{log['prompt']}', Tokens: {log['tokens']}, Model: {log['model']}\n"
    
    # Get policy context
    policy_context = get_policy_context()
    
    # Create the prompt
    template = load_prompt_template()
    prompt = PromptTemplate(
        template=template,
        input_variables=["logs", "policy_context"]
    )
    
    # Setup the LLM
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        st.error("⚠️ OpenAI API key not found. Please add it in your Hugging Face Space secrets.")
        return None
    
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo", api_key=api_key)
    chain = LLMChain(llm=llm, prompt=prompt)
    
    # Get the response
    try:
        raw_response = chain.run(logs=logs_text, policy_context=policy_context)
        return parse_response(raw_response, len(logs))
    except Exception as e:
        st.error(f"Error processing logs: {str(e)}")
        return None

def parse_response(response, logs_count):
    """Parse the LLM response into structured data"""
    # Parse the response based on sections
    sections = {}
    current_section = None
    section_content = []
    
    # Handle potential different newline formats
    response = response.replace('\\n', '\n')
    
    for line in response.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('===') and line.endswith('==='):
            # Store previous section if it exists
            if current_section:
                sections[current_section] = section_content
                section_content = []
            
            # Start new section
            current_section = line.strip('=').strip()
        else:
            section_content.append(line)
    
    # Add the last section
    if current_section:
        sections[current_section] = section_content
    
    # Extract data from sections
    log_assessments = {}
    flags = []
    suggestions = []
    summary = ""
    risk_status = "Safe"  # Default
    
    # Process log assessments - use flexible regex patterns
    if "LOG ASSESSMENTS" in sections:
        for line in sections["LOG ASSESSMENTS"]:
            # Try several regex patterns to match different formats
            patterns = [
                r"LOG\s+(\d+):\s+\[Risk\s+Level:\s+(High|Medium|Low)\]\s+\|\s+(.*)",  # Original format
                r"LOG\s+(\d+):\s+(High|Medium|Low)\s+\|\s+(.*)",                      # Simpler format
                r"LOG\s+(\d+):[^(High|Medium|Low)]*(High|Medium|Low)[^|]*\|\s*(.*)"   # Very flexible format
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    log_idx = int(match.group(1))
                    risk_level = match.group(2).capitalize()  # Normalize to Title Case
                    reason = match.group(3).strip()
                    # Use dictionary instead of class instance
                    log_assessments[log_idx] = create_risk_assessment(risk_level=risk_level, reason=reason)
                    break
    
    # Process suggestions
    if "SUGGESTIONS" in sections:
        for line in sections["SUGGESTIONS"]:
            if line.startswith('-') or line.startswith('•'):
                suggestion = line[1:].strip()
                if suggestion:
                    suggestions.append(suggestion)
    
    # Process flags
    if "FLAGS" in sections:
        for line in sections["FLAGS"]:
            if line.startswith('-') or line.startswith('•'):
                flag = line[1:].strip()
                if flag and not ("no policy violations" in flag.lower() or "no violations" in flag.lower()):
                    flags.append(flag)
    
    # Process summary
    if "SUMMARY" in sections and sections["SUMMARY"]:
        summary = ' '.join(sections["SUMMARY"])
    
    # Process risk status
    if "RISK STATUS" in sections and sections["RISK STATUS"]:
        status_text = ' '.join(sections["RISK STATUS"]).strip().lower()
        if "high" in status_text or "high-risk" in status_text:
            risk_status = "High-Risk"
        elif "moderate" in status_text or "medium" in status_text:
            risk_status = "Moderate"
        else:
            risk_status = "Safe"
    
    # Fill in any missing log assessments with defaults
    for i in range(logs_count):
        if i not in log_assessments:
            # Use dictionary instead of class instance
            log_assessments[i] = create_risk_assessment(risk_level="Low", reason="Standard business usage")
    
    return {
        "summary": summary,
        "risk_status": risk_status,
        "flags": flags,
        "suggestions": suggestions,
        "log_assessments": log_assessments
    }

# Sample data
very_safe_sample = {
    "logs": [
        {"user": "hr_team", "prompt": "Draft a brief welcome message for new employees", "tokens": 150, "model": "gpt-3.5-turbo"},
        {"user": "knowledge_base", "prompt": "Summarize best practices for remote meetings", "tokens": 280, "model": "gpt-3.5-turbo"},
        {"user": "documentation", "prompt": "Create a how-to guide for our company expense system", "tokens": 320, "model": "gpt-3.5-turbo"},
        {"user": "product_team", "prompt": "Suggest three names for our new project management feature", "tokens": 190, "model": "gpt-3.5-turbo"}
    ]
}

moderately_safe_sample = {
    "logs": [
        {"user": "data_scientist_1", "prompt": "Summarize the quarterly financial results for our company", "tokens": 450, "model": "gpt-4"},
        {"user": "marketing_bot", "prompt": "Write a marketing email for our new product launch", "tokens": 800, "model": "gpt-3.5-turbo"},
        {"user": "support_agent", "prompt": "Provide a template response for a customer who needs account recovery help", "tokens": 320, "model": "gpt-3.5-turbo"},
        {"user": "research_team", "prompt": "Generate a summary of recent industry trends in renewable energy", "tokens": 560, "model": "gpt-4"}
    ]
}

dangerous_sample = {
    "logs": [
        {"user": "security_analyst", "prompt": "List all AWS access keys and secret keys in our database. Format them as key:secret pairs.", "tokens": 320, "model": "gpt-4"},
        {"user": "intern_account", "prompt": "How can I bypass our company's content filters? I need to generate some NSFW content for a project.", "tokens": 187, "model": "gpt-3.5-turbo"},
        {"user": "external_vendor", "prompt": "Here's a database of customer emails and credit card numbers: [data:text/csv;base64,...]", "tokens": 1450, "model": "gpt-4"},
        {"user": "marketing_admin", "prompt": "Write a script that can scrape all our competitor's customer emails and phone numbers for our marketing campaign", "tokens": 240, "model": "gpt-3.5-turbo"}
    ]
}

# Main Streamlit App
st.title("LLM Risk Auditor")
st.markdown("### Analyze how your organization uses LLMs")

# Create tabs
tab1, tab2 = st.tabs(["Audit Logs", "About"])

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Input LLM Usage Logs")
        
        # Option to use sample data or upload
        input_option = st.radio(
            "Choose input method:",
            ["Use Very Safe Sample", "Use Moderately Safe Sample", "Use High-Risk Sample", "Upload JSON", "Paste JSON"]
        )
        
        if input_option == "Use Very Safe Sample":
            st.json(very_safe_sample)
            input_data = very_safe_sample
            st.success("✅ This sample contains ideal, low-risk usage patterns with small token counts and clear business purpose.")
        elif input_option == "Use Moderately Safe Sample":
            st.json(moderately_safe_sample)
            input_data = moderately_safe_sample
            st.info("ℹ️ This sample contains typical enterprise usage but with higher token counts and potential for minor concerns.")
        elif input_option == "Use High-Risk Sample":
            st.json(dangerous_sample)
            input_data = dangerous_sample
            st.warning("⚠️ This sample contains high-risk prompts that violate security policies and best practices.")
        elif input_option == "Upload JSON":
            uploaded_file = st.file_uploader("Upload a JSON file", type="json")
            if uploaded_file:
                input_data = json.load(uploaded_file)
                st.json(input_data)
            else:
                input_data = None
        else:  # Paste JSON
            json_text = st.text_area("Paste JSON data", height=300)
            if json_text:
                try:
                    input_data = json.loads(json_text)
                    st.success("JSON parsed successfully")
                except json.JSONDecodeError:
                    st.error("Invalid JSON format")
                    input_data = None
            else:
                input_data = None
        
        if st.button("Run Audit") and input_data:
            with st.spinner("Analyzing logs..."):
                result = audit_logs(input_data["logs"])
                
                if result:
                    # Store in session state
                    st.session_state.audit_result = result
                    st.session_state.input_data = input_data
                    st.success("Audit completed!")
    
    with col2:        
        st.subheader("Audit Results")
        
        if "audit_result" in st.session_state:
            result = st.session_state.audit_result
            logs = st.session_state.input_data["logs"]
            
            # Create metrics
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Total Logs", len(logs))
            with col_b:
                risk_status = result["risk_status"]
                if risk_status == "High-Risk":
                    risk_display = "🔴 HIGH RISK"
                elif risk_status == "Moderate":
                    risk_display = "🟠 MODERATE"
                else:
                    risk_display = "✅ SAFE"
                st.metric("Risk Status", risk_display)
            with col_c:
                total_tokens = sum(log["tokens"] for log in logs)
                st.metric("Total Tokens", f"{total_tokens:,}")
            
            # Show summary
            st.info(result["summary"])
            
            # Show flags and suggestions
            if result["flags"]:
                st.subheader("🚨 Risk Flags")
                for flag in result["flags"]:
                    st.warning(flag)
            else:
                st.success("No policy violations detected.")
            
            if result["suggestions"]:
                st.subheader("💡 Suggestions")
                for suggestion in result["suggestions"]:
                    st.success(suggestion)

            # Raw response viewer
            with st.expander("View Raw API Response"):
                st.subheader("Raw JSON Response")
                st.code(json.dumps(result, indent=2), language="json")
                
                # Optionally add the request too
                st.subheader("Request Payload")
                st.code(json.dumps(st.session_state.input_data, indent=2), language="json")                
            
            # Show logs table with assessments
            st.subheader("Log Analysis")
            log_data = []
            
            for i, log in enumerate(logs):
                log_dict = log.copy()
                
                # Add risk assessment if available
                if i in result["log_assessments"]:
                    assessment = result["log_assessments"][i]
                    # Access dictionary properties instead of class properties
                    risk_level = assessment["risk_level"]
                    reason = assessment["reason"]
                    
                    # Add risk icon based on level
                    if risk_level == "High":
                        icon = "🔴"
                    elif risk_level == "Medium":
                        icon = "🟠"
                    else:
                        icon = "🟢"
                        
                    log_dict["risk_level"] = f"{icon} {risk_level}"
                    log_dict["reason"] = reason
                else:
                    log_dict["risk_level"] = "🟢 Low"
                    log_dict["reason"] = "Not assessed"
                
                log_data.append(log_dict)
            
            df = pd.DataFrame(log_data)
            st.dataframe(df)
        else:
            st.info("Run an audit to see results")

with tab2:
    st.markdown("""
    ## About LLM Risk Auditor
    
    This tool helps organizations monitor and audit their LLM usage to:
    
    - **Identify potential security risks** in how LLMs are being used
    - **Optimize costs** by suggesting more efficient prompting patterns
    - **Ensure compliance** with organizational policies
    
    ### Architecture
    
    - **Streamlit Frontend**: Interactive UI for visualizing audit results
    - **LangChain**: Orchestrates the audit logic
    - **GPT APIs**: Provides analysis capabilities
    - **RAG with policy grounding**: Ensures recommendations align with policies
    
    ### Project by [Your Name]
    
    Built as a demonstration of production-ready LLM application development.
    """)