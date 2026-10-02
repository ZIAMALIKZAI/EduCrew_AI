from pathlib import Path
from pypdf import PdfReader
import pandas as pd

class DocumentService:
    @staticmethod
    def extract_text(file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            reader = PdfReader(str(file_path))
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        elif suffix in [".txt", ".md"]:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    @staticmethod
    def read_tabular(file_path: Path) -> pd.DataFrame:
        suffix = file_path.suffix.lower()
        if suffix in [".xlsx", ".xls"]:
            return pd.read_excel(file_path)
        elif suffix == ".csv":
            return pd.read_csv(file_path)
        else:
            raise ValueError(f"Unsupported tabular format: {suffix}")
