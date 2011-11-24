from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import simplejson
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseNotAllowed, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.views.generic import View, ListView, DetailView, CreateView, UpdateView, TemplateView

from cms.models import Member, News, Page, Project, ProjectMember, BlogPost, Tag
from cms.forms import MemberForm, ProjectForm, BlogForm, MemberAdminForm, ProjectAdminForm

from cms import signals
from cms import academic_year

import time

slc_leader = User.objects.get(first_name=settings.SLC_LEADER.split(' ')[0], last_name=settings.SLC_LEADER.split(' ')[1])

class JSONResponseMixin(object):
    def get_json_response(self, json, **kwargs):
        return HttpResponse(json, content_type='application/json', **kwargs)

    def convert_to_json(self, context):
        return simplejson.dumps(context)

    def render_to_response(self, context):
        return self.get_json_response(self.convert_to_json(context))

class HomepageView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super(HomepageView, self).get_context_data(**kwargs)
        context['blog_posts'] = BlogPost.objects.all().order_by('-date')[:5]

        return context

class ProfileView(DetailView):
    model = Member
    template_name = 'members/profile.html'
    context_object_name = 'member'

    def get_context_data(self, **kwargs):
        context = super(ProfileView, self).get_context_data(**kwargs)

       # NOTE: "year" is a field lookup type so must use "year__exact" instead
        project_members = ProjectMember.objects.filter(member__pk=self.kwargs.get('pk', None)).order_by('-project__year')
        context['project_groups'] = [ {'year': x, 'project_members': project_members.filter(project__year__exact=x).order_by('project__title') } for x in project_members.values_list('project__year', flat=True).distinct() ]

        context['recent_blogs'] = BlogPost.objects.filter(author__pk=self.kwargs.get('pk', None)).order_by('-date')[:3]

        return context

class EditProfileView(UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'members/edit_profile.html'

    def render_to_response(self, context):
        if self.request.user == context['member'].user or self.request.user == slc_leader:
            return UpdateView.render_to_response(self, context)
        else:
            return HttpResponseForbidden('You do not have permission to edit this profile.')

class MembersView(ListView):
    model = Member
    template_name = 'members/members.html'
    context_object_name = 'members'

    def get_queryset(self):
        # NOTE: "year" is a field lookup type so must use "year__exact" instead
        return Member.objects.filter(pk__in=ProjectMember.objects.filter(project__year__exact=self.kwargs.get('year', settings.CURRENT_YEAR)).distinct().values_list('member')).order_by('user__first_name', 'user__last_name')

    def get_context_data(self, **kwargs):
        context = super(MembersView, self).get_context_data(**kwargs)

        context['year'] = self.kwargs.get('year', settings.CURRENT_YEAR)
        next_year = int(context['year']) + 1
        context['year2'] = next_year

        prev_year = int(context['year']) - 1

        if Project.objects.filter(year=next_year).count() > 0:
            context['next_year'] = next_year
            context['next_year2'] = next_year + 1
        if Project.objects.filter(year=prev_year).count() > 0:
            context['prev_year'] = prev_year
            context['prev_year2'] = prev_year + 1

        return context

    def render_to_response(self, context):
        # check for "year" in kwargs to avoid redirect loop when current year has no data
        if len(context['members']) == 0 and 'year' in self.kwargs:
            return HttpResponseRedirect(reverse('cms:members_url'))
        else:
            return super(MembersView, self).render_to_response(context)

class NewsView(ListView):
    model = News
    template_name = 'news/news.html'
    context_object_name = 'news_list'

class NewsDetailView(DetailView):
    model = News
    template_name = 'news/article.html'
    context_object_name = 'news'

class PageDetailView(DetailView):
    model = Page
    template_name = 'pages/page.html'
    context_object_name = 'page'

class ProjectView(ListView):
    model = Project
    template_name = 'projects/projects.html'
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.filter(year=self.kwargs.get('year', settings.CURRENT_YEAR)).order_by('title')

    def get_context_data(self, **kwargs):
        context = super(ProjectView, self).get_context_data(**kwargs)

        if not self.request.user.is_anonymous():
            try:
                coordinated_project_pks = self.request.user.get_profile().get_coordinated_projects().values_list('pk', flat=True)
            except Member.DoesNotExist:
                coordinated_project_pks = []
        else:
            coordinated_project_pks = []

        for project in context['projects']:
            project.show_edit = (project.pk in coordinated_project_pks)

        context['year'] = self.kwargs.get('year', settings.CURRENT_YEAR)
        next_year = int(context['year']) + 1
        context['year2'] = next_year
        prev_year = int(context['year']) - 1

        if Project.objects.filter(year=next_year).count() > 0:
            context['next_year'] = next_year
            context['next_year2'] = next_year + 1
        if Project.objects.filter(year=prev_year).count() > 0:
            context['prev_year'] = prev_year
            context['prev_year2'] = prev_year + 1

        return context

    def render_to_response(self, context):
        # check for "year" in kwargs to avoid redirect loop when current year has no data
        if len(context['projects']) == 0 and 'year' in self.kwargs:
            return HttpResponseRedirect(reverse('cms:projects_url'))
        else:
            return super(ProjectView, self).render_to_response(context)

class EditProjectView(UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/edit_project.html'

    def render_to_response(self, context):
        is_coordinator = context['project'].is_member_coordinator(self.request.user.get_profile())

        if not self.request.user.is_anonymous() and (is_coordinator or self.request.user == slc_leader):
            return UpdateView.render_to_response(self, context)
        else:
            return HttpResponseForbidden('You do not have permission to edit this project.')

class BlogsYearView(ListView):
    model = BlogPost
    template_name = 'blogs/blogs_year.html'
    context_object_name = 'blog_posts'
    paginate_by = 25

    def get_queryset(self):
        return BlogPost.objects.by_academic_year(self.kwargs.get('year', settings.CURRENT_YEAR)).order_by('date')

    def get_context_data(self, **kwargs):
        context = super(BlogsYearView, self).get_context_data(**kwargs)

        context['year'] = int(self.kwargs.get('year', settings.CURRENT_YEAR))
        next_year = context['year'] + 1
        context['year2'] = next_year
        prev_year = context['year'] - 1

        context['months'] = context['blog_posts'].dates('date', 'month', 'ASC')

        if BlogPost.objects.by_academic_year(next_year).count() > 0:
            context['next_year'] = next_year
            context['next_year2'] = next_year + 1
        if BlogPost.objects.by_academic_year(prev_year).count() > 0:
            context['prev_year'] = prev_year
            context['prev_year2'] = prev_year + 1

        return context

    def render_to_response(self, context):
        # check for "year" in kwargs to avoid redirect loop when current year has no data
        if len(context['blog_posts']) == 0 and 'year' in self.kwargs:
            return HttpResponseRedirect(reverse('cms:blogs_url'))
        else:
            return super(BlogsYearView, self).render_to_response(context)

class BlogsMonthView(ListView):
    model = BlogPost
    template_name = 'blogs/blogs_month.html'
    context_object_name = 'blog_posts'
    paginate_by = 25

    def get_queryset(self):
        return BlogPost.objects.filter(date__year=self.kwargs.get('year', settings.CURRENT_YEAR)).filter(date__month=self.kwargs.get('month', time.localtime().tm_mon)).order_by('date')

    def get_context_data(self, **kwargs):
        context = super(BlogsMonthView, self).get_context_data(**kwargs)

        year = int(self.kwargs.get('year', settings.CURRENT_YEAR))
        month = int(self.kwargs.get('month', time.localtime().tm_mon))

        context['year'] = year
        context['month'] = month

        context['next_month'] = (month + 0) % 12 + 1
        context['prev_month'] = (month - 2) % 12 + 1

        context['next_year'] = [ year, year + 1 ][month == 12]
        context['prev_year'] = [ year, year - 1 ][month == 1]

        return context

class BlogView(ListView):
    template_name = 'blogs/blogs.html'
    context_object_name = 'blog_posts'

    def get_queryset(self):
        return BlogPost.objects.filter(author__pk=self.kwargs.get('pk', None))

    def get_context_data(self, **kwargs):
        context = super(BlogView, self).get_context_data(**kwargs)
        context['member'] = Member.objects.get(pk=self.kwargs.get('pk', None))

        return context

    def render_to_response(self, context):
        return ListView.render_to_response(self, context)

class BlogPostView(DetailView):
    model = BlogPost
    template_name = 'blogs/blog_post.html'

    def get_context_data(self, **kwargs):
        context = super(BlogPostView, self).get_context_data(**kwargs)
        context['member'] = Member.objects.get(pk=self.kwargs.get('pk', None))
        context['blog'] = BlogPost.objects.get(pk=self.kwargs.get('blog_pk', None), author__pk=context['member'].pk)

        return context

class AddBlogView(CreateView):
    model = BlogPost
    form_class = BlogForm
    template_name = 'blogs/add_blog.html'
    object = None

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk', None)
        
        if pk is not None:
            member = Member.objects.get(pk=pk)
        else:
            return Http404('Could not locate specified user')

        form = BlogForm(request.POST)

        if form.is_valid():
            self.object = form.save(commit=False)
            self.object.author = member
            self.object.save()
            form.save_m2m()
            return HttpResponseRedirect(self.object.get_absolute_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def render_to_response(self, context):
        pk = self.kwargs.get('pk', None)

        if pk is not None:
            if self.request.user != Member.objects.get(pk=pk).user:
                return HttpResponseForbidden('You do not have permission to post as that user.')
            else:
                return CreateView.render_to_response(self, context)
        else:
            return Http404('Could not located specified user')

class EditBlogView(UpdateView):
    model = BlogPost
    form_class = BlogForm
    template_name = 'blogs/edit_blog.html'

    def get_object(self, **kwargs):
        pk = self.kwargs.get('blog_pk', None)
        return BlogPost.objects.get(pk=self.kwargs.get('blog_pk', None), author__pk=self.kwargs.get('pk', None))

    def get_context_data(self, **kwargs):
        context = super(EditBlogView, self).get_context_data(**kwargs)
        context['member'] = Member.objects.get(pk=self.kwargs.get('pk', None))
        context['blog'] = BlogPost.objects.get(pk=self.kwargs.get('blog_pk', None), author__pk=context['member'].pk)
        return context

    def render_to_response(self, context):
        if self.request.user == context['member'].user or self.request.user == slc_leader:
            return UpdateView.render_to_response(self, context)
        else:
            return HttpResponseForbidden('You do not have permission to edit this blog post.')

class TagCloudView(JSONResponseMixin, View):
    def post(self, request, *args, **kwargs):
        tag_name = request.POST['tag']
        blog_post = BlogPost.objects.get(pk=request.POST['blog_id'], author__pk=request.POST['member_id'])
        tag = Tag.objects.get_or_create(name=tag_name)

        return HttpResponse()

    def get(self, request, *args, **kwargs):
        tags = Tag.objects.all()
        response = {}

        for tag in tags:
            response[tag.name] = BlogPost.objects.filter(tags__name=tag.name).count()

        return JSONResponseMixin.render_to_response(self, response)

class CreateProjectView(CreateView):
    model = Project
    form_class = ProjectAdminForm
    template_name = 'projects/create.html'
    #slc_leader = User.objects.get(first_name=settings.SLC_LEADER.split(' ')[0], last_name=settings.SLC_LEADER.split(' ')[1])

    def get_context_data(self, **kwargs):
        return kwargs
    
    def render_to_response(self, context):
        if self.request.user == slc_leader:
            return CreateView.render_to_response(self, context)
        else:
            return HttpResponseForbidden('You do not have permission to access this page')
    
    def post(self, request, *args, **kwargs):
        if request.user == slc_leader:
            form = ProjectAdminForm(request.POST)

            if form.is_valid():
                project = form.save(commit=False)
                project.year = settings.CURRENT_YEAR
                project.status = 0 # Empty, so a coordinator can fill out the project information
                project.save()

                signals.assign_coordinators.send(sender=None, project=project, members=form.cleaned_data['coordinators'])

                return HttpResponseRedirect(reverse('cms:projects_url'))
            else:
                self.render_to_response(self.get_context_data(form=form))
        else:
            return HttpResponseForbidden('You do not have permission to access this page')

class CreateMemberView(CreateView):
    model = Member
    form_class = MemberAdminForm
    template_name = 'members/create.html'
    #slc_leader = User.objects.get(first_name=settings.SLC_LEADER.split(' ')[0], last_name=settings.SLC_LEADER.split(' ')[1])
    
    def get_context_data(self, **kwargs):
        return kwargs
    
    def render_to_response(self, context):
        if self.request.user == slc_leader:
            return CreateView.render_to_response(self, context)
        else:
            return HttpResponseForbidden('You do not have permission to access this page')
    
    def post(self, request, *args, **kwargs):
        if request.user == slc_leader:
            form = MemberAdminForm(request.POST)
            
            if form.is_valid():
                unity_id = request.POST['unity_id']
                email = request.POST['email']
                first_name = request.POST['first_name']
                last_name = request.POST['last_name']
                group = request.POST['group']
                classification = request.POST['classification']
                
                user = User.objects.create(username=unity_id, email=email, first_name=first_name, last_name=last_name)
                member, project_member = signals.create_profile.send(sender=None, user=user, group=group, classification=classification)

                return HttpResponseRedirect(reverse('cms:members_url'))
            else:
                self.render_to_response(self.get_context_data(form=form))
        else:
            return HttpResponseForbidden('You do not have permission to access this page')

class ActivateMemberView(UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'members/activate.html'
    
    def get_object(self, queryset):
        pass

    def post(self, request, *args, **kwargs):
        pass
    
    def render_to_response(self, context):
        return TemplateView.render_to_response(self, context)




