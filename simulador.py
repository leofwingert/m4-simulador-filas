import heapq

# =============================================================================
#  Gerador de números pseudoaleatórios (LCG) — mesmo do módulo 4
# =============================================================================
LCG_A = 1664525
LCG_C = 1013904223
LCG_M = 2 ** 32

seed  = 1
count = 0


def next_random():
    """Gera o próximo número pseudoaleatório no intervalo [0, 1)."""
    global seed, count
    seed   = (LCG_A * seed + LCG_C) % LCG_M
    count -= 1
    return seed / LCG_M


def uniform(low, high):
    """Retorna um valor uniforme no intervalo [low, high)."""
    return low + next_random() * (high - low)


# =============================================================================
#  Classe Evento
# =============================================================================
class Evento:
    """
    Representa um evento na simulação.
    Tipos: CHEGADA, PASSAGEM, SAIDA.
    """
    CHEGADA  = "CHEGADA"
    PASSAGEM = "PASSAGEM"
    SAIDA    = "SAIDA"

    def __init__(self, tipo, tempo, fila_origem=None, fila_destino=None):
        self.tipo         = tipo
        self.tempo        = tempo
        self.fila_origem  = fila_origem   # índice da fila de origem
        self.fila_destino = fila_destino  # índice da fila de destino

    def __lt__(self, other):
        """Necessário para o heapq ordenar por tempo."""
        return self.tempo < other.tempo

    def __repr__(self):
        return (f"Evento({self.tipo}, t={self.tempo:.4f}, "
                f"orig={self.fila_origem}, dest={self.fila_destino})")


# =============================================================================
#  Classe Escalonador
# =============================================================================
class Escalonador:
    """Fila de prioridade de eventos, ordenada pelo tempo."""

    def __init__(self):
        self._heap = []

    def adicionar(self, evento):
        heapq.heappush(self._heap, evento)

    def proximo(self):
        return heapq.heappop(self._heap)

    def vazio(self):
        return len(self._heap) == 0

    def __len__(self):
        return len(self._heap)


# =============================================================================
#  Classe Fila
# =============================================================================
class Fila:
    """
    Representa uma fila G/G/s/K.
    Propriedades:
        - nome, servidores (s), capacidade (K)
        - atend_min, atend_max: intervalo de atendimento U(a,b)
        - chegada_min, chegada_max: intervalo de chegada U(a,b) (None se não há chegada externa)
        - estado: número de clientes atualmente na fila
        - perdas: clientes que não entraram por fila cheia
        - tempo_acumulado: tempo acumulado em cada estado
    """

    def __init__(self, nome, servidores, capacidade, atend_min, atend_max,
                 chegada_min=None, chegada_max=None):
        self.nome         = nome
        self.servidores   = servidores
        self.capacidade   = capacidade
        self.atend_min    = atend_min
        self.atend_max    = atend_max
        self.chegada_min  = chegada_min
        self.chegada_max  = chegada_max

        self.estado          = 0
        self.perdas          = 0
        self.tempo_acumulado = [0.0] * (capacidade + 1)

    # ---------- métodos auxiliares ----------
    def tem_chegada_externa(self):
        return self.chegada_min is not None

    def esta_cheia(self):
        return self.estado >= self.capacidade

    def esta_vazia(self):
        return self.estado == 0

    def in_(self):
        self.estado += 1

    def out(self):
        self.estado -= 1


# =============================================================================
#  Funções de simulação
# =============================================================================

def acumula_tempo(filas, delta):
    """Acumula delta de tempo no estado atual de TODAS as filas."""
    for fila in filas:
        fila.tempo_acumulado[fila.estado] += delta


def determinar_destino(routing, indice_fila):
    """
    Dado o roteamento e o índice da fila de origem, sorteia a fila
    de destino com base nas probabilidades.
    Retorna o índice da fila destino ou None (cliente sai do sistema).
    """
    rotas = routing.get(indice_fila, [])
    if not rotas:
        return None

    # Se há um único destino com 100% de probabilidade, não consome aleatório
    if len(rotas) == 1 and rotas[0][1] >= 1.0:
        return rotas[0][0]

    # Sorteia o destino com base nas probabilidades
    r = next_random()
    acumulado = 0.0
    for destino, prob in rotas:
        acumulado += prob
        if r < acumulado:
            return destino
    # Segurança: retorna o último destino em caso de arredondamento
    return rotas[-1][0]


def agendar_saida_ou_passagem(escalonador, filas, routing, indice_fila, tempo_atual):
    """
    Agenda o evento correto (PASSAGEM ou SAIDA) para um cliente que
    começa a ser atendido na fila indicada.
    Consome um número aleatório para o tempo de atendimento.
    """
    global count
    if count <= 0:
        return

    fila = filas[indice_fila]
    tempo_atend = uniform(fila.atend_min, fila.atend_max)
    tempo_evento = tempo_atual + tempo_atend

    rotas = routing.get(indice_fila, [])
    if rotas:
        # Há fila(s) de destino → evento PASSAGEM
        # O destino será determinado no momento do evento
        escalonador.adicionar(Evento(
            Evento.PASSAGEM, tempo_evento,
            fila_origem=indice_fila, fila_destino=None  # destino resolvido no despacho
        ))
    else:
        # Sem destino → cliente sai do sistema → evento SAIDA
        escalonador.adicionar(Evento(
            Evento.SAIDA, tempo_evento,
            fila_origem=indice_fila
        ))


# =============================================================================
#  Tratadores de eventos
# =============================================================================

def tratar_chegada(evento, escalonador, filas, routing):
    """Trata evento de CHEGADA de cliente do exterior na fila."""
    global count
    idx  = evento.fila_destino
    fila = filas[idx]

    # Tenta inserir na fila
    if not fila.esta_cheia():
        fila.in_()
        if fila.estado <= fila.servidores:
            # Servidor livre → inicia atendimento (consome aleatório p/ atendimento)
            agendar_saida_ou_passagem(escalonador, filas, routing, idx, evento.tempo)
    else:
        fila.perdas += 1

    # Agenda próxima chegada (consome aleatório p/ entre-chegadas)
    if count > 0 and fila.tem_chegada_externa():
        tempo_prox = evento.tempo + uniform(fila.chegada_min, fila.chegada_max)
        escalonador.adicionar(Evento(
            Evento.CHEGADA, tempo_prox,
            fila_destino=idx
        ))


def tratar_passagem(evento, escalonador, filas, routing):
    """Trata evento de PASSAGEM: cliente sai da fila de origem e tenta entrar na fila de destino."""
    global count
    idx_orig = evento.fila_origem

    fila_orig = filas[idx_orig]

    # Determina o destino
    idx_dest = determinar_destino(routing, idx_orig)

    # Saída da fila de origem
    fila_orig.out()
    if fila_orig.estado >= fila_orig.servidores:
        # Ainda há clientes esperando → agenda novo atendimento
        agendar_saida_ou_passagem(escalonador, filas, routing, idx_orig, evento.tempo)

    if idx_dest is None:
        # Destino indeterminado (não deveria acontecer se routing está correto)
        return

    fila_dest = filas[idx_dest]

    # Tenta inserir na fila de destino
    if not fila_dest.esta_cheia():
        fila_dest.in_()
        if fila_dest.estado <= fila_dest.servidores:
            # Servidor livre na fila destino → inicia atendimento
            agendar_saida_ou_passagem(escalonador, filas, routing, idx_dest, evento.tempo)
    else:
        fila_dest.perdas += 1


def tratar_saida(evento, escalonador, filas, routing):
    """Trata evento de SAIDA: cliente sai do sistema."""
    global count
    idx  = evento.fila_origem
    fila = filas[idx]

    fila.out()
    if fila.estado >= fila.servidores:
        # Ainda há clientes esperando → agenda novo atendimento
        agendar_saida_ou_passagem(escalonador, filas, routing, idx, evento.tempo)


# =============================================================================
#  Loop principal da simulação
# =============================================================================

def simular(filas, routing, initial_seed=1, total_randoms=100_000, first_arrival_time=2.5):
    """
    Executa a simulação de uma rede de filas.

    Parâmetros:
        filas           : lista de objetos Fila
        routing         : dict {indice_fila: [(indice_destino, probabilidade), ...]}
        initial_seed    : semente do LCG
        total_randoms   : número total de aleatórios a consumir
        first_arrival_time : tempo da primeira chegada
    """
    global seed, count
    seed  = initial_seed
    count = total_randoms

    escalonador = Escalonador()
    last_time   = 0.0

    # Agenda a primeira chegada em cada fila que possui entrada externa
    for i, fila in enumerate(filas):
        if fila.tem_chegada_externa():
            escalonador.adicionar(Evento(
                Evento.CHEGADA, first_arrival_time,
                fila_destino=i
            ))

    # Loop de simulação
    while count > 0 and not escalonador.vazio():
        evento = escalonador.proximo()

        # Acumula tempo em TODAS as filas
        delta = evento.tempo - last_time
        acumula_tempo(filas, delta)
        last_time = evento.tempo

        # Despacha o evento
        if evento.tipo == Evento.CHEGADA:
            tratar_chegada(evento, escalonador, filas, routing)
        elif evento.tipo == Evento.PASSAGEM:
            tratar_passagem(evento, escalonador, filas, routing)
        elif evento.tipo == Evento.SAIDA:
            tratar_saida(evento, escalonador, filas, routing)

    return last_time  # tempo global


# =============================================================================
#  Impressão de resultados
# =============================================================================

def imprimir_resultados(filas, tempo_global):
    """Imprime tabelas de resultados para todas as filas."""
    for fila in filas:
        print(f"\n{'='*62}")
        print(f"  {fila.nome}")
        print(f"{'='*62}")
        print(f"  {'Estado':>6}  {'Tempo Acumulado':>18}  {'Probabilidade':>14}")
        print(f"  {'-'*50}")

        soma_prob = 0.0
        for estado in range(fila.capacidade + 1):
            t = fila.tempo_acumulado[estado]
            p = t / tempo_global if tempo_global > 0 else 0
            soma_prob += p
            print(f"  {estado:>6}  {t:>18.4f}s  {p:>13.6f}")

        print(f"  {'-'*50}")
        print(f"  {'TOTAL':>6}  {tempo_global:>18.4f}s  {soma_prob:>13.6f}")
        print(f"\n  Perdas: {fila.perdas}")

    print(f"\n{'='*62}")
    print(f"  Tempo global da simulação: {tempo_global:.4f} s")
    print(f"{'='*62}")


# =============================================================================
#  Configuração e execução
# =============================================================================

if __name__ == "__main__":
    # -------------------------------------------------------------------------
    #  Parâmetros da simulação
    # -------------------------------------------------------------------------
    SEED           = 1
    TOTAL_RANDOM   = 100_000
    FIRST_ARRIVAL  = 2.5

    # -------------------------------------------------------------------------
    #  Definição das filas
    # -------------------------------------------------------------------------
    #  Fila 1: G/G/2/3 — chegadas U(1,5), atendimento U(4,5)
    #  Fila 2: G/G/1/5 — sem chegada externa, atendimento U(1,3)
    # -------------------------------------------------------------------------
    fila1 = Fila(
        nome="Fila 1 — G/G/2/3  |  Chegadas U(1,5)  |  Atend. U(4,5)",
        servidores=2,
        capacidade=3,
        atend_min=4.0,
        atend_max=5.0,
        chegada_min=1.0,
        chegada_max=5.0,
    )

    fila2 = Fila(
        nome="Fila 2 — G/G/1/5  |  Sem chegada ext.  |  Atend. U(1,3)",
        servidores=1,
        capacidade=5,
        atend_min=1.0,
        atend_max=3.0,
    )

    filas = [fila1, fila2]

    # -------------------------------------------------------------------------
    #  Roteamento (matriz de probabilidades)
    # -------------------------------------------------------------------------
    #  Fila 0 (Fila 1) → 100% para Fila 1 (Fila 2)
    #  Fila 1 (Fila 2) → sai do sistema (lista vazia)
    # -------------------------------------------------------------------------
    routing = {
        0: [(1, 1.0)],  # 100% de F1 → F2
        1: [],           # F2 → saída do sistema
    }

    # -------------------------------------------------------------------------
    #  Execução
    # -------------------------------------------------------------------------
    tempo_global = simular(
        filas=filas,
        routing=routing,
        initial_seed=SEED,
        total_randoms=TOTAL_RANDOM,
        first_arrival_time=FIRST_ARRIVAL,
    )

    imprimir_resultados(filas, tempo_global)
