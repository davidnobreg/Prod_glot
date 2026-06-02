// 1. Defina a função de comportamento (como você já tem)
var SPMaskBehavior = function (val) {
    // Remove tudo que não for dígito e retorna a máscara com base no tamanho
    val = val.replace(/\D/g, '');
    return val.length === 11 ? '(00) 00000-0000' : '(00) 0000-00009'; // *IMPORTANTE*: veja a dica abaixo!
};

// 2. Defina as opções da máscara, incluindo a função onKeyPress
var spOptions = {
    onKeyPress: function(val, e, field, options) {
        // Esta função garante que a máscara será reavaliada a cada tecla digitada.
        field.mask(SPMaskBehavior.apply({}, arguments), options);
    },
    // **OPCIONAL, MAS PODE AJUDAR A CORRIGIR O CURSOR:**
    clearIfNotMatch: true
};

// 3. Aplique a máscara ao seu campo de input
jQuery(function($){ // Garante que o código só roda depois que a página carrega
    $('.sp-telefone').mask(SPMaskBehavior, spOptions);
    // Ou use o ID: $('#telefone').mask(SPMaskBehavior, spOptions);
});


// ==============================
// Bootstrap tooltips
// ==============================
var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
tooltipTriggerList.forEach(function (tooltipTriggerEl) {
    new bootstrap.Tooltip(tooltipTriggerEl);
});


// ==============================
// Compartilhar relatório (PDF)
// ==============================
async function compartilharRelatorio() {
    const params = new URLSearchParams(window.location.search);
    const situacao = params.get('situacao') || 'TODOS';
    const botaoCompartilhar = document.querySelector('[data-loteamento-uuid]');
    const loteamento_uuid = botaoCompartilhar ? botaoCompartilhar.dataset.loteamentoUuid : '';
    const textoOriginal = botaoCompartilhar ? botaoCompartilhar.innerText : '';

    if (!loteamento_uuid) {
        alert('Empreendimento nao identificado para gerar o relatorio.');
        return;
    }

    const url = `/empreendimentos/relatorio-lotes/?situacao=${encodeURIComponent(situacao)}&loteamento_uuid=${encodeURIComponent(loteamento_uuid)}`;

    try {
        if (botaoCompartilhar) {
            botaoCompartilhar.disabled = true;
            botaoCompartilhar.innerText = 'Gerando PDF...';
        }

        const response = await fetch(url);

        if (!response.ok) {
            alert('Erro ao gerar o relatorio');
            return;
        }

        const blob = await response.blob();
        const file = new File([blob], 'relatorio_lotes.pdf', { type: 'application/pdf' });

        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            await navigator.share({
                title: 'Relatorio de Lotes',
                text: 'Segue o relatorio de lotes gerado.',
                files: [file]
            });
        } else {
            const urlBlob = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = urlBlob;
            a.setAttribute('download', file.name);
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                URL.revokeObjectURL(urlBlob);
                document.body.removeChild(a);
            }, 1000);

            alert('Este navegador nao suporta compartilhamento direto. O relatorio foi baixado.');
        }
    } catch (err) {
        console.error('Erro ao compartilhar:', err);
        alert('Ocorreu um erro ao gerar ou compartilhar o relatorio.');
    } finally {
        if (botaoCompartilhar) {
            botaoCompartilhar.disabled = false;
            botaoCompartilhar.innerText = textoOriginal;
        }
    }
}

window.compartilharRelatorio = compartilharRelatorio;

// ==============================
// Compartilhar proposta (PDF)
// ==============================
async function compartilharProposta(botao) {
    const url = botao.dataset.propostaUrl;
    const nomeArquivo = botao.dataset.propostaNome || 'proposta.pdf';
    const textoOriginal = botao.innerText;

    if (!url) {
        alert('Proposta nao identificada para gerar o PDF.');
        return;
    }

    const baixarPdf = (blob, fileName) => {
        const urlBlob = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = urlBlob;
        a.download = fileName;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();

        setTimeout(() => {
            URL.revokeObjectURL(urlBlob);
            document.body.removeChild(a);
        }, 1000);
    };

    botao.disabled = true;
    botao.innerText = 'Gerando PDF...';

    try {
        const response = await fetch(url);

        if (!response.ok) {
            alert('Erro ao gerar a proposta.');
            return;
        }

        const blob = await response.blob();
        const file = new File([blob], nomeArquivo, { type: 'application/pdf' });

        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            try {
                botao.innerText = 'Abrindo compartilhamento...';
                await navigator.share({
                    title: 'Proposta',
                    text: 'Segue a proposta em PDF.',
                    files: [file]
                });
            } catch (shareErr) {
                if (shareErr && shareErr.name === 'AbortError') {
                    return;
                }

                console.warn('Compartilhamento indisponivel, baixando PDF:', shareErr);
                baixarPdf(blob, file.name);
            }
        } else {
            baixarPdf(blob, file.name);
        }
    } catch (err) {
        console.error('Erro ao gerar proposta:', err);
        alert('Ocorreu um erro ao gerar a proposta.');
    } finally {
        botao.disabled = false;
        botao.innerText = textoOriginal;
    }
}

window.compartilharProposta = compartilharProposta;

document.addEventListener("DOMContentLoaded", () => {
    const cpfInputs = document.querySelectorAll(".mask-cpf");

    cpfInputs.forEach(input => {
        input.addEventListener("input", (e) => {
            let value = e.target.value.replace(/\D/g, "");
            if (value.length <= 11) {
                // CPF: 000.000.000-00
                value = value.replace(/(\d{3})(\d)/, "$1.$2");
                value = value.replace(/(\d{3})(\d)/, "$1.$2");
                value = value.replace(/(\d{3})(\d{1,2})$/, "$1-$2");
            } else if (value.length <= 14) {
                // CNPJ: 00.000.000/0000-00
                value = value.replace(/^(\d{2})(\d)/, "$1.$2");
                value = value.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
                value = value.replace(/\.(\d{3})(\d)/, ".$1/$2");
                value = value.replace(/(\d{4})(\d)/, "$1-$2");
            }
            e.target.value = value;
        });
    });
});

document.querySelectorAll('.dropdown-submenu .dropdown-toggle')
    .forEach(function(element) {

        element.addEventListener('click', function(e) {

            e.preventDefault();
            e.stopPropagation();

            let submenu = this.nextElementSibling;

            submenu.classList.toggle('show');

        });

    });
