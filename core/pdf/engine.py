from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf(template, context, request=None):
    html = render_to_string(template, context)

    return HTML(
        string=html,
        base_url=request.build_absolute_uri() if request else None
    ).write_pdf()