from django.contrib import admin

from .models import Apoio, Categoria, Demanda, HistoricoStatus


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "grupo", "ativa")
    list_filter = ("grupo", "ativa")


class HistoricoInline(admin.TabularInline):
    model = HistoricoStatus
    extra = 0
    can_delete = False
    readonly_fields = ("status_anterior", "status_novo", "observacao", "alterado_por", "alterado_em")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Demanda)
class DemandaAdmin(admin.ModelAdmin):
    list_display = ("protocolo", "categoria", "status", "total_afetados", "criado_em")
    list_filter = ("status", "categoria")
    search_fields = ("protocolo", "ponto_referencia")
    readonly_fields = ("protocolo", "status", "total_afetados", "criado_em", "atualizado_em")
    inlines = [HistoricoInline]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Apoio)
class ApoioAdmin(admin.ModelAdmin):
    list_display = ("demanda", "criado_em")
    readonly_fields = ("demanda", "telefone_hash", "criado_em")
