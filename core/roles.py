from rolepermissions.roles import AbstractUserRole


class Administrador(AbstractUserRole):
    available_permissions = {
        # MODULO USUARIOS
        'listarUsuario': True,
        'criarUsuario': True,
        'alterarUsuario': True,
        'deletarUsuario': True,

        # MODULO CLIENTE
        'selectCliente': True,
        'criarCliente': True,
        'alterarCliente': True,
        'deletarCliente': True,
        'relatorioCliente': True,
        'criarClienteModal': True,

        # MODULO EMPREENDIMENTO
        'selectEmpresas': True,
        'criarEmpresas': True,
        'alterarEmpresas': True,
        'deletarEmpresas': True,
        'relatorioEmpresas': True,
        'criarEmpresasModal': True,
        'alterarEmpresasModal': True,
        'deletarEmpresasModal': True,

        # MODULO VENDA
        'selectVendas': True,
        'relatorioVendas': True,
        'criarVendas': True,
        'alterarVendas': True,
        'deletarVendas': True,

    }


class Corretor(AbstractUserRole):
    available_permissions = {
        'listarUsuario': True,
    }


class Proprietario(AbstractUserRole):
    available_permissions = {
        'listarUsuario': True,
    }
