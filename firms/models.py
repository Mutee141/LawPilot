from django.db import models

# Create your models here.
from django.db import models
import uuid

class Firm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, blank=True, null=True)

    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    court = models.ForeignKey('cases.Court', on_delete=models.SET_NULL, null=True, blank=True, related_name='associated_firms')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
