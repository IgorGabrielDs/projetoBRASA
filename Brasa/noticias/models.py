from django.db import models
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

    # agregados
    def score(self):
        from django.db.models import Sum
        return self.votos.aggregate(s=Sum('valor'))['s'] or 0

    def upvotes(self):
        return self.votos.filter(valor=1).count()

    def downvotes(self):
        return self.votos.filter(valor=-1).count()

    def __str__(self):
        return self.titulo


class Voto(models.Model):
    UP = 1
    DOWN = -1
    VALORES = ((UP, 'Upvote'), (DOWN, 'Downvote'))

    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='votos')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votos')
    valor = models.SmallIntegerField(choices=VALORES)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('noticia', 'usuario')          # 1 voto por usuário por notícia
        indexes = [models.Index(fields=['noticia', 'usuario'])]

    def __str__(self):
        return f'{self.usuario} → {self.noticia} = {self.valor}'