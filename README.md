# Campus Knowledge Assistant

A production-oriented, permission-aware, version-aware RAG backend for university policies, regulations, and course-related documents.

The project is designed as a backend-focused portfolio project demonstrating document processing, PostgreSQL, pgvector, hybrid retrieval, reranking, authentication, RBAC, Redis, testing, evaluation, and LLM-based answer generation.

---

## Overview

University documents such as regulations, academic policies, and course documents can be large, difficult to search, and frequently updated.

The Campus Knowledge Assistant allows users to ask questions in natural language and retrieves relevant information from university documents before generating an answer.

The system is designed around several important RAG and backend engineering principles:

- Permission-aware retrieval
- Document versioning
- Hybrid search
- Cross-encoder reranking
- Citation-based answers
- Explicit "I don't know" behavior
- Async API and database access
- Background document processing
- Redis-backed job tracking and rate limiting
- Automated testing
- RAG evaluation

The goal is not to build a basic "chat with PDF" application, but a more realistic backend system that considers retrieval quality, permissions, document freshness, and deployment constraints.

---

## Architecture

### Query Pipeline

```text
User
  |
  v
FastAPI
  |
  v
Authentication + RBAC
  |
  v
Query Service
  |
  v
Hybrid Retrieval
  |
  +--------------------------+
  |                          |
  v                          v
Vector Search          PostgreSQL FTS
(pgvector)             (keyword search)
  |                          |
  +------------+-------------+
               |
               v
        Combined Results
               |
               v
       Cross-Encoder Reranker
               |
               v
           Top-K Chunks
               |
               v
        Context Builder
               |
               v
              LLM
               |
               v
       Answer + Citations
```

### Document Ingestion Pipeline

```text
Document Upload
      |
      v
    Docling
      |
      v
Structured Markdown
      |
      v
Structure-Aware Chunking
      |
      v
Metadata Extraction
      |
      v
Embedding Generation
      |
      v
PostgreSQL + pgvector
```

---

## Key Features

### 1. Document Ingestion

The ingestion pipeline uses Docling to extract structured content from uploaded documents.

Supported formats include:

- PDF
- DOCX
- PPTX
- XLSX
- HTML
- Markdown
- TXT

Documents are converted into structured Markdown before they enter the chunking and embedding pipeline.

### 2. Structure-Aware Chunking

Documents are not simply split at arbitrary character boundaries.

The chunking pipeline attempts to preserve useful document structure such as:

- Sections
- Provisions
- Paragraphs
- Page numbers
- Section names

Chunks are also checked against the token limits required by the configured embedding model.

### 3. Document Versioning

Documents are treated as logical entities with multiple versions.

```text
UGC Regulations
|
+-- Version 1
|
+-- Version 2
|
+-- Version 3
```

The system stores:

- Document
- Document version
- Version number
- File name
- Source
- Content hash
- Publication date
- Effective dates
- Current version

Content hashes are used to detect whether a newly uploaded document is different from an existing version.

### 4. Metadata-Aware Retrieval

Chunks can contain:

- Academic year
- Department
- Access level
- Section
- Page number
- Document version

This metadata can be used for retrieval filtering and citation generation.

### 5. Role-Based Access Control

The application supports three roles:

```text
Student
Professor
Admin
```

Access hierarchy:

```text
Student
  |
  +-- Student documents

Professor
  |
  +-- Student documents
  +-- Professor documents

Admin
  |
  +-- Student documents
  +-- Professor documents
  +-- Admin documents
```

Retrieval is permission-aware so users do not receive documents that their role is not allowed to access.

### 6. Hybrid Search

The retrieval system combines semantic and keyword-based search.

#### Vector Search

pgvector is used to find semantically similar chunks.

#### PostgreSQL Full-Text Search

PostgreSQL Full-Text Search is useful for:

- Course codes
- Regulation numbers
- Section numbers
- Policy names
- Exact terminology
- Specific phrases

The vector and keyword result sets are combined before reranking.

### 7. Cross-Encoder Reranking

Initial retrieval produces a candidate set of potentially relevant chunks.

The reranker evaluates the relationship between the query and each candidate.

```text
Query + Candidate Chunk
          |
          v
    Cross-Encoder
          |
          v
    Relevance Score
```

The highest-ranked chunks are passed to the RAG context builder.

### 8. Citations

Generated answers include citation information for retrieved sources.

Citation metadata can include:

- Document title
- Document version
- Page number
- Section
- Chunk ID

The system validates citations against retrieved sources.

### 9. Hallucination Control

If relevant information cannot be retrieved, the service returns:

```text
I don't know based on the available university documents.
```

The goal is to make the assistant answer from the indexed university knowledge base rather than unrestricted model knowledge.

### 10. Redis Job Tracking

Document processing can be executed as a background job.

```text
queued
   |
   v
processing
   |
   v
completed
```

or:

```text
processing
   |
   v
failed
```

Redis stores the job state.

### 11. Rate Limiting

Redis-backed rate limiting is used for:

- Authentication
- Registration
- Document upload
- RAG queries

### 12. Automatic Admin Bootstrap

The application can create the initial administrator account during application startup using environment-based configuration.

Administrator credentials are not hard-coded into the source code.

---

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3.11 |
| API Framework | FastAPI |
| Package Management | uv |
| Database | PostgreSQL |
| Vector Search | pgvector |
| ORM | SQLAlchemy 2.x |
| Database Driver | asyncpg |
| Database Migrations | Alembic |
| Document Processing | Docling |
| Local Embeddings | sentence-transformers |
| Local Reranker | Cross-Encoder |
| Remote Embeddings | Cohere |
| Remote Reranker | Cohere |
| LLM | Groq / OpenAI-compatible API |
| Authentication | JWT |
| Password Hashing | pwdlib |
| Cache / Jobs / Rate Limiting | Redis |
| Testing | pytest |
| RAG Evaluation | Ragas |
| Containerization | Docker |
| Deployment | Render |
| Cloud Database | Neon PostgreSQL |
| Cloud Redis | Upstash Redis |

---

## Embedding Strategy

The project supports local and remote inference.

### Local Inference

```env
INFERENCE_MODE=local
```

Embedding model:

```text
sentence-transformers/all-MiniLM-L6-v2
```

Reranker:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

Local inference is intended primarily for local development and testing.

### Remote Inference

```env
INFERENCE_MODE=remote
```

The deployment configuration uses Cohere for embeddings and reranking.

Remote inference reduces the memory requirements of lightweight cloud environments.

The configured embedding model uses 384-dimensional vectors, matching the current `VECTOR(384)` database column.

---

## Database Design

The main document-related tables are:

```text
documents
     |
     v
document_versions
     |
     v
chunks
```

### Documents

The `documents` table represents the logical document.

### Document Versions

The `document_versions` table represents individual versions.

Important fields include:

- `document_id`
- `version_number`
- `file_name`
- `file_path`
- `extracted_file_path`
- `content_hash`
- `published_at`
- `effective_from`
- `effective_until`
- `is_current`

### Chunks

The `chunks` table stores searchable pieces of a document version.

```text
document_version_id
chunk_index
content
year
department
access_level
embedding
search_vector
section
page_number
created_at
```

---

## Project Structure

```text
campus-knowledge-assistant/
|
+-- main.py
|
+-- src/
|   |
|   +-- core/
|   |   +-- config.py
|   |   +-- database.py
|   |   +-- redis.py
|   |   +-- rate_limit.py
|   |
|   +-- documents/
|   |   +-- models.py
|   |
|   +-- chunks/
|   |   +-- models.py
|   |
|   +-- ingestion/
|   |   +-- parser.py
|   |   +-- chunker.py
|   |   +-- hash.py
|   |   +-- service.py
|   |
|   +-- embeddings/
|   |   +-- local.py
|   |   +-- remote.py
|   |   +-- service.py
|   |   +-- database.py
|   |
|   +-- retrieval/
|   |   +-- vector_search.py
|   |   +-- keyword_search.py
|   |   +-- hybrid_search.py
|   |   +-- reranker.py
|   |
|   +-- rag/
|   |   +-- context.py
|   |   +-- llm.py
|   |   +-- service.py
|   |   +-- schemas.py
|   |   +-- router.py
|   |
|   +-- auth/
|   |   +-- models.py
|   |   +-- schemas.py
|   |   +-- security.py
|   |   +-- jwt.py
|   |   +-- dependencies.py
|   |   +-- rbac.py
|   |   +-- service.py
|   |   +-- router.py
|   |   +-- bootstrap.py
|   |
|   +-- admin/
|   |   +-- router.py
|   |   +-- jobs.py
|   |   +-- schemas.py
|   |   +-- templates/
|   |       +-- dashboard.html
|   |
|   +-- models/
|       +-- registry.py
|       +-- __init__.py
|
+-- alembic/
+-- tests/
+-- scripts/
|
+-- data/
|   +-- documents/
|   +-- extracted/
|
+-- Dockerfile
+-- docker-compose.yml
+-- pyproject.toml
+-- uv.lock
+-- alembic.ini
+-- .env.example
+-- .gitignore
+-- README.md
```

---

# Local Development

## Prerequisites

Install:

- Python 3.11
- uv
- Docker
- Docker Compose
- Git

## Clone the Repository

```bash
git clone <https://github.com/fardeenchawhan/campus-knowledge-assistant.git>
cd campus-knowledge-assistant
```

## Install Dependencies

```bash
uv sync
```

## Configure Environment Variables

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Example configuration:

```env
POSTGRES_DB=campus_knowledge
POSTGRES_USER=campus_user
POSTGRES_PASSWORD=your_password

DATABASE_URL=postgresql+asyncpg://campus_user:your_password@localhost:5433/campus_knowledge

REDIS_URL=redis://localhost:6379/0

INFERENCE_MODE=local

GROQ_API_KEY=your_groq_api_key

JWT_SECRET_KEY=your_secret_key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

ADMIN_NAME=System Admin
ADMIN_EMAIL=admin@campus.local
ADMIN_PASSWORD=your_admin_password

DOCUMENT_UPLOAD_DIR=data/documents
DOCUMENT_EXTRACTED_DIR=data/extracted
MAX_UPLOAD_SIZE_MB=500
```

Never commit `.env` or API keys to Git.

---

# PostgreSQL and Redis

Start Docker services:

```bash
docker compose up -d
```

Check containers:

```bash
docker ps
```

## Enable pgvector

Connect to PostgreSQL and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify:

```sql
\dx
```

---

# Database Migrations

Run:

```bash
uv run alembic upgrade head
```

Check the current migration:

```bash
uv run alembic current
```

---

# Start the API

```bash
uv run uvicorn main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

ReDoc:

```text
http://127.0.0.1:8000/redoc
```

---

# Docker

Build:

```bash
docker compose build
```

Start:

```bash
docker compose up -d
```

View logs:

```bash
docker compose logs -f
```

Stop:

```bash
docker compose down
```

---

# Document Ingestion

The document ingestion process is:

```text
PDF / DOCX / PPTX / XLSX / HTML / Markdown / TXT
                        |
                        v
                     Docling
                        |
                        v
                Structured Markdown
                        |
                        v
                  Chunking
                        |
                        v
                   Metadata
                        |
                        v
                   Embeddings
                        |
                        v
             PostgreSQL + pgvector
```

The ingestion pipeline stores metadata including:

- Page number
- Section
- Academic year
- Department
- Access level
- Document version

---

# Query Flow

When a user asks a question:

```text
User Question
     |
     v
Authentication
     |
     v
Role Validation
     |
     v
Query Embedding
     |
     +-------------------+
     |                   |
     v                   v
Vector Search       Keyword Search
     |                   |
     +---------+---------+
               |
               v
        Hybrid Retrieval
               |
               v
        Candidate Chunks
               |
               v
            Reranker
               |
               v
          Top-K Chunks
               |
               v
        Context Builder
               |
               v
              LLM
               |
               v
       Answer + Citations
```

---

# Example Query

```text
What does the 2018 UGC regulation supersede?
```

The system:

1. Generates a query embedding.
2. Searches pgvector.
3. Searches PostgreSQL Full-Text Search.
4. Combines the results.
5. Reranks the candidates.
6. Selects the most relevant chunks.
7. Builds the context.
8. Sends the context and question to the LLM.
9. Validates generated citations.
10. Returns the final answer.

---

# Authentication

The API uses JWT-based authentication.

```text
Register / Login
      |
      v
Password Verification
      |
      v
JWT Access Token
      |
      v
Authenticated API Request
```

Protected endpoints require a valid access token.

---

# Role-Based Access

Supported roles:

```text
student
professor
admin
```

Permissions are enforced at the API and retrieval layers.

---

# Security

Security-related features include:

- JWT authentication
- Password hashing
- Role-Based Access Control
- Permission-aware retrieval
- Environment-based secrets
- Redis-backed rate limiting
- File type validation
- Upload size validation
- Document access levels
- Citation validation
- Content hashing

Never commit:

```text
.env
DATABASE_URL
GROQ_API_KEY
COHERE_API_KEY
JWT_SECRET_KEY
ADMIN_PASSWORD
POSTGRES_PASSWORD
```

---

# Testing

Run the complete test suite:

```bash
uv run pytest
```

The tests cover:

- Authentication
- Registration
- JWT
- RBAC
- Document ingestion
- Chunking
- Embeddings
- Vector search
- Keyword search
- Hybrid retrieval
- Reranking
- RAG
- Citations
- Admin functionality
- Rate limiting

---

# RAG Evaluation

Ragas was used to evaluate the RAG pipeline.

Evaluation focused on:

- Faithfulness
- Context Recall
- Answer Relevancy

Example evaluation questions:

```text
What does the 2018 UGC regulation supersede?

What are the minimum qualifications for appointment of an Assistant Professor?

What are the qualifications required for an Associate Professor?

What are the qualifications required for appointment of teachers?
```

The evaluation was used as an additional validation step alongside automated tests.

---

# Why Hybrid Retrieval?

University knowledge bases contain both natural-language concepts and exact terminology.

Vector search is useful for semantic similarity.

For example:

```text
"requirements to become an assistant professor"
```

can retrieve:

```text
"minimum qualifications for appointment of Assistant Professor"
```

Keyword search is useful for exact terms such as:

```text
UGC Regulation 2018
Section 3.7
API-101
```

Therefore:

```text
Semantic Search
      +
Keyword Search
      |
      v
Hybrid Retrieval
      |
      v
Reranking
```

---

# Why Reranking?

Initial retrieval is designed to be fast and broad.

The reranker performs a more focused relevance comparison.

```text
Query
  |
  v
Initial Retrieval
  |
  v
20-30 Candidate Chunks
  |
  v
Cross-Encoder
  |
  v
Top 5 Chunks
```

Only the most relevant chunks are passed into the final RAG context.

---

# Local vs Remote Inference

## Local

```text
FastAPI
   |
   +-- Local Embedding Model
   |
   +-- Local Reranker
   |
   +-- PostgreSQL
   |
   +-- Redis
   |
   +-- LLM API
```

This configuration is intended for local development.

## Remote

```text
FastAPI
   |
   +-- Cohere Embeddings
   |
   +-- Cohere Reranking
   |
   +-- Neon PostgreSQL
   |
   +-- Upstash Redis
   |
   +-- LLM API
```

This configuration reduces memory requirements on lightweight cloud instances.

---

# Deployment

The project was tested for cloud deployment using:

- Render
- Neon PostgreSQL
- Upstash Redis
- Cohere remote inference
- Groq LLM API

Architecture:

```text
                     Render
                       |
                       v
                FastAPI Application
                       |
            +----------+----------+
            |                     |
            v                     v
       Neon PostgreSQL       Upstash Redis
            |
            v
         pgvector

FastAPI
   |
   +-- Cohere Embeddings
   |
   +-- Cohere Reranking
   |
   +-- Groq LLM
```

---

# Deployment Status

## Current Status

The project has been prepared for cloud deployment and successfully tested with remote inference support.

The following components work in the deployed environment:

- FastAPI API
- Authentication
- JWT
- RBAC
- PostgreSQL
- Redis
- Remote embeddings
- Remote reranking
- RAG API functionality

However, the complete document-ingestion pipeline is **not currently supported on the Render Free web-service instance**.

## Known Limitation

Document ingestion uses Docling for PDF/document extraction.

Docling is a resource-intensive dependency.

During deployment testing, document processing caused the Render Free instance to become unhealthy because of the limited resources available to the service.

The Render health check timed out while document extraction was running, causing the instance to restart.

Therefore:

> Document upload and full document ingestion are not considered production-ready on the current Render Free deployment.

## Why Deployment Is Incomplete

This limitation is infrastructure-related rather than a failure of the RAG pipeline itself.

The complete ingestion pipeline works in the local development environment, including:

- Docling extraction
- Document versioning
- Structure-aware chunking
- Metadata extraction
- Embedding generation
- pgvector storage
- Hybrid retrieval
- Reranking
- RAG generation
- Citations

The problem is that the Render Free web-service instance does not provide sufficient resources to reliably perform the resource-intensive Docling extraction process while also satisfying the service health check.

A reliable cloud deployment would require a separate resource-appropriate worker or compute environment.

The project therefore documents this limitation rather than claiming that the complete ingestion pipeline is production-ready when it is not.

---

# Deployment Branch

Deployment-specific experimentation is maintained in:

```text
deployment-inference
```

The branch contains deployment-related changes including:

- Remote Cohere inference
- Render configuration
- CORS configuration
- Cloud database configuration
- Cloud Redis configuration
- Automatic admin bootstrap
- Deployment-specific optimizations
- Lazy loading of Docling

The deployment branch is intentionally kept separate from the canonical `main` branch.

---

# Branch Strategy

```text
main
|
+-- Canonical project
+-- Complete local ingestion pipeline
+-- Complete local RAG pipeline
+-- Tests
+-- Documentation


deployment-inference
|
+-- Deployment experiment
+-- Remote inference
+-- Render configuration
+-- Cloud-specific changes
```

The `main` branch represents the complete working project in the local development environment.

The `deployment-inference` branch represents the cloud deployment experiment.

The deployment branch should not be merged into `main` until a suitable resource environment is available for reliable document processing.

---

# Current Project Status

## Backend

- [✔️] FastAPI application
- [✔️] Async SQLAlchemy
- [✔️] PostgreSQL
- [✔️] pgvector
- [✔️] Alembic migrations
- [✔️] Redis integration
- [✔️] Docker support

## Document Processing

- [✔️] Docling extraction
- [✔️] Markdown conversion
- [✔️] Structure-aware chunking
- [✔️] Token-limit validation
- [✔️] Content hashing
- [✔️] Document versioning
- [✔️] Page metadata
- [✔️] Section metadata

## Retrieval

- [✔️] Vector search
- [✔️] PostgreSQL Full-Text Search
- [✔️] Hybrid retrieval
- [✔️] Cross-encoder reranking
- [✔️] Permission-aware retrieval

## RAG

- [✔️] Context construction
- [✔️] LLM integration
- [✔️] Citation generation
- [✔️] Citation validation
- [✔️] "I don't know" fallback
- [✔️] Redis caching

## Authentication and Security

- [✔️] User registration
- [✔️] JWT authentication
- [✔️] Password hashing
- [✔️] Student role
- [✔️] Professor role
- [✔️] Admin role
- [✔️] RBAC
- [✔️] Rate limiting
- [✔️] Automatic admin bootstrap

## Testing and Evaluation

- [✔️] pytest
- [✔️] pytest-asyncio
- [✔️] Authentication tests
- [✔️] Retrieval tests
- [✔️] RAG tests
- [✔️] Admin tests
- [✔️] Ragas evaluation

## Deployment

- [✔️] Docker deployment configuration
- [✔️] Render deployment eperiment
- [✔️] Neon PostgreSQL
- [✔️] Upstash Redis
- [✔️] Remote Cohere embeddings
- [✔️] Remote Cohere reranking
- [✔️] Automatic admin bootstrap
- [✔️] Deployment API
- [❌] Reliable cloud document ingestion on Render Free

---

# Future Improvements

Potential future improvements include:

- Dedicated document-processing workers
- Resource-appropriate cloud compute for Docling
- Object storage for uploaded documents
- Production-grade background job infrastructure
- Improved document metadata extraction
- Larger evaluation datasets
- Retrieval performance benchmarking
- Monitoring and observability
- Production deployment with dedicated worker infrastructure

---

# Project Goals

This project was built as a backend-focused portfolio project to demonstrate how a production-oriented RAG system can be designed beyond a basic "chat with PDF" application.

The main engineering problems addressed include:

- Asynchronous API design
- Relational database design
- Database migrations
- Vector search
- Full-text search
- Hybrid retrieval
- Cross-encoder reranking
- Authentication
- Authorization
- Permission-aware retrieval
- Document versioning
- Background processing
- Redis caching
- Rate limiting
- Testing
- RAG evaluation
- Containerization
- Cloud deployment
- Infrastructure limitations

The project also intentionally documents deployment limitations instead of hiding them behind an unreliable deployment.

---

# End-to-End Flow

A complete local document-to-answer flow looks like this:

```text
                     DOCUMENT INGESTION

University PDF
      |
      v
    Docling
      |
      v
Structured Markdown
      |
      v
Structure-Aware Chunking
      |
      v
Metadata
      |
      v
Embedding Generation
      |
      v
PostgreSQL + pgvector


                     USER QUERY

User Question
      |
      v
Authentication
      |
      v
RBAC
      |
      v
Query Embedding
      |
      +-------------------+
      |                   |
      v                   v
Vector Search       Keyword Search
      |                   |
      +---------+---------+
                |
                v
        Hybrid Retrieval
                |
                v
          Candidate Chunks
                |
                v
          Cross-Encoder
             Reranker
                |
                v
           Top-K Chunks
                |
                v
         Context Builder
                |
                v
                LLM
                |
                v
       Answer + Citations
```

---

# Conclusion

Campus Knowledge Assistant is a backend-focused RAG system designed around real-world concerns such as permissions, document versions, retrieval quality, citations, testing, and deployment constraints.

The project combines:

```text
FastAPI
   +
PostgreSQL
   +
pgvector
   +
Full-Text Search
   +
Hybrid Retrieval
   +
Reranking
   +
Document Processing
   +
Authentication
   +
RBAC
   +
Redis
   +
RAG
   +
Testing
   +
Docker
```

The complete system works locally, while the cloud deployment experiment identified a concrete infrastructure limitation around resource-intensive Docling document processing on the Render Free instance.

That limitation is documented explicitly so that the repository accurately represents the current state of the project.

---

# 👨‍💻 Author

**Fardeen Chavan**

GitHub:
https://github.com/fardeenchawhan

---

# ⭐ If you like this project

Consider giving it a ⭐ on GitHub!
