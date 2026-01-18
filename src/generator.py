"""Motor de generación de tweets."""

import json
import random
from typing import Dict, List, Optional

from .db import Database
from .filters import TweetFilter
from .llm_service import LLMClient
from .utils import hash_text, setup_logging, truncate_text, validate_tweet_length, fetch_article_content
from .voice import VoiceProfile

logger = setup_logging()


class TweetGenerator:
    """Generador de tweets."""
    
    TWEET_TYPES = ["promo", "thought", "question", "thread"]
    
    def __init__(self, db: Database, voice: VoiceProfile, tweet_filter: TweetFilter):
        """Inicializar generador."""
        self.db = db
        self.voice = voice
        self.filter = tweet_filter
        
        # Inicializar cliente LLM unificado
        self.llm_service = LLMClient(voice)
        self.llm_client = self.llm_service.client # Mantener compatibilidad de chequeo
    
    def generate(self, tweet_type: str, article_id: Optional[int] = None, count: int = 1) -> List[Dict]:
        """Generar tweets."""
        if tweet_type not in self.TWEET_TYPES:
            raise ValueError(f"Tipo de tweet inválido: {tweet_type}. Opciones: {self.TWEET_TYPES}")
        
        generated = []
        
        for _ in range(count):
            if self.llm_client:
                tweet = self._generate_with_llm(tweet_type, article_id)
            else:
                tweet = self._generate_with_template(tweet_type, article_id)
            
            if tweet:
                generated.append(tweet)
        
        return generated
    
    def _generate_with_llm(self, tweet_type: str, article_id: Optional[int] = None) -> Optional[Dict]:
        """Generar tweet usando LLM."""
        prompt = self._build_prompt(tweet_type, article_id)
        
        try:
            content = self.llm_service.generate(
                prompt=prompt,
                max_tokens=300,
                system_instruction="Eres un asistente que genera tweets en español siguiendo un perfil de voz específico."
            )
            
            if not content:
                return None
            
            # Limpiar contenido (remover comillas si las hay)
            content = content.strip('"').strip("'")
            
            # Validar longitud
            actual_length = count_chars(content)
            if not validate_tweet_length(content):
                logger.warning(f"Tweet generado excede longitud real: {actual_length} caracteres")
                content = truncate_text(content, 280)
            
            # Crear tweet
            tweet = {
                "content": content,
                "content_hash": hash_text(content),
                "tweet_type": tweet_type,
                "article_id": article_id,
                "metadata": json.dumps({"generator": "llm", "provider": self.llm_service.get_provider_name()})
            }
            
            # Validar con filtros
            is_valid, reason = self.filter.validate(content)
            if not is_valid:
                logger.warning(f"Tweet generado no pasó validación: {reason}")
                return None
            
            return tweet
            
        except Exception as e:
            logger.error(f"Error generando tweet con LLM: {e}")
            return None
    
    def _generate_with_template(self, tweet_type: str, article_id: Optional[int] = None) -> Optional[Dict]:
        """Generar tweet usando plantillas."""
        if tweet_type == "promo" and article_id:
            content = self._generate_promo_template(article_id)
        elif tweet_type == "thought":
            content = self._generate_thought_template()
        elif tweet_type == "question":
            content = self._generate_question_template()
        elif tweet_type == "thread":
            content = self._generate_thread_template(article_id)
        else:
            logger.warning(f"No se puede generar tipo {tweet_type} sin artículo")
            return None
        
        if not content:
            return None
        
        # Validar longitud
        if not validate_tweet_length(content):
            logger.warning(f"Tweet generado excede longitud: {len(content)} caracteres")
            content = truncate_text(content, 280)
        
        # Crear tweet
        tweet = {
            "content": content,
            "content_hash": hash_text(content),
            "tweet_type": tweet_type,
            "article_id": article_id,
            "metadata": json.dumps({"generator": "template"})
        }
        
        # Validar con filtros
        is_valid, reason = self.filter.validate(content)
        if not is_valid:
            logger.warning(f"Tweet generado no pasó validación: {reason}")
            return None
        
        return tweet
    
    def _generate_promo_template(self, article_id: int) -> Optional[str]:
        """Generar tweet de promoción de artículo."""
        article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
        
        if not article:
            logger.error(f"Artículo no encontrado: {article_id}")
            return None
        
        templates = [
            f"Nuevo artículo: {article['titulo']}\n\n{article['resumen']}\n\n{article['url']}",
            f"{article['titulo']}\n\n{article['resumen']}\n\nLeer más: {article['url']}",
            f"Reflexión sobre {article['tags'].split(',')[0] if article['tags'] else 'este tema'}:\n\n{article['titulo']}\n\n{article['url']}",
        ]
        
        return random.choice(templates)
    
    def _generate_thought_template(self) -> str:
        """Generar tweet de pensamiento."""
        # Usar ejemplos del perfil de voz
        if self.voice.ejemplos:
            # Variación de un ejemplo existente
            base = random.choice(self.voice.ejemplos)
            return base
        
        # Plantillas genéricas basadas en temas
        temas = self.voice.temas
        if temas:
            tema = random.choice(temas)
            templates = [
                f"La {tema} no es solo teoría: es una forma de mirar el mundo.",
                f"Pensar la {tema} hoy exige cuestionar las categorías heredadas.",
                f"La pregunta por la {tema} es también una pregunta por nosotros mismos.",
            ]
            return random.choice(templates)
        
        return "Pensar es cuestionar lo dado, no repetir lo sabido."
    
    def _generate_question_template(self) -> str:
        """Generar tweet con pregunta."""
        temas = self.voice.temas
        if temas:
            tema = random.choice(temas)
            templates = [
                f"¿Qué significa realmente hablar de {tema} hoy?",
                f"¿Cómo pensamos la {tema} sin caer en el moralismo?",
                f"¿Qué condiciones hacen posible nuestra comprensión de la {tema}?",
            ]
            return random.choice(templates)
        
        return "¿Qué significa pensar en lugar de repetir?"
    
    def _generate_thread_template(self, article_id: Optional[int] = None) -> str:
        """Generar primer tweet de un hilo."""
        if article_id:
            article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
            if article:
                return f"🧵 Hilo sobre {article['titulo']}\n\n1/ {article['resumen'][:200]}..."
        
        tema = random.choice(self.voice.temas) if self.voice.temas else "este tema"
        return f"🧵 Algunas reflexiones sobre {tema}\n\n1/ Empecemos por cuestionar las categorías que damos por sentadas..."
    
    def _build_prompt(self, tweet_type: str, article_id: Optional[int] = None) -> str:
        """Construir prompt para LLM."""
        prompt_parts = [
            "INSTRUCCIONES:",
            "1. Analiza cuidadosamente el perfil de voz proporcionado.",
            "2. Piensa en cómo el autor abordaría el tema (tono, vocabulario, estructura).",
            "3. Genera un tweet que parezca escrito por este autor, no por una IA.",
            "",
            "PERFIL DE VOZ:",
            self.voice.to_prompt(),
            "",
        ]
        
        if tweet_type == "promo" and article_id:
            article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
            if article:
                # Intentar obtener contenido completo
                if article.get('url'):
                    try:
                        logger.info(f"Obteniendo contenido de: {article['url']}")
                        content_data = fetch_article_content(article['url'])
                        
                        if content_data:
                            # Usar contenido completo (truncado si es muy largo)
                            full_text = content_data.get("text", "")
                            if len(full_text) > 10000:
                                full_text = full_text[:10000] + "..."
                            
                            prompt_parts.append(f"CONTENIDO DEL ARTÍCULO:\n{full_text}")
                        else:
                            # Fallback a resumen
                            prompt_parts.append(f"RESUMEN DEL ARTÍCULO:\n{article['resumen']}")
                    except Exception as e:
                        logger.warning(f"No se pudo obtener contenido del artículo: {e}")
                        prompt_parts.append(f"RESUMEN DEL ARTÍCULO:\n{article['resumen']}")
                else:
                    prompt_parts.append(f"RESUMEN DEL ARTÍCULO:\n{article['resumen']}")
                
                prompt_parts.extend([
                    "TAREA: Escribe un tweet promocionando este artículo.",
                    f"TÍTULO: {article['titulo']}",
                    f"URL: {article['url']}",
                    "",
                    "REGLAS:",
                    "- Presente el artículo de forma atractiva pero intelectualmente honesta.",
                    "- Extrae una idea provocadora o central del texto.",
                    "- NO uses lenguaje de marketing ('descubre', 'imperdible', 'haz click').",
                    "- Incluye el enlace al final.",
                    "- Importante: El enlace cuenta como 23 caracteres. El total NO debe exceder los 280 caracteres.",
                ])
        
        elif tweet_type == "thought":
            prompt_parts.extend([
                "TAREA: Escribe un tweet de pensamiento/reflexión.",
                "",
                "REGLAS:",
                "- Exprese una tesis o reflexión breve y potente.",
                "- Sea conceptualmente denso pero claro.",
                "- Evita lugares comunes.",
                "- No incluyas enlaces.",
                "- No exceda 280 caracteres.",
            ])
        
        elif tweet_type == "question":
            prompt_parts.extend([
                "TAREA: Escribe un tweet que plantee una pregunta.",
                "",
                "REGLAS:",
                "- Plantea una pregunta filosófica o conceptual genuina.",
                "- Invita a pensar, no solo a responder sí/no.",
                "- No seas retórico ni obvio.",
                "- No exceda 280 caracteres.",
            ])
        
        elif tweet_type == "thread":
            prompt_parts.extend([
                "TAREA: Escribe el PRIMER tweet de un hilo.",
                "",
                "REGLAS:",
                "- Introduce un tema complejo de forma interesante.",
                "- Indica claramente que es un hilo (usa 🧵 o '1/').",
                "- Genera curiosidad intelectual.",
                "- No exceda 280 caracteres.",
            ])
        
        prompt_parts.append("\nGenera SOLO el texto del tweet, sin comillas, preámbulos ni explicaciones.")
        
        return "\n".join(prompt_parts)
    
    def save_tweet(self, tweet: Dict) -> int:
        """Guardar tweet candidato en base de datos."""
        return self.db.insert("tweet_candidates", tweet)
    
    def generate_batch(self, mix: Dict[str, int]) -> List[int]:
        """Generar lote de tweets según mix especificado."""
        tweet_ids = []
        
        # Obtener artículos disponibles para promoción
        articles = self.db.fetchall(
            """
            SELECT id FROM articulos
            WHERE id NOT IN (
                SELECT DISTINCT article_id 
                FROM tweet_candidates 
                WHERE article_id IS NOT NULL
            )
            ORDER BY fecha_publicacion DESC
            """
        )
        
        article_pool = [a["id"] for a in articles]
        
        for tweet_type, count in mix.items():
            for i in range(count):
                # Para promos, usar artículos disponibles
                article_id = None
                if tweet_type == "promo" and article_pool:
                    article_id = article_pool[i % len(article_pool)]
                
                tweet = self.generate(tweet_type, article_id, count=1)
                
                if tweet:
                    tweet_id = self.save_tweet(tweet[0])
                    tweet_ids.append(tweet_id)
                    logger.info(f"Tweet generado y guardado: {tweet_type} (ID: {tweet_id})")
        
        return tweet_ids

