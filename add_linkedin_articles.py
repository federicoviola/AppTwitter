#!/usr/bin/env python3
"""
Script interactivo para agregar artículos de LinkedIn a AppTwitter.

Uso:
    python add_linkedin_articles.py
"""

import csv
from pathlib import Path

def main():
    print("=" * 60)
    print("📝 Agregar Artículos de LinkedIn a AppTwitter")
    print("=" * 60)
    print()
    print("Instrucciones:")
    print("1. Ve a: https://www.linkedin.com/in/fedeviola/recent-activity/articles/")
    print("2. Copia la información de cada artículo")
    print("3. Pégala aquí cuando se te pida")
    print()
    print("Presiona Ctrl+C en cualquier momento para terminar")
    print()
    
    articulos = []
    
    while True:
        try:
            print("-" * 60)
            print(f"Artículo #{len(articulos) + 1}")
            print("-" * 60)
            
            titulo = input("Título: ").strip()
            if not titulo:
                break
            
            url = input("URL: ").strip()
            if not url:
                break
            
            fecha = input("Fecha (YYYY-MM-DD): ").strip()
            if not fecha:
                fecha = "2024-01-01"
            
            tags = input("Tags (separados por coma): ").strip()
            if not tags:
                tags = "linkedin,artículo"
            
            resumen = input("Resumen breve: ").strip()
            if not resumen:
                resumen = titulo
            
            articulos.append({
                "titulo": titulo,
                "url": url,
                "plataforma": "linkedin",
                "fecha_publicacion": fecha,
                "tags": tags,
                "resumen": resumen,
                "idioma": "es"
            })
            
            print(f"✓ Artículo agregado ({len(articulos)} total)")
            print()
            
            continuar = input("¿Agregar otro artículo? (s/n): ").strip().lower()
            if continuar != 's':
                break
        
        except KeyboardInterrupt:
            print("\n\nInterrumpido por usuario")
            break
    
    if not articulos:
        print("\nNo se agregaron artículos")
        return
    
    # Guardar en CSV
    output_file = Path("articulos_linkedin.csv")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'titulo', 'url', 'plataforma', 'fecha_publicacion', 
            'tags', 'resumen', 'idioma'
        ])
        writer.writeheader()
        writer.writerows(articulos)
    
    print()
    print("=" * 60)
    print(f"✓ {len(articulos)} artículos guardados en: {output_file}")
    print("=" * 60)
    print()
    print("Ahora ejecuta:")
    print(f"  ./app.sh import-articles --file {output_file}")
    print()

if __name__ == "__main__":
    main()
