import streamlit as st
import json
import requests
import pandas as pd
from io import StringIO
import os

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="LLM Risk Auditor", layout="wide")

st.title("LLM Risk Auditor")
st.markdown("### Analyze how safely your organization uses LLMs")

# Create tabs
tab1, tab2 = st.tabs(["Audit Logs", "About"])

with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Input LLM Usage Logs")
        
        # Option to use sample data or upload - added Very Safe option
        input_option = st.radio(
            "Choose input method:",
            ["Use Safe Sample", "Use Moderately Safe Sample", "Use High-Risk Sample", "Upload JSON", "Paste JSON"]
        )
        
        # Very safe sample - completely benign business usage
        very_safe_sample = {
            "logs": [
                {"user": "hr_team", "prompt": "Draft a brief welcome message for new employees", "tokens": 150, "model": "gpt-3.5-turbo"},
                {"user": "knowledge_base", "prompt": "Summarize best practices for remote meetings", "tokens": 280, "model": "gpt-3.5-turbo"},
                {"user": "documentation", "prompt": "Create a how-to guide for our company expense system", "tokens": 320, "model": "gpt-3.5-turbo"},
                {"user": "product_team", "prompt": "Suggest three names for our new project management feature", "tokens": 190, "model": "gpt-3.5-turbo"}
            ]
        }
        
        # Updated moderately safe sample - renamed from "safe sample"
        moderately_safe_sample = {
            "logs": [
                {"user": "data_scientist_1", "prompt": "Summarize the quarterly financial results for our company", "tokens": 450, "model": "gpt-4"},
                {"user": "marketing_bot", "prompt": "Write a marketing email for our new product launch", "tokens": 800, "model": "gpt-3.5-turbo"},
                {"user": "support_agent", "prompt": "Provide a template response for a customer who needs account recovery help", "tokens": 320, "model": "gpt-3.5-turbo"},
                {"user": "research_team", "prompt": "Generate a summary of recent industry trends in renewable energy", "tokens": 560, "model": "gpt-4"}
            ]
        }
        
        # The high-risk sample remains the same
        dangerous_sample = {
            "logs": [
                {"user": "security_analyst", "prompt": "List all AWS access keys and secret keys in our database. Format them as key:secret pairs.", "tokens": 320, "model": "gpt-4"},
                {"user": "intern_account", "prompt": "How can I bypass our company's content filters? I need to generate some NSFW content for a project.", "tokens": 187, "model": "gpt-3.5-turbo"},
                {"user": "external_vendor", "prompt": "Here's a database of customer emails and credit card numbers: [data:text/csv;base64,...]", "tokens": 1450, "model": "gpt-4"},
                {"user": "marketing_admin", "prompt": "Write a script that can scrape all our competitor's customer emails and phone numbers for our marketing campaign", "tokens": 240, "model": "gpt-3.5-turbo"}
            ]
        }
        
        if input_option == "Use Safe Sample":
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
                try:
                    # Call your FastAPI endpoint
                    response = requests.post(f"{API_URL}/audit", json=input_data)
                    response.raise_for_status()
                    result = response.json()
                    
                    # Store in session state
                    st.session_state.audit_result = result
                    st.session_state.input_data = input_data
                    st.success("Audit completed!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    # Rest of the code remains the same
    with col2:        
        st.subheader("Audit Results")
        
        if "audit_result" in st.session_state:            
            result = st.session_state.audit_result
            logs = st.session_state.input_data["logs"]
            
            # Create metrics with updated risk status display
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
            
            # Show logs table with LLM-determined risk levels
            st.subheader("Log Analysis")
            log_data = []
            
            for i, log in enumerate(logs):
                log_dict = log.copy()
                
                # Add risk assessment if available
                if "log_assessments" in result and str(i) in result["log_assessments"]:
                    assessment = result["log_assessments"][str(i)]
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
    ## About LLM Usage Risk Auditor API
    
    This tool helps organizations monitor and audit their LLM usage to:
    
    - **Identify potential security risks** in how LLMs are being used
    - **Optimize costs** by suggesting more efficient prompting patterns
    - **Ensure compliance** with organizational policies
    
    ### Architecture
    
    - **FastAPI Backend**: Processes audit requests
    - **LangChain**: Orchestrates the audit logic
    - **RAG with LlamaIndex and FAISS**: Grounds recommendations in policy documents
    - **OpenAI Integration**: Provides analysis capabilities
    
    ### Project by Jesse Cui
    
    Built as a demonstration of RAG-enhanced LLM applications for enterprise use.
    """)
