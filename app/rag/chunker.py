"""
Document Chunker Module.
Performs semantic and section-aware chunking of policy documents,
preserving document metadata, section headers, policy IDs, and page references.
"""

from typing import List, Dict, Any
import re


class DocumentChunk:
    def __init__(
        self,
        chunk_id: str,
        content: str,
        metadata: Dict[str, Any]
    ):
        self.chunk_id = chunk_id
        self.content = content.strip()
        self.metadata = metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "metadata": self.metadata
        }


class PolicyChunker:
    @staticmethod
    def chunk_policy_text(
        text: str,
        doc_metadata: Dict[str, Any],
        max_chunk_chars: int = 600,
        overlap_chars: int = 100
    ) -> List[DocumentChunk]:
        """
        Split policy markdown/text into coherent semantic sections based on headers
        and policy demarcations.
        """
        chunks = []
        # Split on headers (# or ##)
        sections = re.split(r'\n(?=#{1,3}\s)', text)
        chunk_idx = 0

        for sec in sections:
            sec_clean = sec.strip()
            if not sec_clean:
                continue

            if len(sec_clean) <= max_chunk_chars:
                cid = f"{doc_metadata.get('document_id', 'DOC')}_chk_{chunk_idx:03d}"
                chunks.append(DocumentChunk(cid, sec_clean, doc_metadata.copy()))
                chunk_idx += 1
            else:
                # Subdivide by paragraphs
                paragraphs = sec_clean.split("\n\n")
                current_chunk = ""
                for p in paragraphs:
                    p_clean = p.strip()
                    if not p_clean:
                        continue
                    if len(current_chunk) + len(p_clean) < max_chunk_chars:
                        current_chunk += ("\n\n" + p_clean) if current_chunk else p_clean
                    else:
                        if current_chunk:
                            cid = f"{doc_metadata.get('document_id', 'DOC')}_chk_{chunk_idx:03d}"
                            chunks.append(DocumentChunk(cid, current_chunk, doc_metadata.copy()))
                            chunk_idx += 1
                        current_chunk = p_clean

                if current_chunk:
                    cid = f"{doc_metadata.get('document_id', 'DOC')}_chk_{chunk_idx:03d}"
                    chunks.append(DocumentChunk(cid, current_chunk, doc_metadata.copy()))
                    chunk_idx += 1

        return chunks

