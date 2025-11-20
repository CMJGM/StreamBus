# Directorio de Tests - StreamBus

Este directorio contiene todos los archivos de tests del proyecto, organizados por aplicación.

## Estructura

```
TEST/
├── buses/
│   └── tests.py
├── categoria/
│   └── tests.py
├── empleados/
│   └── tests.py
├── informes/
│   └── tests.py
├── inicio/
│   └── tests.py
├── siniestros/
│   └── tests.py
├── sit/
│   └── tests.py
├── sucursales/
│   └── tests.py
└── usuarios/
    └── tests.py
```

## Ejecución de Tests

### Todos los tests
```bash
python manage.py test TEST
```

### Tests de una aplicación específica
```bash
python manage.py test TEST.informes
```

### Con cobertura
```bash
coverage run --source='.' manage.py test TEST
coverage report
coverage html
```

## Notas

- Los archivos `tests.py` en cada carpeta de app (`informes/tests.py`, etc.) ahora son solo placeholders
- Los tests reales están aquí en `TEST/`
- Cada subdirectorio tiene un `__init__.py` para que Python lo reconozca como paquete

## Próximos Pasos

1. Implementar tests de seguridad (P0.3)
2. Tests de validación de archivos (P0.4)
3. Tests de rendimiento (P1)
4. Coverage objetivo: 80%+
