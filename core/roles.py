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
        'alterarCliente': True,
        'deletarCliente': True,
        'relatorioCliente': True,
        'relatorioClienteRelatorio': True,

        # MODULO DOCUMENTO

        'proposta': True,
        'propostaRascunho': True,
        'uploadDocumento': True,

        # MODULO DOCUMENTOS (reestruturação)
        'documentoModelos': True,
        'documentoConfig': True,
        'documentoGerar': True,
        'documentoFinalizar': True,
        'documentoVisualizar': True,
        'distratoGerenciar': True,
        'distratoConcluir': True,

        # MODULO EMPREENDIMENTO

        'selectEmpreendimento': True,
        'criarEmpreendimento': True,
        'listaEmpreendimento': True,
        'alterarEmpreendimento': True,
        'deletarEmpreendimento': True,
        'listaEmpreendimentoTabela': True,
        'listaReservasTemporaria': True,
        'listaQuadra': True,
        'liberaLote': True,
        'reservarLote': True,
        'alterarLote': True,
        'atualizarLotes': True,
        'reservadoDetalheEmpreendimento': True,
        'cancelarReservadoTemporaria':True,
        'cancelarReservadoTemporariaLista':True,
        'renovarReservaTemporaria':True,


        # MODULO VENDA
        'aceitaReserva': True,
        'analiseReserva': True,
        'reservado': True,
        'reservadoDetalhe': True,
        'relatorioReserva': True,
        'relatorioVenda': True,
        'listasAnalises': True,
        'listaVenda': True,
        'listaVendaRelatorio': True,
        'cancelarReservadoCadastro': True,
        'criarReservado': True,
        'criarVenda': True,
        'renovarReserva': True,
        'cancelarReservado': True,
        'cancelarAceiteReservado': True,
        'cancelarVenda': True,

    }


class Corretor(AbstractUserRole):
    available_permissions = {

        # MODULO CLIENTE

        'selectCliente': True,
        'criarCliente': True,
        'alterarCliente': True,
        'relatorioCliente': True,
        'relatorioClienteRelatorio': True,

        # MODULO DOCUMENTO

        'proposta': True,
        'propostaRascunho': True,

        # MODULO DOCUMENTOS (reestruturação)
        'documentoGerar': True,
        'documentoVisualizar': True,

        # MODULO EMPREENDIMENTO

        'selectEmpreendimento': True,
        'listaEmpreendimento': True,
        'listaQuadra': True,
        'liberaLote': True,
        'alterarEmpreendimento': True,
        'reservarLote': True,
        #'alterarLote': True,
        #'atualizarLotes': True,
        'reservadoDetalheEmpreendimento':True,
        'cancelarReservadoTemporaria':True,
        'cancelarReservadoTemporariaLista': True,
        'renovarReservaTemporaria':True,


        # MODULO VENDA

        'analiseReserva': True,
        'cancelarAceiteReservado': True,
        'cancelarReservadoCadastro': True,
        'criarReservado': True,
        'criarVenda': True,
        'renovarReserva': True,
        'reservado': True,
        'reservadoDetalhe': True,



    }


class Proprietario(AbstractUserRole):
    available_permissions = {

        # MODULO EMPREENDIMENTO

        'selectEmpreendimento': True,
        'listaEmpreendimento': True,
        'listaQuadra': True,



    }
