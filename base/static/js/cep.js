// ==============================
// UTILITÁRIOS
// ==============================
const eNumero = (numero) => /^[0-9]+$/.test(numero);

const cepValido = (cep) => cep.length === 8 && eNumero(cep);

// ==============================
// LIMPAR FORMULÁRIO
// ==============================
const limparFormulario = () => {
	document.getElementById("id_end_rua").value = "";
	document.getElementById("id_end_complemento").value = "";
	document.getElementById("id_end_bairro").value = "";
	document.getElementById("id_end_cidade").value = "";
	document.getElementById("id_end_estado").value = "";
};

// ==============================
// PREENCHER FORMULÁRIO
// ==============================
const preencherFormulario = (endereco) => {
	document.getElementById("id_end_rua").value = endereco.logradouro || "";
	document.getElementById("id_end_complemento").value = endereco.complemento || "";
	document.getElementById("id_end_bairro").value = endereco.bairro || "";
	document.getElementById("id_end_cidade").value = endereco.localidade || "";
	document.getElementById("id_end_estado").value = endereco.uf || "";
};

// ==============================
// BUSCAR CEP
// ==============================
const pesquisarCep = async () => {
	const inputCep = document.getElementById("id_end_cep");
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
// EVENTOS
// ==============================
document.addEventListener("DOMContentLoaded", () => {
	const cepInput = document.getElementById("id_end_cep");
	if (cepInput) {
		cepInput.addEventListener("focusout", pesquisarCep);
	}
});
