from django.conf import settings


def test_hasher_padrao_e_argon2():
    assert settings.PASSWORD_HASHERS[0].endswith("Argon2PasswordHasher")


def test_senha_minima_de_10_caracteres():
    validador = next(v for v in settings.AUTH_PASSWORD_VALIDATORS if "MinimumLength" in v["NAME"])
    assert validador["OPTIONS"]["min_length"] == 10


def test_rotas_carregam_sem_erro():
    from django.urls import get_resolver

    assert get_resolver().url_patterns
