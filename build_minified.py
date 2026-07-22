#!/usr/bin/env python3
"""Minifica archivos CSS y JS para producción sin dependencias externas.

Genera archivos .min.css y .min.js en las mismas carpetas que los originales.
Uso:
    python build_minified.py
"""
import os
import re


def minify_css(css: str) -> str:
    """Minifica CSS básico."""
    # Elimina comentarios /* ... */
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    # Reduce espacios en blanco
    css = re.sub(r"\s+", " ", css)
    # Elimina espacios alrededor de ciertos caracteres
    css = re.sub(r"\s*([{}:;,])\s*", r"\1", css)
    css = re.sub(r";\}", "}", css)
    return css.strip()


def minify_js(js: str) -> str:
    """Minifica JS básico."""
    # Elimina comentarios de una línea
    js = re.sub(r"//.*?\n", "\n", js)
    # Elimina comentarios multilinea /* ... */
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
    # Reduce espacios en blanco
    js = re.sub(r"\s+", " ", js)
    # Elimina espacios alrededor de operadores y delimitadores
    js = re.sub(r"\s*([{}();,:])\s*", r"\1", js)
    js = re.sub(r"\s*([+\-*/=<>!&|])\s*", r"\1", js)
    return js.strip()


def process_file(path: str, minifier: callable, suffix: str):
    """Minifica un archivo y guarda el resultado con .min."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    minified = minifier(content)
    base, ext = os.path.splitext(path)
    out_path = f"{base}{suffix}{ext}"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(minified)
    original_size = len(content)
    min_size = len(minified)
    reduction = (1 - min_size / original_size) * 100 if original_size else 0
    print(f"[OK] {path} -> {out_path} ({original_size} -> {min_size}, -{reduction:.1f}%)")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    static_dir = os.path.join(base_dir, "static")

    for root, _dirs, files in os.walk(static_dir):
        for filename in files:
            # Ignora archivos ya minificados
            if ".min." in filename:
                continue
            full_path = os.path.join(root, filename)
            if filename.endswith(".css"):
                process_file(full_path, minify_css, ".min")
            elif filename.endswith(".js"):
                process_file(full_path, minify_js, ".min")

    print("\nMinificación completada.")


if __name__ == "__main__":
    main()
