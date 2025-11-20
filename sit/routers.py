# sit/routers.py
class SITRouter:
    """
    Router para dirigir queries de modelos SIT a la base correcta
    """
    
    def db_for_read(self, model, **hints):
        """Direccionar lecturas a la base correcta"""
        if model._meta.app_label == 'sit':
            return 'SIT'
        return None
    
    def db_for_write(self, model, **hints):
        """Prevenir escrituras en modelos SIT (solo lectura)"""
        if model._meta.app_label == 'sit':
            return None  # Previene escrituras
        return None
    
    def allow_relation(self, obj1, obj2, **hints):
        """Permitir relaciones si ambos modelos están en la misma DB"""
        return True
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Controlar migraciones - nunca migrar a SIT"""
        if db == 'SIT':
            return False  # Nunca crear tablas en SIT
        if app_label == 'sit':
            return db == 'default'  # Tablas de mapeo van a default
        return None