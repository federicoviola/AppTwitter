# 🤖 Guía de Configuración de Gemini API

## ¿Por qué Gemini?

**Gemini** (Google) es la opción **recomendada** para AppTwitter por varias razones:

1. ✅ **Gratis para uso personal** - Cuota generosa en el tier gratuito
2. ✅ **Excelente calidad** - Gemini 2.0 Flash es rápido y preciso
3. ✅ **Fácil de configurar** - Solo necesitás una API key
4. ✅ **Multilingüe** - Excelente soporte para español
5. ✅ **Bajo costo** - Si superás el tier gratuito, es muy económico

## 🚀 Configuración en 3 Pasos

### Paso 1: Obtener API Key

1. Ir a: **https://aistudio.google.com/app/apikey**
2. Hacer clic en **"Create API Key"**
3. Seleccionar un proyecto de Google Cloud (o crear uno nuevo)
4. Copiar la API key generada

**Nota**: La API key se ve así: `AIzaSy...` (empieza con `AIzaSy`)

### Paso 2: Configurar en AppTwitter

Editar el archivo `.env`:

```bash
nano .env
```

Agregar tu API key:

```bash
# Gemini (Google) - Recomendado
GEMINI_API_KEY=AIzaSy_tu_api_key_aqui
```

Guardar y salir (`Ctrl+O`, `Enter`, `Ctrl+X`).

### Paso 3: Instalar Dependencia

```bash
poetry install -E llm-gemini
```

**¡Listo!** Ya podés generar tweets con Gemini.

## 🧪 Probar la Integración

```bash
# Generar tweets con Gemini
./app.sh generate --mix "promo:3,thought:2,question:1"
```

Deberías ver en los logs:
```
Cliente Gemini (Google) inicializado
```

## 📊 Límites del Tier Gratuito

Gemini ofrece un tier gratuito muy generoso:

- **15 requests por minuto**
- **1,500 requests por día**
- **1 millón de tokens por mes**

Para AppTwitter, esto significa:
- ✅ Podés generar **cientos de tweets por día** sin costo
- ✅ Suficiente para uso personal intensivo
- ✅ No necesitás tarjeta de crédito

## 🔄 Comparación con Otras Opciones

| Característica | Gemini | OpenAI | Anthropic |
|----------------|--------|--------|-----------|
| **Tier gratuito** | ✅ Sí | ❌ No | ❌ No |
| **Costo** | Muy bajo | Medio | Medio-Alto |
| **Calidad** | Excelente | Excelente | Excelente |
| **Velocidad** | Muy rápida | Rápida | Rápida |
| **Español** | Excelente | Excelente | Excelente |
| **Configuración** | Muy fácil | Fácil | Fácil |

## 💡 Consejos de Uso

### 1. Ajustar Temperatura

En `voz.yaml`, podés ajustar la creatividad:

```yaml
generacion:
  temperatura: 0.7  # 0.0 = conservador, 1.0 = creativo
```

- **0.5-0.6**: Tweets más consistentes y predecibles
- **0.7-0.8**: Balance entre creatividad y coherencia (recomendado)
- **0.9-1.0**: Tweets más creativos y variados

### 2. Optimizar Prompts

El perfil de voz en `voz.yaml` es crucial. Cuanto más específico, mejores resultados:

```yaml
ejemplos:
  - "Ejemplo de tweet 1"
  - "Ejemplo de tweet 2"
  - "Ejemplo de tweet 3"
```

Gemini aprende de tus ejemplos y genera tweets similares.

### 3. Monitorear Uso

Podés ver tu uso en: https://aistudio.google.com/app/apikey

## 🔧 Troubleshooting

### Error: "Cliente Gemini no inicializado"

**Causa**: API key no configurada o inválida.

**Solución**:
```bash
# Verificar que la API key esté en .env
cat .env | grep GEMINI_API_KEY

# Debe mostrar:
# GEMINI_API_KEY=AIzaSy...
```

### Error: "Rate limit exceeded"

**Causa**: Superaste el límite de requests por minuto (15).

**Solución**: Esperar 1 minuto o generar tweets en lotes más pequeños:
```bash
# En lugar de generar 50 tweets de una vez
./app.sh generate --mix "promo:10,thought:5,question:3"

# Esperar 1 minuto entre lotes
```

### Error: "API key not valid"

**Causa**: API key incorrecta o revocada.

**Solución**:
1. Ir a https://aistudio.google.com/app/apikey
2. Verificar que la API key esté activa
3. Generar una nueva si es necesario
4. Actualizar `.env`

## 🌟 Ventajas de Gemini para AppTwitter

### 1. Generación Contextual

Gemini entiende muy bien el contexto de tus artículos:

```
Artículo: "IA y Ética: Una Reflexión Necesaria"
Tweet generado: "La IA no es neutral. Cada algoritmo lleva consigo decisiones éticas implícitas. ¿Estamos listos para hacerlas explícitas?"
```

### 2. Respeto al Estilo

Gemini respeta tu perfil de voz:

```yaml
tono:
  formal: true
  académico: true
  crítico: true
```

Resultado: Tweets formales, académicos y críticos.

### 3. Variedad

Gemini genera tweets variados sin repetirse:

```bash
# Generar 20 tweets
./app.sh generate --mix "thought:20"

# Resultado: 20 tweets únicos y diferentes
```

## 📈 Mejores Prácticas

### 1. Workflow Recomendado

```bash
# 1. Generar lote pequeño para probar
./app.sh generate --mix "promo:3,thought:2"

# 2. Revisar calidad
./app.sh review

# 3. Si la calidad es buena, generar lote grande
./app.sh generate --mix "promo:20,thought:10,question:5"
```

### 2. Ajustar Perfil de Voz

Si los tweets no reflejan tu estilo:

```bash
# Editar perfil de voz
./app.sh edit-voice

# Agregar más ejemplos de tus tweets
# Ajustar temperatura
# Refinar patrones argumentativos
```

### 3. Monitorear Resultados

```bash
# Ver estadísticas
./app.sh stats

# Revisar logs
tail -f logs/app.log | grep Gemini
```

## 🔐 Seguridad

### Proteger tu API Key

1. ✅ **Nunca** compartir tu API key
2. ✅ **Nunca** commitear `.env` a git (ya está en `.gitignore`)
3. ✅ **Rotar** la API key periódicamente
4. ✅ **Monitorear** uso en Google AI Studio

### Revocar API Key

Si creés que tu API key fue comprometida:

1. Ir a: https://aistudio.google.com/app/apikey
2. Hacer clic en el ícono de basura junto a la API key
3. Generar una nueva API key
4. Actualizar `.env`

## 🎓 Recursos Adicionales

- **Documentación oficial**: https://ai.google.dev/docs
- **Google AI Studio**: https://aistudio.google.com/
- **Pricing**: https://ai.google.dev/pricing
- **Límites y cuotas**: https://ai.google.dev/gemini-api/docs/quota

## 🆚 Cambiar de LLM

Si querés probar otro LLM:

```bash
# Desactivar Gemini (comentar en .env)
# GEMINI_API_KEY=...

# Activar OpenAI
OPENAI_API_KEY=sk-...

# O Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

AppTwitter detecta automáticamente qué LLM usar en este orden:
1. Gemini (si está configurado)
2. OpenAI (si está configurado)
3. Anthropic (si está configurado)
4. Plantillas (fallback)

## 💬 Preguntas Frecuentes

### ¿Necesito tarjeta de crédito?

**No.** El tier gratuito de Gemini no requiere tarjeta de crédito.

### ¿Cuántos tweets puedo generar por día?

Con el tier gratuito: **~1,500 tweets por día** (1 request = 1 tweet).

Para uso típico de AppTwitter (20-50 tweets por semana), el tier gratuito es más que suficiente.

### ¿Gemini guarda mis tweets?

Google puede usar los requests para mejorar sus modelos, pero **no** publica tus tweets. Lee la política de privacidad: https://ai.google.dev/gemini-api/terms

### ¿Puedo usar Gemini y OpenAI al mismo tiempo?

Sí, pero AppTwitter usa solo uno a la vez. Prioridad:
1. Gemini
2. OpenAI
3. Anthropic

Para cambiar, comentar la API key que no querés usar en `.env`.

### ¿Qué modelo de Gemini usa AppTwitter?

**Gemini 2.0 Flash** - Es el modelo más rápido y moderno, perfecto para generación de tweets.

---

## 🎉 ¡Listo para Empezar!

```bash
# 1. Configurar API key
nano .env
# Agregar: GEMINI_API_KEY=tu_api_key

# 2. Instalar dependencia
poetry install -E llm-gemini

# 3. Generar tweets
./app.sh generate --mix "promo:10,thought:5,question:3"

# 4. Revisar
./app.sh review

# 5. ¡Publicar!
./app.sh schedule
./app.sh run
```

**¡Disfrutá de la generación de tweets con IA!** 🚀
