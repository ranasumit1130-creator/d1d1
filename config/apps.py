from django.apps import AppConfig


class ConfigConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'
    
    def ready(self):
        """Import signals when app is ready"""
        import config.models  # This triggers signal registration
