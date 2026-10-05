import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import urljoin

import requests
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from pypdf import PdfReader

from local_mcp.rag.repository import LanceDBAdapter


class FileHandler(ABC):
    def __init__(self, repository: LanceDBAdapter) -> None:
        self.repository = repository

    @abstractmethod
    def process(self, path: str, table_name: str) -> None:
        pass


class PDFFileHandler(FileHandler):
    def __init__(self, repository: LanceDBAdapter) -> None:
        super().__init__(repository)

    def process(self, path: str, table_name: str) -> None:
        filename = Path(path).name
        if self.repository.exists(file_path=path, table_name=table_name):
            print(
                f"[Ingest] Skipping {filename}: already exists in table '{table_name}'.",
                file=sys.stderr,
            )
            return

        print(f"[Ingest] Processing file: {path}", file=sys.stderr)
        reader = PdfReader(path)

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=300,
            length_function=len,
        )

        chunks = []
        page_numbers = []

        for page_idx, page in enumerate(reader.pages, 1):
            page_text = page.extract_text() or ""
            if not page_text.strip():
                continue

            # Split text for this page
            page_chunks = text_splitter.split_text(page_text)
            for chunk in page_chunks:
                chunks.append(chunk)
                page_numbers.append(page_idx)

        self.repository.save(
            chunks=chunks,
            page_numbers=page_numbers,
            table_name=table_name,
            file_path=path,
        )


MARKDOWN_NAME_AND_LINK_RE = r"\[([^\]]+)\]\(([^)]+)\)"


class URLHandler(FileHandler):
    def __init__(self, repository: LanceDBAdapter) -> None:
        super().__init__(repository)

    def process(self, path: str, table_name: str) -> None:
        filename = Path(path).name
        if self.repository.exists(file_path=path, table_name=table_name):
            print(
                f"[Ingest] Skipping {filename}: already exists in table '{table_name}'.",
                file=sys.stderr,
            )
            return

        print(f"[Ingest] Processing file: {path}", file=sys.stderr)
        with open(path, "r") as f:
            url = f.read().strip()
            if not url.endswith("/llms.txt"):
                raise NotImplementedError("Currently only supports '/llms.txt'")

        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            index_content = resp.text
        except requests.RequestException as e:
            print(f"[Ingest] Error fetching {url}: {e}", file=sys.stderr)
            return

        text_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.MARKDOWN,
            chunk_size=2000,
            chunk_overlap=300,
        )

        chunks: list[str] = []
        page_numbers: list[int] = []

        matches = re.findall(MARKDOWN_NAME_AND_LINK_RE, index_content)
        for doc_idx, (title, link) in enumerate(matches, start=1):
            sub_url = urljoin(url, link)
            print(f"[Ingest] Processing {title} - {link}", file=sys.stderr)
            try:
                sub_resp = requests.get(sub_url, timeout=10)
                sub_resp.raise_for_status()
                sub_text = sub_resp.text.strip()
                if not sub_text:
                    continue

                sub_chunks = text_splitter.split_text(sub_text)
                for chunk in sub_chunks:
                    chunks.append(f"[{title}]({sub_url})\n\n{chunk}")
                    page_numbers.append(doc_idx)
            except requests.RequestException as e:
                print(
                    f"[Ingest] Warning: Failed to fetch {sub_url}: {e}",
                    file=sys.stderr,
                )

        self.repository.save(
            chunks=chunks,
            page_numbers=page_numbers,
            table_name=table_name,
            file_path=path,
        )
