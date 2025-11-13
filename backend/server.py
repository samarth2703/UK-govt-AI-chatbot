from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage
from langdetect import detect
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Emergent LLM Key
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# Knowledge Base from PDF
KNOWLEDGE_BASE = """
Uttarakhand Government Services - Complete Information:

1. DIGITAL SERVICES & SIGNATURES:
   - Digital Signature Certificate (DSC): Digital equivalent of physical certificate for electronic signatures
   - Aadhaar-based eSign: Secure document signing using Aadhaar authentication
   - emBridge Signer: Digital signing tool with hardware tokens/smart cards

2. PENSIONER SERVICES:
   - Life Certificate Submission: Available physically at treasury offices or digitally via mobile app/CSC centers
   - Eligibility: All government pensioners drawing pension through state treasury system

3. DISTRICT PORTAL SERVICES:
   - Haridwar Portal (haridwar.nic.in): Single-point access to district department services
   - Objective: Provide information and services of all district departments

4. ePROCUREMENT & TENDER SERVICES:
   - Portal: uktenders.gov.in
   - Services: Electronic tendering and procurement for all government departments
   - Access: All current tenders and notices available online

5. JUDICIAL SERVICES:
   - High Court Portal (highcourtofuttarakhand.gov.in)
   - Services: Case status, judgments, orders, cause lists, e-filing facilities

6. GENERAL PROVIDENT FUND (GPF):
   - Scheme: Savings scheme for government employees
   - Features: Monthly contributions accumulated with interest

7. ONLINE CITIZEN SERVICES:
   - Char Dham Yatra Registration: Free tourist registration (no fee)
   - Hemkund Sahib Yatra: Free tourist registration
   - Birth/Death Certificates: Available online
   - Property Tax: Online payment facility

8. BIOMETRIC ATTENDANCE SYSTEM (BAS):
   - Uses: Aadhaar-based authentication (mandatory)
   - Purpose: Employee attendance monitoring with unique IDs

9. HELP & CONTACT:
   - District e-governance centers for assistance
   - Official helplines on department websites

10. OFFICIAL PORTALS:
    - Main Portal: https://uk.gov.in
    - eTreasury: https://ekosh.uk.gov.in
    - eProcurement: https://uktenders.gov.in
    - Haridwar District: https://haridwar.nic.in
    - High Court: https://highcourtofuttarakhand.gov.in

KEY HIGHLIGHTS:
- Most services available online and offline
- Aadhaar integration for secure authentication
- No fee for Char Dham and Hemkund Sahib Yatra registration
- Single window access through district portals
- e-Governance centers available for citizen support
"""

# Models
class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    message: str
    response: str
    language: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatRequest(BaseModel):
    session_id: str
    message: str
    language: Optional[str] = "auto"

class ChatResponse(BaseModel):
    response: str
    detected_language: str

# Initialize LLM Chat with system message
async def get_llm_chat(session_id: str):
    system_message = f"""You are Apni Sarkar Bot, an AI assistant for Uttarakhand Government Services. 
    You help citizens with information about government services in English and Hindi.
    
    Use this knowledge base to answer questions:
    {KNOWLEDGE_BASE}
    
    Guidelines:
    - Be helpful, polite, and concise
    - Answer in the same language as the user's question
    - If asked in Hindi, respond in Hindi
    - If asked in English, respond in English
    - Provide specific information from the knowledge base
    - Include relevant portal links when applicable
    - If information is not in knowledge base, politely say you don't have that information
    """
    
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_message
    )
    chat.with_model("openai", "gpt-5")
    return chat

# Detect language
def detect_language(text: str) -> str:
    try:
        lang = detect(text)
        return "hindi" if lang == "hi" else "english"
    except:
        return "english"

@api_router.get("/")
async def root():
    return {"message": "Apni Sarkar Bot API is running"}

@api_router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Detect language
        detected_language = detect_language(request.message)
        
        # Get LLM chat instance
        chat = await get_llm_chat(request.session_id)
        
        # Create user message
        user_message = UserMessage(text=request.message)
        
        # Get response from LLM
        response = await chat.send_message(user_message)
        
        # Save to database
        chat_doc = ChatMessage(
            session_id=request.session_id,
            message=request.message,
            response=response,
            language=detected_language
        )
        
        doc = chat_doc.model_dump()
        doc['timestamp'] = doc['timestamp'].isoformat()
        await db.chat_history.insert_one(doc)
        
        return ChatResponse(
            response=response,
            detected_language=detected_language
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/chat/history/{session_id}", response_model=List[ChatMessage])
async def get_chat_history(session_id: str):
    try:
        messages = await db.chat_history.find(
            {"session_id": session_id},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(100)
        
        # Convert ISO string timestamps back to datetime objects
        for msg in messages:
            if isinstance(msg['timestamp'], str):
                msg['timestamp'] = datetime.fromisoformat(msg['timestamp'])
        
        return messages
    except Exception as e:
        logger.error(f"History fetch error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/chat/session/{session_id}")
async def clear_session(session_id: str):
    try:
        result = await db.chat_history.delete_many({"session_id": session_id})
        return {"deleted_count": result.deleted_count}
    except Exception as e:
        logger.error(f"Clear session error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()