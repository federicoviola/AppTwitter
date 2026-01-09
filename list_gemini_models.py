#!/usr/bin/env python3
"""Script para listar modelos de Gemini disponibles."""

import os
from dotenv import load_dotenv

load_dotenv()

import google.generativeai as genai

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

print("Modelos de Gemini disponibles para generateContent:\n")

for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"✓ {m.name}")
        print(f"  Display: {m.display_name}")
        print(f"  Description: {m.description}")
        print()
