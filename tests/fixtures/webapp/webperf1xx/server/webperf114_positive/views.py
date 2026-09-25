def list_products(request):
    products = Product.objects.all()
    return render(request, "products.html", {"products": products})
