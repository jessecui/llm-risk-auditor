# LLM Usage Risk Auditor API

A tool for analyzing LLM usage logs to identify security risks and policy violations.

🌐 [Live Demo](https://llm-risk-auditor.onrender.com/)

## What it does

This project audits LLM usage based on prompt logs and flags risky behavior according to acceptable use policies.

This application addresses the critical challenge of ensuring safe and responsible AI use across organizations, particularly as access to powerful language models becomes more widespread.

## Features

- Comprehensive security risk detection including credential leaks and PII exposure
- Policy violation monitoring and flagging
- Risk level assessment for each prompt (Low/Medium/High)
- RAG-based analysis with policy-grounded recommendations
- Interactive visualization dashboard

## Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/llm-risk-auditor.git
cd llm-risk-auditor

# Set up virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure OpenAI API key
echo "OPENAI_API_KEY=your-key-here" > .env
```

## Running it

Start the API:
```bash
uvicorn app.main:app --reload
```

Start the UI (in a new terminal):
```bash
streamlit run app/streamlit/app.py
```

Then open http://localhost:8501 in your browser.

## How to use it

1. Select a sample dataset or upload custom logs
2. Initiate the audit process
3. Review results, including flagged issues and recommendations

## API Usage

The API can be integrated programmatically:

```python
import requests

logs = {
    "logs": [
        {"user": "data_scientist", "prompt": "Summarize quarterly results", "tokens": 450, "model": "gpt-4"},
        {"user": "marketing", "prompt": "Write a product email", "tokens": 800, "model": "gpt-3.5-turbo"}
    ]
}

response = requests.post("http://localhost:8000/audit", json=logs)
print(response.json())
```

## Stack

- FastAPI backend
- LangChain + OpenAI for audit logic
- FAISS + LlamaIndex for policy RAG
- Streamlit frontend

## Development Tools

- Claude 3.7 Sonnet for code generation assistance
- Cursor IDE for development

## Future work

Planned enhancements include:
- Extended model provider support
- Historical audit tracking
- Real-time monitoring capabilities
- Custom policy editor

## License

MIT