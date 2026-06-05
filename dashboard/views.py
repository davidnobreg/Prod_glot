from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.views.generic import TemplateView

from empreendimentos.models import Empreendimento, Lote
from vendas.models import RegisterVenda


<<<<<<< HEAD
    context = {
        'total': total,
        'livre': livre,
        'reservas': reservas,

        'vendidos': vendidos,
    }
    return render(request, 'dash.html', context)
=======
class DashboardView(TemplateView):
	template_name = "dash.html"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)

		lotes = Lote.objects.select_related("quadra", "quadra__empr")
		vendas = RegisterVenda.objects.select_related(
			"cliente",
			"lote",
			"lote__quadra",
			"lote__quadra__empr",
			"corretor",
			"user",
		)

		vendas_ativas = vendas.filter(is_ativo=False).exclude(
			tipo_venda="CANCELADA"
		)
		vendas_vendidas = vendas_ativas.filter(tipo_venda="VENDIDO")
		valor_total_vendido = vendas_vendidas.aggregate(
			total=Coalesce(Sum("valor_financiado"), Decimal("0.00"))
		)["total"]

		context.update({
			"total_empreendimentos": Empreendimento.objects.filter(is_ativo=True).count(),
			"total_lotes": lotes.count(),
			"lotes_disponiveis": lotes.filter(situacao="DISPONIVEL").count(),
			"lotes_reservados": lotes.filter(situacao="RESERVADO").count(),
			"lotes_vendidos": lotes.filter(situacao="VENDIDO").count(),
			"lotes_bloqueados": lotes.filter(
				Q(situacao="CONSTRUTORA") |
				Q(situacao="INDISPONIVEL")
			).count(),
			"total_vendas_ativas": vendas_ativas.count(),
			"valor_total_vendido": self.formatar_moeda(valor_total_vendido),
			"ultimas_vendas": vendas_vendidas.order_by("-dt_venda", "-id")[:8],
			"resumo_empreendimentos": self.get_resumo_empreendimentos(),
		})

		return context

	def get_resumo_empreendimentos(self):
		return Empreendimento.objects.filter(is_ativo=True).annotate(
			total_lotes=Count("empreendimento__lotes", distinct=True),
			lotes_disponiveis=Count(
				"empreendimento__lotes",
				filter=Q(empreendimento__lotes__situacao="DISPONIVEL"),
				distinct=True,
			),
			lotes_reservados=Count(
				"empreendimento__lotes",
				filter=Q(empreendimento__lotes__situacao="RESERVADO"),
				distinct=True,
			),
			lotes_pre_reserva=Count(
				"empreendimento__lotes",
				filter=Q(empreendimento__lotes__situacao="PRE-RESERVA"),
				distinct=True,
			),
			lotes_vendidos=Count(
				"empreendimento__lotes",
				filter=Q(empreendimento__lotes__situacao="VENDIDO"),
				distinct=True,
			),
			lotes_bloqueados=Count(
				"empreendimento__lotes",
				filter=(
					Q(empreendimento__lotes__situacao="CONSTRUTORA") |
					Q(empreendimento__lotes__situacao="INDISPONIVEL")
				),
				distinct=True,
			),
		).order_by("nome")

	@staticmethod
	def formatar_moeda(valor):
		valor = valor or Decimal("0.00")
		return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
>>>>>>> feature/tailwind-paralelo
