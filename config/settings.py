from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AZURE_OPENAI_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str
    
    AZURE_SEARCH_ENDPOINT: str
    AZURE_SEARCH_KEY: str
    AZURE_GLOBAL_INDEX_NAME: str
    EMBEDDING_DIMENSIONS: int
    MAX_CHUNK_SIZE: int
    CHUNK_OVERLAP: int
    GLOBAL_INDEX_TOP_K: int
    PROVIDER_INDEX_TOP_K: int
    MIN_SCORE: float
    MAX_TOKEN: int
    
    AZURE_STORAGE_CONNECTION_STRING: str
    AZURE_GLOBAL_CONTAINER_NAME: str
    
    CLAUDE_API_KEY: str
    CLAUDE_MODEL_HUDDLE: str
    CLAUDE_MODEL_CHATBOT: str
    
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str
    
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str

    class Config:
        env_file = ".env"

settings = Settings()