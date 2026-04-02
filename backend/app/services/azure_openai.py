from openai import AzureOpenAI
from app.core.config import get_settings

settings = get_settings()

# Single client instance — reused across all requests
client = AzureOpenAI(
    azure_endpoint = settings.azure_openai_endpoint,
    api_key        = settings.azure_openai_key,
    api_version    = "2024-08-01-preview",
)


def get_embedding(text_input: str) -> list[float]:
    """
    Generate a vector embedding for a text string.
    Used at ingestion time and at chat query time.
    """
    response = client.embeddings.create(
        input = text_input,
        model = settings.azure_openai_embed_deployment,
    )
    return response.data[0].embedding


def chat_completion(
    messages   : list[dict],
    max_tokens : int = 500,
    temperature: float = 0.2,
) -> str:
    """
    Call GPT-4o-mini and return the response text.
    Low temperature = more factual, less creative.
    """
    response = client.chat.completions.create(
        model       = settings.azure_openai_chat_deployment,
        messages    = messages,
        max_tokens  = max_tokens,
        temperature = temperature,
    )
    return response.choices[0].message.content.strip()


def build_team_embedding_text(team_name: str, year: int, stat: dict) -> str:
    """
    Build a plain text summary of a team season stat row.
    This is what gets embedded — not the raw numbers.
    Good text = better semantic search results.
    """
    ats_pct = round(
        stat.get("ats_wins", 0) /
        max(stat.get("ats_wins", 0) + stat.get("ats_losses", 0), 1) * 100,
        1
    )
    return (
        f"{team_name} {year} season: "
        f"SU {stat.get('su_wins', 0)}-{stat.get('su_losses', 0)} | "
        f"ATS {stat.get('ats_wins', 0)}-{stat.get('ats_losses', 0)}-{stat.get('ats_pushes', 0)} ({ats_pct}%) | "
        f"O/U {stat.get('ou_overs', 0)}-{stat.get('ou_unders', 0)} | "
        f"Home fav ATS {stat.get('home_fav_ats_w', 0)}-{stat.get('home_fav_ats_l', 0)} | "
        f"Home dog ATS {stat.get('home_dog_ats_w', 0)}-{stat.get('home_dog_ats_l', 0)} | "
        f"Road fav ATS {stat.get('road_fav_ats_w', 0)}-{stat.get('road_fav_ats_l', 0)} | "
        f"Road dog ATS {stat.get('road_dog_ats_w', 0)}-{stat.get('road_dog_ats_l', 0)}"
    )