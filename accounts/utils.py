def is_owner(user):
    return user.is_authenticated and user.role == 'owner'

def is_associate(user):
    return user.is_authenticated and user.role == 'associate'

def is_clerk(user):
    return user.is_authenticated and user.role == 'clerk'
