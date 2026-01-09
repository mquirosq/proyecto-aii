"""
URL configuration for courses project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path
from main import views as main_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', main_views.home, name='home'),
    path('courses/', main_views.all_courses, name='all_courses'),
    path('populate/', main_views.populate_with_data, name='populate'),
]
from django.contrib import admin
