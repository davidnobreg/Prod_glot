// static/js/telefone.js
document.addEventListener("DOMContentLoaded", function () {

    window.telefonesTemp = window.telefonesTemp || [];

    // Elemento para mensagens de erro
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

    // Regex para validar telefone brasileiro
    function telefoneValido(numero) {
        const regex = /^(\(?\d{2}\)?\s?)?(\d{4,5})[- ]?(\d{4})$/;
        return regex.test(numero);
    }

    window.addTelefone = function () {
        limparErro();

        const input = document.getElementById("telefoneNumero");
        if (!input) {
            console.error("input telefoneNumero não encontrado");
            return;
        }

        let numero = input.value.trim();
        if (!numero) {
            mostrarErro("Digite um número de telefone.");
            return;
        }

        // VALIDA O FORMATO
        if (!telefoneValido(numero)) {
            mostrarErro("Número inválido. Digite um telefone válido no formato brasileiro.");
            return;
        }

        // NORMALIZA → remove caracteres antes de comparar
        const normalizado = numero.replace(/\D/g, "");

        // IMPEDE DUPLICADOS
        const existe = window.telefonesTemp.some(t => t.replace(/\D/g, "") === normalizado);

        if (existe) {
            mostrarErro("Este telefone já foi adicionado!");
            return;
        }

        // Adiciona à lista
        window.telefonesTemp.push(numero);
        atualizarLista();
        input.value = "";
    }

    window.atualizarLista = function () {
        const ul = document.getElementById("listaTelefones");
        if (!ul) {
            console.error("listaTelefones não encontrada");
            return;
        }

        ul.innerHTML = "";

        window.telefonesTemp.forEach((tel, index) => {
            const li = document.createElement("li");
            li.className = "list-group-item d-flex justify-content-between align-items-center";
            li.innerHTML = `
                <span>${tel}</span>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removerTelefone(${index})">X</button>
            `;
            ul.appendChild(li);
        });

        const hidden = document.getElementById("telefones_json");
        if (hidden) hidden.value = JSON.stringify(window.telefonesTemp);
    }

    window.removerTelefone = function (i) {
        window.telefonesTemp.splice(i, 1);
        atualizarLista();
    }

    window.fecharModal = function () {
        const modalEl = document.getElementById("modalTelefone");
        if (!modalEl) {
            console.error("modalTelefone não encontrado");
            return;
        }
        const instance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
        instance.hide();
    }

    atualizarLista();
});
