import heapq

LCG_A = 1664525
LCG_C = 1013904223
LCG_M = 2 ** 32

seed  = 1
count = 0

CHEGADA = 0
SAIDA   = 1


def next_random():
    global seed, count
    seed   = (LCG_A * seed + LCG_C) % LCG_M
    count -= 1
    return seed / LCG_M


def uniform(low, high):
    return low + next_random() * (high - low)


def simulate(servers, capacity, arrival_min, arrival_max, service_min, service_max,
             initial_seed=1, total_randoms=100_000, first_arrival=3.0):
    global seed, count
    seed  = initial_seed
    count = total_randoms

    queue_state  = 0
    current_time = 0.0
    losses       = 0
    accumulated  = [0.0] * (capacity + 1)
    last_time    = 0.0
    scheduler    = []

    heapq.heappush(scheduler, (first_arrival, CHEGADA))

    while count > 0 and scheduler:
        event_time, event_type = heapq.heappop(scheduler)

        accumulated[queue_state] += event_time - last_time
        last_time    = event_time
        current_time = event_time

        if event_type == CHEGADA:
            if count > 0:
                heapq.heappush(scheduler, (current_time + uniform(arrival_min, arrival_max), CHEGADA))

            if queue_state < capacity:
                queue_state += 1
                if queue_state <= servers and count > 0:
                    heapq.heappush(scheduler, (current_time + uniform(service_min, service_max), SAIDA))
            else:
                losses += 1

        else:
            queue_state -= 1
            if queue_state >= servers and count > 0:
                heapq.heappush(scheduler, (current_time + uniform(service_min, service_max), SAIDA))

    global_time   = current_time
    probabilities = [t / global_time for t in accumulated]

    return accumulated, probabilities, losses, global_time


def print_results(label, accumulated, probabilities, losses, global_time):
    print(f"\n{'='*62}")
    print(f"  {label}")
    print(f"{'='*62}")
    print(f"  {'Estado':>6}  {'Tempo Acumulado':>18}  {'Probabilidade':>14}")
    print(f"  {'-'*50}")
    for i, (t, p) in enumerate(zip(accumulated, probabilities)):
        print(f"  {i:>6}  {t:>18.4f}s  {p:>13.6f}")
    print(f"  {'-'*50}")
    print(f"  {'TOTAL':>6}  {global_time:>18.4f}s  {sum(probabilities):>13.6f}")
    print(f"\n  Tempo global : {global_time:.4f} s")
    print(f"  Perdas       : {losses}")


if __name__ == "__main__":
    SEED          = 1
    TOTAL         = 100_000
    ARR_MIN       = 3.0
    ARR_MAX       = 5.0
    SVC_MIN       = 4.0
    SVC_MAX       = 5.0

    args = dict(arrival_min=ARR_MIN, arrival_max=ARR_MAX,
                service_min=SVC_MIN, service_max=SVC_MAX,
                initial_seed=SEED, total_randoms=TOTAL)

    print_results("G/G/1/5  |  U(3,5) chegadas  |  U(4,5) atendimento",
                  *simulate(servers=1, capacity=5, **args))

    print_results("G/G/2/5  |  U(3,5) chegadas  |  U(4,5) atendimento",
                  *simulate(servers=2, capacity=5, **args))
