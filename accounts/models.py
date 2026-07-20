from django.contrib.auth.models import AbstractUser
from django.db import models
from firms.models import Firm

class User(AbstractUser):
    ROLE_CHOICES = [
        ('firm_owner', 'Firm Owner'),
        ('system_admin', 'System Admin'),
        ('senior_lawyer', 'Senior Lawyer'),
        ('junior_lawyer', 'Junior Lawyer'),
        ('assistant', 'Assistant / Clerk'),
        ('accountant', 'Accountant'),
        ('client', 'Client'),
    ]

    firm = models.ForeignKey(
        Firm,
        on_delete=models.CASCADE,
        related_name='users',
        null=True,
        blank=True
    )
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='junior_lawyer'
    )

    phone_number = models.CharField(max_length=15, blank=True, null=True)

    managed_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff'
    )

    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True, null=True)
    cnic_no = models.CharField(max_length=50, blank=True, null=True)
    ntn_no = models.CharField(max_length=50, blank=True, null=True)
    landline_no = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    secret_question = models.CharField(max_length=255, blank=True, null=True)
    secret_answer = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        if full_name:
            return f"{full_name} ({self.get_role_display()})"
        return f"{self.username} ({self.get_role_display()})"
