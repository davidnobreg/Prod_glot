// ==============================
// UTILITÁRIOS
// ==============================
const eNumero = (numero) => /^[0-9]+$/.test(numero);

const cepValido = (cep) => cep.length === 8 && eNumero(cep);

// ==============================
// LIMPAR FORMULÁRIO
// ==============================
const limparFormulario = () => {
    document.getElementById("id_rua").value = "";
    document.getElementById("id_complemento").value = "";
    document.getElementById("id_bairro").value = "";
    document.getElementById("id_cidade").value = "";
    document.getElementById("id_estado").value = "";

    atualizarEnderecoJson(); // limpa o JSON também
};

// ==============================
// PREENCHER FORMULÁRIO
// ==============================
const preencherFormulario = (endereco) => {
    document.getElementById("id_rua").value = endereco.logradouro || "";
    document.getElementById("id_complemento").value = endereco.complemento || "";
    document.getElementById("id_bairro").value = endereco.bairro || "";
    document.getElementById("id_cidade").value = endereco.localidade || "";
    document.getElementById("id_estado").value = endereco.uf || "";

    atualizarEnderecoJson(); // atualiza JSON após preencher
};

// ==============================
// BUSCAR CEP
// ==============================
const pesquisarCep = async () => {
    const inputCep = document.getElementById("id_cep");
    if (!inputCep) return;

    const cep = inputCep.value.replace(/\D/g, "");
    const url = `https://viacep.com.br/ws/${cep}/json/`;

    if (!cepValido(cep)) {
        limparFormulario();
        alert("CEP incorreto!");
        return;
    }

    try {
        const response = await fetch(url);
        const endereco = await response.json();

        if (endereco.erro) {
            limparFormulario();
            alert("CEP não encontrado!");
        } else {
            preencherFormulario(endereco);
        }
    } catch (error) {
        console.error("Erro ao buscar CEP:", error);
        alert("Erro ao consultar CEP.");
    }
};

// ==============================
// MONTAR JSON DO ENDEREÇO
// ==============================
const atualizarEnderecoJson = () => {
    const endereco = {
        cep: document.getElementById("id_cep")?.value || "",
        rua: document.getElementById("id_rua")?.value || "",
        numero: document.getElementById("id_numero")?.value || "",
        complemento: document.getElementById("id_complemento")?.value || "",
        bairro: document.getElementById("id_bairro")?.value || "",
        cidade: document.getElementById("id_cidade")?.value || "",
        estado: document.getElementById("id_estado")?.value || ""
    };

    const hidden = document.getElementById("endereco_json");
    if (hidden) {
        hidden.value = JSON.stringify(endereco);
    }
};

// ==============================
// EVENTOS
// ==============================
document.addEventListener("DOMContentLoaded", () => {

    const cepInput = document.getElementById("id_cep");
    if (cepInput) {
        cepInput.addEventListener("focusout", pesquisarCep);
    }

    // Atualiza JSON sempre que algum campo do endereço mudar
    const camposEndereco = [
        "id_cep",
        "id_rua",
        "id_numero",
        "id_complemento",
        "id_bairro",
        "id_cidade",
        "id_estado"
    ];

    camposEndereco.forEach(id => {
        const campo = document.getElementById(id);
        if (campo) {
            campo.addEventListener("change", atualizarEnderecoJson);
            campo.addEventListener("keyup", atualizarEnderecoJson);
        }
    });
});
