from django import template

register = template.Library()


@register.filter(name='has_role')
def has_role(user, roles):
    """
    Usage: {% if request.user|has_role:"system_admin,school_admin,dos" %}
    Returns True if user.role is in the comma-separated roles string.
    Also returns True for superusers so they always see everything.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role_list = [r.strip() for r in roles.split(',')]
    return user.role in role_list


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Usage: {{ my_dict|get_item:some_variable }}
    Allows dictionary lookup using a variable key in templates.
    """
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(key)
