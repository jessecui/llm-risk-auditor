---
title: LLM Risk Auditor
emoji: 🔍
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.32.0
app_file: app.py
pinned: false
---

# LLM Risk Auditor

A tool that analyzes LLM usage logs to identify security risks and policy violations.

[Open in Hugging Face Spaces](https://huggingface.co/spaces/jessecui/llm-risk-auditor)

## What it does

This project audits how people are using LLMs in your organization. It analyzes prompt logs, flags risky behavior, and checks against your acceptable use policies.

I built this to help solve the problem of ensuring safe and responsible AI use within teams, especially as more employees get access to powerful models like GPT-4.

## Features

- Detect common security risks like credential leaks and PII exposure
- Flag inappropriate usage patterns that violate policies
- Show risk levels for each prompt (Low/Medium/High)
- RAG-based analysis that grounds recommendations in your policies
- Simple visualization dashboard

## Setup

```bash
# Clone the repo
git clone https://github.com/yourusername/llm-risk-auditor.git
cd llm-risk-auditor

# Set up venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Add your OpenAI API key
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

1. Choose one of the sample datasets or upload your own logs
2. Hit "Run Audit"
3. See the results, including flagged issues and suggestions

## API Usage

You can also use it programmatically:

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

I'd like to add:
- Support for more model providers
- Historical audit tracking
- Real-time monitoring
- Custom policy editor

## License

MIT