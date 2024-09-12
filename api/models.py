from django.db import models


class Keyword(models.Model):
    id = models.AutoField(primary_key=True)
    keyword = models.CharField(max_length=255, unique=True)
    def __str__(self):
        return f"{self.keyword} ({self.id})"