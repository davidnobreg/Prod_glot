document.addEventListener("DOMContentLoaded", function () {
    // Código para Clientes
    const clienteModalDelete = document.getElementById('clienteModalDelete');

    function preencherModalCliente(clienteId, data) {
        if (!data || typeof data !== 'object') {
            console.error('Dados do cliente inválidos:', data);
            return;
        }

        document.getElementById('cliente-id').textContent = clienteId;
        document.getElementById('cliente-id-display').textContent = clienteId;
        document.getElementById('cliente-name').textContent = data.name || 'Nome não encontrado';
        document.getElementById('cliente-documento').textContent = data.documento || 'Documento não encontrado';
        document.getElementById('cliente-email').textContent = data.email || 'Email não encontrado';
    }

    if (clienteModalDelete) {
        clienteModalDelete.addEventListener('show.bs.modal', event => {
            const button = event.relatedTarget;
            const clienteId = button.getAttribute('data-cliente-id');

            fetch(`/clientes/select/${clienteId}/`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Erro na requisição: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => preencherModalCliente(clienteId, data))
                .catch(error => {
                    console.error('Erro ao buscar dados do cliente:', error);
                    // Adicione aqui uma lógica para exibir uma mensagem de erro ao usuário
                });
        });

        const btnDeletarCliente = document.getElementById("btn-deletar-cliente");
        if (btnDeletarCliente) {
            btnDeletarCliente.addEventListener("click", function () {
                let clienteId = document.getElementById("cliente-id").textContent;
                window.location.href = `/clientes/delete_cliente/${clienteId}/`; // Redireciona para a URL de exclusão
            });
        }
    } else {
        console.error("Modal clienteModalDelete não encontrado.");
    }

    // Código para Empreendimentos
    const empreendimentoModal = document.getElementById('empreendimentoModal');

    function preencherModalEmpreendimento(empreendimentoId, data) {
        if (!data || typeof data !== 'object') {
            console.error('Dados do empreendimento inválidos:', data);
            return;
        }

        document.getElementById('empreendimento-id').textContent = data.id;
        document.getElementById('empreendimento-id-display').textContent = data.id;
        document.getElementById('empreendimento-nome').textContent = data.nome || 'Nome não encontrado';
    }

    if (document.querySelectorAll(".btn-detalhes-empreendimento")) {
        document.querySelectorAll(".btn-detalhes-empreendimento").forEach(button => {
            button.addEventListener("click", function () {
                const empreendimentoId = this.getAttribute("data-id");

                fetch(`/empreendimentos/select/${empreendimentoId}/`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`Erro na requisição: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        preencherModalEmpreendimento(empreendimentoId, data);
                        new bootstrap.Modal(empreendimentoModal).show();
                    })
                    .catch(error => {
                        console.error("Erro ao buscar detalhes do empreendimento:", error);
                        alert("Ocorreu um erro ao buscar os detalhes do empreendimento.");
                    });
            });
        });
    }

    function adicionarListenerDeletarEmpreendimento() {
        const btnDeletarEmpreendimento = document.getElementById("btn-deletar-empreendimento");

        console.log(btnDeletarEmpreendimento)

        if (btnDeletarEmpreendimento) {
            btnDeletarEmpreendimento.addEventListener("click", function () {
                const empreendimentoId = document.getElementById("empreendimento-id").textContent;
                window.location.href = `/empreendimentos/deleta_empreendimento/${empreendimentoId}/`;
            });
        } else {
            console.error("Elemento btn-deletar-empreendimento não encontrado dentro do modal.");
        }
    }

    // Garante que o listener seja adicionado após o modal ser exibido e o elemento estar no DOM
    const observer = new MutationObserver(function (mutations) {
        if (document.getElementById("btn-deletar-empreendimento")) {
            adicionarListenerDeletarEmpreendimento();
            observer.disconnect(); // Desconecta o observador após encontrar o elemento
        }
    });

    if (empreendimentoModal) {
        empreendimentoModal.addEventListener('shown.bs.modal', function () {
            observer.observe(empreendimentoModal, { childList: true, subtree: true });
        });
    } else {
        //console.error("Modal empreendimentoModal não encontrado.");
    }
});