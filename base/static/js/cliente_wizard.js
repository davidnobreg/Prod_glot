// Wizard multi-etapas para cadastro de cliente.
// Depende de: DOMContentLoaded → jQuery + telefone.js já carregados.
(function () {
	'use strict';

	var ALL_STEPS = [
		{ id: 'step-1', label: 'Dados pessoais' },
		{ id: 'step-2', label: 'Cônjuge', conditional: true },
		{ id: 'step-3', label: 'Documentos' },
		{ id: 'step-4', label: 'Endereço' },
		{ id: 'step-5', label: 'Contatos' },
		{ id: 'step-6', label: 'Revisão' },
	];

	var steps = [];
	var cur = 0;

	function isCasado() {
		var el = document.getElementById('id_estado_civil');
		return el && el.value === 'casado';
	}

	function rebuildSteps() {
		if (isCasado()) {
			steps = ALL_STEPS.slice();
		} else {
			steps = ALL_STEPS.filter(function (s) { return !s.conditional; });
		}
	}

	function getVal(id) {
		var el = document.getElementById(id);
		return el ? el.value.trim() : '';
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
	}

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

	function fileName(id) {
		var el = document.getElementById(id);
		if (!el || !el.files || !el.files.length) return 'Não informado';
		return el.files[0].name;
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

		html += rvSection('Documentos', 'fas fa-id-card', '#6a1b9a', [
			['RG frente', fileName('id_foto_rg_frente')],
			['RG verso', fileName('id_foto_rg_verso')],
			['CPF (foto)', fileName('id_foto_cpf')],
			['Comprovante res.', fileName('id_comprovante_residencia')],
			['Certidão est. civil', fileName('id_certidao_estado_civil')],
			['RG cônjuge frente', fileName('id_conj_rg_frente')],
			['RG cônjuge verso', fileName('id_conj_rg_verso')],
		]);

		html += rvSection('Endereço', 'fas fa-map-marker-alt', '#1565c0', [
			['CEP', displayVal('id_end_cep')],
			['Rua', displayVal('id_end_rua')],
			['Número', displayVal('id_end_numero')],
			['Complemento', displayVal('id_end_complemento')],
			['Bairro', displayVal('id_end_bairro')],
			['Cidade', displayVal('id_end_cidade')],
			['Estado', displayVal('id_end_estado')],
		]);

		var tels = (window.telefonesTemp || []).join(', ') || 'Não informado';
		html += rvSection('Contatos', 'fas fa-phone', '#0097a7', [
			['Telefones', tels],
		]);

		container.innerHTML = html;
	}

	// -----------------------------------------------------------------------
	// Navegação
	// -----------------------------------------------------------------------

	function next() {
		var errors = validate(steps[cur].id);
		if (errors.length) { showErrors(errors); return; }
		showErrors([]);
		if (cur < steps.length - 1) { cur++; showStep(cur); }
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

		var btnNext = document.getElementById('wizard-btn-next');
		var btnPrev = document.getElementById('wizard-btn-prev');
		if (btnNext) btnNext.addEventListener('click', next);
		if (btnPrev) btnPrev.addEventListener('click', prev);

		showStep(0);
	}

	document.addEventListener('DOMContentLoaded', init);
})();
