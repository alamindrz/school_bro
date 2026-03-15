"""
Site Configuration Services
Implements the "No-Customization" Rule
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from typing import Any, Optional, Dict, List
from django.utils import timezone

from ..models import SiteConfig
from ..constants import SiteConfigKey
from ..selectors import SiteConfigSelector
from ..exceptions import ConfigurationError


class SiteConfigService:
    """
    Site Configuration business operations
    All school-specific requirements become toggles here
    """
    
    @staticmethod
    @transaction.atomic
    def set_config(
        key: str,
        value: Any,
        user=None,
        description: str = "",
        is_public: bool = False
    ) -> SiteConfig:
        """
        Set a configuration value with audit trail
        
        Args:
            key: Configuration key from SiteConfigKey
            value: Value to set (will be converted to string)
            user: User setting the config
            description: Human-readable description
            is_public: Whether config is visible in public API
            
        Returns:
            SiteConfig: Updated or created config instance
            
        Raises:
            ConfigurationError: If key is invalid
        """
        if key not in SiteConfigKey.ALL_KEYS:
            raise ConfigurationError(f"Invalid configuration key: {key}")
        
        # Convert value to string for storage
        str_value = str(value) if value is not None else None
        
        config, created = SiteConfig.objects.update_or_create(
            key=key,
            defaults={
                'value': str_value,
                'updated_by': user,
                'description': description,
                'is_public': is_public,
                'updated_at': timezone.now()
            }
        )
        
        return config
    
    @staticmethod
    @transaction.atomic
    def set_many_configs(
        configs: Dict[str, Any],
        user=None
    ) -> List[SiteConfig]:
        """
        Set multiple configuration values at once
        
        Args:
            configs: Dictionary of key-value pairs
            user: User setting the configs
            
        Returns:
            List[SiteConfig]: Updated config instances
        """
        results = []
        for key, value in configs.items():
            config = SiteConfigService.set_config(
                key=key,
                value=value,
                user=user,
                description=f"Bulk update on {timezone.now().date()}"
            )
            results.append(config)
        return results
    
    @staticmethod
    @transaction.atomic
    def initialize_default_configs(user=None) -> Dict[str, SiteConfig]:
        """
        Initialize all required site configurations with defaults
        Called during system setup
        
        Args:
            user: User initializing the system
            
        Returns:
            Dict[str, SiteConfig]: Mapping of keys to config instances
        """
        defaults = {
            # Academic Structure
            SiteConfigKey.TERMS_PER_SESSION: '3',
            SiteConfigKey.CURRENT_SESSION: None,
            SiteConfigKey.CURRENT_TERM: None,
            
            # Admissions
            SiteConfigKey.ADMISSIONS_OPEN: 'False',
            SiteConfigKey.ADMISSION_DEADLINE: None,
            SiteConfigKey.AUTO_ENROLL_APPROVED: 'True',
          SiteConfigKey.APPLICATION_FEE: '5000',  # ADD THIS
          SiteConfigKey.ADMISSION_DEADLINE_DAYS: '30',  # ADD THIS

            
            # Finance
            SiteConfigKey.INCLUDE_FEE_BALANCE_IN_REPORT: 'True',
            SiteConfigKey.EXAM_CLEARANCE_REQUIRED: 'True',
            
            # Results
            SiteConfigKey.RESULT_TEMPLATE: 'standard',
            SiteConfigKey.PASS_MARK: '40',
            SiteConfigKey.DISTINCTION_MARK: '70',
            
            # Attendance
            SiteConfigKey.ATTENDANCE_TRACKING_ENABLED: 'True',
            
            # System
            SiteConfigKey.MAINTENANCE_MODE: 'False',
            SiteConfigKey.COMPANY_NAME: 'DETs Toolkit',
            SiteConfigKey.COMPANY_EMAIL: 'info@detstoolkit.edu.ng',
        }
        
        descriptions = {
            SiteConfigKey.TERMS_PER_SESSION: "Number of terms per academic session (Nigerian standard: 3)",
            SiteConfigKey.ADMISSIONS_OPEN: "Whether admissions are currently open",
            SiteConfigKey.AUTO_ENROLL_APPROVED: "Automatically enroll approved applicants",
            SiteConfigKey.EXAM_CLEARANCE_REQUIRED: "Require financial clearance for exams",
            SiteConfigKey.PASS_MARK: "Minimum score to pass (Nigerian standard: 40)",
            SiteConfigKey.DISTINCTION_MARK: "Minimum score for distinction (Nigerian standard: 70)",
            SiteConfigKey.COMPANY_NAME: "School/Organization name",
        }
        
        configs = {}
        for key, default_value in defaults.items():
            config, _ = SiteConfig.objects.get_or_create(
                key=key,
                defaults={
                    'value': default_value,
                    'updated_by': user,
                    'description': descriptions.get(key, f"Default configuration for {key}"),
                    'is_public': key in [
                        SiteConfigKey.COMPANY_NAME,
                        SiteConfigKey.ADMISSIONS_OPEN,
                    ]
                }
            )
            configs[key] = config
        
        return configs
    
    @staticmethod
    def get_config(key: str, default=None) -> Any:
        """
        Get configuration value with type inference
        Wrapper around SiteConfig.get for service layer
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Any: Configuration value with correct type
        """
        return SiteConfig.get(key, default)
    
    @staticmethod
    def is_maintenance_mode() -> bool:
        """Check if system is in maintenance mode"""
        return SiteConfigService.get_config(
            SiteConfigKey.MAINTENANCE_MODE,
            False
        )
    
    @staticmethod
    def are_admissions_open() -> bool:
        """Check if admissions are currently open"""
        return SiteConfigService.get_config(
            SiteConfigKey.ADMISSIONS_OPEN,
            False
        )
    
    @staticmethod
    def get_pass_mark() -> int:
        """Get the current pass mark"""
        return SiteConfigService.get_config(
            SiteConfigKey.PASS_MARK,
            40
        )
    
    @staticmethod
    def get_distinction_mark() -> int:
        """Get the current distinction mark"""
        return SiteConfigService.get_config(
            SiteConfigKey.DISTINCTION_MARK,
            70
        )
    
    @staticmethod
    def is_exam_clearance_required() -> bool:
        """Check if financial clearance is required for exams"""
        return SiteConfigService.get_config(
            SiteConfigKey.EXAM_CLEARANCE_REQUIRED,
            True
        )