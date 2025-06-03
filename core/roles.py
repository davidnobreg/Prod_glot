from rolepermissions.roles import AbstractUserRole


class Administrador(AbstractUserRole):
    available_permissions = {
        # MODULO USUARIOS

        'listarUsuario': True,
        'criarUsuario': True,
        'alterarUsuario': True,
        'deletarUsuario': True,
        'criarUsuarioEmpreendimento': True,
        'deleteUsuarioEmpreendimento': True,

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
        'reservarLote': True,
        'alterarLote': True,
        'reservadoDetalheEmpreendimento': True,
        'cancelarReservadoTemporaria':True,
        'renovarReservaTemporaria':True,


        # MODULO VENDA
        'reservado': True,
        'reservadoDetalhe': True,
        'relatorioReserva': True,
        'relatorioVenda': True,
        'listaVendaRelatorio': True,
        'cancelarReservadoCadastro': True,
        'criarReservado': True,
        'criarVenda': True,
        'renovarReserva': True,
        'cancelarReservado': True,
        'cancelarVenda': True,

    }


class Corretor(AbstractUserRole):
    available_permissions = {

        # MODULO CLIENTE

        'selectCliente': True,
        'criarCliente': True,
        'criarClienteModal': True,
        'relatorioClienteRelatorio': True,

        # MODULO EMPREENDIMENTO

        'selectEmpreendimento': True,
        'listaEmpreendimento': True,
        'listaQuadra': True,
        'alterarEmpreendimento': True,
        'reservarLote': True,
        'alterarLote': True,
        'reservadoDetalheEmpreendimento':True,
        'cancelarReservadoTemporaria':True,
        'renovarReservaTemporaria':True,
        


        # MODULO VENDA

        'reservado': True,
        'reservadoDetalhe': True,
        'listaVendaRelatorio': True,
        'criarReservado': True,
        'criarVenda': True,
        'renovarReserva': True,
        'cancelarReservado': True,



    }


class Proprietario(AbstractUserRole):
    available_permissions = {

        # MODULO EMPREENDIMENTO

        'selectEmpreendimento': True,
        'listaEmpreendimento': True,
        'listaQuadra': True,



    }
