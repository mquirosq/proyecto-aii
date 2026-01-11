"""
URL configuration for courses project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from main import views as main_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', main_views.home, name='home'),
    path('courses/', main_views.all_courses, name='all_courses'),
    path('courses/<int:course_id>/', main_views.course_detail, name='course_detail'),
    path('populate/', main_views.populate_with_data, name='populate'),
    path('load-recommender-data/', main_views.load_recommender_data, name='load_recommender_data'),
    path('about/', main_views.about, name='about'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', main_views.signup, name='signup'),
    path('admin-panel/', main_views.admin_panel, name='admin_panel'),
    path('courses/<int:course_id>/feedback/<str:action>/', main_views.toggle_feedback, name='toggle_feedback'),
    path('courses/<int:course_id>/viewed/', main_views.mark_course_viewed, name='mark_course_viewed'),
]
