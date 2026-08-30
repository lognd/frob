#include <cuda_runtime.h>

// Adds two vectors elementwise.
__global__ void vecAdd(float* a, float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        c[i] = addOne(a[i]) + addOne(b[i]);
    }
}

__device__ float addOne(float x) {
    return x + 1.0f;
}

__host__ __device__ int both(int x) {
    return x;
}

static __global__ void staticKernel() {
}

static int hiddenHost() {
    return 0;
}

int visibleHost() {
    return 0;
}

class Widget {
public:
    __device__ void run() {}

private:
    int hidden;
};

int main() {
    return 0;
}
