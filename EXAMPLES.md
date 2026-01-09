# Ejemplos de Uso - AppTwitter

## Escenarios Comunes

### 1. Configuración Inicial

```bash
# Inicializar aplicación
./app.sh init

# Editar configuración
nano .env

# Configurar perfil de voz
./app.sh edit-voice
```

### 2. Importar Artículos

#### Desde CSV
```bash
# Crear archivo articulos.csv
cat > articulos.csv << EOF
titulo,url,plataforma,fecha_publicacion,tags,resumen,idioma
"Mi primer artículo","https://linkedin.com/pulse/ejemplo1","linkedin","2024-01-15","filosofía,IA","Análisis sobre IA y ética","es"
EOF

# Importar
./app.sh import-articles --file articulos.csv
```

#### Desde JSON
```bash
# Crear archivo articulos.json
cat > articulos.json << EOF
[
  {
    "titulo": "Mi artículo",
    "url": "https://substack.com/ejemplo",
    "plataforma": "substack",
    "fecha_publicacion": "2024-01-15",
    "tags": "filosofía,técnica",
    "resumen": "Reflexión sobre la técnica moderna",
    "idioma": "es"
  }
]
EOF

# Importar
./app.sh import-articles --file articulos.json
```

#### Modo Interactivo
```bash
./app.sh add-article
# Seguir prompts interactivos
```

### 3. Generar Tweets

#### Mix Balanceado
```bash
# 50% promoción, 30% pensamientos, 20% preguntas
./app.sh generate --mix "promo:10,thought:6,question:4"
```

#### Solo Promoción
```bash
# Generar solo tweets de promoción de artículos
./app.sh generate --mix "promo:20"
```

#### Solo Engagement
```bash
# Generar solo tweets de engagement (sin links)
./app.sh generate --mix "thought:10,question:5"
```

#### Incluir Hilos
```bash
# Mix con hilos
./app.sh generate --mix "promo:5,thought:3,question:2,thread:2"
```

### 4. Revisar y Aprobar Tweets

```bash
# Revisar borradores
./app.sh review --status drafted

# Para cada tweet:
# - Presionar 'a' para aprobar
# - Presionar 's' para omitir
# - Presionar 'q' para salir
```

### 5. Planificar Tweets

```bash
# Planificar todos los tweets aprobados
./app.sh schedule

# Ver próximo tweet planificado
./app.sh stats
```

### 6. Publicar Tweets

#### Modo Manual (uno por uno)
```bash
# Publicar el próximo tweet pendiente
./app.sh post-now
```

#### Modo Automático (todos los pendientes)
```bash
# Habilitar publicación automática en .env
# AUTO_POST_ENABLED=true

# Publicar todos los tweets pendientes
./app.sh run
```

#### Modo Daemon (loop continuo)
```bash
# Ejecutar en background, verificando cada 60 segundos
./app.sh run --daemon --interval 60

# Detener con Ctrl+C
```

### 7. Exportar Tweets (sin API)

```bash
# Exportar a archivo markdown
./app.sh export --output mis_tweets.md

# Ver el archivo
cat mis_tweets.md
```

### 8. Consultar Estadísticas

```bash
# Ver estadísticas generales
./app.sh stats

# Listar artículos
./app.sh list-articles --limit 20
```

## Workflows Avanzados

### Workflow 1: Campaña de Difusión de Artículo

```bash
# 1. Agregar artículo nuevo
./app.sh add-article
# Título: "IA y Ética: Una Reflexión Necesaria"
# URL: https://linkedin.com/pulse/ia-etica
# ...

# 2. Generar tweets de promoción
./app.sh generate --mix "promo:5"

# 3. Revisar y aprobar
./app.sh review

# 4. Planificar para los próximos 3 días
./app.sh schedule

# 5. Ver plan
./app.sh stats
```

### Workflow 2: Generación Semanal de Engagement

```bash
# 1. Generar lote semanal (21 tweets = 3 por día x 7 días)
./app.sh generate --mix "thought:14,question:7"

# 2. Revisar todos
./app.sh review

# 3. Planificar
./app.sh schedule

# 4. Ejecutar en modo daemon
./app.sh run --daemon --interval 300
```

### Workflow 3: Importación Masiva

```bash
# 1. Preparar CSV con todos los artículos
cat > todos_articulos.csv << EOF
titulo,url,plataforma,fecha_publicacion,tags,resumen,idioma
"Artículo 1","https://...","linkedin","2024-01-01","tag1,tag2","Resumen 1","es"
"Artículo 2","https://...","substack","2024-01-15","tag3,tag4","Resumen 2","es"
...
EOF

# 2. Importar
./app.sh import-articles --file todos_articulos.csv

# 3. Verificar
./app.sh list-articles --limit 50

# 4. Generar tweets para todos
./app.sh generate --mix "promo:50,thought:20,question:10"
```

### Workflow 4: Revisión y Ajuste

```bash
# 1. Ver estadísticas
./app.sh stats

# 2. Revisar borradores
./app.sh review --status drafted

# 3. Si hay tweets omitidos, regenerar
./app.sh generate --mix "thought:5"

# 4. Revisar nuevos
./app.sh review

# 5. Planificar
./app.sh schedule
```

## Configuraciones Específicas

### Configuración Conservadora
```bash
# .env
MAX_TWEETS_PER_DAY=2
MIN_SPACING_MINUTES=180
POST_WINDOW_START=10:00
POST_WINDOW_END=20:00
AUTO_POST_ENABLED=false
```

### Configuración Agresiva
```bash
# .env
MAX_TWEETS_PER_DAY=5
MIN_SPACING_MINUTES=90
POST_WINDOW_START=08:00
POST_WINDOW_END=23:00
AUTO_POST_ENABLED=true
```

### Configuración Solo Mañanas
```bash
# .env
MAX_TWEETS_PER_DAY=3
MIN_SPACING_MINUTES=120
POST_WINDOW_START=07:00
POST_WINDOW_END=12:00
```

## Personalización del Perfil de Voz

### Perfil Académico Formal
```yaml
# voz.yaml
temas:
  - epistemología
  - filosofía de la ciencia
  - ética aplicada

tono:
  formal: true
  académico: true
  claro: true
  crítico: true
  sin_insultos: true

palabras_prohibidas:
  - "obviamente"
  - "claramente"

estilo:
  longitud_preferida: "larga"
  uso_preguntas: true
  uso_citas: true
  uso_hashtags: "nunca"
  uso_emojis: false

generacion:
  temperatura: 0.5
  densidad_conceptual: "alta"
```

### Perfil Divulgación Accesible
```yaml
# voz.yaml
temas:
  - tecnología
  - sociedad
  - cultura digital

tono:
  formal: false
  académico: false
  claro: true
  crítico: true
  sin_insultos: true

estilo:
  longitud_preferida: "media"
  uso_preguntas: true
  uso_ejemplos: true
  uso_hashtags: "moderado"
  uso_emojis: true

generacion:
  temperatura: 0.8
  densidad_conceptual: "media"
```

## Integración con LLM

### Configuración OpenAI
```bash
# .env
OPENAI_API_KEY=sk-...

# Instalar dependencia
poetry install -E llm-openai

# Generar con LLM
./app.sh generate --mix "promo:10,thought:5"
```

### Configuración Anthropic
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...

# Instalar dependencia
poetry install -E llm-anthropic

# Generar con LLM
./app.sh generate --mix "promo:10,thought:5"
```

## Automatización con Cron

### Generar Tweets Diariamente
```bash
# Editar crontab
crontab -e

# Agregar línea (ejecutar a las 8 AM todos los días)
0 8 * * * cd /home/federico/Workspace/AppTwitter && ./app.sh generate --mix "thought:3,question:1" >> logs/cron.log 2>&1
```

### Publicar Tweets Automáticamente
```bash
# Ejecutar cada hora
0 * * * * cd /home/federico/Workspace/AppTwitter && ./app.sh run >> logs/cron.log 2>&1
```

### Backup Semanal
```bash
# Backup de base de datos los domingos a las 23:00
0 23 * * 0 cp /home/federico/Workspace/AppTwitter/data/tweets.db /home/federico/Workspace/AppTwitter/data/backup_$(date +\%Y\%m\%d).db
```

## Debugging

### Ver Logs
```bash
# Logs de aplicación
tail -f logs/app.log

# Filtrar errores
grep ERROR logs/app.log

# Últimas 50 líneas
tail -n 50 logs/app.log
```

### Inspeccionar Base de Datos
```bash
# Abrir SQLite
sqlite3 data/tweets.db

# Ver artículos
SELECT * FROM articulos;

# Ver tweets en cola
SELECT q.id, q.status, c.content 
FROM tweet_queue q 
JOIN tweet_candidates c ON q.candidate_id = c.id;

# Salir
.quit
```

### Resetear Aplicación
```bash
# Eliminar base de datos
rm data/tweets.db

# Reinicializar
./app.sh init

# Reimportar artículos
./app.sh import-articles --file articulos.csv
```

## Tips y Mejores Prácticas

### 1. Revisión Semanal
- Generar lote grande una vez por semana
- Revisar todos de una vez
- Planificar para toda la semana

### 2. Mix Balanceado
- 50-60% promoción de artículos
- 30-40% pensamientos originales
- 10-20% preguntas de engagement

### 3. Horarios Óptimos
- Mañana: 8-10 AM
- Mediodía: 12-2 PM
- Tarde: 6-8 PM

### 4. Evitar Spam
- Máximo 3-5 tweets por día
- Espaciado mínimo de 2 horas
- Variar tipos de tweets

### 5. Monitoreo
- Revisar stats diariamente
- Ajustar mix según engagement
- Mantener logs limpios

## Solución de Problemas Comunes

### Problema: "No hay tweets aprobados"
```bash
# Solución: Revisar y aprobar primero
./app.sh review
./app.sh schedule
```

### Problema: "API de X no disponible"
```bash
# Solución: Usar modo exportación
./app.sh export --output tweets.md
# Publicar manualmente
```

### Problema: Tweets muy similares
```bash
# Solución: Ajustar temperatura en voz.yaml
generacion:
  temperatura: 0.9  # Más variación
```

### Problema: Tweets muy largos
```bash
# Solución: Ajustar longitud preferida
estilo:
  longitud_preferida: "corta"
```

## Recursos Adicionales

- **README.md**: Documentación general
- **ARCHITECTURE.md**: Arquitectura técnica
- **voz.example.yaml**: Ejemplo de perfil de voz
- **articulos.example.csv**: Ejemplo de artículos
- **.env.example**: Ejemplo de configuración

---

**Nota**: Estos son ejemplos ilustrativos. Ajustar según tus necesidades específicas y siempre respetar los términos de servicio de X.
