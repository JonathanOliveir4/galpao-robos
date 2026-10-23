import heapq


def astar(inicio, fim, bloqueios, largura, altura):
    """A* em grid 4-vizinhos. Retorna lista de (x, y) de inicio a fim, ou None.
    A célula de destino é sempre permitida (robô 'entra' no slot da prateleira)."""
    def h(p):
        return abs(p[0] - fim[0]) + abs(p[1] - fim[1])

    aberta = [(h(inicio), 0, inicio)]
    g = {inicio: 0}
    veio = {}
    while aberta:
        _, custo, atual = heapq.heappop(aberta)
        if atual == fim:
            caminho = [atual]
            while atual in veio:
                atual = veio[atual]
                caminho.append(atual)
            return caminho[::-1]
        if custo > g.get(atual, float("inf")):
            continue
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            viz = (atual[0] + dx, atual[1] + dy)
            if not (0 <= viz[0] < largura and 0 <= viz[1] < altura):
                continue
            if viz in bloqueios and viz != fim:
                continue
            novo = custo + 1
            if novo < g.get(viz, float("inf")):
                g[viz] = novo
                veio[viz] = atual
                heapq.heappush(aberta, (novo + h(viz), novo, viz))
    return None
