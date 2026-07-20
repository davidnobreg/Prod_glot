// Wizard multi-etapas para cadastro de cliente.
// Depende de: DOMContentLoaded → jQuery + telefone.js já carregados.
(function () {
	'use strict';

	var ALL_STEPS = [
		{ id: 'step-1', label: 'Dados pessoais' },
		{ id: 'step-2', label: 'Cônjuge', conditional: true },
		{ id: 'step-7', label: 'Representantes', conditional: true },
		{ id: 'step-4', label: 'Endereço' },
		{ id: 'step-5', label: 'Contatos' },
		{ id: 'step-3', label: 'Documentos' },
		{ id: 'step-6', label: 'Revisão' },
	];

	var TIPO_CHOICES_PF = [
		['RG', 'RG'],
		['RG_NOVO', 'RG Novo (com CPF)'],
		['CPF', 'CPF'],
		['CNH', 'CNH'],
		['COMPROVANTE_ESTADO_CIVIL', 'Comprovante de Estado Civil'],
		['COMPROVANTE_RESIDENCIA', 'Comprovante de Residência'],
		['OUTROS', 'Outros'],
	];

	var TIPO_CHOICES_PJ = [
		['CNPJ', 'CNPJ'],
		['CONTRATO_SOCIAL', 'Contrato Social'],
		['RG_CPF_ADMINISTRADOR', 'RG / CPF do Administrador'],
		['COMPROVANTE_RESIDENCIA', 'Comprovante de Residência'],
		['OUTROS', 'Outros'],
	];

	var AJAX_SAVE_STEPS = ['step-1', 'step-2', 'step-4', 'step-5'];

	var steps = [];
	var cur = 0;
	var wizardArquivos = [];
	var wizardRepresentantes = [];
	var clienteUuid = '';

	// -----------------------------------------------------------------------
	// Helpers
	// -----------------------------------------------------------------------

	function isCasado() {
		var el = document.getElementById('id_estado_civil');
		return el && el.value === 'casado';
	}

	function rebuildSteps() {
		steps = ALL_STEPS.filter(function (s) {
			if (s.id === 'step-2') return isCasado();
			if (s.id === 'step-7') return getTipoPessoa() === 'PJ';
			return true;
		});
	}

	function getVal(id) {
		var el = document.getElementById(id);
		return el ? el.value.trim() : '';
	}

	function getCsrf() {
		var el = document.querySelector('[name=csrfmiddlewaretoken]');
		return el ? el.value : '';
	}

	function getTipoPessoa() {
		var doc = getVal('id_documento').replace(/\D/g, '');
		return doc.length === 14 ? 'PJ' : 'PF';
	}

	function updateDocLabels() {
		var isPJ = getTipoPessoa() === 'PJ';
		var labelName = document.getElementById('label-name');
		var labelNomeUsual = document.getElementById('label-nome-usual');
		if (labelName) {
			labelName.innerHTML = (isPJ ? 'Razão Social' : 'Nome')
				+ ' <span class="text-danger">*</span>';
		}
		if (labelNomeUsual) {
			labelNomeUsual.textContent = isPJ ? 'Nome Fantasia' : 'Nome social';
		}
		var camposPF = ['id_data_ns', 'id_estado_civil', 'id_naturalidade', 'id_nacionalidade', 'id_profissao', 'id_renda', 'id_numero_rg', 'id_orgao_emissor_rg'];
		camposPF.forEach(function(id) {
			var el = document.getElementById(id);
			if (!el) return;
			var col = el.closest('.col-md-6');
			if (!col) return;
			col.style.display = isPJ ? 'none' : '';
			if (isPJ) {
				if (el.tagName === 'SELECT') el.selectedIndex = 0;
				else el.value = '';
			}
		});
		rebuildSteps();
	}

	function showErrors(msgs) {
		var box = document.getElementById('wizard-errors');
		if (!box) return;
		if (!msgs || !msgs.length) {
			box.style.display = 'none';
			box.innerHTML = '';
			return;
		}
		box.innerHTML = msgs.map(function (m) {
			return '<div>⚠ ' + m + '</div>';
		}).join('');
		box.style.display = '';
		box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
	}

	// -----------------------------------------------------------------------
	// wizardFetch — fetch com tratamento de erros HTTP e Content-Type
	// -----------------------------------------------------------------------

	function wizardFetch(url, options) {
		var opts = Object.assign({ credentials: 'same-origin' }, options);
		return fetch(url, opts).then(function (r) {
			if (!r.ok) {
				var httpMsgs = {
					401: 'Sessão expirada — recarregue a página.',
					403: 'Sem permissão para esta ação.',
					404: 'Recurso não encontrado.',
					500: 'Erro interno do servidor.',
				};
				var msg = httpMsgs[r.status] || ('Erro HTTP ' + r.status + '.');
				console.error('wizardFetch', r.status, url);
				return Promise.reject(new Error(msg));
			}
			var ct = r.headers.get('Content-Type') || '';
			if (!ct.includes('application/json')) {
				console.error('wizardFetch: resposta não-JSON', ct, url);
				return Promise.reject(new Error('Resposta inesperada do servidor.'));
			}
			return r.json();
		});
	}

	// -----------------------------------------------------------------------
	// Validação por step
	// -----------------------------------------------------------------------

	function validate(stepId) {
		var errors = [];

		if (stepId === 'step-1') {
			if (!getVal('id_name')) errors.push('Nome é obrigatório.');
			if (!getVal('id_documento')) errors.push('CPF/CNPJ é obrigatório.');
			var email = getVal('id_email');
			if (!email) {
				errors.push('E-mail é obrigatório.');
			} else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
				errors.push('E-mail inválido.');
			}
		}

		if (stepId === 'step-2') {
			if (!getVal('id_conj_nome')) errors.push('Nome do cônjuge é obrigatório.');
		}

		if (stepId === 'step-7') {
			if (!wizardRepresentantes.length) errors.push('Informe ao menos um representante legal.');
		}

		// step-3 (Documentos) — sem campos obrigatórios

		if (stepId === 'step-4') {
			var req = {
				'id_end_cep': 'CEP',
				'id_end_rua': 'Rua',
				'id_end_numero': 'Número',
				'id_end_bairro': 'Bairro',
				'id_end_cidade': 'Cidade',
				'id_end_estado': 'Estado',
			};
			Object.keys(req).forEach(function (id) {
				if (!getVal(id)) errors.push(req[id] + ' é obrigatório.');
			});
		}

		if (stepId === 'step-5') {
			var tels = window.telefonesTemp;
			if (!tels || !tels.length) {
				errors.push('Informe pelo menos um telefone.');
			}
		}

		return errors;
	}

	// -----------------------------------------------------------------------
	// Progresso e navegação
	// -----------------------------------------------------------------------

	function renderProgress() {
		var bar = document.getElementById('wizard-progress-items');
		var mobile = document.getElementById('wizard-progress-mobile');
		if (!bar) return;

		bar.innerHTML = '';

		steps.forEach(function (step, i) {
			var done = i < cur;
			var active = i === cur;
			var cls = done ? 'wz-done' : (active ? 'wz-active' : 'wz-future');

			var item = document.createElement('div');
			item.className = 'wz-step ' + cls;

			var icon = done
				? '<i class="fas fa-check"></i>'
				: '<span class="wz-num">' + (i + 1) + '</span>';

			item.innerHTML = '<div class="wz-circle">' + icon + '</div>'
				+ '<div class="wz-label d-none d-sm-block">' + step.label + '</div>';
			bar.appendChild(item);

			if (i < steps.length - 1) {
				var conn = document.createElement('div');
				conn.className = 'wz-connector' + (done ? ' done' : '');
				bar.appendChild(conn);
			}
		});

		if (mobile) {
			mobile.textContent = 'Etapa ' + (cur + 1) + ' de ' + steps.length + ': ' + steps[cur].label;
		}
	}

	function renderNav() {
		var prev = document.getElementById('wizard-btn-prev');
		var next = document.getElementById('wizard-btn-next');
		var sub = document.getElementById('wizard-btn-submit');
		var isLast = cur === steps.length - 1;

		if (prev) prev.style.display = cur === 0 ? 'none' : '';
		if (next) next.style.display = isLast ? 'none' : '';
		if (sub) sub.style.display = isLast ? '' : 'none';
	}

	function showStep(index) {
		ALL_STEPS.forEach(function (s) {
			var el = document.getElementById(s.id);
			if (el) el.style.display = 'none';
		});

		var el = document.getElementById(steps[index].id);
		if (el) {
			el.style.display = '';
			var card = document.getElementById('wizard-card');
			if (card) card.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}

		renderProgress();
		renderNav();
		showErrors([]);

		if (steps[index].id === 'step-6') renderReview();
		if (steps[index].id === 'step-3') onArquivosStepEnter();
		if (steps[index].id === 'step-7') renderRepresentantesList();
	}

	// -----------------------------------------------------------------------
	// Step Documentos — AJAX inline
	// -----------------------------------------------------------------------

	function onArquivosStepEnter() {
		var tipoEl = document.getElementById('wz-doc-tipo');
		if (!tipoEl) return;

		var choices = getTipoPessoa() === 'PJ' ? TIPO_CHOICES_PJ : TIPO_CHOICES_PF;
		tipoEl.innerHTML = '<option value="">— selecione —</option>'
			+ choices.map(function (c) {
				return '<option value="' + c[0] + '">' + c[1] + '</option>';
			}).join('');

		var pertenceGroup = document.getElementById('wz-doc-pertence-a-group');
		if (pertenceGroup) pertenceGroup.style.display = isCasado() ? '' : 'none';

		renderArquivosList();
	}

	function renderArquivosList() {
		var container = document.getElementById('wz-arquivos-lista');
		if (!container) return;

		if (!wizardArquivos.length) {
			container.innerHTML = '<p class="text-muted small mb-0">Nenhum arquivo adicionado ainda.</p>';
			return;
		}

		container.innerHTML = '<table class="table table-sm table-bordered mb-0">'
			+ '<thead><tr><th>Tipo</th><th>Descrição</th><th>Arquivo</th><th></th></tr></thead>'
			+ '<tbody>'
			+ wizardArquivos.map(function (d) {
				return '<tr>'
					+ '<td>' + d.tipo_display + '</td>'
					+ '<td>' + (d.descricao || '—') + '</td>'
					+ '<td><a href="' + d.arquivo_url + '" target="_blank" rel="noopener">'
					+ '<i class="fas fa-file me-1"></i>Ver</a></td>'
					+ '<td><button type="button" class="btn btn-danger btn-sm" '
					+ 'style="border-radius:6px;padding:.2rem .5rem;" '
					+ 'onclick="wizardDelArquivo(' + d.id + ')">'
					+ '<i class="fas fa-trash"></i></button></td>'
					+ '</tr>';
			}).join('')
			+ '</tbody></table>';
	}

	function _wzUrlAdd() {
		var base = (window.WIZARD_URLS && window.WIZARD_URLS.arquivoAddBase)
			|| '/clientes/00000000-0000-0000-0000-000000000000/wizard/arquivo-add/';
		return base.replace('00000000-0000-0000-0000-000000000000', clienteUuid);
	}

	function _wzUrlDel(id) {
		var base = (window.WIZARD_URLS && window.WIZARD_URLS.arquivoDelBase)
			|| '/clientes/00000000-0000-0000-0000-000000000000/wizard/arquivo-del/0/';
		return base
			.replace('00000000-0000-0000-0000-000000000000', clienteUuid)
			.replace('/arquivo-del/0/', '/arquivo-del/' + id + '/');
	}

	function _wzUrlFinalizar() {
		var base = (window.WIZARD_URLS && window.WIZARD_URLS.finalizarBase)
			|| '/clientes/00000000-0000-0000-0000-000000000000/wizard/finalizar/';
		return base.replace('00000000-0000-0000-0000-000000000000', clienteUuid);
	}

	window.wizardAddArquivo = function () {
		var errEl = document.getElementById('wz-arquivos-erro');

		if (!clienteUuid) {
			if (errEl) { errEl.textContent = 'Aguarde: o cadastro ainda está sendo salvo.'; errEl.style.display = ''; }
			return;
		}

		var tipo = document.getElementById('wz-doc-tipo') ? document.getElementById('wz-doc-tipo').value : '';
		var descricao = document.getElementById('wz-doc-descricao') ? document.getElementById('wz-doc-descricao').value : '';
		var arquivoInput = document.getElementById('wz-doc-arquivo');
		var pertenceEl = document.getElementById('wz-doc-pertence-a');
		var pertenceA = (isCasado() && pertenceEl) ? pertenceEl.value : 'TITULAR';

		if (!tipo) {
			if (errEl) { errEl.textContent = 'Selecione o tipo do documento.'; errEl.style.display = ''; }
			return;
		}
		if (!arquivoInput || !arquivoInput.files || !arquivoInput.files[0]) {
			if (errEl) { errEl.textContent = 'Selecione um arquivo.'; errEl.style.display = ''; }
			return;
		}
		if (errEl) errEl.style.display = 'none';

		var data = new FormData();
		data.append('csrfmiddlewaretoken', getCsrf());
		data.append('tipo', tipo);
		data.append('pertence_a', pertenceA);
		data.append('descricao', descricao);
		data.append('arquivo', arquivoInput.files[0]);

		wizardFetch(_wzUrlAdd(), { method: 'POST', body: data })
			.then(function (d) {
				if (d.ok) {
					wizardArquivos.push(d.doc);
					renderArquivosList();
					if (document.getElementById('wz-doc-tipo')) document.getElementById('wz-doc-tipo').value = '';
					if (document.getElementById('wz-doc-descricao')) document.getElementById('wz-doc-descricao').value = '';
					if (arquivoInput) arquivoInput.value = '';
				} else {
					if (errEl) { errEl.textContent = d.error || 'Erro ao adicionar documento.'; errEl.style.display = ''; }
				}
			})
			.catch(function (err) {
				if (errEl) { errEl.textContent = err.message || 'Erro de conexão.'; errEl.style.display = ''; }
			});
	};

	window.wizardDelArquivo = function (id) {
		if (!confirm('Excluir este arquivo?')) return;

		var data = new FormData();
		data.append('csrfmiddlewaretoken', getCsrf());

		wizardFetch(_wzUrlDel(id), { method: 'POST', body: data })
			.then(function (d) {
				if (d.ok) {
					wizardArquivos = wizardArquivos.filter(function (a) { return a.id !== id; });
					renderArquivosList();
				}
			})
			.catch(function () {});
	};

	// -----------------------------------------------------------------------
	// Step Representantes legais (PJ) — AJAX inline
	// -----------------------------------------------------------------------

	function _wzUrlRepresentanteAdd() {
		var base = (window.WIZARD_URLS && window.WIZARD_URLS.representanteAddBase)
			|| '/clientes/00000000-0000-0000-0000-000000000000/wizard/representante/add/';
		return base.replace('00000000-0000-0000-0000-000000000000', clienteUuid);
	}

	function _wzUrlRepresentanteDel(repUuid) {
		var base = (window.WIZARD_URLS && window.WIZARD_URLS.representanteDelBase)
			|| '/clientes/00000000-0000-0000-0000-000000000000/wizard/representante/11111111-1111-1111-1111-111111111111/del/';
		return base
			.replace('00000000-0000-0000-0000-000000000000', clienteUuid)
			.replace('11111111-1111-1111-1111-111111111111', repUuid);
	}

	function _wzUrlRepresentanteArquivoAdd(repUuid) {
		var base = (window.WIZARD_URLS && window.WIZARD_URLS.representanteArquivoAddBase)
			|| '/clientes/wizard/representante/11111111-1111-1111-1111-111111111111/arquivo-add/';
		return base.replace('11111111-1111-1111-1111-111111111111', repUuid);
	}

	function _wzUrlRepresentanteArquivoDel(docUuid) {
		var base = (window.WIZARD_URLS && window.WIZARD_URLS.representanteArquivoDelBase)
			|| '/clientes/wizard/representante/arquivo-del/22222222-2222-2222-2222-222222222222/';
		return base.replace('22222222-2222-2222-2222-222222222222', docUuid);
	}

	function toggleRepConjugeGroup() {
		var ec = document.getElementById('wz-rep-estado-civil');
		var group = document.getElementById('wz-rep-conjuge-group');
		if (group) group.style.display = (ec && ec.value === 'casado') ? '' : 'none';
	}

	function renderRepresentantesList() {
		var container = document.getElementById('wz-rep-lista');
		if (!container) return;

		if (!wizardRepresentantes.length) {
			container.innerHTML = '<p class="text-muted small mb-0">Nenhum representante adicionado ainda.</p>';
			return;
		}

		container.innerHTML = wizardRepresentantes.map(function (r, idx) {
			var docsHtml = (r.documentos || []).map(function (d) {
				return '<span class="badge bg-secondary me-1 mb-1">' + d.tipo_display
					+ ' <i class="fas fa-times ms-1" style="cursor:pointer;" '
					+ 'onclick="wizardDelRepresentanteArquivo(\'' + r.uuid + '\',\'' + d.uuid + '\')"></i></span>';
			}).join('');
			return '<div class="card mb-2" style="border-radius:8px;">'
				+ '<div class="card-body py-2 px-3">'
				+ '<div class="d-flex justify-content-between align-items-start">'
				+ '<div><strong>' + r.nome + '</strong> — ' + r.documento
				+ (r.cargo ? ' · ' + r.cargo : '') + (r.estado_civil ? ' · ' + r.estado_civil : '') + '</div>'
				+ '<button type="button" class="btn btn-danger btn-sm" style="border-radius:6px;" '
				+ 'onclick="wizardDelRepresentante(\'' + r.uuid + '\')"><i class="fas fa-trash"></i></button>'
				+ '</div>'
				+ '<div class="mt-2">'
				+ '<div class="mb-1">' + (docsHtml || '<span class="text-muted small">Sem documentos anexados.</span>') + '</div>'
				+ '<div class="d-flex gap-1 align-items-end flex-wrap">'
				+ '<select id="wz-rep-doc-tipo-' + idx + '" class="glot-select" style="max-width:160px;">'
				+ '<option value="">Tipo doc.</option><option value="RG">RG</option><option value="CPF">CPF</option>'
				+ '<option value="CNH">CNH</option><option value="PROCURACAO">Procuração</option>'
				+ '<option value="COMPROVANTE_ESTADO_CIVIL">Comprovante de Estado Civil</option>'
				+ '<option value="OUTROS">Outros</option>'
				+ '</select>'
				+ '<input type="file" id="wz-rep-doc-arquivo-' + idx + '" class="glot-input" '
				+ 'accept=".jpg,.jpeg,.png,.pdf" style="max-width:200px;">'
				+ '<button type="button" class="btn btn-outline-primary btn-sm" '
				+ 'onclick="wizardAddRepresentanteArquivo(\'' + r.uuid + '\',' + idx + ')">'
				+ '<i class="fas fa-paperclip"></i></button>'
				+ '</div></div></div></div>';
		}).join('');
	}

	window.wizardAddRepresentante = function () {
		var errEl = document.getElementById('wz-rep-erro');

		if (!clienteUuid) {
			if (errEl) { errEl.textContent = 'Aguarde: o cadastro ainda está sendo salvo.'; errEl.style.display = ''; }
			return;
		}

		var nome = getVal('wz-rep-nome');
		var documento = getVal('wz-rep-documento');
		if (!nome || !documento) {
			if (errEl) { errEl.textContent = 'Nome e CPF são obrigatórios.'; errEl.style.display = ''; }
			return;
		}
		var estadoCivil = getVal('wz-rep-estado-civil');
		if (estadoCivil === 'casado' && !getVal('wz-rep-conj-nome')) {
			if (errEl) { errEl.textContent = 'Informe o nome do cônjuge do representante.'; errEl.style.display = ''; }
			return;
		}
		if (errEl) errEl.style.display = 'none';

		var data = new FormData();
		data.append('csrfmiddlewaretoken', getCsrf());
		data.append('nome', nome);
		data.append('documento', documento);
		data.append('numero_rg', getVal('wz-rep-numero-rg'));
		data.append('orgao_emissor_rg', getVal('wz-rep-orgao-emissor-rg'));
		data.append('email', getVal('wz-rep-email'));
		data.append('cargo', getVal('wz-rep-cargo'));
		data.append('estado_civil', estadoCivil);
		data.append('conj_nome', getVal('wz-rep-conj-nome'));
		data.append('conj_numero_rg', getVal('wz-rep-conj-numero-rg'));
		data.append('conj_orgao_emissor_rg', getVal('wz-rep-conj-orgao-emissor-rg'));
		data.append('conj_documento', getVal('wz-rep-conj-documento'));

		wizardFetch(_wzUrlRepresentanteAdd(), { method: 'POST', body: data })
			.then(function (d) {
				if (d.ok) {
					d.representante.documentos = [];
					wizardRepresentantes.push(d.representante);
					renderRepresentantesList();
					['wz-rep-nome', 'wz-rep-documento', 'wz-rep-numero-rg', 'wz-rep-orgao-emissor-rg',
					 'wz-rep-email', 'wz-rep-cargo', 'wz-rep-conj-nome', 'wz-rep-conj-numero-rg',
					 'wz-rep-conj-orgao-emissor-rg', 'wz-rep-conj-documento'].forEach(function (id) {
						var el = document.getElementById(id);
						if (el) el.value = '';
					});
					var ecEl = document.getElementById('wz-rep-estado-civil');
					if (ecEl) ecEl.selectedIndex = 0;
					toggleRepConjugeGroup();
				} else {
					if (errEl) { errEl.textContent = d.error || 'Erro ao adicionar representante.'; errEl.style.display = ''; }
				}
			})
			.catch(function (err) {
				if (errEl) { errEl.textContent = err.message || 'Erro de conexão.'; errEl.style.display = ''; }
			});
	};

	window.wizardDelRepresentante = function (repUuid) {
		if (!confirm('Remover este representante?')) return;

		var data = new FormData();
		data.append('csrfmiddlewaretoken', getCsrf());

		wizardFetch(_wzUrlRepresentanteDel(repUuid), { method: 'POST', body: data })
			.then(function (d) {
				if (d.ok) {
					wizardRepresentantes = wizardRepresentantes.filter(function (r) { return r.uuid !== repUuid; });
					renderRepresentantesList();
				}
			})
			.catch(function () {});
	};

	window.wizardAddRepresentanteArquivo = function (repUuid, idx) {
		var tipoEl = document.getElementById('wz-rep-doc-tipo-' + idx);
		var arquivoEl = document.getElementById('wz-rep-doc-arquivo-' + idx);
		if (!tipoEl || !tipoEl.value) { alert('Selecione o tipo do documento.'); return; }
		if (!arquivoEl || !arquivoEl.files || !arquivoEl.files[0]) { alert('Selecione um arquivo.'); return; }

		var data = new FormData();
		data.append('csrfmiddlewaretoken', getCsrf());
		data.append('tipo', tipoEl.value);
		data.append('pertence_a', 'TITULAR');
		data.append('arquivo', arquivoEl.files[0]);

		wizardFetch(_wzUrlRepresentanteArquivoAdd(repUuid), { method: 'POST', body: data })
			.then(function (d) {
				if (d.ok) {
					var rep = wizardRepresentantes.filter(function (r) { return r.uuid === repUuid; })[0];
					if (rep) {
						rep.documentos = rep.documentos || [];
						rep.documentos.push(d.doc);
					}
					renderRepresentantesList();
				} else {
					alert(d.error || 'Erro ao anexar documento.');
				}
			})
			.catch(function (err) { alert(err.message || 'Erro de conexão.'); });
	};

	window.wizardDelRepresentanteArquivo = function (repUuid, docUuid) {
		if (!confirm('Excluir este arquivo?')) return;

		var data = new FormData();
		data.append('csrfmiddlewaretoken', getCsrf());

		wizardFetch(_wzUrlRepresentanteArquivoDel(docUuid), { method: 'POST', body: data })
			.then(function (d) {
				if (d.ok) {
					var rep = wizardRepresentantes.filter(function (r) { return r.uuid === repUuid; })[0];
					if (rep) rep.documentos = (rep.documentos || []).filter(function (doc) { return doc.uuid !== docUuid; });
					renderRepresentantesList();
				}
			})
			.catch(function () {});
	};

	// -----------------------------------------------------------------------
	// Revisão
	// -----------------------------------------------------------------------

	function displayVal(id) {
		var el = document.getElementById(id);
		if (!el) return '—';
		if (el.tagName === 'SELECT') {
			var opt = el.options[el.selectedIndex];
			return (opt && opt.text.trim()) || '—';
		}
		return el.value.trim() || '—';
	}

	function rvSection(title, icon, color, rows) {
		var rowsHtml = rows.map(function (r) {
			return '<div class="wz-rv-row">'
				+ '<span class="wz-rv-label">' + r[0] + '</span>'
				+ '<span class="wz-rv-val">' + r[1] + '</span>'
				+ '</div>';
		}).join('');
		return '<div class="wz-rv-section">'
			+ '<div class="wz-rv-head" style="color:' + color + '">'
			+ '<i class="' + icon + ' me-2"></i>' + title + '</div>'
			+ '<div class="wz-rv-body">' + rowsHtml + '</div>'
			+ '</div>';
	}

	function renderReview() {
		var container = document.getElementById('review-content');
		if (!container) return;

		var html = rvSection('Dados pessoais', 'fas fa-user', '#2e7d32', [
			['Nome', displayVal('id_name')],
			['Nome usual', displayVal('id_nome_usual')],
			['CPF / CNPJ', displayVal('id_documento')],
			['E-mail', displayVal('id_email')],
			['Data de nasc.', displayVal('id_data_ns')],
			['Estado civil', displayVal('id_estado_civil')],
			['RG', displayVal('id_numero_rg')],
			['Órgão emissor', displayVal('id_orgao_emissor_rg')],
			['Profissão', displayVal('id_profissao')],
			['Renda', displayVal('id_renda')],
			['Naturalidade', displayVal('id_naturalidade')],
			['Nacionalidade', displayVal('id_nacionalidade')],
		]);

		if (isCasado()) {
			html += rvSection('Cônjuge', 'fas fa-heart', '#e65100', [
				['Nome', displayVal('id_conj_nome')],
				['CPF', displayVal('id_conj_documento')],
				['RG', displayVal('id_conj_numero_rg')],
				['Órgão emissor', displayVal('id_conj_orgao_emissor_rg')],
			]);
		}

		if (getTipoPessoa() === 'PJ') {
			var repRows = wizardRepresentantes.length
				? wizardRepresentantes.map(function (r) {
					return [r.nome, r.documento + (r.cargo ? ' · ' + r.cargo : '')];
				})
				: [['Representantes', 'Nenhum representante adicionado']];
			html += rvSection('Representantes legais', 'fas fa-user-tie', '#c62828', repRows);
		}

		var arqRows = wizardArquivos.length
			? wizardArquivos.map(function (a) { return [a.tipo_display, a.descricao || '—']; })
			: [['Arquivos', 'Nenhum arquivo adicionado']];
		html += rvSection('Arquivos', 'fas fa-folder-open', '#7b1fa2', arqRows);

		html += rvSection('Endereço', 'fas fa-map-marker-alt', '#1565c0', [
			['CEP', displayVal('id_end_cep')],
			['Rua', displayVal('id_end_rua')],
			['Número', displayVal('id_end_numero')],
			['Complemento', displayVal('id_end_complemento')],
			['Bairro', displayVal('id_end_bairro')],
			['Cidade', displayVal('id_end_cidade')],
			['Estado', displayVal('id_end_estado')],
		]);

		var tels = (window.telefonesTemp || []).map(function (t) {
			return typeof t === 'string' ? t : (t.numero || '');
		}).join(', ') || 'Não informado';
		html += rvSection('Contatos', 'fas fa-phone', '#0097a7', [
			['Telefones', tels],
		]);

		container.innerHTML = html;
	}

	// -----------------------------------------------------------------------
	// Save AJAX por etapa
	// -----------------------------------------------------------------------

	function _appendField(formData, fieldId) {
		var el = document.getElementById(fieldId);
		if (!el) return;
		var name = el.name || fieldId.replace('id_', '');
		formData.append(name, el.value);
	}

	function saveStep(stepId, callback) {
		var data = new FormData();
		data.append('csrfmiddlewaretoken', getCsrf());
		data.append('step_id', stepId);
		data.append('cliente_uuid', clienteUuid);

		if (stepId === 'step-1') {
			['id_name', 'id_nome_usual', 'id_documento', 'id_email',
			 'id_data_ns', 'id_estado_civil', 'id_numero_rg', 'id_orgao_emissor_rg',
			 'id_profissao', 'id_renda', 'id_naturalidade', 'id_nacionalidade',
			 'id_observacao'].forEach(function (id) { _appendField(data, id); });
		} else if (stepId === 'step-2') {
			['id_conj_nome', 'id_conj_documento',
			 'id_conj_numero_rg', 'id_conj_orgao_emissor_rg'].forEach(function (id) { _appendField(data, id); });
		} else if (stepId === 'step-4') {
			['id_end_cep', 'id_end_rua', 'id_end_numero',
			 'id_end_complemento', 'id_end_bairro', 'id_end_cidade', 'id_end_estado'].forEach(function (id) { _appendField(data, id); });
		} else if (stepId === 'step-5') {
			data.append('telefones_json', JSON.stringify(window.telefonesTemp || []));
		}

		var url = (window.WIZARD_URLS && window.WIZARD_URLS.salvarPasso)
			|| '/clientes/wizard/salvar-passo/';

		wizardFetch(url, { method: 'POST', body: data })
			.then(function (d) {
				if (d.ok) {
					if (d.uuid) {
						clienteUuid = d.uuid;
						var uuidEl = document.getElementById('wizard-cliente-uuid');
						if (uuidEl) uuidEl.value = d.uuid;
					}
					callback(true);
				} else {
					var msgs = [];
					if (d.errors) {
						Object.keys(d.errors).forEach(function (k) {
							(d.errors[k] || []).forEach(function (e) { msgs.push(e); });
						});
					} else if (d.error) {
						msgs.push(d.error);
					}
					showErrors(msgs.length ? msgs : ['Erro ao salvar. Tente novamente.']);
					callback(false);
				}
			})
			.catch(function (err) {
				showErrors([err.message || 'Erro de conexão. Tente novamente.']);
				callback(false);
			});
	}

	// -----------------------------------------------------------------------
	// Navegação
	// -----------------------------------------------------------------------

	function next() {
		var stepId = steps[cur].id;
		var errors = validate(stepId);
		if (errors.length) { showErrors(errors); return; }
		showErrors([]);

		if (AJAX_SAVE_STEPS.indexOf(stepId) >= 0) {
			saveStep(stepId, function (ok) {
				if (ok && cur < steps.length - 1) {
					cur++;
					showStep(cur);
				}
			});
		} else {
			if (cur < steps.length - 1) { cur++; showStep(cur); }
		}
	}

	function prev() {
		showErrors([]);
		if (cur > 0) { cur--; showStep(cur); }
	}

	function onEstadoCivilChange() {
		var wasOnConjuge = steps[cur] && steps[cur].id === 'step-2';
		rebuildSteps();
		if (wasOnConjuge && !isCasado()) cur = Math.max(0, cur - 1);
		showStep(cur);
	}

	// -----------------------------------------------------------------------
	// Finalizar wizard
	// -----------------------------------------------------------------------

	window.wizardFinalizar = function () {
		if (!clienteUuid) {
			showErrors(['Dados não salvos. Preencha e avance todos os passos anteriores.']);
			return;
		}

		var btn = document.getElementById('wizard-btn-submit');
		if (btn) {
			btn.disabled = true;
			btn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Aguarde...';
		}

		var data = new FormData();
		data.append('csrfmiddlewaretoken', getCsrf());
		var origemEl = document.getElementById('wizard-origem');
		var loteEl = document.getElementById('wizard-lote-uuid');
		var nextEl = document.getElementById('wizard-next');
		var transferenciaUuidEl = document.getElementById('wizard-transferencia-uuid');
		var vendaUuidEl = document.getElementById('wizard-venda-uuid');
		data.append('origem', origemEl ? origemEl.value : 'lista');
		data.append('lote_uuid', loteEl ? loteEl.value : '');
		data.append('next', nextEl ? nextEl.value : '');
		data.append('transferencia_uuid', transferenciaUuidEl ? transferenciaUuidEl.value : '');
		data.append('venda_uuid', vendaUuidEl ? vendaUuidEl.value : '');

		wizardFetch(_wzUrlFinalizar(), { method: 'POST', body: data })
			.then(function (d) {
				if (d.ok) {
					window.location.href = d.redirect_url;
				} else {
					var msgs = [];
					if (d.errors) {
						Object.keys(d.errors).forEach(function (k) { msgs.push(d.errors[k]); });
					} else {
						msgs.push(d.error || 'Erro ao finalizar cadastro.');
					}
					showErrors(msgs);
					if (btn) {
						btn.disabled = false;
						btn.innerHTML = '<i class="fas fa-save me-1"></i>Cadastrar cliente';
					}
				}
			})
			.catch(function (err) {
				showErrors([err.message || 'Erro de conexão ao finalizar.']);
				if (btn) {
					btn.disabled = false;
					btn.innerHTML = '<i class="fas fa-save me-1"></i>Cadastrar cliente';
				}
			});
	};

	// -----------------------------------------------------------------------
	// Init
	// -----------------------------------------------------------------------

	function init() {
		rebuildSteps();

		var estadoCivil = document.getElementById('id_estado_civil');
		if (estadoCivil) {
			estadoCivil.addEventListener('change', onEstadoCivilChange);
			if (typeof $ !== 'undefined') {
				$(document).on('change select2:select select2:unselect', '[name="estado_civil"]', onEstadoCivilChange);
			}
		}

		var docField = document.getElementById('id_documento');
		if (docField) {
			docField.addEventListener('input', updateDocLabels);
			updateDocLabels();
		}

		var repEstadoCivil = document.getElementById('wz-rep-estado-civil');
		if (repEstadoCivil) repEstadoCivil.addEventListener('change', toggleRepConjugeGroup);

		var btnNext = document.getElementById('wizard-btn-next');
		var btnPrev = document.getElementById('wizard-btn-prev');
		if (btnNext) btnNext.addEventListener('click', next);
		if (btnPrev) btnPrev.addEventListener('click', prev);

		showStep(0);
	}

	if (document.readyState === 'loading') {
		document.addEventListener('DOMContentLoaded', init);
	} else {
		init();
	}
})();