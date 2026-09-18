from django.contrib import admin
from .models import Classe, Profil, Matiere, Note

admin.site.register(Classe)
admin.site.register(Profil)
admin.site.register(Matiere)
admin.site.register(Note)