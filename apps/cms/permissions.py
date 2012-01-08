from django.contrib.auth.models import User, Group
from cms.models import Member, Project, ProjectMember, BlogPost
from django.conf import settings

def is_user_slc_leader(user):
    if user.is_anonymous():
        return False
    else:
        return (user.get_full_name() == settings.SLC_LEADER)

def can_user_create_project(user):
    # only the SLC leader can create projects through the main interface
    return is_user_slc_leader(user)

def can_user_edit_project(user, project):
    # only project coordinators (active/empty projects) and the SLC leader
    # can edit projects through the main interface
    if user.is_anonymous():
        return False

    if is_user_slc_leader(user):
        return True

    try:
        return project.status != Project.STATUS_ARCHIVED and project.is_member_coordinator(user.get_profile())
    except Member.DoesNotExist:
        return False

def can_user_create_member(user):
    # only the SLC leader can create members through the main interface
    return is_user_slc_leader(user)

def can_user_edit_member(user, member):
    # only the user that owns a member profile and the SLC leader can perform edits
    # through the main interface
    return (user == member.user) or is_user_slc_leader(user)

def can_user_post_as_member(user, member):
    # only the user that owns a member profile can post to that member's blog
    return (user == member.user)

def can_user_edit_blogpost(user, blogpost):
    # only blogpost authors and the SLC leader can edit blogposts
    # through the main interface
    return (user == blogpost.author.user) or is_user_slc_leader(user)
