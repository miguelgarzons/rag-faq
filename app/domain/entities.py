from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str
    department_id: str
    user_id: str
    session_id: str | None = None

class AnswerResponse(BaseModel):
    answer: str
    sources: list[str] = []
    session_id: str

class UploadResponse(BaseModel):
    message: str
    chunks_processed: int
