from django.utils.safestring import mark_safe


def render_bio(request):
    return mark_safe("<b>static</b>")
