"""Planificación y gestión de cola de tweets."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .db import Database
from .utils import get_env_int, parse_datetime, setup_logging

logger = setup_logging()


class TweetScheduler:
    """Planificador de tweets."""
    
    def __init__(self, db: Database):
        """Inicializar planificador."""
        self.db = db
        
        # Configuración
        self.max_tweets_per_day = get_env_int("MAX_TWEETS_PER_DAY", 2)  # Default 2 (mañana y noche)
        
        # Slots fijos de publicación (hora argentina)
        import os
        self.morning_slot = os.getenv("POST_SLOT_MORNING", "09:00")
        self.evening_slot = os.getenv("POST_SLOT_EVENING", "21:00")
        
        # Construir lista de slots ordenados
        self.daily_slots = self._parse_slots()
    
    def _parse_slots(self) -> List[tuple]:
        """Parsear slots de horario a tuplas (hora, minuto)."""
        slots = []
        
        # Slot mañana
        h, m = map(int, self.morning_slot.split(":"))
        slots.append((h, m))
        
        # Slot noche
        h, m = map(int, self.evening_slot.split(":"))
        slots.append((h, m))
        
        # Ordenar por hora
        slots.sort()
        return slots
    
    def add_to_queue(self, candidate_id: int, status: str = "drafted") -> int:
        """Agregar tweet a la cola."""
        queue_item = {
            "candidate_id": candidate_id,
            "status": status,
        }
        
        queue_id = self.db.insert("tweet_queue", queue_item)
        logger.info(f"Tweet agregado a cola: {candidate_id} (cola ID: {queue_id})")
        
        return queue_id
    
    def approve_tweet(self, queue_id: int) -> bool:
        """Aprobar tweet para publicación."""
        updated = self.db.update(
            "tweet_queue",
            {"status": "approved", "updated_at": datetime.now().isoformat()},
            "id = ?",
            (queue_id,)
        )
        
        if updated:
            logger.info(f"Tweet aprobado: {queue_id}")
            return True
        
        return False
    
    def skip_tweet(self, queue_id: int) -> bool:
        """Omitir tweet."""
        updated = self.db.update(
            "tweet_queue",
            {"status": "skipped", "updated_at": datetime.now().isoformat()},
            "id = ?",
            (queue_id,)
        )
        
        if updated:
            logger.info(f"Tweet omitido: {queue_id}")
            return True
        
        return False
    
    def schedule_approved_tweets(self) -> int:
        """Planificar tweets aprobados usando slots fijos (mañana y noche)."""
        # Obtener tweets aprobados sin planificar
        approved = self.db.fetchall(
            """
            SELECT id, candidate_id 
            FROM tweet_queue 
            WHERE status = 'approved' AND scheduled_at IS NULL
            ORDER BY created_at ASC
            """
        )
        
        if not approved:
            logger.info("No hay tweets aprobados para planificar")
            return 0
        
        scheduled_count = 0
        current_time = datetime.now()
        
        # Obtener próximo slot disponible
        next_slot = self._get_next_available_slot(current_time)
        
        for tweet in approved:
            # Verificar límite diario
            if not self._can_schedule_on_day(next_slot):
                # Mover al siguiente día, primer slot
                next_slot = self._get_next_day_slot(next_slot)
            
            # Actualizar tweet con horario
            self.db.update(
                "tweet_queue",
                {
                    "scheduled_at": next_slot.isoformat(),
                    "status": "scheduled",
                    "updated_at": datetime.now().isoformat()
                },
                "id = ?",
                (tweet["id"],)
            )
            
            logger.info(f"Tweet planificado: {tweet['id']} para {next_slot}")
            scheduled_count += 1
            
            # Avanzar al siguiente slot
            next_slot = self._get_next_slot_after(next_slot)
        
        return scheduled_count
    
    def _get_next_slot_after(self, dt: datetime) -> datetime:
        """Obtener el siguiente slot después de una fecha dada."""
        current_slot_idx = self._get_slot_index(dt)
        
        if current_slot_idx < len(self.daily_slots) - 1:
            # Hay más slots hoy
            next_idx = current_slot_idx + 1
            h, m = self.daily_slots[next_idx]
            return dt.replace(hour=h, minute=m, second=0, microsecond=0)
        else:
            # Siguiente día, primer slot
            return self._get_next_day_slot(dt)
    
    def _get_slot_index(self, dt: datetime) -> int:
        """Obtener el índice del slot para una fecha dada."""
        for i, (h, m) in enumerate(self.daily_slots):
            if dt.hour == h and dt.minute == m:
                return i
        return -1
    
    def get_pending_tweets(self) -> List[Dict]:
        """Obtener tweets pendientes de publicación."""
        now = datetime.now()
        
        return self.db.fetchall(
            """
            SELECT q.id, q.candidate_id, q.scheduled_at, 
                   c.content, c.tweet_type, c.article_id,
                   a.url as article_url, a.titulo as article_title
            FROM tweet_queue q
            JOIN tweet_candidates c ON q.candidate_id = c.id
            LEFT JOIN articulos a ON c.article_id = a.id
            WHERE q.status = 'scheduled' 
            AND q.scheduled_at <= ?
            ORDER BY q.scheduled_at ASC
            """,
            (now.isoformat(),)
        )
    
    def mark_as_posted(self, queue_id: int, tweet_id: Optional[str] = None, response: Optional[str] = None) -> bool:
        """Marcar tweet como publicado."""
        # Actualizar cola
        self.db.update(
            "tweet_queue",
            {"status": "posted", "updated_at": datetime.now().isoformat()},
            "id = ?",
            (queue_id,)
        )
        
        # Obtener candidate_id
        queue_item = self.db.fetchone("SELECT candidate_id FROM tweet_queue WHERE id = ?", (queue_id,))
        
        if not queue_item:
            return False
        
        # Registrar en tweets_publicados
        self.db.insert("tweets_publicados", {
            "candidate_id": queue_item["candidate_id"],
            "tweet_id": tweet_id,
            "platform_response": response
        })
        
        logger.info(f"Tweet marcado como publicado: {queue_id}")
        return True
    
    def mark_as_failed(self, queue_id: int, error: str) -> bool:
        """Marcar tweet como fallido."""
        self.db.update(
            "tweet_queue",
            {"status": "failed", "updated_at": datetime.now().isoformat()},
            "id = ?",
            (queue_id,)
        )
        
        self.db.log("ERROR", f"Fallo al publicar tweet {queue_id}", error)
        logger.error(f"Tweet marcado como fallido: {queue_id} - {error}")
        
        return True
    
    def get_queue_stats(self) -> Dict:
        """Obtener estadísticas de la cola."""
        stats = {}
        
        # Por estado
        for status in ["drafted", "approved", "scheduled", "posted", "failed", "skipped"]:
            count = self.db.fetchone(
                "SELECT COUNT(*) as count FROM tweet_queue WHERE status = ?",
                (status,)
            )
            stats[status] = count["count"] if count else 0
        
        # Tweets publicados hoy
        today = datetime.now().date()
        posted_today = self.db.fetchone(
            """
            SELECT COUNT(*) as count 
            FROM tweets_publicados 
            WHERE DATE(posted_at) = ?
            """,
            (today.isoformat(),)
        )
        stats["posted_today"] = posted_today["count"] if posted_today else 0
        
        # Próximo tweet planificado
        next_scheduled = self.db.fetchone(
            """
            SELECT scheduled_at 
            FROM tweet_queue 
            WHERE status = 'scheduled' 
            ORDER BY scheduled_at ASC 
            LIMIT 1
            """
        )
        stats["next_scheduled"] = next_scheduled["scheduled_at"] if next_scheduled else None
        
        return stats
    
    def _get_next_available_slot(self, from_time: datetime) -> datetime:
        """Obtener próximo slot disponible basado en slots fijos."""
        # Buscar el próximo slot que sea después de from_time y no esté ocupado
        current_date = from_time.date()
        
        for _ in range(30):  # Buscar hasta 30 días adelante
            for h, m in self.daily_slots:
                slot = datetime(current_date.year, current_date.month, current_date.day, h, m, 0)
                
                # El slot debe ser en el futuro
                if slot <= from_time:
                    continue
                
                # Verificar que no hay otro tweet ya programado en este slot
                existing = self.db.fetchone(
                    """
                    SELECT COUNT(*) as count 
                    FROM tweet_queue 
                    WHERE scheduled_at = ? 
                    AND status IN ('scheduled', 'posted')
                    """,
                    (slot.isoformat(),)
                )
                
                if existing and existing["count"] > 0:
                    continue
                
                return slot
            
            # Pasar al siguiente día
            current_date = current_date + timedelta(days=1)
        
        # Fallback: devolver primer slot del día actual + 30 días
        h, m = self.daily_slots[0]
        return datetime(current_date.year, current_date.month, current_date.day, h, m, 0)
    
    def _can_schedule_on_day(self, dt: datetime) -> bool:
        """Verificar si se puede planificar en este día."""
        day = dt.date()
        
        count = self.db.fetchone(
            """
            SELECT COUNT(*) as count 
            FROM tweet_queue 
            WHERE DATE(scheduled_at) = ? 
            AND status IN ('scheduled', 'posted')
            """,
            (day.isoformat(),)
        )
        
        current_count = count["count"] if count else 0
        return current_count < self.max_tweets_per_day
    
    def _get_next_day_slot(self, dt: datetime) -> datetime:
        """Obtener primer slot del siguiente día."""
        next_day = dt + timedelta(days=1)
        h, m = self.daily_slots[0]  # Primer slot del día (mañana)
        return next_day.replace(hour=h, minute=m, second=0, microsecond=0)
    
    def list_queue(self, status: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Listar tweets en cola."""
        if status:
            return self.db.fetchall(
                """
                SELECT q.id, q.status, q.scheduled_at, q.created_at,
                       c.content, c.tweet_type
                FROM tweet_queue q
                JOIN tweet_candidates c ON q.candidate_id = c.id
                WHERE q.status = ?
                ORDER BY q.created_at DESC
                LIMIT ?
                """,
                (status, limit)
            )
        else:
            return self.db.fetchall(
                """
                SELECT q.id, q.status, q.scheduled_at, q.created_at,
                       c.content, c.tweet_type
                FROM tweet_queue q
                JOIN tweet_candidates c ON q.candidate_id = c.id
                ORDER BY q.created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
