"""Interfaz de línea de comandos (CLI)."""

import json
import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm

from .db import Database
from .filters import TweetFilter
from .generator import TweetGenerator
from .ingest import ArticleImporter
from .scheduler import TweetScheduler
from .utils import get_env_bool, get_project_root, setup_logging
from .voice import VoiceProfile
from .x_client import XClient

logger = setup_logging()
console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    AppTwitter - Automatización de difusión en X (Twitter)
    
    Aplicación local para automatizar la difusión de artículos y generar tweets de engagement.
    """
    pass


@cli.command()
@click.option("--file", "-f", type=click.Path(exists=True), required=True, help="Archivo CSV o JSON con artículos")
def import_articles(file):
    """Importar artículos desde archivo CSV o JSON."""
    file_path = Path(file)
    
    with Database() as db:
        importer = ArticleImporter(db)
        
        try:
            if file_path.suffix == ".csv":
                count = importer.import_from_csv(file_path)
            elif file_path.suffix == ".json":
                count = importer.import_from_json(file_path)
            else:
                console.print("[red]Error: Formato no soportado. Usar CSV o JSON.[/red]")
                sys.exit(1)
            
            console.print(f"[green]✓ {count} artículos importados exitosamente[/green]")
        
        except Exception as e:
            console.print(f"[red]Error importando artículos: {e}[/red]")
            sys.exit(1)


@cli.command()
def add_article():
    """Agregar artículo de forma interactiva."""
    with Database() as db:
        importer = ArticleImporter(db)
        article_id = importer.add_article_interactive()
        
        if article_id:
            console.print(f"[green]✓ Artículo agregado con ID: {article_id}[/green]")
        else:
            console.print("[red]✗ Error agregando artículo[/red]")


@cli.command()
@click.option("--limit", "-l", default=10, help="Número de artículos a mostrar")
def list_articles(limit):
    """Listar artículos importados."""
    with Database() as db:
        importer = ArticleImporter(db)
        articles = importer.list_articles(limit)
        
        if not articles:
            console.print("[yellow]No hay artículos importados[/yellow]")
            return
        
        table = Table(title=f"Artículos ({len(articles)})")
        table.add_column("ID", style="cyan")
        table.add_column("Título", style="white")
        table.add_column("Plataforma", style="magenta")
        table.add_column("Fecha", style="green")
        table.add_column("Tags", style="yellow")
        
        for article in articles:
            table.add_row(
                str(article["id"]),
                article["titulo"][:50] + "..." if len(article["titulo"]) > 50 else article["titulo"],
                article["plataforma"],
                article["fecha_publicacion"],
                article["tags"][:30] + "..." if article.get("tags") and len(article["tags"]) > 30 else article.get("tags", "")
            )
        
        console.print(table)


@cli.command()
@click.option("--file", "-f", type=click.Path(), help="Archivo de configuración de voz")
def set_voice(file):
    """Configurar perfil de voz."""
    if file:
        file_path = Path(file)
        if not file_path.exists():
            console.print(f"[red]Error: Archivo no encontrado: {file}[/red]")
            sys.exit(1)
        
        # Copiar a voz.yaml
        import shutil
        dest = get_project_root() / "voz.yaml"
        shutil.copy(file_path, dest)
        console.print(f"[green]✓ Perfil de voz configurado desde: {file}[/green]")
    else:
        console.print("[yellow]Usar: app set-voice --file voz.yaml[/yellow]")


@cli.command()
def edit_voice():
    """Editar perfil de voz."""
    import os
    
    voice_file = get_project_root() / "voz.yaml"
    
    if not voice_file.exists():
        # Copiar ejemplo
        example = get_project_root() / "voz.example.yaml"
        if example.exists():
            import shutil
            shutil.copy(example, voice_file)
            console.print("[green]✓ Archivo de voz creado desde ejemplo[/green]")
    
    editor = os.getenv("EDITOR", "nano")
    os.system(f"{editor} {voice_file}")


@cli.command()
@click.option("--count", "-c", default=10, help="Número de tweets a generar")
@click.option("--mix", "-m", default="promo:5,thought:3,question:2", help="Mix de tipos (ej: promo:5,thought:3,question:2)")
def generate(count, mix):
    """Generar tweets candidatos."""
    # Parsear mix
    mix_dict = {}
    try:
        for item in mix.split(","):
            tweet_type, num = item.split(":")
            mix_dict[tweet_type.strip()] = int(num)
    except:
        console.print("[red]Error: Formato de mix inválido. Usar: tipo:cantidad,tipo:cantidad[/red]")
        sys.exit(1)
    
    with Database() as db:
        voice = VoiceProfile()
        tweet_filter = TweetFilter(db, voice)
        generator = TweetGenerator(db, voice, tweet_filter)
        
        console.print(f"[cyan]Generando {sum(mix_dict.values())} tweets...[/cyan]")
        
        tweet_ids = generator.generate_batch(mix_dict)
        
        console.print(f"[green]✓ {len(tweet_ids)} tweets generados y guardados[/green]")
        
        # Agregar a cola
        scheduler = TweetScheduler(db)
        for tweet_id in tweet_ids:
            scheduler.add_to_queue(tweet_id, status="drafted")
        
        console.print(f"[green]✓ Tweets agregados a la cola para revisión[/green]")


@cli.command()
@click.option("--status", "-s", default="drafted", help="Estado de tweets a revisar")
def review(status):
    """Revisar y aprobar tweets."""
    with Database() as db:
        scheduler = TweetScheduler(db)
        tweets = scheduler.list_queue(status=status, limit=50)
        
        if not tweets:
            console.print(f"[yellow]No hay tweets con estado '{status}'[/yellow]")
            return
        
        console.print(f"\n[cyan]Revisando {len(tweets)} tweets[/cyan]\n")
        
        approved = 0
        skipped = 0
        
        for tweet in tweets:
            panel = Panel(
                f"[white]{tweet['content']}[/white]\n\n"
                f"[dim]Tipo: {tweet['tweet_type']} | ID: {tweet['id']} | Caracteres: {len(tweet['content'])}[/dim]",
                title=f"Tweet {tweets.index(tweet) + 1}/{len(tweets)}",
                border_style="cyan"
            )
            console.print(panel)
            
            action = click.prompt(
                "Acción",
                type=click.Choice(["a", "s", "q"], case_sensitive=False),
                default="a",
                show_choices=True,
                show_default=True
            )
            
            if action == "a":
                scheduler.approve_tweet(tweet["id"])
                console.print("[green]✓ Aprobado[/green]\n")
                approved += 1
            elif action == "s":
                scheduler.skip_tweet(tweet["id"])
                console.print("[yellow]⊘ Omitido[/yellow]\n")
                skipped += 1
            elif action == "q":
                break
        
        console.print(f"\n[green]Revisión completada: {approved} aprobados, {skipped} omitidos[/green]")


@cli.command()
def schedule():
    """Planificar tweets aprobados."""
    with Database() as db:
        scheduler = TweetScheduler(db)
        
        count = scheduler.schedule_approved_tweets()
        
        if count > 0:
            console.print(f"[green]✓ {count} tweets planificados[/green]")
            
            # Mostrar próximos tweets
            stats = scheduler.get_queue_stats()
            if stats.get("next_scheduled"):
                console.print(f"[cyan]Próximo tweet: {stats['next_scheduled']}[/cyan]")
        else:
            console.print("[yellow]No hay tweets aprobados para planificar[/yellow]")


@cli.command()
def list_scheduled():
    """Listar tweets planificados con detalles."""
    with Database() as db:
        tweets = db.fetchall(
            """
            SELECT 
                q.id,
                c.content,
                c.tweet_type,
                q.scheduled_at,
                q.status
            FROM tweet_queue q
            JOIN tweet_candidates c ON q.candidate_id = c.id
            WHERE q.status = 'scheduled'
            ORDER BY q.scheduled_at
            """
        )
        
        if not tweets:
            console.print("[yellow]No hay tweets planificados[/yellow]")
            return
        
        console.print(f"\n[bold cyan]📅 Tweets Planificados ({len(tweets)})[/bold cyan]\n")
        
        for i, tweet in enumerate(tweets, 1):
            # Formato de fecha más legible
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(tweet["scheduled_at"])
                fecha_str = dt.strftime("%d/%m/%Y %H:%M")
            except:
                fecha_str = tweet["scheduled_at"]
            
            # Tipo de tweet con emoji
            tipo_emoji = {
                "promo": "📢",
                "thought": "💭",
                "question": "❓",
                "thread": "🧵"
            }
            emoji = tipo_emoji.get(tweet["tweet_type"], "📝")
            
            panel = Panel(
                f"[white]{tweet['content']}[/white]\n\n"
                f"[dim]{emoji} {tweet['tweet_type'].capitalize()} | "
                f"🕐 {fecha_str} | "
                f"📏 {len(tweet['content'])} caracteres[/dim]",
                title=f"[cyan]Tweet #{i} (ID: {tweet['id']})[/cyan]",
                border_style="blue"
            )
            console.print(panel)
        
        console.print(f"\n[green]Total: {len(tweets)} tweets programados[/green]\n")


@cli.command()
@click.option("--id", "-i", "tweet_id", type=int, required=True, help="ID del tweet en la cola")
@click.option("--datetime", "-d", "new_datetime", help="Nueva fecha y hora (formato: YYYY-MM-DD HH:MM)")
@click.option("--minutes", "-m", type=int, help="Reprogramar para dentro de X minutos")
@click.option("--hours", "-h", type=int, help="Reprogramar para dentro de X horas")
@click.option("--days", "-D", type=int, help="Reprogramar para dentro de X días")
def reschedule(tweet_id, new_datetime, minutes, hours, days):
    """Reprogramar un tweet para otra fecha/hora."""
    from datetime import datetime, timedelta
    
    with Database() as db:
        # Verificar que el tweet existe
        tweet = db.fetchone(
            """
            SELECT q.id, q.scheduled_at, c.content, c.tweet_type
            FROM tweet_queue q
            JOIN tweet_candidates c ON q.candidate_id = c.id
            WHERE q.id = ? AND q.status = 'scheduled'
            """,
            (tweet_id,)
        )
        
        if not tweet:
            console.print(f"[red]✗ Tweet {tweet_id} no encontrado o no está planificado[/red]")
            return
        
        # Mostrar tweet actual
        try:
            dt_actual = datetime.fromisoformat(tweet["scheduled_at"])
            fecha_actual = dt_actual.strftime("%d/%m/%Y %H:%M")
        except:
            fecha_actual = tweet["scheduled_at"]
        
        console.print(f"\n[cyan]Tweet a reprogramar:[/cyan]")
        panel = Panel(
            f"[white]{tweet['content'][:100]}{'...' if len(tweet['content']) > 100 else ''}[/white]\n\n"
            f"[dim]Tipo: {tweet['tweet_type']} | Programado: {fecha_actual}[/dim]",
            border_style="yellow"
        )
        console.print(panel)
        
        # Calcular nueva fecha
        nueva_fecha = None
        
        if new_datetime:
            try:
                nueva_fecha = datetime.strptime(new_datetime, "%Y-%m-%d %H:%M")
            except ValueError:
                console.print("[red]✗ Formato de fecha inválido. Usar: YYYY-MM-DD HH:MM[/red]")
                console.print("[yellow]Ejemplo: 2026-01-09 14:30[/yellow]")
                return
        
        elif minutes:
            nueva_fecha = datetime.now() + timedelta(minutes=minutes)
        
        elif hours:
            nueva_fecha = datetime.now() + timedelta(hours=hours)
        
        elif days:
            nueva_fecha = datetime.now() + timedelta(days=days)
        
        else:
            console.print("[red]✗ Debe especificar --datetime, --minutes, --hours o --days[/red]")
            console.print("\n[yellow]Ejemplos:[/yellow]")
            console.print("  app reschedule --id 11 --datetime '2026-01-09 14:30'")
            console.print("  app reschedule --id 11 --minutes 30")
            console.print("  app reschedule --id 11 --hours 2")
            console.print("  app reschedule --id 11 --days 1")
            return
        
        # Formatear para mostrar
        nueva_fecha_str = nueva_fecha.strftime("%d/%m/%Y %H:%M")
        nueva_fecha_iso = nueva_fecha.strftime("%Y-%m-%d %H:%M:%S")
        
        console.print(f"\n[cyan]Nueva fecha programada: {nueva_fecha_str}[/cyan]")
        
        if not Confirm.ask("¿Confirmar reprogramación?"):
            console.print("[yellow]Cancelado[/yellow]")
            return
        
        # Actualizar en base de datos
        db.execute(
            "UPDATE tweet_queue SET scheduled_at = ? WHERE id = ?",
            (nueva_fecha_iso, tweet_id)
        )
        
        console.print(f"[green]✓ Tweet {tweet_id} reprogramado para {nueva_fecha_str}[/green]")


@cli.command()
@click.option("--daemon", "-d", is_flag=True, help="Ejecutar en modo daemon (loop continuo)")
@click.option("--interval", "-i", default=60, help="Intervalo de verificación en segundos (modo daemon)")
def run(daemon, interval):
    """Ejecutar publicación de tweets planificados."""
    import time
    
    with Database() as db:
        scheduler = TweetScheduler(db)
        x_client = XClient()
        
        if not x_client.is_available():
            console.print("[yellow]⚠ API de X no disponible. Usar modo exportación.[/yellow]")
            console.print("[yellow]Ejecutar: app export[/yellow]")
            return
        
        auto_post = get_env_bool("AUTO_POST_ENABLED", False)
        
        if not auto_post:
            console.print("[yellow]⚠ Publicación automática deshabilitada[/yellow]")
            console.print("[yellow]Habilitar en .env: AUTO_POST_ENABLED=true[/yellow]")
            return
        
        def publish_pending():
            pending = scheduler.get_pending_tweets()
            
            if not pending:
                console.print("[dim]No hay tweets pendientes de publicación[/dim]")
                return 0
            
            published = 0
            auto_attach_image = os.getenv("AUTO_ATTACH_IMAGE", "true").lower() == "true"
            
            for tweet in pending:
                console.print(f"\n[cyan]Publicando tweet {tweet['id']}...[/cyan]")
                console.print(f"[white]{tweet['content']}[/white]")
                
                # Obtener URL del artículo si existe (para imagen automática)
                article_url = tweet.get("article_url") if auto_attach_image else None
                if article_url:
                    console.print(f"[dim]Artículo: {article_url}[/dim]")
                
                result = x_client.post_tweet(
                    tweet["content"],
                    article_url=article_url
                )
                
                if result and result.get("success"):
                    has_image = result.get("has_image", False)
                    scheduler.mark_as_posted(
                        tweet["id"],
                        tweet_id=result.get("tweet_id"),
                        response=result.get("response")
                    )
                    console.print(f"[green]✓ Publicado exitosamente" + 
                                 (" (con imagen)" if has_image else "") + "[/green]")
                    published += 1
                else:
                    error = result.get("error", "Error desconocido") if result else "Sin respuesta"
                    scheduler.mark_as_failed(tweet["id"], error)
                    console.print(f"[red]✗ Error: {error}[/red]")
                
                # Esperar entre publicaciones
                time.sleep(5)
            
            return published
        
        if daemon:
            console.print(f"[cyan]Modo daemon activado. Verificando cada {interval} segundos.[/cyan]")
            console.print("[dim]Presionar Ctrl+C para detener[/dim]\n")
            
            try:
                while True:
                    published = publish_pending()
                    if published > 0:
                        console.print(f"\n[green]✓ {published} tweets publicados[/green]\n")
                    
                    time.sleep(interval)
            
            except KeyboardInterrupt:
                console.print("\n[yellow]Detenido por usuario[/yellow]")
        
        else:
            published = publish_pending()
            console.print(f"\n[green]✓ {published} tweets publicados[/green]")


@cli.command()
@click.option("--output", "-o", default="tweets_export.md", help="Archivo de salida")
def export(output):
    """Exportar tweets pendientes a archivo."""
    with Database() as db:
        scheduler = TweetScheduler(db)
        x_client = XClient()
        
        pending = scheduler.get_pending_tweets()
        
        if not pending:
            console.print("[yellow]No hay tweets pendientes[/yellow]")
            return
        
        tweets = [tweet["content"] for tweet in pending]
        
        if x_client.export_to_file(tweets, output):
            console.print(f"[green]✓ {len(tweets)} tweets exportados a: {output}[/green]")
        else:
            console.print("[red]Error exportando tweets[/red]")


@cli.command()
def post_now():
    """Publicar un tweet inmediatamente (modo manual)."""
    with Database() as db:
        scheduler = TweetScheduler(db)
        x_client = XClient()
        
        pending = scheduler.get_pending_tweets()
        
        if not pending:
            console.print("[yellow]No hay tweets pendientes[/yellow]")
            return
        
        tweet = pending[0]
        
        panel = Panel(
            f"[white]{tweet['content']}[/white]\n\n"
            f"[dim]Tipo: {tweet['tweet_type']} | Caracteres: {len(tweet['content'])}[/dim]",
            title="Tweet a publicar",
            border_style="cyan"
        )
        console.print(panel)
        
        article_url = tweet.get("article_url")
        if article_url:
            console.print(f"[dim]Artículo: {article_url} (imagen automática)[/dim]")
        
        if not Confirm.ask("¿Publicar este tweet ahora?"):
            console.print("[yellow]Cancelado[/yellow]")
            return
        
        if x_client.is_available():
            result = x_client.post_tweet(tweet["content"], article_url=article_url)
            
            if result and result.get("success"):
                has_image = result.get("has_image", False)
                scheduler.mark_as_posted(
                    tweet["id"],
                    tweet_id=result.get("tweet_id"),
                    response=result.get("response")
                )
                console.print(f"[green]✓ Tweet publicado exitosamente" + 
                             (" (con imagen)" if has_image else "") + "[/green]")
            else:
                error = result.get("error", "Error desconocido") if result else "Sin respuesta"
                console.print(f"[red]✗ Error: {error}[/red]")
        else:
            # Modo exportación
            if x_client.export_to_clipboard(tweet["content"]):
                console.print("[green]✓ Tweet copiado al portapapeles[/green]")
                console.print("[yellow]Pegar manualmente en X[/yellow]")
            else:
                console.print(f"\n[cyan]{tweet['content']}[/cyan]\n")
                console.print("[yellow]Copiar manualmente y publicar en X[/yellow]")


@cli.command()
def stats():
    """Mostrar estadísticas."""
    with Database() as db:
        scheduler = TweetScheduler(db)
        
        # Estadísticas de cola
        queue_stats = scheduler.get_queue_stats()
        
        # Estadísticas de artículos
        article_count = db.fetchone("SELECT COUNT(*) as count FROM articulos")
        
        # Estadísticas de tweets
        total_candidates = db.fetchone("SELECT COUNT(*) as count FROM tweet_candidates")
        
        # Tabla de estadísticas
        table = Table(title="Estadísticas")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="white")
        
        table.add_row("Artículos importados", str(article_count["count"]))
        table.add_row("Tweets candidatos", str(total_candidates["count"]))
        table.add_row("", "")
        table.add_row("[bold]Cola de tweets[/bold]", "")
        table.add_row("  Borradores", str(queue_stats.get("drafted", 0)))
        table.add_row("  Aprobados", str(queue_stats.get("approved", 0)))
        table.add_row("  Planificados", str(queue_stats.get("scheduled", 0)))
        table.add_row("  Publicados", str(queue_stats.get("posted", 0)))
        table.add_row("  Fallidos", str(queue_stats.get("failed", 0)))
        table.add_row("  Omitidos", str(queue_stats.get("skipped", 0)))
        table.add_row("", "")
        table.add_row("Publicados hoy", str(queue_stats.get("posted_today", 0)))
        
        if queue_stats.get("next_scheduled"):
            table.add_row("Próximo tweet", queue_stats["next_scheduled"])
        
        console.print(table)


@cli.command()
def init():
    """Inicializar aplicación (crear archivos de configuración)."""
    import shutil
    
    root = get_project_root()
    
    # Copiar .env.example a .env si no existe
    if not (root / ".env").exists():
        shutil.copy(root / ".env.example", root / ".env")
        console.print("[green]✓ Archivo .env creado[/green]")
    
    # Copiar voz.example.yaml a voz.yaml si no existe
    if not (root / "voz.yaml").exists():
        shutil.copy(root / "voz.example.yaml", root / "voz.yaml")
        console.print("[green]✓ Archivo voz.yaml creado[/green]")
    
    # Inicializar base de datos
    with Database() as db:
        console.print("[green]✓ Base de datos inicializada[/green]")
    
    console.print("\n[cyan]Aplicación inicializada correctamente[/cyan]")
    console.print("\n[yellow]Próximos pasos:[/yellow]")
    console.print("1. Editar .env con tus credenciales")
    console.print("2. Editar voz.yaml con tu perfil de voz")
    console.print("3. Importar artículos: app import-articles --file articulos.csv")
    console.print("4. Generar tweets: app generate")
    console.print("5. Revisar tweets: app review")


# ==================== LinkedIn Commands ====================

@cli.command()
def linkedin_auth():
    """Autenticarse en LinkedIn (OAuth 2.0)."""
    from .linkedin_client import LinkedInClient
    
    client = LinkedInClient()
    
    if client.is_available():
        user = client.get_user_info()
        console.print(f"[green]✓ Ya estás autenticado en LinkedIn como: {user['user_name']}[/green]")
        
        if Confirm.ask("¿Querés volver a autenticarte?"):
            client.logout()
        else:
            return
    
    console.print("[cyan]Iniciando autenticación de LinkedIn...[/cyan]")
    console.print("[dim]Se abrirá un navegador para autorizar la aplicación[/dim]\n")
    
    if client.authenticate():
        user = client.get_user_info()
        console.print(f"\n[green]✓ Autenticación exitosa![/green]")
        console.print(f"[green]Usuario: {user['user_name']}[/green]")
    else:
        console.print("\n[red]✗ Error en la autenticación[/red]")
        console.print("[yellow]Verificar LINKEDIN_CLIENT_ID y LINKEDIN_CLIENT_SECRET en .env[/yellow]")


@cli.command()
def linkedin_status():
    """Ver estado de conexión con LinkedIn."""
    from .linkedin_client import LinkedInClient
    
    client = LinkedInClient()
    
    if client.is_available():
        user = client.get_user_info()
        console.print(f"[green]✓ Conectado a LinkedIn[/green]")
        console.print(f"[white]Usuario: {user['user_name']}[/white]")
        console.print(f"[dim]ID: {user['user_id']}[/dim]")
    else:
        console.print("[yellow]✗ No conectado a LinkedIn[/yellow]")
        console.print("[dim]Ejecutar: app linkedin-auth[/dim]")


@cli.command()
@click.option("--text", "-t", required=True, help="Texto del post")
@click.option("--url", "-u", help="URL del artículo a compartir (opcional)")
@click.option("--title", help="Título del artículo (opcional)")
def linkedin_post(text, url, title):
    """Publicar un post en LinkedIn."""
    from .linkedin_client import LinkedInClient
    
    client = LinkedInClient()
    
    if not client.is_available():
        console.print("[red]✗ No autenticado en LinkedIn[/red]")
        console.print("[yellow]Ejecutar primero: app linkedin-auth[/yellow]")
        return
    
    # Mostrar preview
    panel = Panel(
        f"[white]{text}[/white]" + 
        (f"\n\n[cyan]🔗 {url}[/cyan]" if url else ""),
        title="Post a publicar en LinkedIn",
        border_style="blue"
    )
    console.print(panel)
    console.print(f"[dim]Caracteres: {len(text)}[/dim]\n")
    
    if not Confirm.ask("¿Publicar este post?"):
        console.print("[yellow]Cancelado[/yellow]")
        return
    
    result = client.post(text, article_url=url, article_title=title)
    
    if result and result.get("success"):
        console.print(f"[green]✓ Post publicado en LinkedIn[/green]")
        console.print(f"[dim]ID: {result.get('post_id')}[/dim]")
    else:
        error = result.get("error", "Error desconocido") if result else "Sin respuesta"
        console.print(f"[red]✗ Error: {error}[/red]")


@cli.command()
def linkedin_logout():
    """Cerrar sesión de LinkedIn."""
    from .linkedin_client import LinkedInClient
    
    client = LinkedInClient()
    
    if not client.is_available():
        console.print("[yellow]No hay sesión activa de LinkedIn[/yellow]")
        return
    
    if Confirm.ask("¿Cerrar sesión de LinkedIn?"):
        client.logout()
        console.print("[green]✓ Sesión cerrada[/green]")


@cli.command()
@click.option("--mix", "-m", default="promo:3,thought:2,insight:1", 
              help="Mix de tipos (ej: promo:3,thought:2,story:1,insight:1)")
def linkedin_generate(mix):
    """Generar posts de LinkedIn con IA."""
    from .linkedin_generator import LinkedInGenerator
    
    # Parsear mix
    mix_dict = {}
    try:
        for item in mix.split(","):
            post_type, num = item.split(":")
            mix_dict[post_type.strip()] = int(num)
    except:
        console.print("[red]Error: Formato de mix inválido. Usar: tipo:cantidad,tipo:cantidad[/red]")
        console.print("[yellow]Tipos válidos: promo, thought, story, insight[/yellow]")
        sys.exit(1)
    
    with Database() as db:
        voice = VoiceProfile()
        generator = LinkedInGenerator(db, voice)
        
        if not generator.llm_client:
            console.print("[yellow]⚠ No hay cliente LLM disponible[/yellow]")
            console.print("[yellow]Configurar GEMINI_API_KEY en .env[/yellow]")
            return
        
        console.print(f"[cyan]Generando {sum(mix_dict.values())} posts de LinkedIn...[/cyan]")
        
        post_ids = generator.generate_batch(mix_dict)
        
        console.print(f"[green]✓ {len(post_ids)} posts de LinkedIn generados[/green]")
        console.print("[dim]Revisar con: app linkedin-review[/dim]")


@cli.command()
@click.option("--limit", "-l", default=10, help="Número de posts a revisar")
def linkedin_review(limit):
    """Revisar y publicar posts de LinkedIn generados."""
    from .linkedin_client import LinkedInClient
    
    with Database() as db:
        # Obtener posts de LinkedIn pendientes de revisión
        posts = db.fetchall(
            """
            SELECT c.*, q.id as queue_id, q.status
            FROM tweet_candidates c
            LEFT JOIN tweet_queue q ON c.id = q.candidate_id
            WHERE c.tweet_type LIKE 'linkedin_%'
            AND (q.status IS NULL OR q.status = 'drafted')
            ORDER BY c.created_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        if not posts:
            console.print("[yellow]No hay posts de LinkedIn pendientes de revisión[/yellow]")
            console.print("[dim]Generar con: app linkedin-generate[/dim]")
            return
        
        # Verificar conexión a LinkedIn
        client = LinkedInClient()
        linkedin_available = client.is_available()
        
        if not linkedin_available:
            console.print("[yellow]⚠ No conectado a LinkedIn. Solo podrás aprobar para después.[/yellow]")
            console.print("[dim]Conectar con: app linkedin-auth[/dim]\n")
        
        console.print(f"\n[cyan]Revisando {len(posts)} posts de LinkedIn[/cyan]\n")
        
        published = 0
        approved = 0
        skipped = 0
        
        for i, post in enumerate(posts, 1):
            # Parsear metadata
            try:
                metadata = json.loads(post.get("metadata", "{}"))
            except:
                metadata = {}
            
            # Mostrar post
            post_type = post['tweet_type'].replace('linkedin_', '')
            
            panel = Panel(
                f"[white]{post['content']}[/white]\n\n"
                f"[dim]Tipo: {post_type} | ID: {post['id']} | "
                f"Caracteres: {len(post['content'])} | "
                f"Generador: {metadata.get('provider', 'template')}[/dim]",
                title=f"[cyan]Post {i}/{len(posts)}[/cyan]",
                border_style="blue"
            )
            console.print(panel)
            
            # Opciones
            if linkedin_available:
                console.print("[dim]Opciones: [p]ublicar ahora, [a]probar para después, [s]kip, [q]uit[/dim]")
                action = click.prompt(
                    "Acción",
                    type=click.Choice(["p", "a", "s", "q"], case_sensitive=False),
                    default="a"
                )
            else:
                console.print("[dim]Opciones: [a]probar para después, [s]kip, [q]uit[/dim]")
                action = click.prompt(
                    "Acción",
                    type=click.Choice(["a", "s", "q"], case_sensitive=False),
                    default="a"
                )
            
            if action == "p" and linkedin_available:
                # Publicar ahora
                result = client.post(
                    post['content'],
                    article_url=post.get('article_url'),
                    article_title=post.get('article_title')
                )
                
                if result and result.get("success"):
                    console.print(f"[green]✓ Publicado en LinkedIn[/green]\n")
                    # Marcar como publicado
                    if post.get('queue_id'):
                        db.execute("UPDATE tweet_queue SET status = 'posted' WHERE id = ?", (post['queue_id'],))
                    published += 1
                else:
                    error = result.get("error", "Error desconocido") if result else "Sin respuesta"
                    console.print(f"[red]✗ Error: {error}[/red]\n")
            
            elif action == "a":
                # Aprobar para después
                if not post.get('queue_id'):
                    # Agregar a cola
                    db.insert("tweet_queue", {
                        "candidate_id": post['id'],
                        "status": "approved"
                    })
                else:
                    db.execute("UPDATE tweet_queue SET status = 'approved' WHERE id = ?", (post['queue_id'],))
                console.print("[green]✓ Aprobado[/green]\n")
                approved += 1
            
            elif action == "s":
                if post.get('queue_id'):
                    db.execute("UPDATE tweet_queue SET status = 'skipped' WHERE id = ?", (post['queue_id'],))
                else:
                    db.insert("tweet_queue", {
                        "candidate_id": post['id'],
                        "status": "skipped"
                    })
                console.print("[yellow]⊘ Omitido[/yellow]\n")
                skipped += 1
            
            elif action == "q":
                break
        
        console.print(f"\n[green]Revisión completada:[/green]")
        if published > 0:
            console.print(f"  📤 {published} publicados")
        if approved > 0:
            console.print(f"  ✅ {approved} aprobados")
        if skipped > 0:
            console.print(f"  ⊘ {skipped} omitidos")


if __name__ == "__main__":
    cli()
