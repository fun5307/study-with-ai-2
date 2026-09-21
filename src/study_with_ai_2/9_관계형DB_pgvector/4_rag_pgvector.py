"""Samsung 지속가능경영보고서를 pgvector에 저장하고 검색하는 예제."""

from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector
from psycopg.types.json import Json
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


DB_URL = "postgresql://postgres:pgvector-demo@127.0.0.1:5432/rag"
CATEGORY = "Samsung_Sustainability"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PDF_PATH = DATA_DIR / "Samsung_Electronics_Sustainability_Report_2026_KOR.pdf"


def prepare_database(conn):
    """pgvector 확장과 문서 테이블을 준비한다."""
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            category text NOT NULL,
            content text NOT NULL,
            embedding vector(1536),
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb
        )
    """)
    # 기존 pgvector 실습에서 만든 테이블에 metadata가 없는 경우를 대비한다.
    conn.execute("""
        ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS metadata jsonb NOT NULL DEFAULT '{}'::jsonb
    """)
    conn.commit()
    register_vector(conn)


def load_and_split_pdf():
    """PDF를 읽어 페이지 정보를 가진 작은 청크 목록으로 만든다."""
    reader = PdfReader(PDF_PATH)
    pdf_docs = [
        Document(
            page_content=page.extract_text() or "",
            metadata={"source": "삼성전자_지속가능성_보고서", "page": page_number},
        )
        for page_number, page in enumerate(reader.pages, start=1)
    ]

    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=80)
    return splitter.split_documents(pdf_docs)


def save_chunks(conn, chunks, embeddings):
    """청크와 임베딩을 documents 테이블에 저장한다."""
    # 이 보고서만 지우므로 다른 category의 문서는 유지된다.
    conn.execute("DELETE FROM documents WHERE category = %s", (CATEGORY,))

    chunk_embeddings = embeddings.embed_documents(
        [doc.page_content for doc in chunks]
    )
    rows = [
        (CATEGORY, doc.page_content, embedding, Json(doc.metadata))
        for doc, embedding in zip(chunks, chunk_embeddings)
    ]

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO documents (category, content, embedding, metadata)
            VALUES (%s, %s, %s, %s)
        """, rows)
    conn.commit()
    print(f"{len(rows)}개 청크를 pgvector에 저장했습니다.")


def retrieve_docs(conn, question, embeddings, k=5):
    """질문과 가까운 청크 k개를 Document 목록으로 반환한다."""
    query_embedding = embeddings.embed_query(question)
    rows = conn.execute("""
        SELECT content, metadata
        FROM documents
        WHERE category = %s
        ORDER BY embedding <=> %s
        LIMIT %s
    """, (CATEGORY, query_embedding, k)).fetchall()

    return [Document(page_content=content, metadata=metadata) for content, metadata in rows]


if __name__ == "__main__":
    load_dotenv()
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    with psycopg.connect(DB_URL) as conn:
        prepare_database(conn)
        chunks = load_and_split_pdf()
        save_chunks(conn, chunks, embeddings)

        docs = retrieve_docs(conn, "삼성전자 주가 전망", embeddings)
        for doc in docs:
            print(f"[p.{doc.metadata['page']}] {doc.page_content[:120]}...")
