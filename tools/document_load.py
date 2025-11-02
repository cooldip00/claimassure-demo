import os
from pydantic import BaseModel, Field
from typing import List, ClassVar
from pathlib import Path
import PyPDF2
import docx
from crewai.tools import BaseTool

class DirectoryLoaderInput(BaseModel):
    directory_path: str = Field(default="", description="Path to the directory containing documents")

class DirectoryLoaderTool(BaseTool):
    """CrewAI Tool to load and extract data from all documents in a directory"""

    name: str = "DirectoryLoaderTool"
    description: str = "Loads all documents from a directory and extracts their text"

    supported_extensions: ClassVar[List[str]] = ['.pdf', '.docx', '.txt']

    def extract_text_from_pdf(self, file_path: str) -> str:
        text = ""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            text = f"[Error reading PDF: {e}]"
        return text

    def extract_text_from_docx(self, file_path: str) -> str:
        text = ""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        except Exception as e:
            text = f"[Error reading DOCX: {e}]"
        return text

    def extract_text_from_txt(self, file_path: str) -> str:
        text = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            text = f"[Error reading TXT: {e}]"
        return text

    def extract_text(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self.extract_text_from_pdf(file_path)
        elif ext == ".docx":
            return self.extract_text_from_docx(file_path)
        elif ext == ".txt":
            return self.extract_text_from_txt(file_path)
        else:
            return f"[Unsupported file type: {ext}]"

    # Accept either structured input or a plain kwarg to be robust
    def _run(self, directory_path: str = ""):
        # default project data directory
        default_dir = Path(__file__).resolve().parents[1] / "data"

        # prefer an uploaded directory from env if set (webapp sets nothing here; we inject via task text too)
        env_dir = os.getenv("UPLOAD_DIR")
        candidates = []

        # caller-provided
        if directory_path:
            p = Path(directory_path)
            candidates += [p, Path.cwd() / directory_path, Path(__file__).resolve().parents[1] / directory_path]

        # environment
        if env_dir:
            candidates.append(Path(env_dir))

        # default
        candidates.append(default_dir)

        directory = None
        tried = []
        for c in candidates:
            tried.append(str(c))
            if c.exists() and c.is_dir():
                directory = c
                break

        if directory is None:
            return [{"error": "Directory not found. Tried: " + " | ".join(tried)}]

        all_data = []
        for file_path in directory.iterdir():
            if file_path.suffix.lower() in self.supported_extensions:
                text = self.extract_text(str(file_path))
                all_data.append({"file_name": file_path.name, "content": text})

        if not all_data:
            return [{"warning": f"No supported files found in: {directory}"}]

        return all_data
    
    # # Accept either structured input or a plain kwarg to be robust
    # def _run(self, directory_path: str = ""):
    #     # 1) Define the default project data directory
    #     default_dir = Path(__file__).resolve().parents[1] / "data"

    #     # 2) Resolve candidate path from the provided argument (if any)
    #     candidates = []
    #     if directory_path:
    #         p = Path(directory_path)
    #         # as-is
    #         candidates.append(p)
    #         # relative to CWD
    #         candidates.append(Path.cwd() / directory_path)
    #         # relative to project root (tools/.. -> project/)
    #         candidates.append(Path(__file__).resolve().parents[1] / directory_path)
    #     # 3) Always include the default data/ as final fallback
    #     candidates.append(default_dir)

    #     # 4) Pick the first existing directory
    #     directory = None
    #     tried = []
    #     for c in candidates:
    #         tried.append(str(c))
    #         if c.exists() and c.is_dir():
    #             directory = c
    #             break

    #     if directory is None:
    #         # Return a helpful error listing what we tried
    #         return [{"error": "Directory not found. Tried: " + " | ".join(tried)}]

    #     # 5) Load all supported files
    #     all_data = []
    #     for file_path in directory.iterdir():
    #         if file_path.suffix.lower() in self.supported_extensions:
    #             text = self.extract_text(str(file_path))
    #             all_data.append({"file_name": file_path.name, "content": text})

    #     # Handle empty folder nicely
    #     if not all_data:
    #         return [{"warning": f"No supported files found in: {directory}"}]

    #     return all_data

    # # Accept either structured input or a plain kwarg to be robust
    # def _run(self, directory_path: str = ""):
    #     if not directory_path:
    #         directory_path = str(Path(__file__).resolve().parents[1] / "data")
    #     directory = Path(directory_path)

    #     if not directory.exists() or not directory.is_dir():
    #         return [{"error": f"Directory not found: {directory_path}"}]

    #     all_data = []
    #     for file_path in directory.iterdir():
    #         if file_path.suffix.lower() in self.supported_extensions:
    #             text = self.extract_text(str(file_path))
    #             all_data.append({"file_name": file_path.name, "content": text})
    #     return all_data
