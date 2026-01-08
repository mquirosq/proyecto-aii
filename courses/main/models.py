from django.db import models

class Course(models.Model):
    LEVEL_CHOICES = [
        ('Principiante', 'Principiante'),
        ('Intermedio', 'Intermedio'),
        ('Avanzado', 'Avanzado'),
    ]

    PLATFORM_CHOICES = [
        ('Coursera', 'Coursera'),
        ('edX', 'edX'),
        ('Udemy', 'Udemy'),
        ('FutureLearn', 'FutureLearn'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    duration = models.FloatField(
        null=True, blank=True, help_text="Approximate duration in hours"
    )
    instructor = models.CharField(max_length=255, blank=True)
    rating = models.FloatField(null=True, blank=True)
    url = models.URLField(unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["platform", "title"]

    def __str__(self):
        return f"{self.title} ({self.platform})"
