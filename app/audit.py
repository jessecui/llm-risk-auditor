import os
import re
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from .models import PromptLogEntry, AuditResponse, LogRiskAssessment
from .rag_policy import get_policy_context

# Load the prompt template
def load_prompt_template():
    with open("app/prompts/prompt_template.txt", "r") as f:
        return f.read()

def check_format(response, log_count):
    """Check if the response has the correct format for parsing"""
    # Check for section headers
    required_sections = ["LOG ASSESSMENTS", "SUGGESTIONS", "FLAGS", "SUMMARY", "RISK STATUS"]
    
    for section in required_sections:
        if f"==={section}===" not in response:
            return False
    
    # Check if we can find log assessments for each log
    log_pattern = r"LOG\s+(\d+):\s+(High|Medium|Low)\s+\|\s+(.*)"
    log_matches = re.findall(log_pattern, response, re.IGNORECASE)
    
    # Make sure we found at least one log assessment per log
    if len(log_matches) < log_count:
        return False
    
    return True

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
                    log_assessments[log_idx] = LogRiskAssessment(risk_level=risk_level, reason=reason)
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
    
    # As a fallback, derive risk status from log assessments if we have them
    if not flags and log_assessments:
        high_risk_count = sum(1 for a in log_assessments.values() if a.risk_level == "High")
        medium_risk_count = sum(1 for a in log_assessments.values() if a.risk_level == "Medium")
        
        if high_risk_count > 0:
            risk_status = "High-Risk"
        elif medium_risk_count > 0:
            risk_status = "Moderate"
    
    # Fill in any missing log assessments based on risk status
    if len(log_assessments) == 0 and risk_status != "Safe":
        # Create default assessments based on risk level
        default_level = "Medium" if risk_status == "Moderate" else "High" if risk_status == "High-Risk" else "Low"
        for i in range(logs_count):
            log_assessments[i] = LogRiskAssessment(
                risk_level=default_level, 
                reason="Assessment inferred from overall risk status"
            )
    
    # Fill in any missing log assessments with defaults
    for i in range(logs_count):
        if i not in log_assessments:
            log_assessments[i] = LogRiskAssessment(
                risk_level="Low", 
                reason="Standard business usage"
            )
    
    return AuditResponse(
        summary=summary,
        risk_status=risk_status,
        flags=flags,
        suggestions=suggestions,
        log_assessments=log_assessments
    )

def audit_logs(logs: List[PromptLogEntry]) -> AuditResponse:
    # Format logs for the prompt
    logs_text = ""
    for i, log in enumerate(logs):
        logs_text += f"LOG {i}: User: {log.user}, Prompt: '{log.prompt}', Tokens: {log.tokens}, Model: {log.model}\n"
    
    # Try to get policy context (if RAG is enabled)
    try:
        policy_context = get_policy_context(logs_text)
        has_policy = True
    except Exception as e:
        policy_context = f"No policy information available. Error: {str(e)}"
        has_policy = False
    
    # Create the prompt
    template = load_prompt_template()
    prompt = PromptTemplate(
        template=template,
        input_variables=["logs", "policy_context"]
    )
    
    # Setup the LLM
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo")
    chain = LLMChain(llm=llm, prompt=prompt)
    
    # Get the response
    raw_response = chain.run(logs=logs_text, policy_context=policy_context)
    
    # Check if it matches our expected format
    format_valid = check_format(raw_response, len(logs))
    
    # If format is invalid, retry once with explicit instructions
    if not format_valid:
        print("Initial response format invalid. Retrying with explicit instructions...")
        
        retry_template = """
        Your previous response did not follow the required format. Here was your response:

        {previous_response}

        Please redo your analysis and provide it in EXACTLY this format:

        ===LOG ASSESSMENTS===
        LOG 0: High/Medium/Low | Brief reason
        LOG 1: High/Medium/Low | Brief reason
        (one line for EACH log number from 0 to {log_count})

        ===SUGGESTIONS===
        - First suggestion
        - Second suggestion

        ===FLAGS===
        - First flag/concern
        - Second flag/concern
        (or "- No policy violations detected" if none)

        ===SUMMARY===
        One paragraph summary

        ===RISK STATUS===
        Safe OR Moderate OR High-Risk

        Original logs:
        {logs}

        Policy context:
        {policy_context}
        """
        
        retry_prompt = PromptTemplate(
            template=retry_template,
            input_variables=["previous_response", "log_count", "logs", "policy_context"]
        )
        
        retry_chain = LLMChain(llm=ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo"), prompt=retry_prompt)
        
        raw_response = retry_chain.run(
            previous_response=raw_response,
            log_count=len(logs)-1,  # Logs are 0-indexed
            logs=logs_text,
            policy_context=policy_context
        )
        
        # Check format again
        format_valid = check_format(raw_response, len(logs))
        
        if not format_valid:
            # Still failed, return error response
            print("Retry failed. Returning error response.")
            return AuditResponse(
                summary="⚠️ Parsing Error: Could not properly analyze the logs due to formatting issues",
                risk_status="High-Risk",  # Default to high risk on parsing failure
                flags=["Unable to properly analyze logs due to parsing error", 
                       "System defaulted to High-Risk as a precaution"],
                suggestions=["Try again with a different set of logs", 
                             "Check for any unusual characters or formatting in the logs"],
                log_assessments={i: LogRiskAssessment(risk_level="Medium", reason="Not analyzed due to parsing error") 
                               for i in range(len(logs))}
            )
    
    # Parse the valid response
    try:
        result = parse_response(raw_response, len(logs))
        return result
    except Exception as e:
        # Handle any parsing errors
        print(f"Error parsing response: {str(e)}")
        return AuditResponse(
            summary=f"Error parsing LLM response: {str(e)}",
            risk_status="High-Risk",
            flags=["Error in processing audit results"],
            suggestions=["Please try again"],
            log_assessments={i: LogRiskAssessment(risk_level="Medium", reason="Processing error") 
                          for i in range(len(logs))}
        )