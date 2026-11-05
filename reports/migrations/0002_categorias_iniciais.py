from django.db import migrations

CATEGORIAS = [
    ("Esgoto a céu aberto", "🚽", "saneamento", "#7A3E00"),
    ("Água parada", "💧", "saneamento", "#1565C0"),
    ("Falta de água", "🚱", "saneamento", "#00838F"),
    ("Buraco", "🕳️", "pavimentacao", "#424242"),
    ("Barro", "🟫", "pavimentacao", "#6D4C41"),
]


def criar(apps, schema_editor):
    Categoria = apps.get_model("reports", "Categoria")
    for nome, icone, grupo, cor in CATEGORIAS:
        Categoria.objects.get_or_create(nome=nome, defaults={"icone": icone, "grupo": grupo, "cor_mapa": cor})


def remover(apps, schema_editor):
    apps.get_model("reports", "Categoria").objects.filter(nome__in=[c[0] for c in CATEGORIAS]).delete()


class Migration(migrations.Migration):
    dependencies = [("reports", "0001_inicial")]
    operations = [migrations.RunPython(criar, remover)]
