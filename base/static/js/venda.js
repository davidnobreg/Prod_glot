document.addEventListener("DOMContentLoaded", function () {
    // ==============================
    // Modal de Venda (Deleção)
    // ==============================
    const vendaModalDelete = document.getElementById('vendaModalDelete');

    function preencherModalVenda(vendaId, data) {
        if (!data || typeof data !== 'object') return;
        document.getElementById('empreendimento').textContent = vendaId;
        document.getElementById('venda-id-display').textContent = clienteId;
        document.getElementById('cliente-name').textContent = data.name || 'Nome não encontrado';
        document.getElementById('cliente-documento').textContent = data.documento || 'Documento não encontrado';
        document.getElementById('cliente-email').textContent = data.email || 'Email não encontrado';
    }

    if (vendaModalDelete) {
        vendaModalDelete.addEventListener('show.bs.modal', event => {
            const button = event.relatedTarget;
            const vendaId = button.getAttribute('data-venda-id');

            fetch(`/vendas/select/${vendaId}/`)
                .then(resp => resp.ok ? resp.json() : Promise.reject(resp.status))
                .then(data => preencherModalVenda(vendaId, data))
                .catch(err => console.error('Erro ao buscar dados da venda:', err));
        });

        const btnDeletarVenda = document.getElementById("btn-deletar-venda");
        if (btnDeletarVenda) {
            btnDeletarVenda.addEventListener("click", () => {
                const vendaId = document.getElementById("venda-id").textContent;
                window.location.href = `/vendas/venda_delete/${vendaId}/`;
            });
        }
    }
}