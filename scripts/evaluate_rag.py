import sys
from pathlib import Path
import os
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ragas.run_config import RunConfig
import asyncio
from src.auth.models import UserRole
from src.core.config import settings
from src.rag.context import build_context
from src.rag.llm import generate_answer
from src.retrieval.reranker import reranked_search
from sentence_transformers import SentenceTransformer
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ragas import SingleTurnSample
from ragas.llms import llm_factory
from ragas.embeddings import HuggingfaceEmbeddings
from ragas.metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextRecall,
)



EVALUATION_MODEL = "openai/gpt-oss-20b"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


EVALUATION_DATASET = [
    {
        "question": (
            "What does the 2018 UGC regulation supersede?"
        ),
        "reference": (
            "The 2018 UGC Regulations supersede the UGC Regulations "
            "on Minimum Qualifications for Appointment of Teachers and "
            "Other Academic Staff issued in 2010."
        ),
    },
    {
        "question": (
            "What are the minimum qualifications for appointment "
            "of an Assistant Professor?"
        ),
        "reference": (
            "The UGC Regulations, 2018 specify the minimum "
            "qualifications required for appointment as an "
            "Assistant Professor."
        ),
    },
    {
        "question": (
            "What are the qualifications required for an "
            "Associate Professor?"
        ),
        "reference": (
            "The UGC Regulations, 2018 specify the qualifications "
            "and experience requirements for appointment as an "
            "Associate Professor."
        ),
    },
    {
        "question": (
            "What are the qualifications required for appointment "
            "of teachers?"
        ),
        "reference": (
            "The UGC Regulations on Minimum Qualifications for "
            "Appointment of Teachers and Other Academic Staff, "
            "2018 specify the minimum qualifications required "
            "for appointment of teachers."
        ),
    },
]


async def build_evaluation_samples(
    db: AsyncSession,
) -> list[SingleTurnSample]:

    samples = []

    for item in EVALUATION_DATASET:
        question = item["question"]
        reference = item["reference"]

        print("\n" + "=" * 80)
        print(f"Question: {question}")

        results = await reranked_search(
            db=db,
            query=question,
            role=UserRole.STUDENT,
            top_k=5,
            candidate_k=30,
        )

        chunks = [chunk for chunk, _ in results]

        if not chunks:
            print("WARNING: No chunks retrieved.")
            continue

        context, _ = build_context(chunks)

        response = await generate_answer(
            question=question,
            context=context,
        )

        retrieved_contexts = [
            chunk.content
            for chunk in chunks
        ]

        sample = SingleTurnSample(
            user_input=question,
            retrieved_contexts=retrieved_contexts,
            response=response,
            reference=reference,
        )

        samples.append(sample)

        print(f"Retrieved chunks: {len(chunks)}")
        print(f"Answer:\n{response}")

    return samples

class RagasEmbeddingWrapper:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
        )
        return embedding.tolist()

    async def aembed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return await asyncio.to_thread(
            self.embed_documents,
            texts,
        )

    async def aembed_query(
        self,
        text: str,
    ) -> list[float]:
        return await asyncio.to_thread(
            self.embed_query,
            text,
        )


async def evaluate():
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as db:
            samples = await build_evaluation_samples(db)

        if not samples:
            print("\nNo evaluation samples were created.")
            return

        # Ragas evaluator LLM.
        #
        # This uses the same Groq OpenAI-compatible endpoint
        # as the production RAG application.
        os.environ["OPENAI_API_KEY"] = settings.GROQ_API_KEY

        evaluator_llm = llm_factory(
            model=EVALUATION_MODEL,
            base_url="https://api.groq.com/openai/v1",
            run_config=RunConfig(
                max_retries=3,
                timeout=120,
                max_wait=10,
            ),
        )

        # Ragas 0.3.1 wraps ChatOpenAI internally.
        # Configure the underlying LangChain model with a larger completion limit.
        evaluator_llm.langchain_llm.max_tokens = 4096

        evaluator_embeddings = RagasEmbeddingWrapper(
            EMBEDDING_MODEL,
        )

        faithfulness = Faithfulness(
            llm=evaluator_llm,
        )

        answer_relevancy = AnswerRelevancy(
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )

        context_recall = ContextRecall(
            llm=evaluator_llm,
        )

        faithfulness_scores = []
        answer_relevancy_scores = []
        context_recall_scores = []

        print("\n" + "=" * 80)
        print("RAGAS EVALUATION")
        print("=" * 80)

        for sample in samples:
            print(f"\nEvaluating: {sample.user_input}")

            try:
                faithfulness_score = (
                    await faithfulness.single_turn_ascore(sample)
                )
            except Exception as exc:
                print(f"  Faithfulness failed: {exc}")
                faithfulness_score = None

            try:
                context_recall_score = (
                    await context_recall.single_turn_ascore(sample)
                )
            except Exception as exc:
                print(f"  Context Recall failed: {exc}")
                context_recall_score = None

            try:
                answer_relevancy_score = (
                    await answer_relevancy.single_turn_ascore(sample)
                )
            except Exception as exc:
                print(f"  Answer Relevancy failed: {exc}")
                answer_relevancy_score = None

            if faithfulness_score is not None:
                faithfulness_scores.append(faithfulness_score)

            if context_recall_score is not None:
                context_recall_scores.append(context_recall_score)

            if answer_relevancy_score is not None:
                answer_relevancy_scores.append(answer_relevancy_score)

            print(
                f"  Faithfulness:     "
                f"{faithfulness_score:.4f}"
                if faithfulness_score is not None
                else "  Faithfulness:     FAILED"
            )

            print(
                f"  Context Recall:   "
                f"{context_recall_score:.4f}"
                if context_recall_score is not None
                else "  Context Recall:   FAILED"
            )

            print(
                f"  Answer Relevancy: "
                f"{answer_relevancy_score:.4f}"
                if answer_relevancy_score is not None
                else "  Answer Relevancy: FAILED"
            )

        print("\n" + "=" * 80)
        print("AVERAGE SCORES")
        print("=" * 80)

        if faithfulness_scores:
                print(
                    f"Faithfulness:     "
                    f"{sum(faithfulness_scores) / len(faithfulness_scores):.4f}"
                )

        if context_recall_scores:
            print(
                f"Context Recall:   "
                f"{sum(context_recall_scores) / len(context_recall_scores):.4f}"
            )

        if answer_relevancy_scores:
            print(
                f"Answer Relevancy: "
                f"{sum(answer_relevancy_scores) / len(answer_relevancy_scores):.4f}"
            )

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(evaluate())