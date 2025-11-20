#!/bin/bash
# Script de verificación completa P0.1

echo "=== VERIFICACIÓN P0.1 ==="
echo ""

check_item() {
    echo -n "$1: "
    if eval "$2" > /dev/null 2>&1; then
        echo "✅ SÍ"
        return 0
    else
        echo "❌ NO"
        return 1
    fi
}

check_item "✓ .env existe" "[ -f .env ]"
check_item "✓ .env protegido" "git check-ignore .env"
check_item "✓ python-decouple instalado" "pip freeze | grep -q decouple"
check_item "✓ Settings usa config()" "grep -q 'from decouple import' StreamBus/settings.py"
check_item "✓ Carpeta DOC existe" "[ -d DOC ]"
check_item "✓ Carpeta TEST existe" "[ -d TEST ]"

echo ""
echo -n "✓ No hay secrets hardcoded: "
if ! grep -rq "HPsql2012\|cristian6163\|Buses2024\|django-insecure" \
    --include="*.py" --exclude-dir=DOC --exclude-dir=venv . 2>/dev/null; then
    echo "✅ SÍ"
else
    echo "❌ ENCONTRADOS"
fi

echo ""
echo "=== VERIFICACIÓN COMPLETADA ==="
