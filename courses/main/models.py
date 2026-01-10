from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

class Platform(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
    
class Instructor(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Course(models.Model):
    LEVEL_CHOICES = [
        ('Beginner', 'Principiante'),
        ('Intermediate', 'Intermedio'),
        ('Advanced', 'Avanzado'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    duration = models.FloatField(
        null=True, blank=True, help_text="Approximate duration in hours"
    )
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.FloatField(null=True, blank=True, 
                               validators=[
                                    MinValueValidator(0.0),
                                    MaxValueValidator(5.0)
                               ],
                               help_text="Rating from 0.0 to 5.0")

    url = models.URLField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)

    last_scraped = models.DateTimeField()

    class Meta:
        ordering = ["platform", "title"]

    def __str__(self):
        return f"{self.title} ({self.platform}) - {self.url}"

class UserCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    liked = models.BooleanField(default=False)      # usuario le gustó - Explícito
    disliked = models.BooleanField(default=False)   # usuario no le gustó - Explícito
    viewed = models.IntegerField(default=0)         # curso visto - Implícito
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')

