document.addEventListener("DOMContentLoaded", function () {

    // =====================================================
    // MÁSCARAS
    // =====================================================

    const mascaras = {

        // =================================================
        // CPF / CNPJ
        // =================================================

        documento: function (input) {

            let value = input.value.replace(/\D/g, "");

            if (value.length <= 11) {

                // CPF
                value = value
                    .replace(/(\d{3})(\d)/, "$1.$2")
                    .replace(/(\d{3})(\d)/, "$1.$2")
                    .replace(/(\d{3})(\d{1,2})$/, "$1-$2");

            } else {

                // CNPJ
                value = value
                    .replace(/^(\d{2})(\d)/, "$1.$2")
                    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
                    .replace(/\.(\d{3})(\d)/, ".$1/$2")
                    .replace(/(\d{4})(\d{1,2})$/, "$1-$2");

            }

            input.value = value;

        },

        // =================================================
        // TELEFONE
        // =================================================

        telefone: function (input) {

            let value = input.value.replace(/\D/g, "");

            if (value.length > 10) {

                // CELULAR
                value = value.replace(
                    /^(\d{2})(\d{5})(\d{4}).*/,
                    "($1) $2-$3"
                );

            } else {

                // FIXO
                value = value.replace(
                    /^(\d{2})(\d{4})(\d{4}).*/,
                    "($1) $2-$3"
                );

            }

            input.value = value;

        }

    };

    // =====================================================
    // APLICA MÁSCARA CPF/CNPJ
    // =====================================================

    document.querySelectorAll(".mask-doc").forEach(input => {

        input.addEventListener("input", () => {
            mascaras.documento(input);
        });

        mascaras.documento(input);

    });

    // =====================================================
    // APLICA MÁSCARA TELEFONE
    // =====================================================

    document.querySelectorAll(".mask-phone").forEach(input => {

        input.addEventListener("input", () => {
            mascaras.telefone(input);
        });

        mascaras.telefone(input);

    });

    // =====================================================
    // MÁSCARA MONETÁRIA
    // =====================================================

    function formatarDinheiro(input) {

        let pos = input.selectionStart || 0;

        let value = input.value;

        // Remove tudo que não for número
        let numeros = value.replace(/\D/g, "");

        // Campo vazio
        if (numeros.length === 0) {

            input.value = "R$ 0,00";

            return;

        }

        // Divide por 100 para centavos
        let valor = (parseInt(numeros, 10) / 100).toFixed(2);

        // Separa parte inteira e decimal
        let partes = valor.split(".");

        // Adiciona separador de milhar
        partes[0] = partes[0].replace(
            /\B(?=(\d{3})+(?!\d))/g,
            "."
        );

        // Resultado final
        input.value = "R$ " + partes.join(",");

        // Mantém cursor
        let diff = input.value.length - value.length;

        input.setSelectionRange(
            pos + diff,
            pos + diff
        );

    }

    // =====================================================
    // APLICA MÁSCARA MONETÁRIA
    // =====================================================

    document.querySelectorAll(".mask-money").forEach(input => {

        input.addEventListener("input", () => {

            formatarDinheiro(input);

        });

        // Inicializa valor
        formatarDinheiro(input);

    });

    // =====================================================
    // ESTADO CIVIL -> SEÇÃO DO CÔNJUGE
    // =====================================================

    function initConjugeSection() {

        const estadoCivil = document.getElementById("id_estado_civil");
        const secao = document.getElementById("secaoConjuge");

        if (!estadoCivil || !secao) {
            return;
        }

        const conjugeNome = document.getElementById("id_conj_nome");
        const conjugeDocumento = document.getElementById("id_conj_documento");
        const conjugeRg = document.getElementById("id_conj_numero_rg");
        const conjugeOrgao = document.getElementById("id_conj_orgao_emissor_rg");

        const campos = [
            conjugeNome,
            conjugeDocumento,
            conjugeRg,
            conjugeOrgao
        ].filter(Boolean);

        function setEnabled(enabled) {
            campos.forEach((el) => {
                el.disabled = !enabled;
            });

            // regra atual do backend exige apenas nome
            if (conjugeNome) {
                conjugeNome.required = enabled;
                conjugeNome.setAttribute("aria-required", enabled ? "true" : "false");
            }
        }

        function update() {
            const val = (estadoCivil.value || "").toLowerCase();
            const isCasado = val === "casado";

            if (isCasado) {
                secao.hidden = false;
                secao.setAttribute("aria-hidden", "false");
                setEnabled(true);
            } else {
                secao.hidden = true;
                secao.setAttribute("aria-hidden", "true");
                setEnabled(false);
            }
        }

        estadoCivil.addEventListener("change", update);

        // compatibilidade se em algum ponto virar select2
        if (typeof $ !== "undefined") {
            $(document).on("change select2:select select2:unselect", "[name='estado_civil']", update);
        }

        update();

    }

    initConjugeSection();

    // =====================================================
    // MODAL CLIENTE DELETE
    // =====================================================

    const clienteModalDelete = document.getElementById(
        'clienteModalDelete'
    );

    function preencherModalCliente(clienteId, data) {

        if (!data || typeof data !== 'object') {
            return;
        }

        const clienteIdInput = document.getElementById('cliente-id');
        if (clienteIdInput) {
            clienteIdInput.value = clienteId;
        }

        document.getElementById(
            'cliente-name'
        ).textContent = data.name || 'Nome não encontrado';

        document.getElementById(
            'cliente-documento'
        ).textContent = data.documento || 'Documento não encontrado';

        document.getElementById(
            'cliente-email'
        ).textContent = data.email || 'Email não encontrado';

    }

    if (clienteModalDelete) {

        clienteModalDelete.addEventListener(
            'show.bs.modal',
            event => {

                const button = event.relatedTarget;

                const clienteId = button.getAttribute(
                    'data-cliente-id'
                );

                fetch(`/clientes/select/${clienteId}/`)
                    .then(resp => (
                        resp.ok
                            ? resp.json()
                            : Promise.reject(resp.status)
                    ))
                    .then(data => {
                        preencherModalCliente(
                            clienteId,
                            data
                        );
                    })
                    .catch(err => {
                        console.error(
                            'Erro ao buscar dados do cliente:',
                            err
                        );
                    });

            }
        );

        const btnDeletarCliente = document.getElementById(
            "btn-deletar-cliente"
        );

        if (btnDeletarCliente) {

            btnDeletarCliente.addEventListener(
                "click",
                (event) => {

                    event.preventDefault();

                    const clienteId = document.getElementById(
                        "cliente-id"
                    ).value;

                    if (!clienteId) {
                        return;
                    }

                    window.location.href =
                        `/clientes/delete_cliente/${clienteId}/`;

                }
            );

        }

    }

    // =====================================================
    // MODAL ENDEREÇO
    // =====================================================

    const enderecoModal = document.getElementById(
        'enderecoModal'
    );

    function preencherModalClienteEndereco(enderecoId, data) {

        if (!data || typeof data !== 'object') {
            return;
        }

        document.getElementById(
            'endereco-id'
        ).textContent = enderecoId;

        document.getElementById(
            'endereco-id-display'
        ).textContent = enderecoId;

        document.getElementById(
            'endereco-rua'
        ).textContent = data.rua || 'Rua não encontrada';

        document.getElementById(
            'endereco-complemento'
        ).textContent = data.complemento || 'Complemento não encontrado';

        document.getElementById(
            'endereco-numero'
        ).textContent = data.numero || 'Número não encontrado';

        document.getElementById(
            'endereco-bairro'
        ).textContent = data.bairro || 'Bairro não encontrado';

        document.getElementById(
            'endereco-cep'
        ).textContent = data.cep || 'CEP não encontrado';

        document.getElementById(
            'endereco-cidade'
        ).textContent = data.cidade || 'Cidade não encontrada';

        document.getElementById(
            'endereco-estado'
        ).textContent = data.estado || 'Estado não encontrado';

    }

    if (enderecoModal) {

        enderecoModal.addEventListener(
            'show.bs.modal',
            event => {

                const button = event.relatedTarget;

                const enderecoId = button.getAttribute(
                    'data-endereco-id'
                );

                if (!enderecoId) {
                    return;
                }

                fetch(`/clientes/select_endereco/${enderecoId}/`)
                    .then(resp => (
                        resp.ok
                            ? resp.json()
                            : Promise.reject(resp.status)
                    ))
                    .then(data => {
                        preencherModalClienteEndereco(
                            enderecoId,
                            data
                        );
                    })
                    .catch(err => {
                        console.error(
                            'Erro ao buscar dados do endereço:',
                            err
                        );
                    });

            }
        );

        const btnClienteEndereco = document.getElementById(
            "btn-cliente-endereco"
        );

        if (btnClienteEndereco) {

            btnClienteEndereco.addEventListener(
                "click",
                () => {

                    const enderecoId = document.getElementById(
                        "endereco-id"
                    ).textContent;

                    window.location.href =
                        `/clientes/update_endereco/${enderecoId}/`;

                }
            );

        }

    }

    // =====================================================
    // TOOLTIPS
    // =====================================================

    document.querySelectorAll(
        '[data-bs-toggle="tooltip"]'
    ).forEach(el => {

        new bootstrap.Tooltip(el);

    });

});


// =========================================================
// FLATPICKR
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

    flatpickr(".mask-data", {

        dateFormat: "d/m/Y",
        allowInput: true,
        locale: "pt",
        clickOpens: true,
        disableMobile: true

    });

});


// =========================================================
// MÁSCARA DATA
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

    const input = document.querySelector('.mask-data');

    if (!input) {
        return;
    }

    input.addEventListener('input', function (e) {

        let v = e.target.value.replace(/\D/g, '');

        if (v.length > 2) {
            v = v.slice(0, 2) + '/' + v.slice(2);
        }

        if (v.length > 5) {
            v = v.slice(0, 5) + '/' + v.slice(5, 9);
        }

        e.target.value = v;

    });

});
