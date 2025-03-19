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
        'criarClienteModal': True,
        'alterarCliente': True,
        'deletarCliente': True,
        'relatorioCliente': True,
        'relatorioClienteRelatorio': True,

        # MODULO EMPREENDIMENTO

        'selectEmpreendimento': True,
        'criarEmpreendimento': True,
        'listaEmpreendimento': True,
        'alterarEmpreendimento': True,
        'deletarEmpreendimento': True,
        'listaEmpreendimentoTabela': True,
        'listaQuadra': True,

        # MODULO VENDA
        'reservado': True,
        'relatorioReserva': True,
        'relatorioVenda': True,
        'listaVendaRelatorio': True,
        'cancelarReservadoCadastro': True,
        'cancelarReservado': True,
        'criarReservado': True,
        'criarVenda': True,
        'renovarReserva': True,
        'cancelarReservado': True,
        'cancelarVenda': True,

    }


class Corretor(AbstractUserRole):
    available_permissions = {
        # MODULO USUARIOS

        'listarUsuario': True,
        'criarUsuario': True,
        'alterarUsuario': True,
        'deletarUsuario': True,

        # MODULO CLIENTE

        'selectCliente': True,
        'criarCliente': True,
        'criarClienteModal': True,
        'alterarCliente': True,
        'deletarCliente': True,
        'relatorioCliente': True,
        'relatorioClienteRelatorio': True,

        # MODULO EMPREENDIMENTO

        'selectEmpreendimento': True,
        'criarEmpreendimento': True,
        'listaEmpreendimento': True,
        'alterarEmpreendimento': True,
        'deletarEmpreendimento': True,
        'listaEmpreendimentoTabela': True,
        'listaQuadra': True,

        # MODULO VENDA
        'reservado': True,
        'relatorioReserva': True,
        'relatorioVenda': True,
        'listaVendaRelatorio': True,
        'cancelarReservadoCadastro': True,
        'cancelarReservado': True,
        'criarReservado': True,
        'criarVenda': True,
        'renovarReserva': True,
        'cancelarReservado': True,
        'cancelarVenda': True,

    }


class Proprietario(AbstractUserRole):
    available_permissions = {
        # MODULO USUARIOS

        'listarUsuario': True,
        'criarUsuario': True,
        'alterarUsuario': True,
        'deletarUsuario': True,

        # MODULO CLIENTE

        'selectCliente': True,
        'criarCliente': True,
        'criarClienteModal': True,
        'alterarCliente': True,
        'deletarCliente': True,
        'relatorioCliente': True,
        'relatorioClienteRelatorio': True,

        # MODULO EMPREENDIMENTO

        'selectEmpreendimento': True,
        'criarEmpreendimento': True,
        'listaEmpreendimento': True,
        'alterarEmpreendimento': True,
        'deletarEmpreendimento': True,
        'listaEmpreendimentoTabela': True,
        'listaQuadra': True,

        # MODULO VENDA
        'reservado': True,
        'relatorioReserva': True,
        'relatorioVenda': True,
        'listaVendaRelatorio': True,
        'cancelarReservadoCadastro': True,
        'cancelarReservado': True,
        'criarReservado': True,
        'criarVenda': True,
        'renovarReserva': True,
        'cancelarReservado': True,
        'cancelarVenda': True,
    }
