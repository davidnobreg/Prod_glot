document.addEventListener("DOMContentLoaded", function () {

    // ==============================
    // Modal de Empreendimento (Deleção)
    // ==============================
    function preencherModalEmpreendimento(empreendimentoId, data) {
        if (!data || typeof data !== 'object') {
            console.error('Dados do empreendimento inválidos:', data);
            return;
        }

        document.getElementById('empreendimento-id').value = empreendimentoId;
        document.getElementById('empreendimento-id-display').textContent = data.id;
        document.getElementById('empreendimento-nome').textContent = data.nome || 'Nome não encontrado';
    }

    const empreendimentoModal = document.getElementById('empreendimentoModal');
    const formDeletarEmpreendimento = document.getElementById("form-deletar-empreendimento");

    if (empreendimentoModal) {
        empreendimentoModal.addEventListener('show.bs.modal', event => {
            const button = event.relatedTarget;
            const empreendimentoUuid = button.getAttribute('data-uuid');

            fetch(`/empreendimentos/select/${empreendimentoUuid}/`)
                .then(response => {
                    if (!response.ok) throw new Error(`Erro na requisição: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    preencherModalEmpreendimento(empreendimentoUuid, data);

                    if (formDeletarEmpreendimento) {
                        formDeletarEmpreendimento.setAttribute("action", `/empreendimentos/deleta_empreendimento/${empreendimentoUuid}/`);
                    }
                })
                .catch(error => {
                    console.error("Erro ao buscar detalhes do empreendimento:", error);
                    alert("Erro ao buscar detalhes do empreendimento.");
                });
        });
    } else {
        console.warn("Modal empreendimentoModal não encontrado.");
    }

    // ==============================
    // Modal de Empreendimento (ARQUIVO)
    // ==============================
    function preencherModalEmpreendimento(empreendimentoId, data) {
        if (!data || typeof data !== 'object') {
            console.error('Dados do empreendimento inválidos:', data);
            return;
        }

        document.getElementById('empreendimento-id').value = empreendimentoId;
        document.getElementById('empreendimento-id-display').textContent = data.id;
        document.getElementById('empreendimento-nome').textContent = data.nome || 'Nome não encontrado';
    }

    const arquivoModal = document.getElementById('arquivoModal');
    const formArquivoEmpreendimento = document.getElementById("form-arquivo-empreendimento");

    if (arquivoModal) {
        arquivoModal.addEventListener('show.bs.modal', event => {
            const button = event.relatedTarget;
            const empreendimentoId = button.getAttribute('data-id');

            fetch(`/empreendimentos/select/${empreendimentoId}/`)
                .then(response => {
                    if (!response.ok) throw new Error(`Erro na requisição: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    preencherModalEmpreendimento(empreendimentoId, data);

                    if (formArquivoEmpreendimento) {
                        formArquivoEmpreendimento.setAttribute("action", `/empreendimentos/insert_arq/${data.id}/`);
                    }
                })
                .catch(error => {
                    console.error("Erro ao buscar detalhes do empreendimento:", error);
                    alert("Erro ao buscar detalhes do empreendimento.");
                });
        });
    } else {
        console.warn("Modal empreendimentoModal não encontrado.");
    }
});
