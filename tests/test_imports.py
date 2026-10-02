import unittest

class TestEnvironment(unittest.TestCase):
    def test_imports(self):
        try:
            import streamlit
            import crewai
            import langchain_google_genai
            import pandas
            import openpyxl
            import pypdf
        except ImportError as e:
            self.fail(f"Dependency import failed: {e}")

if __name__ == "__main__":
    unittest.main()
