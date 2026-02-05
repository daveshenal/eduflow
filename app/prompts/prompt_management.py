from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
import aiomysql
from enum import Enum


VALID_PROMPT_NAMES = frozenset({
    "main_prompt",
    "developer_chatbot",
    "curr_planner",
    "pdf_generator",
    "voice_script",
})


class PromptNames(Enum):
    """Valid prompt names (5 allowed)."""
    MAIN_PROMPT = "main_prompt"
    DEVELOPER_CHATBOT = "developer_chatbot"
    CURR_PLANNER = "curr_planner"
    PDF_GENERATOR = "pdf_generator"
    VOICESCRIPT = "voice_script"


# Pydantic models for request/response
class PromptCreate(BaseModel):
    name: str = Field(..., max_length=100)
    version: str = Field(..., max_length=20)
    prompt: str
    description: Optional[str] = Field(None, max_length=255)


class PromptUpdate(BaseModel):
    prompt: Optional[str] = None
    description: Optional[str] = Field(None, max_length=255)


class PromptResponse(BaseModel):
    id: str
    name: str
    version: str
    prompt: str
    description: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActivatePromptRequest(BaseModel):
    name: str
    version: str


class AsyncPromptManager:
    """Single-table prompt manager. Prompts are differentiated by name (5 valid names)."""

    TABLE_NAME = "use_case_prompts"

    def _validate_name(self, name: str) -> bool:
        return name in VALID_PROMPT_NAMES

    async def create_prompt(self, prompt_data: PromptCreate, db_conn) -> PromptResponse:
        if prompt_data.name not in VALID_PROMPT_NAMES:
            raise ValueError(f"Invalid name '{prompt_data.name}'. Allowed: {sorted(VALID_PROMPT_NAMES)}")

        async with db_conn.cursor() as cur:
            await cur.execute(
                f"SELECT COUNT(*) FROM {self.TABLE_NAME} WHERE name=%s AND version=%s",
                (prompt_data.name, prompt_data.version)
            )
            if (await cur.fetchone())[0] > 0:
                raise ValueError(f"Prompt '{prompt_data.name}' version '{prompt_data.version}' already exists")

        prompt_id = str(uuid.uuid4())
        now = datetime.utcnow()

        async with db_conn.cursor() as cur:
            await cur.execute(
                f"INSERT INTO {self.TABLE_NAME} "
                "(id, name, version, prompt, description, status, created_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (prompt_id, prompt_data.name, prompt_data.version, prompt_data.prompt,
                 prompt_data.description, 'inactive', now, now)
            )

        return PromptResponse(
            id=prompt_id,
            name=prompt_data.name,
            version=prompt_data.version,
            prompt=prompt_data.prompt,
            description=prompt_data.description,
            status='inactive',
            created_at=now,
            updated_at=now
        )
    
    async def activate_prompt(self, name: str, version: str, db_conn) -> bool:
        """Activate a specific version and deactivate all others with the same name"""
        if not self._validate_name(name):
            raise ValueError(f"Invalid name '{name}'")
        
        async with db_conn.cursor() as cursor:
            # First, deactivate all versions of this prompt name
            await cursor.execute(
                f"UPDATE {self.TABLE_NAME} SET status = 'inactive' WHERE name = %s",
                (name,)
            )
            
            # Then activate the specific version
            await cursor.execute(
                f"UPDATE {self.TABLE_NAME} SET status = 'active' WHERE name = %s AND version = %s",
                (name, version)
            )
            
            if cursor.rowcount == 0:
                raise ValueError(f"Prompt '{name}' with version '{version}' not found")
        
        return True
    
    async def get_active_prompt(self, name: str, db_conn) -> Optional[PromptResponse]:
        """Get the active prompt by name"""
        if not self._validate_name(name):
            raise ValueError(f"Invalid name '{name}'")
        
        async with db_conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                f"SELECT * FROM {self.TABLE_NAME} WHERE name = %s AND status = 'active'",
                (name,)
            )
            row = await cursor.fetchone()
            if row:
                return PromptResponse(**row)
            return None
    
    async def get_all_versions(self, name: str, db_conn) -> List[PromptResponse]:
        """Get all versions of a prompt by name"""
        if not self._validate_name(name):
            raise ValueError(f"Invalid name '{name}'")
        
        async with db_conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                f"SELECT * FROM {self.TABLE_NAME} WHERE name = %s ORDER BY created_at DESC",
                (name,)
            )
            rows = await cursor.fetchall()
            return [PromptResponse(**row) for row in rows]
    
    async def get_all_prompts(self, skip: int = 0, limit: int = 100, db_conn=None) -> List[PromptResponse]:
        """Get all prompts in the table"""
        async with db_conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                f"SELECT * FROM {self.TABLE_NAME} ORDER BY name, version LIMIT %s OFFSET %s",
                (limit, skip)
            )
            rows = await cursor.fetchall()
            return [PromptResponse(**row) for row in rows]
    
    async def get_by_name_version(self, name: str, version: str, db_conn) -> Optional[PromptResponse]:
        """Get prompt by name and version"""
        if not self._validate_name(name):
            raise ValueError(f"Invalid name '{name}'")
        
        async with db_conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                f"SELECT * FROM {self.TABLE_NAME} WHERE name = %s AND version = %s",
                (name, version)
            )
            row = await cursor.fetchone()
            if row:
                return PromptResponse(**row)
            return None
    
    async def update_prompt(self, name: str, version: str, prompt_update: PromptUpdate, db_conn) -> Optional[PromptResponse]:
        """Update an existing prompt"""
        if not self._validate_name(name):
            raise ValueError(f"Invalid name '{name}'")
        
        update_fields = []
        values = []
        
        update_data = prompt_update.dict(exclude_unset=True)
        if 'prompt' in update_data:
            update_fields.append("prompt = %s")
            values.append(update_data['prompt'])
        if 'description' in update_data:
            update_fields.append("description = %s")
            values.append(update_data['description'])
        
        if not update_fields:
            return await self.get_by_name_version(name, version, db_conn)
        
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        values.extend([name, version])
        
        query = f"UPDATE {self.TABLE_NAME} SET {', '.join(update_fields)} WHERE name = %s AND version = %s"
        
        async with db_conn.cursor() as cursor:
            await cursor.execute(query, values)
            if cursor.rowcount == 0:
                raise ValueError(f"Prompt '{name}' with version '{version}' not found")
        
        return await self.get_by_name_version(name, version, db_conn)
    
    async def delete_prompt(self, name: str, version: str, db_conn) -> bool:
        """Delete a specific prompt version"""
        if not self._validate_name(name):
            raise ValueError(f"Invalid name '{name}'")
        
        async with db_conn.cursor() as cursor:
            await cursor.execute(
                f"DELETE FROM {self.TABLE_NAME} WHERE name = %s AND version = %s",
                (name, version)
            )
            return cursor.rowcount > 0

    async def get_all_active_prompts(self, db_conn) -> List[PromptResponse]:
        """Return all active prompts in this table."""
        async with db_conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                f"SELECT * FROM {self.TABLE_NAME} WHERE status = 'active' ORDER BY name"
            )
            rows = await cursor.fetchall()
            return [PromptResponse(**row) for row in rows]


def get_prompt_manager() -> AsyncPromptManager:
    return AsyncPromptManager()