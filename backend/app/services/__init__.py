from app.services.azure_openai import (
    get_embedding,
    chat_completion,
    build_team_embedding_text,
)
from app.services.azure_di import (
    analyze_pdf,
    extract_tables,
    extract_page_text,
    get_low_confidence_pages,
)
from app.services.chat_service import answer_question
from app.services.ingestion_service import (
    run_ingestion,
    generate_embeddings_for_all_teams,
)