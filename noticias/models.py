from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

class Assunto(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

class Noticia(models.Model):
    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    imagem = models.ImageField(upload_to="noticias/", null=True, blank=True)
    legenda = models.CharField(max_length=255, null=True, blank=True)

    assuntos = models.ManyToManyField(Assunto, related_name="noticias", blank=True)

    salvos = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='Salvo',
        related_name='noticias_salvas',
        blank=True,
    )

    def is_salva_por(self, user):
        if not user.is_authenticated:
            return False
        return self.salvos.filter(pk=user.pk).exists()

    def salvos_count(self):
        return self.salvos.count()

    def score(self):
        return sum(v.valor for v in self.votos.all())

    def upvotes(self):
        return self.votos.filter(valor=1).count()

    def downvotes(self):
        return self.votos.filter(valor=-1).count()

    def __str__(self):
        return self.titulo

class Voto(models.Model):
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name="votos")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    valor = models.IntegerField()  # 1 ou -1

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["noticia", "usuario"], name="unique_user_vote_per_news")
        ]

    def __str__(self):
        return f'{self.usuario} -> {self.valor} em {self.noticia}'
    
class Salvo(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('usuario', 'noticia')
        ordering = ['-criado_em']
