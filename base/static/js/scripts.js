//função seleciona clientes modal
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".btn-detalhes").forEach(button => {
        button.addEventListener("click", function () {
            let clienteId = this.getAttribute("data-id");
            console.log("Cliente ID capturado:", clienteId);

            let modal = new bootstrap.Modal(document.getElementById("clienteModal"));
            let loadingIndicator = document.getElementById("loading-indicator");
            loadingIndicator.style.display = "block";

            fetch(`/clientes/select/${clienteId}/`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Erro HTTP! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    document.getElementById("cliente-id").textContent = data.id;
                    document.getElementById("cliente-name").textContent = data.name;
                    document.getElementById("cliente-email").textContent = data.email;

                    loadingIndicator.style.display = "none";
                    modal.show();
                })
                .catch(error => {
                    console.error("Erro ao buscar os detalhes:", error);
                    loadingIndicator.style.display = "none";
                    alert("Ocorreu um erro ao buscar os detalhes do cliente.");
                });
        });
    });
});

//deleta cliente atraves do modal
document.addEventListener("DOMContentLoaded", function () {
    // ... (seu código existente para buscar e exibir detalhes do cliente) ...

    document.getElementById("btn-deletar-cliente").addEventListener("click", function () {
        let clienteId = document.getElementById("cliente-id").textContent;
        window.location.href = `/clientes/delete_cliente/${clienteId}/`; // Redireciona para a URL de exclusão
    });
});


//cadastra cliente model
document.addEventListener("DOMContentLoaded", function () {
    // Função para preencher o modal com os dados do cliente
    function preencherModalAlterar(cliente) {
        console.log("Dados do cliente recebidos:", cliente); // Adiciona esta linha

        document.getElementById("alterarClienteId").value = cliente.id;
        document.getElementById("alterarClienteNome").value = cliente.name;
        document.getElementById("alterarClienteEmail").value = cliente.email;
        document.getElementById("alterarClienteTelefone").value = cliente.fone;
    }

    // Evento de clique nos botões "Alterar"
    document.querySelectorAll(".btn-alterar").forEach(button => {
        button.addEventListener("click", function () {
            let clienteId = this.getAttribute("data-id");

            fetch(`/clientes/select/${clienteId}/`)
                .then(response => response.json())
                .then(data => {
                    preencherModalAlterar(data);
                    let modal = new bootstrap.Modal(document.getElementById("alterarClienteModal"));
                    modal.show();
                })
                .catch(error => console.error("Erro ao buscar os detalhes:", error));
        });
    });

    // Evento de clique no botão "Salvar"
    document.getElementById("salvarAlteracoes").addEventListener("click", function () {
        let clienteId = document.getElementById("alterarClienteId").value;
        let nome = document.getElementById("alterarClienteNome").value;
        let email = document.getElementById("alterarClienteEmail").value;
        let telefone = document.getElementById("alterarClienteTelefone").value;

        // Função para obter o CSRF token do cookie
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        const csrftoken = getCookie('csrftoken');

        fetch(`/clientes/update/${clienteId}/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrftoken, // Adiciona o CSRF token aos cabeçalhos
            },
            body: JSON.stringify({
                name: nome,
                email: email,
                telefone: telefone,
            }),
        })
            .then(response => {
                if (response.ok) {
                    alert("Cliente atualizado com sucesso!");
                    let modal = bootstrap.Modal.getInstance(document.getElementById("alterarClienteModal"));
                    modal.hide();
                    location.reload();
                } else {
                    alert("Erro ao atualizar o cliente.");
                }
            })
            .catch(error => console.error("Erro ao atualizar o cliente:", error));
    });
});

//carrrega empreendimento
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".btn-detalhes-empreendimento").forEach(button => {
        button.addEventListener("click", function () {
            let empreendimentoId = this.getAttribute("data-id");
           // console.log("Cliente ID capturado:", empreendimentoId);

            let modal = new bootstrap.Modal(document.getElementById("empreendimentoModal"));
            let loadingIndicator = document.getElementById("loading-indicator");
            loadingIndicator.style.display = "block";

            fetch(`/empreendimentos/select/${empreendimentoId}/`)
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Erro HTTP! status: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    document.getElementById("empreendimento-id").textContent = data.id;
                    document.getElementById("empreendimento-nome").textContent = data.nome;


                    loadingIndicator.style.display = "none";
                    modal.show();
                })
                .catch(error => {
                    console.error("Erro ao buscar os detalhes:", error);
                    loadingIndicator.style.display = "none";
                    alert("Ocorreu um erro ao buscar os detalhes do cliente.");
                });
        });
    });
})

//deleta Empreendimento atraves do modal
document.addEventListener("DOMContentLoaded", function () {
    // ... (seu código existente para buscar e exibir detalhes do empreendimento) ...

    document.getElementById("btn-deletar-empreendimento").addEventListener("click", function () {
        let empreendimento_Id = document.getElementById("empreendimento-id").textContent;
        window.location.href = `/empreendimentos/deleta_empreendimento/${empreendimento_Id}/`; // Redireciona para a URL de exclusão
    });
});
