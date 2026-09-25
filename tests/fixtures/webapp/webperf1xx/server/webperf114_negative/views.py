from django.views.decorators.cache import cache_page


@cache_page(60 * 15)
def list_products(request):
    products = Product.objects.all()
    return render(request, "products.html", {"products": products})
