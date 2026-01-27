from django import template
from bar.models import BarComanda

register = template.Library()

@register.inclusion_tag('bar/comandas_sidebar.html', takes_context=True)
def comandas_abertas(context):
    """Inclui template com comandas abertas do tenant"""
    user = context.get('user')
    if user and user.is_authenticated and hasattr(user, 'tenant'):
        comandas = BarComanda.objects.filter(
            tenant=user.tenant, 
            status='aberta'
        ).order_by('numero_mesa')
    else:
        comandas = []
    
    return {'comandas': comandas}