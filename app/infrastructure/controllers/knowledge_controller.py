import io
import fitz  # PyMuPDF para PDFs
import docx  # python-docx para Word
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from app.domain.entities import UploadResponse
from app.application.upload_use_case import UploadDocumentUseCase
from app.dependencies import get_upload_use_case

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Cargar documento a la base de conocimiento",
    description=(
        "Carga un archivo .txt, .pdf o .docx para un departamento. "
        "El backend extrae texto, lo fragmenta, genera embeddings y guarda chunks en pgvector. "
        "Si detecta chunks repetidos para el mismo departamento, los omite."
    ),
    responses={
        200: {
            "description": "Documento procesado y almacenado correctamente",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Documento procesado correctamente",
                        "chunks_processed": 12,
                    }
                }
            },
        },
        400: {
            "description": "Formato no soportado o archivo sin texto legible",
        },
        500: {
            "description": "Error interno al extraer texto o procesar archivo",
        },
    },
)
async def upload_document(
    department_id: str = Form(..., description="ID del departamento. Ejemplo: rrhh"),
    file: UploadFile = File(..., description="Archivo .txt, .pdf o .docx"),
    use_case: UploadDocumentUseCase = Depends(get_upload_use_case)
):
    # Leemos los bytes del archivo en memoria
    content = await file.read()
    filename = file.filename.lower()
    text_content = ""
    
    try:
        # 1. Procesar archivo TXT
        if filename.endswith(".txt"):
            text_content = content.decode("utf-8")
        
        # 2. Procesar archivo PDF
        elif filename.endswith(".pdf"):
            pdf_document = fitz.open(stream=content, filetype="pdf")
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                text_content += page.get_text()
            pdf_document.close()
        
        # 3. Procesar archivo Word (DOCX)
        elif filename.endswith(".docx"):
            doc = docx.Document(io.BytesIO(content))
            text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        
        else:
            raise HTTPException(
                status_code=400, 
                detail="Formato no soportado. Por favor sube un archivo .txt, .pdf o .docx"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al extraer texto del archivo: {str(e)}")
    
    # Verificamos que el archivo realmente contuviera texto
    if not text_content.strip():
        raise HTTPException(
            status_code=400, 
            detail="El archivo está vacío o no se pudo extraer texto legible (ej. es un PDF de puras imágenes)."
        )
    
    # Pasamos el texto extraído al Caso de Uso
    return use_case.execute(text_content, department_id)
