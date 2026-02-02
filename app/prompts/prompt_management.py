from fastapi import HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
import aiomysql
from enum import Enum
from app.adapters.azure_sql import get_db_connection


class MainPromptNames(Enum):
    """Predefined names for base prompts"""
    MAIN_PROMPT = "main_prompt"


class UseCasePromptNames(Enum):
    """Predefined names for use case prompts"""
    DEVELOPER_CHATBOT = "developer_chatbot"
    EDUCATOR_CHATBOT = "educator_chatbot"
    HUDDLE_PLANNER = "huddle_planner"
    HUDDLE_GENERATOR = "huddle_generator"
    VOICESCRIPT = "voice_script"
    SCOPE_VALIDATION = "scope_validation"


class RolePromptNames(Enum):
    """Predefined names for role prompts"""
    FRONTLINE_STAFF = "frontline_staff"
    CLINICAL_MANAGER = "clinical_manager"
    EDUCATOR = "educator"
    DIRECTOR = "director"


class DisciplinePromptNames(Enum):
    """Predefined names for discipline prompts"""
    REGISTERED_NURSE = "registered_nurse"
    LICENSED_PRACTICAL_NURSE = "licensed_practical_nurse"
    PHYSICAL_THERAPIST = "physical_therapist"
    PHYSICAL_THERAPIST_ASSISTANT = "physical_therapist_assistant"
    OCCUPATIONAL_THERAPIST = "occupational_therapist"
    OCCUPATIONAL_THERAPIST_ASSISTANT = "occupational_therapist_assistant"
    SPEECH_LANGUAGE_PATHOLOGIST = "speech_language_pathologist"
    MEDICAL_SOCIAL_WORKER = "medical_social_worker"
    HOME_HEALTH_AIDE = "home_health_aide"


# Database schema (for reference)
TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS {table_name} (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    prompt TEXT NOT NULL,
    description VARCHAR(255),
    status VARCHAR(50) DEFAULT 'inactive',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_name_version (name, version)
);
"""


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
    """Async version of the prompt manager for API use"""
    
    def __init__(self, table_name: str, allowed_names: Enum):
        self.table_name = table_name
        self.allowed_names = allowed_names
        
    def _validate_name(self, name: str) -> bool:
        """Validate if the name is in allowed names"""
        allowed_values = [item.value for item in self.allowed_names]
        return name in allowed_values
    
    async def create_prompt(self, prompt_data: PromptCreate, db_conn) -> PromptResponse:
        """Create a new prompt"""
        if not self._validate_name(prompt_data.name):
            allowed_names = [item.value for item in self.allowed_names]
            raise ValueError(f"Invalid name '{prompt_data.name}'. Allowed names: {allowed_names}")
        
        # Check if prompt with same name and version already exists
        async with db_conn.cursor() as cursor:
            await cursor.execute(
                f"SELECT COUNT(*) FROM {self.table_name} WHERE name = %s AND version = %s",
                (prompt_data.name, prompt_data.version)
            )
            result = await cursor.fetchone()
            if result[0] > 0:
                raise ValueError(f"Prompt '{prompt_data.name}' with version '{prompt_data.version}' already exists")
        
        # Insert new prompt (inactive by default)
        prompt_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        query = f"""
        INSERT INTO {self.table_name} (id, name, version, prompt, description, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        async with db_conn.cursor() as cursor:
            await cursor.execute(query, (
                prompt_id, prompt_data.name, prompt_data.version, prompt_data.prompt, 
                prompt_data.description, 'inactive', now, now
            ))
        
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
                f"UPDATE {self.table_name} SET status = 'inactive' WHERE name = %s",
                (name,)
            )
            
            # Then activate the specific version
            await cursor.execute(
                f"UPDATE {self.table_name} SET status = 'active' WHERE name = %s AND version = %s",
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
                f"SELECT * FROM {self.table_name} WHERE name = %s AND status = 'active'",
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
                f"SELECT * FROM {self.table_name} WHERE name = %s ORDER BY created_at DESC",
                (name,)
            )
            rows = await cursor.fetchall()
            return [PromptResponse(**row) for row in rows]
    
    async def get_all_prompts(self, skip: int = 0, limit: int = 100, db_conn=None) -> List[PromptResponse]:
        """Get all prompts in the table"""
        async with db_conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                f"SELECT * FROM {self.table_name} ORDER BY name, version LIMIT %s OFFSET %s",
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
                f"SELECT * FROM {self.table_name} WHERE name = %s AND version = %s",
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
        
        query = f"UPDATE {self.table_name} SET {', '.join(update_fields)} WHERE name = %s AND version = %s"
        
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
                f"DELETE FROM {self.table_name} WHERE name = %s AND version = %s",
                (name, version)
            )
            print(f"Deletet: {name}, {version}")
            return cursor.rowcount > 0

    async def get_all_active_prompts(self, db_conn) -> List[PromptResponse]:
        """Return all active prompts in this table."""
        async with db_conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(
                f"SELECT * FROM {self.table_name} WHERE status = 'active' ORDER BY name"
            )
            rows = await cursor.fetchall()
            return [PromptResponse(**row) for row in rows]



# Initialize managers for each table
managers = {
    "main_prompts": AsyncPromptManager("main_prompts", MainPromptNames),
    "use_case_prompts": AsyncPromptManager("use_case_prompts", UseCasePromptNames),
    "role_prompts": AsyncPromptManager("role_prompts", RolePromptNames),
    "discipline_prompts": AsyncPromptManager("discipline_prompts", DisciplinePromptNames)
}


def get_manager(table_name: str) -> AsyncPromptManager:
    """Get the appropriate manager for the table"""
    if table_name not in managers:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
    return managers[table_name]