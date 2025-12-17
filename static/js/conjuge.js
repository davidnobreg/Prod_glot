// ==============================
// UTILITÁRIOS
// ==============================
const somenteNumeros = (valor) => valor.replace(/\D/g, "");

const validarCPF = (cpf) => {
    cpf = somenteNumeros(cpf);
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;

    let soma = 0;
    for (let i = 0; i < 9; i++) soma += cpf[i] * (10 - i);
    let dig1 = (soma * 10 % 11) % 10;
    if (dig1 != cpf[9]) return false;

    soma = 0;
    for (let i = 0; i < 10; i++) soma += cpf[i] * (11 - i);
    let dig2 = (soma * 10 % 11) % 10;
    return dig2 == cpf[10];
};

const formatarCPF = (cpf) =>
    cpf
        .replace(/\D/g, "")
        .replace(/^(\d{3})(\d)/, "$1.$2")
        .replace(/^(\d{3})\.(\d{3})(\d)/, "$1.$2.$3")
        .replace(/\.(\d{3})(\d)/, ".$1-$2");

// ==============================
// MODAL
// ==============================
let modalConjuge = null;

// ==============================
// MONTAR JSON DO CÔNJUGE
// ==============================
const atualizarConjugeJson = () => {

    const nome = document.getElementById("id_nome_conjuge")?.value.trim() || "";
    const documentoInput = document.getElementById("id_documento_conjuge");
    const rg = document.getElementById("id_numero_rg_conjuge")?.value.trim() || "";
    const orgao = document.getElementById("id_orgao_emissor_rg_conjuge")?.value.trim() || "";

    let documento = "";

    if (documentoInput) {
        documento = somenteNumeros(documentoInput.value);

        // Formatação visual do CPF
        if (documento.length <= 11) {
            documentoInput.value = formatarCPF(documentoInput.value);
        }
    }

    const conjuge = {
        nome_conjuge: nome,
        documento_conjuge: documento,
        numero_rg_conjuge: rg,
        orgao_emissor_rg_conjuge: orgao
    };

    const hidden = document.getElementById("conjuge_json");
    if (hidden) {
        hidden.value = JSON.stringify(conjuge);
    }
};

// ==============================
// EVENTOS
// ==============================
document.addEventListener("DOMContentLoaded", () => {

    // Inicializa modal
    const modalEl = document.getElementById("modalConjuge");
    if (modalEl && window.bootstrap) {
        modalConjuge = new bootstrap.Modal(modalEl);
    }

    // Abre modal ao selecionar estado civil CASADO
    const estadoCivil = document.getElementById("id_estado_civil");
    if (estadoCivil && modalConjuge) {
        estadoCivil.addEventListener("change", () => {
            if (estadoCivil.value?.toLowerCase() === "casado") {
                modalConjuge.show();
            }
        });
    }

    // Atualiza JSON automaticamente (igual endereço)
    const camposConjuge = [
        "id_nome_conjuge",
        "id_documento_conjuge",
        "id_numero_rg_conjuge",
        "id_orgao_emissor_rg_conjuge"
    ];

    camposConjuge.forEach(id => {
        const campo = document.getElementById(id);
        if (campo) {
            campo.addEventListener("change", atualizarConjugeJson);
            campo.addEventListener("keyup", atualizarConjugeJson);
            campo.addEventListener("blur", atualizarConjugeJson);
        }
    });
});
