document.addEventListener("DOMContentLoaded", function () {

    // ==============================
    // Funções de máscara
    // ==============================
    const mascaras = {

        // CPF ou CNPJ
        documento: function (input) {
            let value = input.value.replace(/\D/g, "");

            if (value.length <= 11) {
                // CPF: 000.000.000-00
                value = value
                    .replace(/(\d{3})(\d)/, "$1.$2")
                    .replace(/(\d{3})(\d)/, "$1.$2")
                    .replace(/(\d{3})(\d{1,2})$/, "$1-$2");
            } else {
                // CNPJ: 00.000.000/0000-00
                value = value
                    .replace(/^(\d{2})(\d)/, "$1.$2")
                    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
                    .replace(/\.(\d{3})(\d)/, ".$1/$2")
                    .replace(/(\d{4})(\d{1,2})$/, "$1-$2");
            }

            input.value = value;
        },

        // Telefone / Celular
        telefone: function (input) {
            let value = input.value.replace(/\D/g, "");
            if (value.length > 10) {
                // Celular
                value = value.replace(/^(\d{2})(\d{5})(\d{4}).*/, "($1) $2-$3");
            } else {
                // Fixo
                value = value.replace(/^(\d{2})(\d{4})(\d{4}).*/, "($1) $2-$3");
            }
            input.value = value;
        }

    };

    // ==============================
    // Aplica máscaras em campos com classes específicas
    // ==============================
    document.querySelectorAll(".mask-doc").forEach(input => {
        input.addEventListener("input", () => mascaras.documento(input));
        mascaras.documento(input);
    });

    document.querySelectorAll(".mask-phone").forEach(input => {
        input.addEventListener("input", () => mascaras.telefone(input));
        mascaras.telefone(input);
    });

    function formatarDinheiro(input) {
        let pos = input.selectionStart; // posição do cursor
        let value = input.value;

        // remove tudo que não é número
        let numeros = value.replace(/\D/g, "");

        if (!numeros) {
            input.value = "";
            return;
        }

        // transforma em centavos
        let valor = (parseInt(numeros) / 100).toFixed(2);

        // separador decimal
        let partes = valor.split(".");
        partes[0] = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, ".");
        let resultado = "R$ " + partes.join(",");

        input.value = resultado;

        // tenta manter o cursor na posição correta
        let diff = input.value.length - value.length;
        input.setSelectionRange(pos + diff, pos + diff);
    }

// Aplica a máscara
    document.querySelectorAll(".mask-money").forEach(input => {
        input.addEventListener("input", () => formatarDinheiro(input));
        formatarDinheiro(input);
    });


    const conjugeForm = document.getElementById('conjugeForm');
    if (conjugeForm) {
        conjugeForm.addEventListener('submit', function (e) {
            e.preventDefault();
            // Pode validar/enviar via AJAX
            conjugeModal.hide();
            alert('Dados do cônjuge salvos!');
        });
    }

    // ==============================
    // Modal de Cliente (Deleção)
    // ==============================
    const clienteModalDelete = document.getElementById('clienteModalDelete');

    function preencherModalCliente(clienteId, data) {
        if (!data || typeof data !== 'object') return;
        document.getElementById('cliente-id').value = clienteId;
        const clienteIdDisplay = document.getElementById('cliente-id-display');
        if (clienteIdDisplay) clienteIdDisplay.textContent = clienteId;
        document.getElementById('cliente-name').textContent = data.name || 'Nome não encontrado';
        document.getElementById('cliente-documento').textContent = data.documento || 'Documento não encontrado';
        document.getElementById('cliente-email').textContent = data.email || 'Email não encontrado';
    }

    if (clienteModalDelete) {
        clienteModalDelete.addEventListener('show.bs.modal', event => {
            const button = event.relatedTarget;
            const clienteId = button.getAttribute('data-cliente-id');

            fetch(`/clientes/select/${clienteId}/`)
                .then(resp => resp.ok ? resp.json() : Promise.reject(resp.status))
                .then(data => preencherModalCliente(clienteId, data))
                .catch(err => console.error('Erro ao buscar dados do cliente:', err));
        });

        const btnDeletarCliente = document.getElementById("btn-deletar-cliente");
        if (btnDeletarCliente) {
            btnDeletarCliente.addEventListener("click", (event) => {
                event.preventDefault();
                const clienteId = document.getElementById("cliente-id").value;
                if (!clienteId) return;
                window.location.href = `/clientes/delete_cliente/${clienteId}/`;
            });
        }
    }

    // ==============================
    // Modal de ClienteEndereço (Deleção)
    // ==============================
    const enderecoModal = document.getElementById('enderecoModal');

    function preencherModalClienteEndereco(enderecoId, data) {
        if (!data || typeof data !== 'object') return;
        document.getElementById('endereco-id').textContent = enderecoId;
        document.getElementById('endereco-id-display').textContent = enderecoId;
        document.getElementById('endereco-rua').textContent = data.rua || 'Rua não encontrado';
        document.getElementById('endereco-complemento').textContent = data.complemento || 'Complemento não encontrado';
        document.getElementById('endereco-numero').textContent = data.numero || 'Numero não encontrado';
        document.getElementById('endereco-bairro').textContent = data.bairro || 'Bairro não encontrado';
        document.getElementById('endereco-cep').textContent = data.cep || 'Cep não encontrado';
        document.getElementById('endereco-cidade').textContent = data.cidade || 'Cidade não encontrado';
        document.getElementById('endereco-estado').textContent = data.estado || 'Estado não encontrado';

    }

    if (enderecoModal) {
        enderecoModal.addEventListener('show.bs.modal', event => {
            const button = event.relatedTarget;
            const enderecoId = button.getAttribute('data-endereco-id');

            if (!enderecoId) return;

            fetch(`/clientes/select_endereco/${enderecoId}/`)
                .then(resp => resp.ok ? resp.json() : Promise.reject(resp.status))
                .then(data => preencherModalClienteEndereco(enderecoId, data))
                .catch(err => console.error('Erro ao buscar dados do cliente:', err));
        });

        const btnClienteEndereco = document.getElementById("btn-cliente-endereco");
        if (btnClienteEndereco) {
            btnClienteEndereco.addEventListener("click", () => {
                const enderecoId = document.getElementById("endereco-id").textContent;
                window.location.href = `/clientes/update_endereco/${enderecoId}/`;
            });
        }
    }


    // ==============================
    // Bootstrap Tooltips
    // ==============================
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
        new bootstrap.Tooltip(el);
    });

    // ==============================
    // Compartilhar Relatório PDF
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
            const file = new File([blob], "relatorio_lotes.pdf", {type: "application/pdf"});

            if (navigator.canShare && navigator.canShare({files: [file]})) {
                await navigator.share({
                    title: "Relatório de Lotes",
                    text: "Segue o relatório de lotes gerado.",
                    files: [file]
                });
            } else {
                const urlBlob = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = urlBlob;
                a.setAttribute('download', file.name);
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

    // Oculta botão compartilhar se navegador não suportar
    const botaoCompartilhar = document.querySelector('button[onclick="compartilharRelatorio()"]');
    if (botaoCompartilhar && (!navigator.canShare || !navigator.canShare({files: [new File([""], "teste.pdf", {type: "application/pdf"})]}))) {
        botaoCompartilhar.style.display = 'none';
    }

    // Torna função global para botão
    window.compartilharRelatorio = compartilharRelatorio;
});

document.addEventListener("DOMContentLoaded", function () {
    flatpickr(".mask-data", {
        dateFormat: "d/m/Y",
        allowInput: true,
        locale: "pt",
        clickOpens: true,
        disableMobile: true
    });
});

document.addEventListener("DOMContentLoaded", function () {

    const input = document.querySelector('.mask-data');

    input.addEventListener('input', function (e) {
        let v = e.target.value.replace(/\D/g, '');

        if (v.length > 2) v = v.slice(0, 2) + '/' + v.slice(2);
        if (v.length > 5) v = v.slice(0, 5) + '/' + v.slice(5, 9);

        e.target.value = v;
    });

});

