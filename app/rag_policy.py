import os
from llama_index.core import VectorStoreIndex
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.core.storage import StorageContext
from llama_index.vector_stores.faiss import FaissVectorStore  # Note: Capital F, no "FAISS"
import faiss

# Global index variable
_index = None

def initialize_index():
    """Initialize the FAISS index with policy documents"""
    global _index
    
    # Check if the policy file exists
    policy_file = "app/policies/acceptable_use_policy.md"
    if not os.path.exists(policy_file):
        os.makedirs(os.path.dirname(policy_file), exist_ok=True)
        with open(policy_file, "w") as f:
            f.write("# Acceptable Use Policy\n\n")
            f.write("1. Users should not submit prompts containing PII (Personal Identifiable Information).\n")
            f.write("2. Large token usage should be justified by business requirements.\n")
            f.write("3. Repetitive prompts should be optimized or cached.\n")
            f.write("4. Users should not attempt to extract internal system information.\n")
            f.write("5. Production use cases should use approved models only.\n")
    
    # Load documents
    documents = SimpleDirectoryReader(input_files=[policy_file]).load_data()
    
    # Create FAISS index
    dimension = 1536  # OpenAI embedding dimension
    faiss_index = faiss.IndexFlatL2(dimension)
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Create index
    _index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context
    )
    
    return _index

def get_policy_context(query, num_results=2):
    """Get relevant policy context for a query"""
    global _index
    
    # Initialize if not already done
    if _index is None:
        try:
            _index = initialize_index()
        except Exception as e:
            return f"Error initializing policy index: {str(e)}"
    
    # Query the index
    try:
        query_engine = _index.as_query_engine(similarity_top_k=num_results)
        response = query_engine.query(query)
        return response.response
    except Exception as e:
        return f"Error querying policy index: {str(e)}"
