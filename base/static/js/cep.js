const CEP_MAPEAMENTOS = [
	{ cep: 'id_end_cep', rua: 'id_end_rua', complemento: 'id_end_complemento', bairro: 'id_end_bairro', cidade: 'id_end_cidade', estado: 'id_end_estado' },
	{ cep: 'id_cep', rua: 'id_rua', complemento: 'id_complemento', bairro: 'id_bairro', cidade: 'id_cidade', estado: 'id_estado' },
];

const cepValido = (cep) => cep.length === 8 && /^[0-9]+$/.test(cep);

function limparCampos(mapa) {
	['rua', 'complemento', 'bairro', 'cidade', 'estado'].forEach((campo) => {
		const el = document.getElementById(mapa[campo]);
		if (el) el.value = "";
	});
}

function preencherCampos(mapa, endereco) {
	const preencher = { rua: 'logradouro', complemento: 'complemento', bairro: 'bairro', cidade: 'localidade', estado: 'uf' };
	for (const [campo, chave] of Object.entries(preencher)) {
		const el = document.getElementById(mapa[campo]);
		if (el) el.value = endereco[chave] || "";
	}
}

async function pesquisarCep(mapa) {
	const inputCep = document.getElementById(mapa.cep);
	if (!inputCep) return;

	const cep = inputCep.value.replace(/\D/g, "");

	if (!cepValido(cep)) {
		limparCampos(mapa);
		alert("CEP incorreto!");
		return;
	}

	try {
		const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
		const endereco = await response.json();

		if (endereco.erro) {
			limparCampos(mapa);
			alert("CEP não encontrado!");
		} else {
			preencherCampos(mapa, endereco);
		}
	} catch (error) {
		console.error("Erro ao buscar CEP:", error);
		alert("Erro ao consultar CEP.");
	}
}

const _handlers = new Map();

function registrarListenersCep() {
	for (const mapa of CEP_MAPEAMENTOS) {
		const cepInput = document.getElementById(mapa.cep);
		if (!cepInput) continue;
		if (_handlers.has(cepInput)) {
			cepInput.removeEventListener('focusout', _handlers.get(cepInput));
		}
		const handler = () => pesquisarCep(mapa);
		_handlers.set(cepInput, handler);
		cepInput.addEventListener('focusout', handler);
	}
}

document.addEventListener("DOMContentLoaded", registrarListenersCep);

document.addEventListener("shown.bs.modal", registrarListenersCep);
