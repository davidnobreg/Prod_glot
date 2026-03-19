// ==============================
// UTILITÁRIOS
// ==============================
const somenteNumeros = (valor = "") => valor.replace(/\D/g, "");

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
// CONTROLE DE CAMPOS
// ==============================
const CAMPOS_CONJUGE = [
    "id_nome_conjuge",
    "id_documento_conjuge",
    "id_numero_rg_conjuge",
    "id_orgao_emissor_rg_conjuge"
];

const getCampo = (id) => document.getElementById(id);

const toggleCamposConjuge = (ativo) => {
    CAMPOS_CONJUGE.forEach(id => {
        const campo = getCampo(id);
        if (!campo) return;

        campo.required = ativo;
        campo.disabled = !ativo;

        if (!ativo) campo.value = "";
    });
};

// ==============================
// JSON DO CÔNJUGE
// ==============================
const atualizarConjugeJson = () => {
    const nome = getCampo("id_nome_conjuge")?.value.trim() || "";
    const documentoInput = getCampo("id_documento_conjuge");
    const rg = getCampo("id_numero_rg_conjuge")?.value.trim() || "";
    const orgao = getCampo("id_orgao_emissor_rg_conjuge")?.value.trim() || "";

    let documento = "";

    if (documentoInput) {
        documento = somenteNumeros(documentoInput.value);

        // Formatação visual
        documentoInput.value = formatarCPF(documentoInput.value);
    }

    const conjuge = {
        nome_conjuge: nome,
        documento_conjuge: documento,
        numero_rg_conjuge: rg,
        orgao_emissor_rg_conjuge: orgao
    };

    const hidden = getCampo("conjuge_json");
    if (hidden) {
        hidden.value = JSON.stringify(conjuge);
    }
};

// ==============================
// INICIALIZAÇÃO
// ==============================
document.addEventListener("DOMContentLoaded", () => {

    const estadoCivil = getCampo("id_estado_civil");
    const modalEl = getCampo("modalConjuge");

    let modalConjuge = null;

    if (modalEl && window.bootstrap) {
        modalConjuge = new bootstrap.Modal(modalEl);
    }

    // ==========================
    // CONTROLE ESTADO CIVIL
    // ==========================
    const atualizarEstadoCivil = () => {
        const isCasado = estadoCivil?.value?.toLowerCase() === "casado";

        toggleCamposConjuge(isCasado);

        if (isCasado && modalConjuge) {
            modalConjuge.show();
        }

        // limpa JSON se não for casado
        if (!isCasado) {
            const hidden = getCampo("conjuge_json");
            if (hidden) hidden.value = "";
        }
    };

    if (estadoCivil) {
        estadoCivil.addEventListener("change", atualizarEstadoCivil);

        // Executa ao carregar (edição de cliente, por exemplo)
        atualizarEstadoCivil();
    }

    // ==========================
    // EVENTOS DOS CAMPOS
    // ==========================
    CAMPOS_CONJUGE.forEach(id => {
        const campo = getCampo(id);
        if (!campo) return;

        ["input", "change", "blur"].forEach(evento => {
            campo.addEventListener(evento, atualizarConjugeJson);
        });
    });
});