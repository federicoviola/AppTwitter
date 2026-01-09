# 📅 Guía de Comandos de Programación

## Comandos Disponibles

### 1. `list-scheduled` - Ver Tweets Planificados

Muestra todos los tweets programados con detalles completos.

```bash
./app.sh list-scheduled
```

**Salida:**
- 📅 Fecha y hora programada
- 📝 Contenido del tweet
- 📢/💭/❓ Tipo de tweet (promo/thought/question)
- 📏 Longitud del tweet

**Ejemplo:**
```
📅 Tweets Planificados (4)

╭────────────── Tweet #1 ──────────────╮
│ La dicotomía "bueno/malo" aplicada a │
│ la IA soslaya la pregunta...         │
│                                      │
│ 📢 Promo | 🕐 09/01/2026 09:00 | 📏  │
│ 219 caracteres                       │
╰──────────────────────────────────────╯
```

---

### 2. `reschedule` - Reprogramar un Tweet

Cambia la fecha y hora de publicación de un tweet específico.

#### Opciones:

**Por fecha y hora específica:**
```bash
./app.sh reschedule --id 11 --datetime "2026-01-09 14:30"
```

**Por minutos desde ahora:**
```bash
./app.sh reschedule --id 11 --minutes 30
```

**Por horas desde ahora:**
```bash
./app.sh reschedule --id 11 --hours 2
```

**Por días desde ahora:**
```bash
./app.sh reschedule --id 11 --days 1
```

#### Parámetros:

- `--id` o `-i`: **Requerido**. ID del tweet en la cola (ver con `list-scheduled`)
- `--datetime` o `-d`: Fecha y hora específica (formato: `YYYY-MM-DD HH:MM`)
- `--minutes` o `-m`: Minutos desde ahora
- `--hours` o `-h`: Horas desde ahora
- `--days` o `-D`: Días desde ahora

**Nota:** Solo se puede usar UNA opción de tiempo a la vez.

---

## Workflow Completo

### 1. Ver Tweets Planificados
```bash
./app.sh list-scheduled
```

Esto te muestra todos los tweets con sus IDs y horarios.

### 2. Reprogramar si es Necesario
```bash
# Ejemplo: Mover el tweet #11 para mañana a las 14:30
./app.sh reschedule --id 11 --datetime "2026-01-09 14:30"

# O moverlo para dentro de 3 horas
./app.sh reschedule --id 11 --hours 3
```

### 3. Verificar Cambios
```bash
./app.sh list-scheduled
```

### 4. Ver Estadísticas Generales
```bash
./app.sh stats
```

---

## Ejemplos de Uso

### Caso 1: Mover un Tweet para Más Tarde Hoy

```bash
# Ver tweets planificados
./app.sh list-scheduled

# Mover tweet #11 para dentro de 2 horas
./app.sh reschedule --id 11 --hours 2

# Confirmar cambio
./app.sh list-scheduled
```

### Caso 2: Programar para una Fecha Específica

```bash
# Programar tweet #12 para el viernes a las 10:00
./app.sh reschedule --id 12 --datetime "2026-01-10 10:00"
```

### Caso 3: Adelantar un Tweet

```bash
# Adelantar tweet #13 para dentro de 30 minutos
./app.sh reschedule --id 13 --minutes 30
```

### Caso 4: Posponer para la Próxima Semana

```bash
# Posponer tweet #14 para dentro de 7 días
./app.sh reschedule --id 14 --days 7
```

---

## Tips y Mejores Prácticas

### 1. Verificar Antes de Reprogramar

Siempre usa `list-scheduled` primero para ver:
- Los IDs correctos de los tweets
- Los horarios actuales
- El contenido de cada tweet

### 2. Slots Fijos de Publicación

El sistema usa **slots fijos** de publicación:
- **Mañana:** 09:00 (configurable con `POST_SLOT_MORNING`)
- **Noche:** 21:00 (configurable con `POST_SLOT_EVENING`)

Cada día se publica **un tweet por la mañana** y **uno por la noche**. Los tweets aprobados se asignan automáticamente al próximo slot disponible.

### 3. Configuración de Horarios

Podés personalizar los horarios en tu archivo `.env`:

```bash
# Slot de mañana (default: 09:00)
POST_SLOT_MORNING=09:00

# Slot de noche (default: 21:00, hora argentina)
POST_SLOT_EVENING=21:00

# Máximo de tweets por día (default: 2)
MAX_TWEETS_PER_DAY=2
```

### 4. Límite Diario

El sistema respeta el límite diario de tweets configurado en `MAX_TWEETS_PER_DAY` (default: 2, uno por cada slot).

---

## Troubleshooting

### Error: "Tweet no encontrado"

**Causa:** El ID no existe o el tweet no está en estado `scheduled`.

**Solución:**
```bash
# Ver todos los tweets planificados con sus IDs
./app.sh list-scheduled

# Verificar que el tweet esté en estado 'scheduled'
./app.sh stats
```

### Error: "Formato de fecha inválido"

**Causa:** El formato de fecha no es correcto.

**Solución:** Usar el formato exacto `YYYY-MM-DD HH:MM`:
```bash
# ✓ Correcto
./app.sh reschedule --id 11 --datetime "2026-01-09 14:30"

# ✗ Incorrecto
./app.sh reschedule --id 11 --datetime "09/01/2026 14:30"
./app.sh reschedule --id 11 --datetime "2026-01-09"
```

### Tweet No Se Publica en el Horario Programado

**Causa:** El daemon no está corriendo o está detenido.

**Solución:**
```bash
# Iniciar daemon
./app.sh run --daemon --interval 60
```

---

## Comandos Relacionados

- `./app.sh schedule` - Planificar tweets aprobados automáticamente
- `./app.sh list-scheduled` - Ver tweets planificados
- `./app.sh reschedule` - Reprogramar un tweet específico
- `./app.sh stats` - Ver estadísticas generales
- `./app.sh run --daemon` - Ejecutar publicación automática

---

## Resumen de Comandos

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `list-scheduled` | Ver tweets planificados | `./app.sh list-scheduled` |
| `reschedule` | Reprogramar un tweet | `./app.sh reschedule --id 11 --hours 2` |
| `schedule` | Planificar tweets aprobados | `./app.sh schedule` |
| `stats` | Ver estadísticas | `./app.sh stats` |
| `run --daemon` | Publicación automática | `./app.sh run --daemon --interval 60` |

---

**¡Ahora tenés control total sobre cuándo se publican tus tweets!** 📅✨
