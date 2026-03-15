"""
Corecode Serializers
"""

from rest_framework import serializers
from .models import AcademicSession, AcademicTerm, StudentClass, SiteConfig


class AcademicSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = ['id', 'name', 'code', 'start_date', 'end_date', 'is_current']


class AcademicTermSerializer(serializers.ModelSerializer):
    session_name = serializers.CharField(source='session.name', read_only=True)
    
    class Meta:
        model = AcademicTerm
        fields = ['id', 'session', 'session_name', 'term', 'name', 'start_date', 'end_date', 'is_current']


class StudentClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentClass
        fields = ['id', 'name', 'display_name', 'education_level', 'max_students', 'is_active']


class SiteConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteConfig
        fields = ['id', 'key', 'value', 'description', 'is_public']