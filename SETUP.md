# ⚡ Configuración Rápida - AppTwitter

## 🚀 Inicio Rápido (5 minutos)

### Paso 1: Verificar Instalación ✅

```bash
# Ya está instalado Poetry y las dependencias
~/.local/bin/poetry --version
# Poetry (version 2.2.1)

# Verificar que la app funciona
./app.sh --version
# app, version 0.1.0
```

### Paso 2: Configurar Credenciales (Opcional)

#### Opción A: Con API de X (para publicación automática)

1. **Obtener credenciales de X:**
   - Ir a: https://developer.twitter.com/en/portal/dashboard
   - Crear una App
   - Obtener: API Key, API Secret, Access Token, Access Token Secret

2. **Configurar en `.env`:**
   ```bash
   nano .env
   ```
   
   Agregar:
   ```bash
   X_API_KEY=tu_api_key_aqui
   X_API_SECRET=tu_api_secret_aqui
   X_ACCESS_TOKEN=tu_access_token_aqui
   X_ACCESS_TOKEN_SECRET=tu_access_token_secret_aqui
   ```

#### Opción B: Sin API (modo exportación)

Si no tenés credenciales de X, la app funciona igual:
- Genera tweets
- Los exporta a archivo markdown
- Los copiás y pegás manualmente en X

**No necesitás hacer nada más.** ✅

### Paso 3: Personalizar Perfil de Voz

```bash
# Editar perfil de voz
./app.sh edit-voice
```

**Configurar:**
- Tus temas prioritarios
- Tu tono y estilo
- Palabras que querés evitar
- Ejemplos de tus tweets

**Ejemplo mínimo:**
```yaml
temas:
  - filosofía
  - tecnología
  - ética

tono:
  formal: true
  claro: true
  crítico: true

palabras_prohibidas:
  - "obviamente"
  - "claramente"

ejemplos:
  - "La técnica no es neutral, pero tampoco determinista."
  - "Pensar es cuestionar lo dado, no repetir lo sabido."
```

### Paso 4: Importar Tus Artículos

#### Opción A: Usar el ejemplo

```bash
# Ya hay 5 artículos de ejemplo importados
./app.sh list-articles
```

#### Opción B: Importar tus artículos

1. **Crear archivo CSV:**
   ```bash
   nano mis_articulos.csv
   ```

2. **Formato:**
   ```csv
   titulo,url,plataforma,fecha_publicacion,tags,resumen,idioma
   "Mi artículo","https://linkedin.com/...","linkedin","2024-01-15","filosofía,IA","Resumen breve","es"
   ```

3. **Importar:**
   ```bash
   ./app.sh import-articles --file mis_articulos.csv
   ```

### Paso 5: Generar Tweets

```bash
# Generar 10 tweets de promoción + 5 pensamientos + 3 preguntas
./app.sh generate --mix "promo:10,thought:5,question:3"
```

**Resultado:**
```
✓ 18 tweets generados y guardados
✓ Tweets agregados a la cola para revisión
```

### Paso 6: Revisar y Aprobar

```bash
./app.sh review
```

**Para cada tweet:**
- Presionar `a` para **aprobar**
- Presionar `s` para **omitir**
- Presionar `q` para **salir**

### Paso 7: Planificar

```bash
./app.sh schedule
```

**Resultado:**
```
✓ 15 tweets planificados
Próximo tweet: 2026-01-09 09:00:00
```

### Paso 8: Publicar

#### Opción A: Con API de X

```bash
# Publicar todos los pendientes
./app.sh run
```

#### Opción B: Sin API (exportar)

```bash
# Exportar a archivo
./app.sh export --output mis_tweets.md

# Ver el archivo
cat mis_tweets.md

# Copiar y pegar manualmente en X
```

### Paso 9: Ver Estadísticas

```bash
./app.sh stats
```

**Resultado:**
```
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ Métrica              ┃ Valor ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ Artículos importados │ 5     │
│ Tweets candidatos    │ 18    │
│ Tweets planificados  │ 15    │
│ Publicados hoy       │ 0     │
└──────────────────────┴───────┘
```

## 🎯 Workflow Recomendado

### Semanal (Domingo por la tarde)

```bash
# 1. Importar artículos nuevos de la semana
./app.sh import-articles --file articulos_semana.csv

# 2. Generar lote para toda la semana (21 tweets = 3/día x 7 días)
./app.sh generate --mix "promo:12,thought:6,question:3"

# 3. Revisar todos de una vez
./app.sh review

# 4. Planificar para toda la semana
./app.sh schedule

# 5. Ver plan
./app.sh stats
```

### Diario (Automático)

```bash
# Opción 1: Publicación automática (si tenés API)
./app.sh run --daemon --interval 300

# Opción 2: Exportación diaria (sin API)
./app.sh export --output tweets_$(date +%Y%m%d).md
```

## ⚙️ Configuración Avanzada

### Ajustar Límites de Publicación

```bash
nano .env
```

**Configuración conservadora:**
```bash
MAX_TWEETS_PER_DAY=2
MIN_SPACING_MINUTES=180
POST_WINDOW_START=10:00
POST_WINDOW_END=20:00
```

**Configuración agresiva:**
```bash
MAX_TWEETS_PER_DAY=5
MIN_SPACING_MINUTES=90
POST_WINDOW_START=08:00
POST_WINDOW_END=23:00
```

### Habilitar LLM (Opcional)

#### Gemini (Google) - **Recomendado**

```bash
# 1. Instalar dependencia
~/.local/bin/poetry install -E llm-gemini

# 2. Configurar API key
nano .env
# Agregar: GEMINI_API_KEY=AIzaSy...

# 3. Obtener API key gratis en:
# https://aistudio.google.com/app/apikey

# 4. Generar con LLM
./app.sh generate --mix "promo:10,thought:5"
```

**Ver guía completa**: `GEMINI.md`

#### OpenAI (GPT-4)

```bash
# 1. Instalar dependencia
~/.local/bin/poetry install -E llm-openai

# 2. Configurar API key
nano .env
# Agregar: OPENAI_API_KEY=sk-...

# 3. Generar con LLM
./app.sh generate --mix "promo:10,thought:5"
```

#### Anthropic (Claude)

```bash
# 1. Instalar dependencia
~/.local/bin/poetry install -E llm-anthropic

# 2. Configurar API key
nano .env
# Agregar: ANTHROPIC_API_KEY=sk-ant-...

# 3. Generar con LLM
./app.sh generate --mix "promo:10,thought:5"
```

## 🔧 Comandos Útiles

### Ver Logs

```bash
# Logs en tiempo real
tail -f logs/app.log

# Últimas 50 líneas
tail -n 50 logs/app.log

# Filtrar errores
grep ERROR logs/app.log
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

## 📋 Checklist de Configuración

- [ ] ✅ Aplicación inicializada (`./app.sh init`)
- [ ] ⚙️ Credenciales configuradas en `.env` (opcional)
- [ ] 🎨 Perfil de voz personalizado en `voz.yaml`
- [ ] 📚 Artículos importados
- [ ] 🤖 Tweets generados
- [ ] ✅ Tweets revisados y aprobados
- [ ] 📅 Tweets planificados
- [ ] 🚀 Primer tweet publicado (o exportado)

## 🆘 Ayuda Rápida

### Comando no funciona

```bash
# Verificar que Poetry está en el PATH
export PATH="$HOME/.local/bin:$PATH"

# Usar el script de ayuda
./app.sh [comando]
```

### No tengo credenciales de X

**No hay problema.** Usar modo exportación:

```bash
./app.sh export --output tweets.md
# Copiar y pegar manualmente
```

### Tweets muy similares

Ajustar temperatura en `voz.yaml`:

```yaml
generacion:
  temperatura: 0.9  # Más variación (0.0-1.0)
```

### Tweets muy largos

Ajustar longitud en `voz.yaml`:

```yaml
estilo:
  longitud_preferida: "corta"  # corta | media | larga
```

## 📚 Documentación Completa

- **README.md**: Guía de usuario completa
- **ARCHITECTURE.md**: Arquitectura técnica
- **EXAMPLES.md**: Ejemplos de uso
- **COMPLETADO.md**: Resumen visual del proyecto

## 🎉 ¡Listo!

Ya tenés todo configurado. Ahora podés:

1. ✅ Importar tus artículos
2. ✅ Generar tweets
3. ✅ Revisar y aprobar
4. ✅ Planificar publicaciones
5. ✅ Publicar (o exportar)

**¡A tuitear!** 🐦

---

**Tip:** Empezá con el modo exportación para familiarizarte con la app antes de habilitar publicación automática.
