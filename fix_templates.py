# fix_templates.py
import re
from pathlib import Path

def clean_template_response(content: str) -> str:
    """Limpeza forte para Starlette 1.0"""
    original = content

    # 1. Remove duplicatas de request=request
    content = re.sub(r'request=request,\s*request=request', 'request=request', content)
    content = re.sub(r'request=request\s*,\s*request=request', 'request=request', content)
    
    # 2. Remove comentários problemáticos
    content = re.sub(r',\s*request=request\s*#.*', '', content)
    content = re.sub(r'request=request\s*#.*', 'request=request', content)

    # 3. Corrige formatos antigos
    content = re.sub(
        r'TemplateResponse\(\s*["\']([^"\']+)["\']\s*,\s*(\{[^}]+\})',
        r'''TemplateResponse(request=request,
        name="\1",
        context=\2''',
        content
    )

    # 4. Corrige com status_code
    content = re.sub(
        r'TemplateResponse\(\s*["\']([^"\']+)["\']\s*,\s*(\{[^}]+\})\s*(,\s*status_code=\d+)?',
        r'''TemplateResponse(request=request,
        name="\1",
        context=\2\3''',
        content
    )

    # 5. Garante que request fique apenas uma vez no início
    content = re.sub(
        r'TemplateResponse\(\s*(?:request=request,\s*)+',
        r'TemplateResponse(request=request, ',
        content
    )

    # 6. Formata bonitinho
    content = re.sub(r',\s*name=', ',\n        name=', content)
    content = re.sub(r',\s*context=', ',\n        context=', content)
    content = re.sub(r',\s*status_code=', ',\n        status_code=', content)

    return content


def main():
    project_root = Path.cwd()
    
    print("[INFO] Aplicando correção AGRESSIVA contra 'keyword argument repeated: request'\n")
    
    files_fixed = 0
    for py_file in project_root.rglob("*.py"):
        if any(ex in str(py_file) for ex in ['.venv', 'venv', 'env', '__pycache__', 'migrations']):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                original = f.read()
            
            new_content = clean_template_response(original)
            
            if new_content != original:
                # Backup
                backup = py_file.with_suffix('.py.bak2')
                with open(backup, 'w', encoding='utf-8') as f:
                    f.write(original)
                
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                print(f"[OK] Corrigido: {py_file.name}")
                files_fixed += 1
            else:
                # Mesmo sem mudança, verifica se tem duplicata residual
                if 'request=request' in original or 'request=request' in original:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"[OK] Limpeza de duplicata: {py_file.name}")
                    files_fixed += 1
                    
        except Exception as e:
            print(f"[ERRO] Erro em {py_file.name}: {e}")

    print(f"\n[FIM] Finalizado! {files_fixed} arquivo(s) processado(s).")
    print("   Backups criados com .bak2")


if __name__ == "__main__":
    main()