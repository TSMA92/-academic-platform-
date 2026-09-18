from django.db import models
from django.contrib.auth.models import User


class Classe(models.Model):
    """Une classe / promotion, ex: INGE2, TSMA"""
    nom = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nom


class Profil(models.Model):
    """Étend l'utilisateur Django de base avec un rôle et une classe"""
    ETUDIANT = 'etudiant'
    PROF = 'prof'
    ROLES = [
        (ETUDIANT, 'Étudiant'),
        (PROF, 'Professeur'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLES)
    classe = models.ForeignKey(Classe, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Matiere(models.Model):
    """Une matière enseignée, ex: Physique, Mathématiques"""
    nom = models.CharField(max_length=100)
    coefficient = models.PositiveIntegerField(default=1)
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='matieres')

    def __str__(self):
        return self.nom


class Note(models.Model):
    """Une note attribuée à un étudiant dans une matière"""
    etudiant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='notes')
    valeur = models.DecimalField(max_digits=4, decimal_places=2)
    periode = models.CharField(max_length=50, default='Trimestre 1')
    date_saisie = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.etudiant.username} - {self.matiere.nom} : {self.valeur}"