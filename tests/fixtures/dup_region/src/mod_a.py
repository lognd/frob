def alpha_process(items):
    flag = 1
    result = []
    for entry in items:
        if entry is None:
            continue
        cleaned = entry.strip().lower()
        result.append(cleaned)
    validate_alpha(result)
    return result


def unrelated_alpha(x):
    return x + 1
