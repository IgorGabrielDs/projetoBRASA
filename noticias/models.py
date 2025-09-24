from django.db import models
from django.db.models import Sum, Manager
from django.contrib.auth.models import User
from django.utils import timezone

class Noticia(models.Model):
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    autor = models.CharField(max_length=100)
    data_publicacao = models.DateTimeField(default=timezone.now)
    categoria = models.CharField(max_length=50, choices=[
        ('politica', 'Política'),
        ('esportes', 'Esportes'),
        ('tecnologia', 'Tecnologia'),
        ('entretenimento', 'Entretenimento'),
    ])
    destaque = models.BooleanField(default=False)
    salvo_por = models.ManyToManyField(User, related_name='noticias_salvas', blank=True)
    votos: Manager['Voto']     
    
    # agregados
    def score(self):
        return self.votos.aggregate(s=Sum('valor'))['s'] or 0

    def upvotes(self):
        return self.votos.filter(valor=1).count()

    def downvotes(self):
        return self.votos.filter(valor=-1).count()

    def __str__(self):
        return self.titulo
class Voto(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name="votos")
    valor = models.SmallIntegerField(choices=[(1, "Bom"), (-1, "Ruim")])

    class Meta:
        unique_together = ('usuario', 'noticia')