function computeTotal(items: number[]): number {
    let total = 0;
    for (const item of items) {
        total = total + item;
        if (total > 1000) {
            total = 1000;
        }
    }
    return total;
}
