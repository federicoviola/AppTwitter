"""Motor de generación de posts para LinkedIn."""

import json
import random
from typing import Dict, List, Optional

from .db import Database
from .llm_service import LLMClient
from .utils import hash_text, setup_logging, fetch_article_content
from .voice import VoiceProfile

logger = setup_logging()


class LinkedInGenerator:
    """Generador de posts para LinkedIn."""
    
    POST_TYPES = ["promo", "thought", "question", "insight"]
    MAX_LENGTH = 3000  # LinkedIn permite hasta 3000 caracteres
    
    def __init__(self, db: Database, voice: VoiceProfile):
        """Inicializar generador."""
        self.db = db
        self.voice = voice
        
        # Inicializar cliente LLM unificado
        self.llm_service = LLMClient(voice)
        self.llm_client = self.llm_service.client # Mantener compatibilidad
        
    def generate(self, post_type: str, article_id: Optional[int] = None, count: int = 1) -> List[Dict]:
        """Generar posts de LinkedIn."""
        if post_type not in self.POST_TYPES:
            raise ValueError(f"Tipo de post inválido: {post_type}. Opciones: {self.POST_TYPES}")
        
        generated = []
        
        for _ in range(count):
            if self.llm_client:
                post = self._generate_with_llm(post_type, article_id)
            else:
                post = self._generate_with_template(post_type, article_id)
            
            if post:
                generated.append(post)
        
        return generated
    
    def _generate_with_llm(self, post_type: str, article_id: Optional[int] = None) -> Optional[Dict]:
        """Generar post usando LLM."""
        prompt = self._build_prompt(post_type, article_id)
        
        try:
            content = self.llm_service.generate(
                prompt=prompt,
                max_tokens=1000,
                system_instruction="Eres un asistente que genera posts profesionales para LinkedIn en español."
            )
            
            if not content:
                return None
            
            # Limpiar contenido
            content = content.strip('"').strip("'")
            
            # Validar longitud
            if len(content) > self.MAX_LENGTH:
                logger.warning(f"Post generado excede longitud: {len(content)} caracteres")
                content = content[:self.MAX_LENGTH - 3] + "..."
            
            # Obtener artículo si hay
            article_url = None
            article_title = None
            article_image_url = None
            
            if article_id:
                article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
                if article:
                    article_url = article.get("url")
                    article_title = article.get("titulo")
                    
                    # Si ya hemos obtenido el contenido en _build_prompt, idealmente deberíamos reusarlo.
                    # Pero _build_prompt devuelve un string.
                    # Para simplificar y evitar doble fetch, podríamos confiar en que fetch_article_content cachea/es rápido,
                    # O (mejor) hacer el fetch aquí si no lo hicimos antes, PERO _build_prompt se llama antes.
                    # MALA ARQUITECTURA: _build_prompt hace el fetch pero no devuelve la metadata.
                    # FIX: Vamos a hacer un fetch rápido aquí para obtener la imagen, asumiendo que el contenido ya fue usado.
                    # O mejor: mover la lógica de fetch AQUÍ y pasar el contenido a _build_prompt?
                    # Por ahora, para no romper todo, hacemos fetch aquí de nuevo.
                    if article_url:
                        try:
                           content_data = fetch_article_content(article_url)
                           if content_data:
                               article_image_url = content_data.get("image_url")
                        except:
                            pass
            
            # Crear post
            post = {
                "content": content,
                "content_hash": hash_text(content),
                "post_type": post_type,
                "article_id": article_id,
                "article_url": article_url,
                "article_title": article_title,
                "article_image_url": article_image_url,
                "metadata": json.dumps({"generator": "llm", "provider": self.llm_service.get_provider_name()})
            }
            
            return post
            
        except Exception as e:
            logger.error(f"Error generando post de LinkedIn con LLM: {e}")
            return None
    
    def _generate_with_template(self, post_type: str, article_id: Optional[int] = None) -> Optional[Dict]:
        """Generar post usando plantillas."""
        if post_type == "promo" and article_id:
            content, article_url, article_title = self._generate_promo_template(article_id)
        elif post_type == "thought":
            content = self._generate_thought_template()
            article_url = None
            article_title = None
        elif post_type == "question":
            content = self._generate_question_template()
            article_url = None
            article_title = None
        elif post_type == "insight":
            content = self._generate_insight_template()
            article_url = None
            article_title = None
        else:
            logger.warning(f"No se puede generar tipo {post_type} sin artículo")
            return None
        
        if not content:
            return None
        
        post = {
            "content": content,
            "content_hash": hash_text(content),
            "post_type": post_type,
            "article_id": article_id,
            "article_url": article_url,
            "article_title": article_title,
            "metadata": json.dumps({"generator": "template"})
        }
        
        return post
    
    def _generate_promo_template(self, article_id: int) -> tuple:
        """Generar post de promoción de artículo."""
        article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
        
        if not article:
            logger.error(f"Artículo no encontrado: {article_id}")
            return None, None, None
        
        content = f"""🔵 Nuevo artículo publicado

{article['titulo']}

{article['resumen']}

En este artículo exploro algunas ideas que me parecen fundamentales para entender {article['tags'].split(',')[0] if article.get('tags') else 'este tema'}.

Me encantaría conocer tu perspectiva. ¿Qué pensás?

👉 Link en comentarios

#Reflexiones #Pensamiento"""
        
        return content, article.get("url"), article.get("titulo")
    
    def _generate_thought_template(self) -> str:
        """Generar post de pensamiento."""
        temas = self.voice.temas
        if temas:
            tema = random.choice(temas)
            return f"""Una reflexión sobre {tema}:

A veces me pregunto si no estamos confundiendo la profundidad con la complejidad.

Pensar bien no es acumular capas de abstracción.
Es llegar al núcleo de las cosas.
Sin adornos innecesarios.

¿Qué pensás? ¿Cómo distinguimos la claridad de la simplificación?

#Reflexiones #Pensamiento #Filosofía"""
        
        return """A veces me pregunto si no estamos confundiendo la profundidad con la complejidad.

Pensar bien no es acumular capas de abstracción.
Es llegar al núcleo de las cosas.

¿Qué pensás?

#Reflexiones #Pensamiento #Filosofía"""
    
    def _generate_question_template(self) -> str:
        """Generar post con pregunta filosófica/profesional."""
        temas = self.voice.temas
        tema = random.choice(temas) if temas else "nuestro tiempo"
        return f"""¿Qué significa realmente pensar la {tema} en un mundo saturado de respuestas rápidas?
        
A menudo confundimos la información con el conocimiento, y el conocimiento con la sabiduría.

¿Estamos perdiendo la capacidad de sostener una pregunta sin buscar el alivio de una solución inmediata?

Me encantaría leer tus reflexiones en los comentarios.

#Filosofía #PensamientoCrítico #{tema.replace(' ', '')}"""
    
    def _generate_insight_template(self) -> str:
        """Generar post tipo insight profesional."""
        return """3 cosas que aprendí este año sobre automatización:

1️⃣ La mejor automatización es la que no notás
   → Debe integrarse naturalmente en tu flujo

2️⃣ Automatizar lo incorrecto es peor que no automatizar
   → Primero entendé el proceso, después automatizá

3️⃣ La revisión humana sigue siendo esencial
   → La IA asiste, no reemplaza el criterio

¿Cuál agregarías?

#Automatización #Productividad #IA #Tecnología"""
    
    def _build_prompt(self, post_type: str, article_id: Optional[int] = None) -> str:
        """Construir prompt para LLM."""
        # Obtener temas del perfil de voz para sugerir hashtags
        temas = self.voice.temas or []
        hashtags_sugeridos = [f"#{t.replace(' ', '')}" for t in temas[:5]]
        
        prompt_parts = [
            "INSTRUCCIONES:",
            "1. Analiza el perfil de voz. Genera post que suene humano y profesional.",
            "2. Usa párrafos cortos y claros (estilo LinkedIn).",
            "3. Aporta VALOR real, no solo relleno.",
            "",
            "PERFIL DE VOZ:",
            self.voice.to_prompt(),
            "",
            "FORMATO LINKEDIN:",
            "- Máximo 3000 caracteres.",
            "- Usa saltos de línea frecuentes.",
            "- Tono profesional pero cercano.",
            "- Emojis: uso moderado (1-3 max).",
            "- Termina con pregunta/call to action.",
            "- SIEMPRE incluye hashtags al final.",
            f"- Hashtags sugeridos: {', '.join(hashtags_sugeridos)}" if hashtags_sugeridos else "",
            "",
        ]
        
        if post_type == "promo" and article_id:
            article = self.db.fetchone("SELECT * FROM articulos WHERE id = ?", (article_id,))
            if article:
                # Intentar obtener contenido completo
                full_content = None
                if article.get('url'):
                    try:
                        logger.info(f"Obteniendo contenido de: {article['url']}")
                        content_data = fetch_article_content(article['url'])
                        if content_data:
                            full_content = content_data.get("text", "")
                    except Exception as e:
                        logger.warning(f"No se pudo obtener contenido: {e}")
                
                context_content = full_content if full_content else article['resumen']
                if context_content and len(context_content) > 12000:
                    context_content = context_content[:12000] + "..."

                prompt_parts.extend([
                    "TAREA: Post promocionando artículo.",
                    f"TÍTULO: {article['titulo']}",
                    f"CONTENIDO: {context_content}",
                    f"PLATAFORMA: {article.get('plataforma', 'blog')}",
                    "",
                    "REGLAS:",
                    "- NO pongas el enlace en el texto del post (di 'Link en comentarios').",
                    "- Extrae una lección valiosa o insight del texto.",
                    "- Genera curiosidad sin ser clickbait.",
                ])
        
        elif post_type == "thought":
            prompt_parts.extend([
                "TAREA: Reflexión profunda sobre un tema.",
                "",
                "REGLAS:",
                "- Desarrolla una idea contraintuitiva o profunda.",
                "- Cuestiona el status quo.",
                "- Usa estructura: Gancho -> Desarrollo -> Conclusión/Pregunta.",
            ])
        
        elif post_type == "question":
            prompt_parts.extend([
                "TAREA: Plantea una pregunta filosófica o conceptual profunda.",
                "",
                "REGLAS:",
                "- Evita las anécdotas personales superficiales.",
                "- Enfócate en la base conceptual de un tema de actualidad o profesional.",
                "- Invita a una reflexión pausada, no a una respuesta impulsiva.",
                "- Estructura: Provocación/Contexto -> La Pregunta -> Invitación al diálogo.",
            ])
        
        elif post_type == "insight":
            prompt_parts.extend([
                "TAREA: Lista de insights (3-5 puntos).",
                "",
                "REGLAS:",
                "- Usa formato de lista con emojis (1️⃣, 2️⃣, etc).",
                "- Cada punto debe ser accionable o revelador.",
                "- Estructura: Afirmación -> Explicación breve.",
            ])
        
        prompt_parts.extend([
            "",
            "REQUISITO CRÍTICO:",
            "- Genera DIRECTAMENTE el texto del post listo para publicar.",
            "- NO incluyas introducciones como 'Aquí tienes', 'Aquí está', etc.",
            "- NO uses formato de respuesta a un prompt.",
            "- El texto debe empezar INMEDIATAMENTE con el contenido del post.",
        ])
        
        return "\n".join(prompt_parts)
    
    def save_post(self, post: Dict) -> int:
        """Guardar post de LinkedIn en base de datos."""
        # Preparar metadata incluyendo article_url y article_title
        existing_metadata = post.get("metadata", "{}")
        try:
            metadata = json.loads(existing_metadata) if isinstance(existing_metadata, str) else existing_metadata
        except json.JSONDecodeError:
            metadata = {}
        
        # Agregar article_url y article_title al metadata
        if post.get("article_url"):
            metadata["article_url"] = post["article_url"]
        if post.get("article_title"):
            metadata["article_title"] = post["article_title"]
        if post.get("article_image_url"):
            metadata["article_image_url"] = post["article_image_url"]
        
        # Usamos la misma tabla pero con metadata diferente
        db_post = {
            "content": post["content"],
            "content_hash": post["content_hash"],
            "tweet_type": f"linkedin_{post['post_type']}",  # Prefijo para distinguir
            "article_id": post.get("article_id"),
            "metadata": json.dumps(metadata)
        }
        return self.db.insert("tweet_candidates", db_post)
    
    def generate_batch(self, mix: Dict[str, int]) -> List[int]:
        """Generar lote de posts según mix especificado."""
        post_ids = []
        
        # Obtener artículos disponibles para promoción
        articles = self.db.fetchall(
            """
            SELECT id FROM articulos
            WHERE id NOT IN (
                SELECT DISTINCT article_id 
                FROM tweet_candidates 
                WHERE article_id IS NOT NULL
                AND tweet_type LIKE 'linkedin_%'
            )
            ORDER BY fecha_publicacion DESC
            """
        )
        
        article_pool = [a["id"] for a in articles]
        
        for post_type, count in mix.items():
            for i in range(count):
                article_id = None
                if post_type == "promo" and article_pool:
                    article_id = article_pool[i % len(article_pool)]
                
                posts = self.generate(post_type, article_id, count=1)
                
                if posts:
                    post_id = self.save_post(posts[0])
                    post_ids.append(post_id)
                    logger.info(f"Post de LinkedIn generado y guardado: {post_type} (ID: {post_id})")
        
        return post_ids
