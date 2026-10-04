import os
from pathlib import Path
import pandas as pd
from pypdf import PdfReader
from PIL import Image
import google.generativeai as genai
from core.config import GEMINI_API_KEY

class DocumentService:
    @classmethod
    def extract_text_from_image(cls, image_path: Path) -> str:
        """Uses Gemini Vision to read textbook pages from photographs or scans."""
        api_key = os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
        if not api_key:
            return ""
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            img = Image.open(image_path)
            
            prompt = (
                "You are an academic OCR specialist. Transcribe all text, headings, "
                "diagram descriptions, questions, and curriculum content from this textbook page clearly into text. "
                "Do not include meta commentary."
            )
            response = model.generate_content([prompt, img])
            return response.text.strip() if response and response.text else ""
        except Exception as e:
            return f"[Error transcribing textbook image: {e}]"

    @classmethod
    def extract_text(cls, file_path: Path) -> str:
        """Extracts text seamlessly from PDF, TXT, or Book Photos (JPG, JPEG, PNG, WEBP)."""
        suffix = file_path.suffix.lower()

        # 1. Image Files (Book Photos / Scans)
        if suffix in [".jpg", ".jpeg", ".png", ".webp"]:
            return cls.extract_text_from_image(file_path)

        # 2. PDF Documents
        elif suffix == ".pdf":
            try:
                reader = PdfReader(str(file_path))
                text_parts = []
                for idx, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                    if len(text_parts) >= 15:  # Cap at 15 pages to keep context focused
                        break
                return "\n".join(text_parts)
            except Exception as e:
                return f"[Error reading PDF: {e}]"

        # 3. Plain Text Files
        elif suffix == ".txt":
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                return f"[Error reading TXT: {e}]"

        return ""

    @classmethod
    def read_tabular(cls, file_path: Path) -> pd.DataFrame:
        """Reads CSV, XLSX, or XLS files."""
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(file_path)
        elif suffix in [".xlsx", ".xls"]:
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported spreadsheet format: {suffix}")
