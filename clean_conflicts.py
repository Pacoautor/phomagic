import os
import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent / "products"

pattern = re.compile(r"^<{7}|^={7}|^>{7}")

for py_file in PROJECT_DIR.rglob("*.py"):
    try:
        with open(py_file, encoding="utf-8") as f:
            lines = f.readlines()

        cleaned_lines = [line for line in lines if not pattern.match(line)]

        with open(py_file, "w", encoding="utf-8") as f:
            f.writelines(cleaned_lines)

        print(f"✅ Limpio: {py_file}")
    except Exception as e:
        print(f"⚠️ Error con {py_file}: {e}")

print("\n🧹 Limpieza completada. Ahora puedes ejecutar:")
print("git add . && git commit -m 'Limpieza automática de conflictos' && git push -u origin main")
