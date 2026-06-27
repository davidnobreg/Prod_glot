// static/js/telefone.js
document.addEventListener("DOMContentLoaded", function () {

     // Normaliza para objetos {numero, tipo, observacao} — compat com strings legadas
    window.telefonesTemp = Array.isArray(window.telefonesTemp)
        ? window.telefonesTemp.map(function (t) {
            return typeof t === 'string'
                ? { numero: t, tipo: 'celular', observacao: '' }
                : t;
        })
        : [];

    // ===============================
    // MENSAGEM DE ERRO
    // ===============================
    function mostrarErro(msg) {
        let box = document.getElementById("telefoneErro");
        if (!box) {
            box = document.createElement("div");
            box.id = "telefoneErro";
            box.className = "alert alert-danger mt-2";
            const formRow = document.querySelector("#telefoneNumero")?.parentNode;
            if (formRow) formRow.appendChild(box);
        }
        box.innerText = msg;
        box.style.display = "block";
    }

    function limparErro() {
        const box = document.getElementById("telefoneErro");
        if (box) box.style.display = "none";
    }

    // ===============================
    // VALIDA TELEFONE BR
    // ===============================
    function telefoneValido(numero) {
        const regex = /^(\(?\d{2}\)?\s?)?(\d{4,5})[- ]?(\d{4})$/;
        return regex.test(numero);
    }

    function _telNumero(t) {
        return typeof t === 'string' ? t : (t.numero || '');
    }

    // ===============================
    // ADICIONAR
    // ===============================
    window.addTelefone = function () {
        limparErro();

        const input = document.getElementById("telefoneNumero");
        if (!input) return;

        const numero = input.value.trim();
        if (!numero) {
            mostrarErro("Digite um número de telefone.");
            return;
        }

        if (!telefoneValido(numero)) {
            mostrarErro("Telefone inválido.");
            return;
        }

        const normalizado = numero.replace(/\D/g, "");

        const existe = window.telefonesTemp.some(t =>
            _telNumero(t).replace(/\D/g, "") === normalizado
        );

        if (existe) {
            mostrarErro("Este telefone já foi adicionado.");
            return;
        }

        const tipoEl = document.getElementById("id_tipo");
        const obsEl = document.getElementById("id_observacao");

        window.telefonesTemp.push({
            numero: numero,
            tipo: tipoEl ? (tipoEl.value || 'celular') : 'celular',
            observacao: obsEl ? obsEl.value.trim() : '',
        });

        atualizarLista();
        input.value = "";
        if (tipoEl && tipoEl.options.length) tipoEl.selectedIndex = 0;
        if (obsEl) obsEl.value = "";
    };

    // ===============================
    // LISTAR
    // ===============================
    window.atualizarLista = function () {
        const ul = document.getElementById("listaTelefones");
        if (!ul) return;

        ul.innerHTML = "";

        window.telefonesTemp.forEach((tel, index) => {
            const numero = _telNumero(tel);
            const tipo = typeof tel === 'object' && tel.tipo ? tel.tipo : '';
            const display = tipo ? `${numero} (${tipo})` : numero;

            const li = document.createElement("li");
            li.className =
                "list-group-item d-flex justify-content-between align-items-center";
            li.innerHTML = `
                <span>${display}</span>
                <button type="button"
                        class="btn btn-sm btn-outline-danger"
                        onclick="removerTelefone(${index})">
                    ✕
                </button>
            `;
            ul.appendChild(li);
        });

        const hidden = document.getElementById("telefones_json");
        if (hidden) hidden.value = JSON.stringify(window.telefonesTemp);
    };

    // ===============================
    // REMOVER
    // ===============================
    window.removerTelefone = function (index) {
        window.telefonesTemp.splice(index, 1);
        atualizarLista();
    };

    // ===============================
    // FECHAR MODAL
    // ===============================
    window.fecharModal = function () {
        const modalEl = document.getElementById("modalTelefone");
        if (!modalEl) return;

        const instance =
            bootstrap.Modal.getInstance(modalEl) ||
            new bootstrap.Modal(modalEl);

        instance.hide();
    };

    // ✅ CARREGA AUTOMATICAMENTE AO ABRIR
    atualizarLista();
});