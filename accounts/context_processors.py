from accounts.models import User

def firm_employees_processor(request):
    """
    Adds firm employees to the context for firm owners to use in the sidebar.
    """
    if request.user.is_authenticated and request.user.role == 'firm_owner' and request.user.firm:
        # Get all users in the same firm (including the owner)
        employees = User.objects.filter(firm=request.user.firm).order_by('role', 'first_name')
        return {
            'sidebar_employees': employees
        }
    return {}
