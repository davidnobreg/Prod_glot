document.addEventListener("DOMContentLoaded", function () {

    // -----------------------------
    // Função para preencher modal de cliente
    // -----------------------------
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

    // -----------------------------
    // Modal de Deleção de Cliente
    // -----------------------------
    const clienteModalDelete = document.getElementById('clienteModalDelete');
    if (clienteModalDelete) {
        clienteModalDelete.addEventListener('show.bs.modal', event => {
            const button = event.relatedTarget;
            const clienteId = button.getAttribute('data-cliente-id');

            fetch(`/clientes/select/${clienteId}/`)
                .then(response => {
                    if (!response.ok) throw new Error(`Erro na requisição: ${response.status}`);
                    return response.json();
                })
                .then(data => preencherModalCliente(clienteId, data))
                .catch(error => {
                    console.error('Erro ao buscar dados do cliente:', error);
                });
        });

        const btnDeletarCliente = document.getElementById("btn-deletar-cliente");
        if (btnDeletarCliente) {
            btnDeletarCliente.addEventListener("click", () => {
                const clienteId = document.getElementById("cliente-id").textContent;
                window.location.href = `/clientes/delete_cliente/${clienteId}/`;
            });
        }
    } else {
        console.warn("Modal clienteModalDelete não encontrado.");
    }

    // -----------------------------
    // Função para preencher modal de empreendimento
    // -----------------------------
    function preencherModalEmpreendimento(empreendimentoId, data) {
        if (!data || typeof data !== 'object') {
            console.error('Dados do empreendimento inválidos:', data);
            return;
        }

        document.getElementById('empreendimento-id').value = empreendimentoId;
        document.getElementById('empreendimento-id-display').textContent = data.id;
        document.getElementById('empreendimento-nome').textContent = data.nome || 'Nome não encontrado';
    }

    // -----------------------------
    // Modal de Deleção de Empreendimento
    // -----------------------------
    const empreendimentoModal = document.getElementById('empreendimentoModal');
    const formDeletarEmpreendimento = document.getElementById("form-deletar-empreendimento");

    if (empreendimentoModal) {
        empreendimentoModal.addEventListener('show.bs.modal', event => {
            const button = event.relatedTarget;
            const empreendimentoId = button.getAttribute('data-id');

            fetch(`/empreendimentos/select/${empreendimentoId}/`)
                .then(response => {
                    if (!response.ok) throw new Error(`Erro na requisição: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    preencherModalEmpreendimento(empreendimentoId, data);

                    if (formDeletarEmpreendimento) {
                        formDeletarEmpreendimento.setAttribute("action", `/empreendimentos/deleta_empreendimento/${data.id}/`);
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

var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
tooltipTriggerList.forEach(function (tooltipTriggerEl) {
    new bootstrap.Tooltip(tooltipTriggerEl)
})

async function compartilharRelatorio() {
    const situacao = new URLSearchParams(window.location.search).get('situacao') || 'TODOS';

    try {
        const response = await fetch(`/empreendimentos/relatorio-lotes/?situacao=${situacao}`);

        if (!response.ok) {
            alert('Erro ao gerar o relatório');
            return;
        }

        const blob = await response.blob();
        const file = new File([blob], "relatorio_lotes.pdf", { type: "application/pdf" });

        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            await navigator.share({
                title: "Relatório de Lotes",
                text: "Segue o relatório de lotes gerado.",
                files: [file]
            });
        } else {
            // Fallback confiável para download no Edge Desktop
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.setAttribute('download', file.name);
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                URL.revokeObjectURL(url);
                document.body.removeChild(a);
            }, 1000);

            alert("Este navegador não suporta compartilhamento direto. O relatório foi baixado.");
        }
    } catch (err) {
        console.error("Erro ao compartilhar:", err);
        alert("Ocorreu um erro ao gerar ou compartilhar o relatório.");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Verifica se o navegador suporta navigator.share com arquivos
    if (!navigator.canShare || !navigator.canShare({ files: [new File([""], "teste.pdf", { type: "application/pdf" })] })) {
        const botao = document.querySelector('button[onclick="compartilharRelatorio()"]');
        if (botao) botao.style.display = 'none';
    }
});