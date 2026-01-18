"""Filtros de seguridad y detección de duplicados."""

import re
from typing import List, Optional

from rapidfuzz import fuzz

from .db import Database
from .utils import hash_text, normalize_text, setup_logging, count_chars
from .voice import VoiceProfile

logger = setup_logging()


class TweetFilter:
    """Filtros de seguridad y calidad para tweets."""
    
    def __init__(self, db: Database, voice: VoiceProfile):
        """Inicializar filtros."""
        self.db = db
        self.voice = voice
    
    def is_duplicate(self, text: str, threshold: float = 0.85) -> bool:
        """Verificar si el tweet es duplicado."""
        # Verificar por hash exacto
        text_hash = hash_text(text)
        existing = self.db.fetchone(
            "SELECT id FROM tweet_candidates WHERE content_hash = ?",
            (text_hash,)
        )
        
        if existing:
            logger.info(f"Tweet duplicado encontrado (hash exacto): {text[:50]}...")
            return True
        
        # Verificar similitud con tweets existentes
        normalized = normalize_text(text)
        
        # Obtener tweets recientes
        recent_tweets = self.db.fetchall(
            """
            SELECT content FROM tweet_candidates
            ORDER BY created_at DESC
            LIMIT 100
            """
        )
        
        for tweet in recent_tweets:
            existing_normalized = normalize_text(tweet["content"])
            similarity = fuzz.ratio(normalized, existing_normalized) / 100.0
            
            if similarity >= threshold:
                logger.info(f"Tweet similar encontrado (similitud: {similarity:.2f}): {text[:50]}...")
                return True
        
        return False
    
    def contains_forbidden_words(self, text: str) -> bool:
        """Verificar si el tweet contiene palabras prohibidas."""
        text_lower = text.lower()
        
        for word in self.voice.palabras_prohibidas:
            if word.lower() in text_lower:
                logger.warning(f"Palabra prohibida encontrada: {word}")
                return True
        
        return False
    
    def is_aggressive(self, text: str) -> bool:
        """Detectar lenguaje agresivo o personalista."""
        # Patrones de lenguaje agresivo
        aggressive_patterns = [
            r'\bestúpid[oa]s?\b',
            r'\bidiot[oa]s?\b',
            r'\bimbécil(es)?\b',
            r'\bpelotud[oa]s?\b',
            r'\bboludos?\b',
            r'\bpendej[oa]s?\b',
            r'\bataques?\b.*\bpersonal(es)?\b',
            r'\bvos\b.*\b(sos|eres)\b.*\b(un|una)\b',
        ]
        
        text_lower = text.lower()
        
        for pattern in aggressive_patterns:
            if re.search(pattern, text_lower):
                logger.warning(f"Lenguaje agresivo detectado: {pattern}")
                return True
        
        return False
    
    def is_misleading(self, text: str) -> bool:
        """Detectar instrucciones engañosas o problemáticas."""
        # Patrones de contenido engañoso
        misleading_patterns = [
            r'click\s+aqu[íi]',
            r'haz\s+click',
            r'sigue\s+este\s+enlace',
            r'garant[íi]a',
            r'100%\s+(seguro|efectivo|gratis)',
            r'(gana|gan[áa])\s+(dinero|plata)',
        ]
        
        text_lower = text.lower()
        
        for pattern in misleading_patterns:
            if re.search(pattern, text_lower):
                logger.warning(f"Contenido potencialmente engañoso detectado: {pattern}")
                return True
        
        return False
    
    def validate(self, text: str) -> tuple[bool, Optional[str]]:
        """Validar tweet con todos los filtros."""
        # Verificar duplicados
        if self.is_duplicate(text):
            return False, "Tweet duplicado o muy similar a uno existente"
        
        # Verificar palabras prohibidas
        if self.contains_forbidden_words(text):
            return False, "Contiene palabras prohibidas"
        
        # Verificar lenguaje agresivo
        if self.is_aggressive(text):
            return False, "Contiene lenguaje agresivo o personalista"
        
        # Verificar contenido engañoso
        if self.is_misleading(text):
            return False, "Contiene contenido potencialmente engañoso"
        
        # Verificar longitud
        # Verificar longitud usando lógica de Twitter (URLs = 23 chars)
        actual_length = count_chars(text)
        if actual_length > 280:
            return False, f"Excede longitud máxima (280 caracteres): {actual_length}"
        
        if len(text) < 10:
            return False, "Demasiado corto (mínimo 10 caracteres)"
        
        return True, None
    
    def filter_tweets(self, tweets: List[str]) -> List[tuple[str, bool, Optional[str]]]:
        """Filtrar lista de tweets."""
        results = []
        
        for tweet in tweets:
            is_valid, reason = self.validate(tweet)
            results.append((tweet, is_valid, reason))
        
        return results
    
    def get_duplicate_threshold(self) -> float:
        """Obtener umbral de similitud para duplicados."""
        # Puede ser configurable en el futuro
        return 0.85
