from django.contrib import admin

# Register your models here.
from .models import Course, Platform, Category, Instructor, UserCourse
admin.site.register(Course)
admin.site.register(Platform)
admin.site.register(Category)
admin.site.register(Instructor)
admin.site.register(UserCourse)