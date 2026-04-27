from pydantic import BaseModel

class AskRequest(BaseModel):
    question: str
    department_id: str

class AnswerResponse(BaseModel):
    answer: str
    sources: list[str] = []

class UploadResponse(BaseModel):
    message: str
    chunks_processed: int