// Função Eventos para os botões do Painel Administrativo
document.addEventListener("DOMContentLoaded", () => {
    // Seleciona todos os botões de apagar e adiciona um listener de click
    document.querySelectorAll(".btn-delete-video").forEach(btn => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.videoId;
            if (!confirm(`Tem a certeza que quer eliminar o vídeo ${id}?`)) {
                return;
            }
            try {
                const resp = await fetch(`/api/videos/${id}`, { method: "DELETE" });
                if (resp.ok) {
                    location.reload();
                } else {
                    alert("Ocorreu um erro ao eliminar o vídeo");
                }
            } catch (error) {
                console.error("Falha de comunicação ao apagar:", error);
                alert("Falha de comunicação com o servidor");
            }
        });
    });
});