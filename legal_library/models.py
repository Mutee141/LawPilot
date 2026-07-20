from django.db import models

# No models are currently defined for this app.
from django.db import models
from django.conf import settings
import os

class Justice(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="e.g., Justice Ayesha A. Malik")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Justices"
        ordering = ['name']

    def __str__(self):
        return self.name


def judgment_upload_path(instance, filename):
    # This ensures files uploaded via admin match your directory structure exactly
    return os.path.join('legal_library', 'supreme_court', instance.justice.name, filename)

class Judgment(models.Model):
    title = models.CharField(max_length=500, help_text="e.g., C.A. 3/2016 or case title")
    case_number = models.CharField(max_length=100, blank=True, null=True, help_text="Extracted case number if available")
    year = models.IntegerField(blank=True, null=True)
    justice = models.ForeignKey(Justice, on_delete=models.CASCADE, related_name='judgments')
    pdf_file = models.FileField(upload_to=judgment_upload_path, max_length=1000)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.justice.name}"