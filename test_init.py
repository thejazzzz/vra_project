from services.structured_llm import StructuredLLMService
from services.reporting.section_compiler import SectionCompiler

try:
    print("Initializing StructuredLLMService...")
    svc = StructuredLLMService()
    print("StructuredLLMService initialized.")
    
    print("Initializing SectionCompiler...")
    compiler = SectionCompiler({"state": "dummy"})
    print("SectionCompiler initialized.")
    
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
