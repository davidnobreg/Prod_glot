from rest_framework import serializers
from .models import Cliente

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nome', 'documento', 'email', 'fone', 'is_ativo']

    def validate_documento(self, value):
        if not Cliente.validar_documento(value):
            raise serializers.ValidationError("Documento inválido. Informe um CPF ou CNPJ válido.")
        return ''.join(filter(str.isdigit, value))  # salvar apenas números

