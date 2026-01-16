
import unittest
from unittest.mock import MagicMock, patch
from services.reporting.section_compiler import SectionCompiler

class TestAbstractCompilation(unittest.TestCase):
    
    @patch("services.reporting.section_compiler.generate_response")
    def test_abstract_compilation(self, mock_generate):
        # Mock LLM Response
        mock_generate.return_value = "This is a synthesized abstract."
        
        # 1. Setup State with Completed Chapters
        dummy_state = {
            "sections": [
                {
                    "section_id": "chapter_1",
                    "status": "accepted",
                    "content": "# 1.3 Problem Statement\nThe problem is manual reporting is slow.\n# 1.4 Objectives\nTo automate it."
                },
                {
                    "section_id": "chapter_4",
                    "status": "accepted",
                    "content": "# 4.1 Proposed System\nWe use a multi-agent system.\n# 4.2 Advantages\nIt is fast and deterministic."
                },
                {
                    "section_id": "chapter_6",
                    "status": "accepted",
                    "content": "# 6.5 Implemented System Flow\nThe user inputs a query, agents process it.\n# 6.6 Sub Agents\nMany sub agents."
                },
                {
                    "section_id": "chapter_8",
                    "status": "accepted",
                    "content": "# 8.1 Performance Analysis\nIt runs in 30 seconds."
                },
                {
                    "section_id": "chapter_9",
                    "status": "accepted",
                    "content": "# 9.1 Conclusion\nThe system works well."
                },
                {
                    "section_id": "abstract",
                    "status": "generating",
                    "target_words": 300,
                    "title": "Abstract",
                    "description": "Synth"
                }
            ],
            "research_gaps": [{"rationale": "Lack of automation."}]
        }
        
        compiler = SectionCompiler(dummy_state)
        abstract_section = dummy_state["sections"][-1]
        
        # 2. Compile Abstract
        result = compiler.compile(abstract_section)
        
        # 3. Verifications
        self.assertEqual(result, "This is a synthesized abstract.")
        
        # Check if inputs were extracted correctly
        inputs = compiler._build_abstract_inputs()
        print("Extracted Inputs:", inputs)
        
        # Assertions on extracted content (stripping whitespace)
        self.assertIn("The problem is manual reporting is slow.", inputs["problem_statement"])
        self.assertIn("We use a multi-agent system.", inputs["methodology_summary"])
        self.assertIn("It is fast and deterministic.", inputs["key_contributions"]) # From advantages
        self.assertIn("The user inputs a query", inputs["implementation_summary"])
        self.assertIn("It runs in 30 seconds.", inputs["results_summary"])
        
        # Check if LLM was called with correct context
        args, kwargs = mock_generate.call_args
        prompt_used = args[0]
        # print("\nPrompt Used:\n", prompt_used)
        
        self.assertIn("The problem is manual reporting is slow", prompt_used)
        self.assertIn("It is fast and deterministic", prompt_used)

        print("ABSTRACT TEST PASSED")

if __name__ == "__main__":
    unittest.main()
