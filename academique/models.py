from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


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
    """Une matière/UE enseignée, avec son nombre de crédits (système LMD)"""
    nom = models.CharField(max_length=100)
    credits = models.PositiveIntegerField(default=3, help_text="Nombre de crédits LMD/ECTS")
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='matieres')

    def __str__(self):
        return f"{self.nom} ({self.credits} crédits)"


class Note(models.Model):
    """Une note attribuée à un étudiant dans une matière, pour une session donnée"""
    NORMALE = 'normale'
    RATTRAPAGE = 'rattrapage'
    SESSIONS = [
        (NORMALE, 'Session normale'),
        (RATTRAPAGE, 'Rattrapage'),
    ]

    SEUIL_VALIDATION = Decimal('10')      # moyenne minimale pour valider une matière seule
    SEUIL_ELIMINATOIRE = Decimal('7')     # en dessous : rattrapage obligatoire, pas de compensation possible

    etudiant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='notes')
    valeur = models.DecimalField(max_digits=4, decimal_places=2)
    session = models.CharField(max_length=10, choices=SESSIONS, default=NORMALE)
    periode = models.CharField(max_length=50, default='Semestre 1')
    date_saisie = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('etudiant', 'matiere', 'session', 'periode')

    def __str__(self):
        return f"{self.etudiant.username} - {self.matiere.nom} ({self.session}) : {self.valeur}"

    @staticmethod
    def note_finale(etudiant, matiere, periode):
        """
        Note définitive pour une matière/période :
        - la note de rattrapage (si elle existe) remplace la note normale
        - sinon on retourne la note normale
        """
        rattrapage = Note.objects.filter(
            etudiant=etudiant, matiere=matiere, periode=periode, session=Note.RATTRAPAGE
        ).first()
        if rattrapage:
            return rattrapage.valeur

        normale = Note.objects.filter(
            etudiant=etudiant, matiere=matiere, periode=periode, session=Note.NORMALE
        ).first()
        return normale.valeur if normale else None

    @staticmethod
    def matieres_eliminatoires(etudiant, periode):
        """
        Renvoie la liste des matières où la note finale est < 7/20
        (rattrapage obligatoire, aucune compensation possible pour celles-ci)
        """
        matieres = Matiere.objects.filter(classe__profil__user=etudiant).distinct()
        eliminatoires = []
        for matiere in matieres:
            note = Note.note_finale(etudiant, matiere, periode)
            if note is not None and note < Note.SEUIL_ELIMINATOIRE:
                eliminatoires.append(matiere)
        return eliminatoires

    @staticmethod
    def moyenne_semestre(etudiant, periode):
        """
        Moyenne pondérée par les crédits, sur toutes les matières du semestre
        où une note finale existe. Retourne None si aucune note.
        """
        matieres = Matiere.objects.filter(classe__profil__user=etudiant).distinct()
        total_points = Decimal('0')
        total_credits = 0
        for matiere in matieres:
            note = Note.note_finale(etudiant, matiere, periode)
            if note is not None:
                total_points += note * matiere.credits
                total_credits += matiere.credits
        if total_credits == 0:
            return None
        return total_points / total_credits

    @staticmethod
    def semestre_valide(etudiant, periode):
        """
        Un semestre est validé si :
        - aucune matière n'est en dessous du seuil éliminatoire (7/20), ET
        - la moyenne pondérée du semestre est >= 10/20 (compensation entre matières)
        Retourne True / False, ou None si pas assez de notes pour juger.
        """
        eliminatoires = Note.matieres_eliminatoires(etudiant, periode)
        moyenne = Note.moyenne_semestre(etudiant, periode)

        if moyenne is None:
            return None
        if eliminatoires:
            return False  # au moins une matière < 7/20 => rattrapage obligatoire
        return moyenne >= Note.SEUIL_VALIDATION