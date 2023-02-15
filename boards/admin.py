from django.contrib import admin

from .models import Board


class BoardAdmin(admin.ModelAdmin):
    filter_horizontal = ['members']
    
admin.site.register(Board, BoardAdmin)