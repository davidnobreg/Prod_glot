import re

from rest_framework import serializers

from .forms import validar_cnpj, validar_cpf
from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    telefones = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = [
            'id',
            'uuid',
            'name',
            'nome_usual',
            'documento',
            'email',
            'telefones',
            'is_ativo',
        ]
        read_only_fields = ['id', 'uuid', 'telefones']

    def get_telefones(self, obj):
        return list(
            obj.telefones
            .filter(is_ativo=True)
            .values('id', 'numero', 'tipo', 'observacao')
        )

    def validate_documento(self, value):
        documento = re.sub(r'\D', '', value or '')

        if len(documento) == 11 and not validar_cpf(documento):
            raise serializers.ValidationError("CPF invalido.")
        if len(documento) == 14 and not validar_cnpj(documento):
            raise serializers.ValidationError("CNPJ invalido.")
        if len(documento) not in (11, 14):
            raise serializers.ValidationError("Documento deve ter 11 ou 14 digitos.")

        qs = Cliente.objects.filter(documento=documento)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Este CPF/CNPJ ja esta cadastrado.")

        return documento

    def validate_email(self, value):
        email = (value or '').strip().lower()
        if not email:
            return email

        qs = Cliente.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Este e-mail ja esta cadastrado.")

        return email
