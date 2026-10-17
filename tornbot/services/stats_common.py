def fmt_int(n: int) -> str:
    return f"{n:,}"


def pad_right(s: str, width: int) -> str:
    return s + (" " * max(0, width - len(s)))


def pct_change(delta: int, base: int) -> float:
    if base <= 0:
        return 0.0
    return (delta / base) * 100.0
