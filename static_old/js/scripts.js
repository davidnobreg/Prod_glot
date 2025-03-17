//abri modal com os dados do cliente

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".btn-detalhes").forEach(button => {
        button.addEventListener("click", function () {
            let clienteId = this.getAttribute("data-id"); // Obtém o ID do cliente
            //console.log("Cliente ID capturado:", clienteId);  Verifica se o ID está correto

            fetch(`/clientes/select/${clienteId}/`)
                .then(response => {
                    console.log("Status da resposta:", response.status); // Verifica se a API responde
                    return response.json();
                })
                .then(data => {
                    // console.log("Dados recebidos:", data);  Mostra os dados recebidos

                    document.getElementById("cliente-id").textContent = data.id;
                    document.getElementById("cliente-name").textContent = data.name;
                    document.getElementById("cliente-documento").textContent = data.documento;
                    document.getElementById("cliente-email").textContent = data.email;
                })
                .catch(error => console.error("Erro ao buscar os detalhes:", error));
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

//abre modal de alteração
document.addEventListener("DOMContentLoaded", function () {
    // ... (seu código existente para buscar e exibir detalhes do cliente) ...

    document.querySelectorAll(".btn-alterar").forEach(button => {
        button.addEventListener("click", function () {
            let clienteId = this.getAttribute("data-id");

            fetch(`/cliente/${clienteId}/`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById("alterar-cliente-id").value = data.id;
                    document.getElementById("alterar-cliente-name").value = data.name;
                    document.getElementById("alterar-cliente-email").value = data.email;


                    let modal = new bootstrap.Modal(document.getElementById("clienteAlterarModal"));
                    modal.show();
                })
                .catch(error => console.error("Erro ao buscar os detalhes:", error));
        });
    });


// modal update
    document.getElementById("btn-salvar-alteracoes").addEventListener("click", function () {
        let clienteId = document.getElementById("alterar-cliente-id").value;
        let name = document.getElementById("alterar-cliente-name").value;
        let email = document.getElementById("alterar-cliente-email").value;


        fetch(`/clientes/update/${clienteId}/`, {
            method: "PUT", // Ou "PATCH", dependendo da sua API
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                name: name,
                email: email,

            }),
        })
            .then(response => {
                if (response.ok) {
                    // Atualização bem-sucedida
                    alert("Cliente atualizado com sucesso!");
                    // Feche o modal e atualize a tabela/lista de clientes
                    let modal = bootstrap.Modal.getInstance(document.getElementById("clienteAlterarModal"));
                    modal.hide();
                    // Recarregue a página ou atualize a tabela de clientes
                    location.reload();
                } else {
                    // Erro na atualização
                    alert("Erro ao atualizar o cliente.");
                }
            })
            .catch(error => console.error("Erro ao atualizar o cliente:", error));
    });
});
