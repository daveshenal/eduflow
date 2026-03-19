from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AZURE_OPENAI_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: str
    GPT4O_DEPLOYMENT: str

    AZURE_SEARCH_KEY: str
    AZURE_SEARCH_ENDPOINT: str
    EMBEDDING_DIMENSIONS: int
    MAX_CHUNK_SIZE: int
    CHUNK_OVERLAP: int
    INDEX_TOP_K: int
    MIN_SCORE: float
    
    AZURE_STORAGE_CONNECTION_STRING: str
    
    CLAUDE_API_KEY: str
    CLAUDE_MODEL_DOC: str
    CLAUDE_MODEL_CHATBOT: str
    MAX_TOKEN: int
    
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str
    
    AZURE_SPEECH_KEY: str
    AZURE_SPEECH_REGION: str

    class Config:
        # env_file = ".env"
        env_file = ".env.local"


settings = Settings()