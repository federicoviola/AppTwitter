# AppTwitter

**Aplicación local para automatizar la difusión en X (Twitter) de artículos y generar tweets de engagement**

## 📋 Descripción

AppTwitter es una aplicación local-first desarrollada en Python que permite automatizar la difusión de artículos publicados en LinkedIn y Substack, además de generar tweets originales de engagement alineados con tu forma de pensar, ideas y estilo discursivo.

### Características principales

- ✅ **Importación de artículos** desde CSV o JSON
- ✅ **Perfil de voz personalizable** (temas, tono, patrones argumentativos)
- ✅ **Generación inteligente de tweets** con plantillas o LLM (Gemini/OpenAI/Anthropic)
- ✅ **Filtros de seguridad** (duplicados, palabras prohibidas, lenguaje agresivo)
- ✅ **Cola de publicación** con planificación automática
- ✅ **Revisión humana** antes de publicar
- ✅ **Publicación en X** vía API oficial
- ✅ **Modo exportación** para publicación manual
- ✅ **Base de datos SQLite** local
- ✅ **CLI robusta** con Rich

## 🚀 Instalación

### Requisitos

- Ubuntu 20.04+ (o cualquier distribución Linux)
- Python 3.11 o superior
- Poetry (gestor de dependencias)

### Pasos

1. **Clonar o descargar el proyecto**

```bash
cd ~/Workspace/AppTwitter
```

2. **Instalar Poetry** (si no lo tenés)

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. **Instalar dependencias**

```bash
poetry install
```

4. **Instalar dependencias opcionales** (LLM)

Para Gemini (Google) - **Recomendado**:
```bash
poetry install -E llm-gemini
```

Para OpenAI:
```bash
poetry install -E llm-openai
```

Para Anthropic:
```bash
poetry install -E llm-anthropic
```

5. **Inicializar la aplicación**

```bash
poetry run app init
```

Esto creará:
- `.env` (configuración)
- `voz.yaml` (perfil de voz)
- `data/tweets.db` (base de datos)

## ⚙️ Configuración

### 1. Credenciales de X (Twitter)

Editar `.env` y agregar tus credenciales:

```bash
X_API_KEY=tu_api_key
X_API_SECRET=tu_api_secret
X_ACCESS_TOKEN=tu_access_token
X_ACCESS_TOKEN_SECRET=tu_access_token_secret
```

**Obtener credenciales:** https://developer.twitter.com/en/portal/dashboard

### 2. LLM (opcional)

Si querés usar generación con LLM, agregar en `.env`:

```bash
# Para Gemini (Google) - Recomendado
GEMINI_API_KEY=tu_api_key

# O para OpenAI
OPENAI_API_KEY=tu_api_key

# O para Anthropic
ANTHROPIC_API_KEY=tu_api_key
```

**Obtener API key de Gemini:** https://aistudio.google.com/app/apikey

### 3. Perfil de voz

Editar `voz.yaml` con tu perfil:

```bash
poetry run app edit-voice
```

O copiar desde el ejemplo:

```bash
cp voz.example.yaml voz.yaml
nano voz.yaml
```

### 4. Configuración de publicación

En `.env`:

```bash
# Habilitar publicación automática
AUTO_POST_ENABLED=false  # Cambiar a true cuando estés listo

# Límites
MAX_TWEETS_PER_DAY=3
MIN_SPACING_MINUTES=120

# Ventana horaria (formato HH:MM)
POST_WINDOW_START=09:00
POST_WINDOW_END=22:00
```

## 📖 Uso

### Workflow completo

#### 1. Importar artículos

Desde CSV:
```bash
poetry run app import-articles --file articulos.csv
```

Desde JSON:
```bash
poetry run app import-articles --file articulos.json
```

Modo interactivo:
```bash
poetry run app add-article
```

#### 2. Listar artículos

```bash
poetry run app list-articles --limit 20
```

#### 3. Generar tweets

Generar con mix personalizado:
```bash
poetry run app generate --mix "promo:10,thought:6,question:4"
```

Tipos de tweets:
- `promo`: Difusión de artículo (con link)
- `thought`: Pensamiento breve (sin link)
- `question`: Pregunta abierta
- `thread`: Primer tweet de un hilo

#### 4. Revisar tweets

```bash
poetry run app review
```

Opciones:
- `a` = Aprobar
- `s` = Omitir (skip)
- `q` = Salir

#### 5. Planificar tweets aprobados

```bash
poetry run app schedule
```

Esto asigna horarios automáticamente respetando:
- Ventana horaria configurada
- Espaciado mínimo entre tweets
- Límite diario de tweets

#### 6. Publicar tweets

**Modo manual** (publicar uno ahora):
```bash
poetry run app post-now
```

**Modo automático** (publicar todos los pendientes):
```bash
poetry run app run
```

**Modo daemon** (loop continuo):
```bash
poetry run app run --daemon --interval 60
```

#### 7. Exportar tweets (sin API)

Si no tenés credenciales de X:

```bash
poetry run app export --output tweets.md
```

Esto genera un archivo markdown con los tweets para copiar/pegar manualmente.

### Comandos adicionales

**Ver estadísticas:**
```bash
poetry run app stats
```

**Configurar perfil de voz:**
```bash
poetry run app set-voice --file mi_voz.yaml
```

**Ayuda:**
```bash
poetry run app --help
poetry run app [comando] --help
```

## 📁 Estructura del proyecto

```
AppTwitter/
├── .env                    # Configuración (credenciales, límites)
├── .env.example            # Plantilla de configuración
├── voz.yaml                # Perfil de voz (temas, tono, ejemplos)
├── voz.example.yaml        # Plantilla de perfil de voz
├── articulos.example.csv   # Ejemplo de artículos
├── pyproject.toml          # Dependencias y configuración
├── README.md               # Este archivo
├── data/
│   └── tweets.db           # Base de datos SQLite
├── logs/
│   └── app.log             # Logs de la aplicación
└── src/
    ├── cli.py              # Interfaz CLI
    ├── db.py               # Gestión de base de datos
    ├── ingest.py           # Importación de artículos
    ├── voice.py            # Perfil de voz
    ├── generator.py        # Generación de tweets
    ├── filters.py          # Filtros de seguridad
    ├── scheduler.py        # Planificación y cola
    ├── x_client.py         # Cliente de API de X
    └── utils.py            # Utilidades
```

## 🗄️ Esquema de base de datos

### Tablas

- **articulos**: Artículos importados
- **tweet_candidates**: Tweets generados (candidatos)
- **tweet_queue**: Cola de publicación
- **tweets_publicados**: Historial de tweets publicados
- **settings**: Configuración de la aplicación
- **logs**: Logs de eventos

### Estados de la cola

- `drafted`: Borrador (generado, pendiente de revisión)
- `approved`: Aprobado (listo para planificar)
- `scheduled`: Planificado (con fecha/hora asignada)
- `posted`: Publicado
- `failed`: Fallido
- `skipped`: Omitido

## 🔒 Seguridad y privacidad

- ✅ **Local-first**: Todos los datos se almacenan localmente
- ✅ **Credenciales seguras**: Variables de entorno, nunca hardcodeadas
- ✅ **Revisión humana**: Activada por defecto
- ✅ **Filtros de seguridad**: Evita duplicados, lenguaje agresivo, contenido engañoso
- ✅ **Rate limits**: Respeta límites de la API de X
- ✅ **Modo exportación**: Alternativa sin API para mayor control

## 🛡️ Términos de uso

Esta aplicación:
- Usa **exclusivamente la API oficial de X**
- **Respeta los términos de servicio** de X
- **No intenta bypass** ni automatización agresiva
- Implementa **límites conservadores** de publicación
- Requiere **revisión humana** por defecto

## 🐛 Troubleshooting

### Error: "API de X no disponible"

**Solución:** Verificar credenciales en `.env` o usar modo exportación:

```bash
poetry run app export
```

### Error: "LLM no disponible"

**Solución:** La app funciona sin LLM usando plantillas. Para habilitar LLM:

```bash
# Opción 1: Gemini (Google) - Recomendado
poetry install -E llm-gemini
# Agregar GEMINI_API_KEY en .env

# Opción 2: OpenAI
poetry install -E llm-openai
# Agregar OPENAI_API_KEY en .env

# Opción 3: Anthropic
poetry install -E llm-anthropic
# Agregar ANTHROPIC_API_KEY en .env
```

### Error: "No hay tweets aprobados"

**Solución:** Primero revisar y aprobar tweets:

```bash
poetry run app review
```

### Tweets duplicados

Los filtros detectan duplicados automáticamente. Si querés ajustar el umbral de similitud, editar `src/filters.py`.

## 📊 Ejemplo de uso completo

```bash
# 1. Inicializar
poetry run app init

# 2. Configurar credenciales
nano .env

# 3. Configurar perfil de voz
poetry run app edit-voice

# 4. Importar artículos
poetry run app import-articles --file articulos.csv

# 5. Generar tweets
poetry run app generate --mix "promo:10,thought:5,question:3"

# 6. Revisar y aprobar
poetry run app review

# 7. Planificar
poetry run app schedule

# 8. Ver estadísticas
poetry run app stats

# 9. Publicar (modo manual)
poetry run app post-now

# O exportar para publicación manual
poetry run app export
```

## 🔄 Workflow recomendado

1. **Semanal**: Importar nuevos artículos
2. **Semanal**: Generar lote de tweets (20-30)
3. **Semanal**: Revisar y aprobar tweets
4. **Automático**: Planificación y publicación según configuración

## 📝 Formato de artículos CSV

```csv
titulo,url,plataforma,fecha_publicacion,tags,resumen,idioma
"Mi artículo","https://...","linkedin","2024-01-15","filosofía,IA","Resumen breve","es"
```

## 🤝 Contribuciones

Este es un proyecto personal. Si encontrás bugs o tenés sugerencias, podés:
- Reportar issues
- Proponer mejoras
- Hacer fork y adaptar a tus necesidades

## 📄 Licencia

Uso personal. Respetar términos de servicio de X y APIs de terceros.

## 🙏 Créditos

Desarrollado con:
- Python 3.11+
- Click (CLI)
- Rich (UI)
- Tweepy (X API)
- SQLite (DB)
- Gemini / OpenAI / Anthropic (LLM opcional)

---

**Nota**: Esta aplicación está diseñada para uso responsable y ético. Asegurate de cumplir con los términos de servicio de X y usar la automatización de forma transparente y no engañosa.
