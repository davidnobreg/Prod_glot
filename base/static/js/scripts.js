document.addEventListener("DOMContentLoaded", function () {

    // ==============================
    // Máscaras automáticas CPF/CNPJ e Telefone
    // ==============================
    function aplicarMascaraDocumento(input) {
        let value = input.value.replace(/\D/g, "");

        if (value.length <= 11) {
            // CPF
            value = value
                .replace(/(\d{3})(\d)/, "$1.$2")
                .replace(/(\d{3})(\d)/, "$1.$2")
                .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
        } else if (value.length <= 14) {
            // CNPJ
            value = value
                .replace(/^(\d{2})(\d)/, "$1.$2")
                .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
                .replace(/\.(\d{3})(\d)/, ".$1/$2")
                .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
        }

        input.value = value;
    }

    function aplicarMascaraTelefone(input) {
        let value = input.value.replace(/\D/g, "");

        if (value.length > 10) {
            // Celular
            value = value.replace(/^(\d{2})(\d{5})(\d{4}).*/, "($1) $2-$3");
        } else {
            // Telefone fixo
            value = value.replace(/^(\d{2})(\d{4})(\d{4}).*/, "($1) $2-$3");
        }

        input.value = value;
    }

    // Aplica máscaras automaticamente em todos os inputs
    document.querySelectorAll(".mask-doc").forEach(input => {
        input.addEventListener("input", () => aplicarMascaraDocumento(input));
        aplicarMascaraDocumento(input); // Aplica ao carregar (caso edição)
    });

    document.querySelectorAll(".mask-phone").forEach(input => {
        input.addEventListener("input", () => aplicarMascaraTelefone(input));
        aplicarMascaraTelefone(input); // Aplica ao carregar (caso edição)
    });


    // ==============================
    // Modal de Cliente (Deleção)
    // ==============================
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


// ==============================
// Bootstrap tooltips
// ==============================
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
tooltipTriggerList.forEach(function (tooltipTriggerEl) {
    new bootstrap.Tooltip(tooltipTriggerEl);
});


// ==============================
// Compartilhar relatório (PDF)
// ==============================
async function compartilharRelatorio() {
    const params = new URLSearchParams(window.location.search);
    const situacao = params.get('situacao') || 'TODOS';
    const loteamento_id = document.body.dataset.loteamentoId || '';

    const url = `/empreendimentos/relatorio-lotes/?situacao=${encodeURIComponent(situacao)}&loteamento_id=${encodeURIComponent(loteamento_id)}`;

    try {
        const response = await fetch(url);

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
            // Fallback: download
            const urlBlob = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = urlBlob;
            a.setAttribute('download', file.name);
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                URL.revokeObjectURL(urlBlob);
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
    // Oculta o botão se não suportar compartilhamento de arquivos
    if (!navigator.canShare || !navigator.canShare({ files: [new File([""], "teste.pdf", { type: "application/pdf" })] })) {
        const botao = document.querySelector('button[onclick="compartilharRelatorio()"]');
        if (botao) botao.style.display = 'none';
    }
});
document.addEventListener("DOMContentLoaded", () => {
    const cpfInputs = document.querySelectorAll(".mask-cpf");

    cpfInputs.forEach(input => {
        input.addEventListener("input", (e) => {
            let value = e.target.value.replace(/\D/g, "");
            if (value.length <= 11) {
                // CPF: 000.000.000-00
                value = value.replace(/(\d{3})(\d)/, "$1.$2");
                value = value.replace(/(\d{3})(\d)/, "$1.$2");
                value = value.replace(/(\d{3})(\d{1,2})$/, "$1-$2");
            } else if (value.length <= 14) {
                // CNPJ: 00.000.000/0000-00
                value = value.replace(/^(\d{2})(\d)/, "$1.$2");
                value = value.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
                value = value.replace(/\.(\d{3})(\d)/, ".$1/$2");
                value = value.replace(/(\d{4})(\d)/, "$1-$2");
            }
            e.target.value = value;
        });
    });
});