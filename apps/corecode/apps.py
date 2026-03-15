from django.apps import AppConfig

class CorecodeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.corecode'
    label = 'corecode'
    verbose_name = 'Core Foundation'
    
    def ready(self):
        """
        Import signals only when app is ready.
        No cross-app signals allowed per manifesto.
        """
        import apps.corecode.signals.handlers
        
        # Safely initialize the menu registry after all apps and models are loaded
        from apps.corecode.navigation import MenuRegistry
        MenuRegistry.initialize()
