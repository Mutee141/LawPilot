def can_manage_case(user, case):
    """Owner can manage all cases, associate only assigned ones"""
    if user.role == 'owner':
        return True

    if user.role == 'associate' and user in case.assigned_lawyers.all():
        return True

    return False


def can_edit_case(user, case):
    """Edit case details"""
    return can_manage_case(user, case)


def can_delete_case(user):
    """Only owner can delete cases"""
    return user.role == 'owner'


def can_manage_hearing(user):
    """Owner, associate, and clerk can manage hearings"""
    return user.role in ['owner', 'associate', 'clerk']
