/* Mapeamentos legados (ids fixos, sem prefix de formset/prefix Django). */
const CEP_MAPEAMENTOS_FIXOS = [
	{ cep: 'id_end_cep', rua: 'id_end_rua', complemento: 'id_end_complemento', bairro: 'id_end_bairro', cidade: 'id_end_cidade', estado: 'id_end_estado' },
	{ cep: 'id_cep', rua: 'id_rua', complemento: 'id_complemento', bairro: 'id_bairro', cidade: 'id_cidade', estado: 'id_estado' },
];

/* Deriva o mapa de um input de CEP qualquer, incluindo os com prefix
 * (ex: id_empresa-cep, id_representante-0-endereco-cep) — troca o sufixo
 * "cep" por cada campo irmão, mantendo o mesmo prefixo. */
function mapaDoInputCep(cepInput) {
	const id = cepInput.id;
	if (!id.endsWith('cep')) return null;
	const base = id.slice(0, -'cep'.length);
	return {
		cep: id,
		rua: base + 'rua',
		complemento: base + 'complemento',
		bairro: base + 'bairro',
		cidade: base + 'cidade',
		estado: base + 'estado',
	};
}

function encontrarInputsCep() {
	const encontrados = new Map();
	for (const mapa of CEP_MAPEAMENTOS_FIXOS) {
		const input = document.getElementById(mapa.cep);
		if (input) encontrados.set(input, mapa);
	}
	document.querySelectorAll('input[id$="cep"], input[id$="-cep"]').forEach((input) => {
		if (encontrados.has(input)) return;
		const mapa = mapaDoInputCep(input);
		if (mapa) encontrados.set(input, mapa);
	});
	return encontrados;
}

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
	for (const [cepInput, mapa] of encontrarInputsCep()) {
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
