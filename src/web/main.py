"""FastAPI web application for AppTwitter."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import existing modules
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.db import Database
from src.generator import TweetGenerator
from src.linkedin_generator import LinkedInGenerator
from src.scheduler import TweetScheduler
from src.filters import TweetFilter
from src.voice import VoiceProfile
from src.ingest import ArticleImporter
from src.utils import setup_logging

logger = setup_logging()

# Pydantic models for request/response
class GenerateRequest(BaseModel):
    platform: str  # "twitter" or "linkedin"
    mix: Dict[str, int]  # e.g. {"promo": 3, "thought": 2}

class ArticleCreate(BaseModel):
    titulo: str
    url: str
    plataforma: str
    fecha_publicacion: str
    tags: Optional[str] = None
    resumen: Optional[str] = None

class CandidateUpdate(BaseModel):
    content: str

class ApproveRequest(BaseModel):
    approve: bool  # true to approve, false to skip

class RescheduleRequest(BaseModel):
    scheduled_at: str  # ISO format datetime

# Initialize FastAPI app
app = FastAPI(
    title="AppTwitter Web UI",
    description="Web interface for AppTwitter content automation",
    version="1.0.0"
)

# CORS middleware (localhost only)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and services
db = Database()
voice = VoiceProfile()
tweet_filter = TweetFilter(db=db, voice=voice)
tweet_generator = TweetGenerator(db=db, voice=voice, tweet_filter=tweet_filter)
linkedin_generator = LinkedInGenerator(db=db, voice=voice)
scheduler = TweetScheduler(db=db)
importer = ArticleImporter(db=db)

# Static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# API Routes

@app.get("/")
async def root():
    """Serve the main HTML page."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return JSONResponse({
            "message": "AppTwitter Web UI",
            "status": "Frontend not yet deployed"
        })

@app.get("/api/status")
async def get_status():
    """Get global application status."""
    try:
        # Count articles
        articles = db.fetchall("SELECT COUNT(*) as count FROM articulos")
        articles_count = articles[0]["count"] if articles else 0
        
        # Count candidates (drafted)
        candidates = db.fetchall(
            "SELECT COUNT(*) as count FROM tweet_queue WHERE status = 'drafted'"
        )
        candidates_count = candidates[0]["count"] if candidates else 0
        
        # Count scheduled
        scheduled = db.fetchall(
            "SELECT COUNT(*) as count FROM tweet_queue WHERE status = 'scheduled'"
        )
        scheduled_count = scheduled[0]["count"] if scheduled else 0
        
        # Next publication
        next_pub = db.fetchone(
            """
            SELECT scheduled_at 
            FROM tweet_queue 
            WHERE status = 'scheduled' 
            ORDER BY scheduled_at ASC 
            LIMIT 1
            """
        )
        next_publication = next_pub["scheduled_at"] if next_pub else None
        
        return {
            "success": True,
            "data": {
                "articles": articles_count,
                "candidates": candidates_count,
                "scheduled": scheduled_count,
                "next_publication": next_publication
            }
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/articles")
async def list_articles(limit: int = 50):
    """List imported articles."""
    try:
        articles = db.fetchall(
            """
            SELECT id, titulo, url, plataforma, fecha_publicacion, tags, resumen, created_at
            FROM articulos
            ORDER BY fecha_publicacion DESC
            LIMIT ?
            """,
            (limit,)
        )
        return {"success": True, "data": articles}
    except Exception as e:
        logger.error(f"Error listing articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/articles")
async def create_article(article: ArticleCreate):
    """Add a new article."""
    try:
        article_id = db.insert("articulos", {
            "titulo": article.titulo,
            "url": article.url,
            "plataforma": article.plataforma,
            "fecha_publicacion": article.fecha_publicacion,
            "tags": article.tags,
            "resumen": article.resumen
        })
        return {
            "success": True,
            "data": {"id": article_id},
            "message": "Artículo agregado exitosamente"
        }
    except Exception as e:
        logger.error(f"Error creating article: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate")
async def generate_content(request: GenerateRequest):
    """Generate tweets or LinkedIn posts."""
    try:
        if request.platform == "twitter":
            results = tweet_generator.generate_batch(request.mix)
        elif request.platform == "linkedin":
            results = linkedin_generator.generate_batch(request.mix)
        else:
            raise HTTPException(status_code=400, detail="Invalid platform")
        
        # Add generated candidates to queue with status "drafted"
        for candidate_id in results:
            scheduler.add_to_queue(candidate_id, status="drafted")
        
        logger.info(f"Generated {len(results)} candidates for {request.platform} and added to queue")
        
        return {
            "success": True,
            "data": {"generated": len(results)},
            "message": f"Generados {len(results)} candidatos para {request.platform}"
        }
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/candidates/{platform}")
async def list_candidates(platform: str, status: str = "drafted"):
    """List candidate tweets/posts."""
    try:
        # Get candidates with their metadata
        query = """
            SELECT 
                tc.id,
                tc.content,
                tc.tweet_type,
                tc.article_id,
                tc.metadata,
                tc.created_at,
                tq.id as queue_id,
                tq.status,
                a.titulo as article_title,
                a.url as article_url
            FROM tweet_candidates tc
            LEFT JOIN tweet_queue tq ON tc.id = tq.candidate_id
            LEFT JOIN articulos a ON tc.article_id = a.id
            WHERE tq.status = ?
            ORDER BY tc.created_at DESC
        """
        
        candidates = db.fetchall(query, (status,))
        
        # Parse metadata JSON and determine platform
        for candidate in candidates:
            # Determine platform from tweet_type
            if candidate.get("tweet_type", "").startswith("linkedin_"):
                candidate["platform"] = "linkedin"
            else:
                candidate["platform"] = "twitter"

            if candidate.get("metadata"):
                try:
                    candidate["metadata"] = json.loads(candidate["metadata"])
                except:
                    candidate["metadata"] = {}
        
        # Filter by platform using tweet_type prefix
        if platform in ["twitter", "linkedin"]:
            if platform == "linkedin":
                # LinkedIn posts have tweet_type starting with 'linkedin_'
                candidates = [c for c in candidates if c.get("tweet_type", "").startswith("linkedin_")]
            else:
                # Twitter posts don't have the 'linkedin_' prefix
                candidates = [c for c in candidates if not c.get("tweet_type", "").startswith("linkedin_")]
        
        return {"success": True, "data": candidates}
    except Exception as e:
        logger.error(f"Error listing candidates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/candidates/{candidate_id}")
async def get_candidate(candidate_id: int):
    """Get single candidate."""
    try:
        candidate = db.fetchone(
            """
            SELECT 
                tc.id,
                tc.content,
                tc.tweet_type,
                tc.article_id,
                tc.metadata,
                tc.created_at,
                tq.id as queue_id,
                tq.status,
                a.titulo as article_title,
                a.url as article_url
            FROM tweet_candidates tc
            LEFT JOIN tweet_queue tq ON tc.id = tq.candidate_id
            LEFT JOIN articulos a ON tc.article_id = a.id
            WHERE tc.id = ?
            """,
            (candidate_id,)
        )
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Parse metadata
        if candidate.get("metadata"):
            try:
                candidate["metadata"] = json.loads(candidate["metadata"])
            except:
                candidate["metadata"] = {}
        
        return {"success": True, "data": candidate}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/candidates/{candidate_id}")
async def update_candidate(candidate_id: int, update: CandidateUpdate):
    """Update candidate content."""
    try:
        # Update the content
        db.update(
            "tweet_candidates",
            {"content": update.content},
            "id = ?",
            (candidate_id,)
        )
        
        return {
            "success": True,
            "message": "Candidato actualizado exitosamente"
        }
    except Exception as e:
        logger.error(f"Error updating candidate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/candidates/{candidate_id}/approve")
async def approve_candidate(candidate_id: int, request: ApproveRequest):
    """Approve or skip a candidate."""
    try:
        # Get queue_id for this candidate
        queue_item = db.fetchone(
            "SELECT id FROM tweet_queue WHERE candidate_id = ?",
            (candidate_id,)
        )
        
        if not queue_item:
            raise HTTPException(status_code=404, detail="Queue item not found")
        
        queue_id = queue_item["id"]
        
        if request.approve:
            # Approve the tweet
            scheduler.approve_tweet(queue_id)
            
            # Automatically schedule all approved tweets
            # This assigns a date/time to the tweet and changes status to 'scheduled'
            scheduled_count = scheduler.schedule_approved_tweets()
            
            if scheduled_count > 0:
                message = f"Candidato aprobado y programado ({scheduled_count} post(s) programado(s))"
            else:
                message = "Candidato aprobado (no se pudo programar, verificá límites diarios)"
        else:
            scheduler.skip_tweet(queue_id)
            message = "Candidato omitido"
        
        return {
            "success": True,
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving/skipping candidate: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scheduled")
async def list_scheduled():
    """List all scheduled posts (Twitter + LinkedIn)."""
    try:
        scheduled = db.fetchall(
            """
            SELECT 
                tc.id as candidate_id,
                tc.content,
                tc.tweet_type,
                tc.metadata,
                tq.id as queue_id,
                tq.scheduled_at,
                a.titulo as article_title,
                a.url as article_url
            FROM tweet_queue tq
            JOIN tweet_candidates tc ON tq.candidate_id = tc.id
            LEFT JOIN articulos a ON tc.article_id = a.id
            WHERE tq.status = 'scheduled'
            ORDER BY tq.scheduled_at ASC
            """
        )
        
        # Parse metadata to determine platform
        for item in scheduled:
            # Determine platform from tweet_type (LinkedIn posts have 'linkedin_' prefix)
            if item.get("tweet_type", "").startswith("linkedin_"):
                item["platform"] = "linkedin"
            else:
                item["platform"] = "twitter"
            
            # Parse metadata JSON if present
            if item.get("metadata"):
                try:
                    item["metadata"] = json.loads(item["metadata"])
                except:
                    item["metadata"] = {}
            else:
                item["metadata"] = {}
        
        return {"success": True, "data": scheduled}
    except Exception as e:
        logger.error(f"Error listing scheduled: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/scheduled/{queue_id}/reschedule")
async def reschedule_post(queue_id: int, request: RescheduleRequest):
    """Reschedule a post."""
    try:
        db.update(
            "tweet_queue",
            {"scheduled_at": request.scheduled_at},
            "id = ?",
            (queue_id,)
        )
        
        return {
            "success": True,
            "message": "Post reprogramado exitosamente"
        }
    except Exception as e:
        logger.error(f"Error rescheduling post: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get global statistics."""
    try:
        # Total articles
        total_articles = db.fetchone(
            "SELECT COUNT(*) as count FROM articulos"
        )["count"]
        
        # Total candidates
        total_candidates = db.fetchone(
            "SELECT COUNT(*) as count FROM tweet_candidates"
        )["count"]
        
        # Total published
        total_published = db.fetchone(
            "SELECT COUNT(*) as count FROM tweets_publicados"
        )["count"]
        
        # Candidates by status
        by_status = db.fetchall(
            """
            SELECT status, COUNT(*) as count
            FROM tweet_queue
            GROUP BY status
            """
        )
        status_counts = {row["status"]: row["count"] for row in by_status}
        
        # Recent activity (last 7 days)
        recent = db.fetchall(
            """
            SELECT DATE(posted_at) as date, COUNT(*) as count
            FROM tweets_publicados
            WHERE posted_at >= date('now', '-7 days')
            GROUP BY DATE(posted_at)
            ORDER BY date ASC
            """
        )
        
        return {
            "success": True,
            "data": {
                "total_articles": total_articles,
                "total_candidates": total_candidates,
                "total_published": total_published,
                "by_status": status_counts,
                "recent_activity": recent
            }
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
