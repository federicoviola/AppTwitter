# Arquitectura Técnica - AppTwitter

## Visión General

AppTwitter es una aplicación local-first diseñada con arquitectura modular, separación de responsabilidades y enfoque en seguridad y control del usuario.

## Principios de Diseño

1. **Local-first**: Todos los datos se almacenan localmente en SQLite
2. **Modularidad**: Cada módulo tiene una responsabilidad clara
3. **Seguridad**: Revisión humana obligatoria, filtros múltiples
4. **Extensibilidad**: Fácil agregar nuevos generadores, filtros o integraciones
5. **Transparencia**: Logs completos, estado visible en todo momento

## Arquitectura de Módulos

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                        │
│                    Interfaz de usuario                      │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐      ┌──────────────┐     ┌──────────────┐
│   Ingest     │      │  Generator   │     │  Scheduler   │
│  (ingest.py) │      │(generator.py)│     │(scheduler.py)│
└──────────────┘      └──────────────┘     └──────────────┘
        │                     │                     │
        │              ┌──────┴──────┐              │
        │              │             │              │
        ▼              ▼             ▼              ▼
┌──────────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐
│    Voice     │  │ Filters │  │ X Client│  │   Database   │
│  (voice.py)  │  │(filters)│  │(x_client)│  │   (db.py)    │
└──────────────┘  └─────────┘  └─────────┘  └──────────────┘
                                                    │
                                                    ▼
                                            ┌──────────────┐
                                            │   SQLite     │
                                            │ tweets.db    │
                                            └──────────────┘
```

## Módulos Principales

### 1. CLI (cli.py)
**Responsabilidad**: Interfaz de línea de comandos

**Comandos principales**:
- `init`: Inicializar aplicación
- `import-articles`: Importar artículos
- `add-article`: Agregar artículo interactivo
- `list-articles`: Listar artículos
- `generate`: Generar tweets
- `review`: Revisar y aprobar tweets
- `schedule`: Planificar tweets
- `run`: Publicar tweets
- `export`: Exportar tweets
- `stats`: Ver estadísticas

**Dependencias**: Todos los demás módulos

### 2. Database (db.py)
**Responsabilidad**: Gestión de base de datos SQLite

**Tablas**:
- `articulos`: Artículos importados
- `tweet_candidates`: Tweets generados
- `tweet_queue`: Cola de publicación
- `tweets_publicados`: Historial
- `settings`: Configuración
- `logs`: Logs de eventos

**Métodos clave**:
- `execute()`: Ejecutar query
- `fetchone()`, `fetchall()`: Consultas
- `insert()`, `update()`, `delete()`: Operaciones CRUD
- `get_setting()`, `set_setting()`: Configuración
- `log()`: Registrar eventos

### 3. Ingest (ingest.py)
**Responsabilidad**: Importación de artículos

**Formatos soportados**:
- CSV
- JSON
- Modo interactivo

**Validaciones**:
- Duplicados por URL
- Campos requeridos
- Formato de fecha

**Métodos clave**:
- `import_from_csv()`
- `import_from_json()`
- `add_article_interactive()`
- `list_articles()`
- `search_articles()`

### 4. Voice (voice.py)
**Responsabilidad**: Perfil de voz y pensamiento

**Configuración**:
- Temas prioritarios
- Tono y estilo
- Palabras prohibidas
- Patrones argumentativos
- Ejemplos de tweets

**Métodos clave**:
- `to_prompt()`: Convertir a prompt para LLM
- Getters para todas las configuraciones

### 5. Generator (generator.py)
**Responsabilidad**: Generación de tweets

**Modos de generación**:
1. **LLM** (OpenAI/Anthropic): Generación inteligente
2. **Plantillas**: Fallback determinístico

**Tipos de tweets**:
- `promo`: Difusión de artículo
- `thought`: Pensamiento breve
- `question`: Pregunta abierta
- `thread`: Hilo (primer tweet)

**Métodos clave**:
- `generate()`: Generar tweet individual
- `generate_batch()`: Generar lote con mix
- `_generate_with_llm()`: Generación con LLM
- `_generate_with_template()`: Generación con plantillas

### 6. Filters (filters.py)
**Responsabilidad**: Filtros de seguridad y calidad

**Filtros implementados**:
1. **Duplicados**: Hash exacto + similitud fuzzy
2. **Palabras prohibidas**: Lista configurable
3. **Lenguaje agresivo**: Patrones regex
4. **Contenido engañoso**: Patrones de spam
5. **Longitud**: Min/max caracteres

**Métodos clave**:
- `validate()`: Validación completa
- `is_duplicate()`: Detección de duplicados
- `contains_forbidden_words()`
- `is_aggressive()`
- `is_misleading()`

### 7. Scheduler (scheduler.py)
**Responsabilidad**: Planificación y cola de tweets

**Estados de cola**:
- `drafted`: Borrador
- `approved`: Aprobado
- `scheduled`: Planificado
- `posted`: Publicado
- `failed`: Fallido
- `skipped`: Omitido

**Reglas de planificación**:
- Ventana horaria configurable
- Espaciado mínimo entre tweets
- Límite diario de tweets

**Métodos clave**:
- `add_to_queue()`
- `approve_tweet()`
- `schedule_approved_tweets()`
- `get_pending_tweets()`
- `mark_as_posted()`
- `mark_as_failed()`

### 8. X Client (x_client.py)
**Responsabilidad**: Interacción con API de X

**Modos de operación**:
1. **API mode**: Publicación automática vía Tweepy
2. **Export mode**: Exportación a archivo/clipboard

**Métodos clave**:
- `post_tweet()`: Publicar tweet individual
- `post_thread()`: Publicar hilo
- `delete_tweet()`: Eliminar tweet
- `export_to_clipboard()`: Copiar al portapapeles
- `export_to_file()`: Exportar a markdown

### 9. Utils (utils.py)
**Responsabilidad**: Utilidades comunes

**Funciones**:
- Gestión de paths
- Configuración de logging
- Normalización de texto
- Hashing
- Variables de entorno
- Validación de tweets

## Flujo de Datos

### Flujo de Importación
```
CSV/JSON → ArticleImporter → Database (articulos)
```

### Flujo de Generación
```
Database (articulos) → Generator → Filters → Database (tweet_candidates)
                          ↑
                      VoiceProfile
                          ↑
                      LLM (opcional)
```

### Flujo de Revisión
```
Database (tweet_candidates) → CLI (review) → Scheduler → Database (tweet_queue)
                                                              ↓
                                                          status: approved
```

### Flujo de Planificación
```
Database (tweet_queue: approved) → Scheduler → Database (tweet_queue: scheduled)
                                                              ↓
                                                      scheduled_at: timestamp
```

### Flujo de Publicación
```
Database (tweet_queue: scheduled) → XClient → X API
                                        ↓
                                    Database (tweets_publicados)
                                        ↓
                                    tweet_queue: status = posted
```

## Esquema de Base de Datos

### Tabla: articulos
```sql
CREATE TABLE articulos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    plataforma TEXT NOT NULL,
    fecha_publicacion DATE NOT NULL,
    tags TEXT,
    resumen TEXT,
    idioma TEXT DEFAULT 'es',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Tabla: tweet_candidates
```sql
CREATE TABLE tweet_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    tweet_type TEXT NOT NULL,
    article_id INTEGER,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articulos(id)
);
```

### Tabla: tweet_queue
```sql
CREATE TABLE tweet_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    status TEXT DEFAULT 'drafted',
    scheduled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES tweet_candidates(id)
);
```

### Tabla: tweets_publicados
```sql
CREATE TABLE tweets_publicados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    tweet_id TEXT,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    platform_response TEXT,
    FOREIGN KEY (candidate_id) REFERENCES tweet_candidates(id)
);
```

## Seguridad

### 1. Credenciales
- Variables de entorno (`.env`)
- Nunca hardcodeadas
- Nunca commiteadas a git

### 2. Validación de Entrada
- Sanitización de datos importados
- Validación de formatos
- Prevención de SQL injection (parametrized queries)

### 3. Filtros de Contenido
- Múltiples capas de validación
- Detección de duplicados
- Prevención de spam
- Control de lenguaje

### 4. Rate Limiting
- Respeto a límites de API de X
- Espaciado configurable
- Límite diario de tweets

### 5. Revisión Humana
- Obligatoria por defecto
- Modo automático requiere habilitación explícita

## Extensibilidad

### Agregar Nuevo Generador
1. Implementar método en `Generator`
2. Agregar tipo a `TWEET_TYPES`
3. Implementar plantilla fallback

### Agregar Nuevo Filtro
1. Implementar método en `TweetFilter`
2. Agregar llamada en `validate()`

### Agregar Nueva Plataforma
1. Crear nuevo cliente (ej. `linkedin_client.py`)
2. Implementar interfaz similar a `XClient`
3. Integrar en `Scheduler`

### Agregar Nuevo LLM
1. Agregar credenciales en `.env.example`
2. Implementar inicialización en `Generator._init_llm_client()`
3. Implementar generación en `Generator._generate_with_llm()`

## Logging

### Niveles
- `DEBUG`: Información detallada de desarrollo
- `INFO`: Eventos normales (importación, generación, publicación)
- `WARNING`: Situaciones inusuales pero manejables
- `ERROR`: Errores que impiden operación

### Destinos
1. **Archivo**: `logs/app.log`
2. **Consola**: stdout
3. **Base de datos**: tabla `logs`

## Configuración

### Variables de Entorno (.env)
```bash
# API de X
X_API_KEY=
X_API_SECRET=
X_ACCESS_TOKEN=
X_ACCESS_TOKEN_SECRET=

# LLM (opcional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Configuración
AUTO_POST_ENABLED=false
MAX_TWEETS_PER_DAY=3
MIN_SPACING_MINUTES=120
POST_WINDOW_START=09:00
POST_WINDOW_END=22:00
DEFAULT_LANGUAGE=es
LOG_LEVEL=INFO
```

### Perfil de Voz (voz.yaml)
```yaml
temas: [...]
tono: {...}
palabras_prohibidas: [...]
patrones: [...]
ejemplos: [...]
estilo: {...}
generacion: {...}
```

## Testing

### Estrategia
1. **Unit tests**: Cada módulo independiente
2. **Integration tests**: Flujos completos
3. **Manual testing**: Revisión de tweets generados

### Ejecutar tests
```bash
poetry run pytest
```

## Deployment

### Requisitos de Sistema
- Ubuntu 20.04+
- Python 3.11+
- 100MB espacio en disco
- Conexión a internet (para APIs)

### Instalación
```bash
poetry install
poetry run app init
```

### Actualización
```bash
git pull
poetry install
```

## Monitoreo

### Métricas Clave
- Artículos importados
- Tweets generados
- Tweets publicados
- Tasa de aprobación
- Errores de publicación

### Comando
```bash
poetry run app stats
```

## Troubleshooting

### Problema: LLM no disponible
**Solución**: Verificar API key en `.env` o usar modo plantillas

### Problema: API de X no disponible
**Solución**: Verificar credenciales o usar modo exportación

### Problema: Tweets duplicados
**Solución**: Ajustar umbral en `filters.py` o limpiar base de datos

### Problema: Base de datos corrupta
**Solución**: Eliminar `data/tweets.db` y ejecutar `app init`

## Roadmap Futuro

### Corto Plazo
- [ ] Interfaz web local (FastAPI)
- [ ] Soporte para imágenes en tweets
- [ ] Métricas de engagement (manual)
- [ ] Exportación de estadísticas

### Mediano Plazo
- [ ] Integración con LinkedIn API
- [ ] Integración con Substack API
- [ ] Generación automática de hilos completos
- [ ] A/B testing de tweets

### Largo Plazo
- [ ] Machine learning para optimización
- [ ] Análisis de sentimiento
- [ ] Recomendaciones de horarios óptimos
- [ ] Multi-cuenta

## Contribuciones

Para contribuir:
1. Fork del repositorio
2. Crear branch de feature
3. Implementar cambios
4. Agregar tests
5. Crear pull request

## Licencia

Uso personal. Respetar términos de servicio de X y APIs de terceros.
