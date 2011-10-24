from django.db import models
from django.conf import settings
from django.db.models import signals
from django.contrib.auth.models import User
import django.contrib.localflavor.us.us_states as states

class Project(models.Model):
    title           = models.CharField(max_length=255)
    description     = models.TextField()
    coordinator     = models.ForeignKey('Member')
    image           = models.ImageField(upload_to='project_images')
<<<<<<< HEAD
    coordinator     = models.ForeignKey('Member', related_name='project')
    year            = models.IntegerField()
    active          = models.BooleanField(default=False)
=======
    active          = models.BooleanField(default=False)
    year            = models.IntegerField()
>>>>>>> e57ed0568e4865aa02e26f83729c3459bac8abfa

    def __unicode__(self):
        return unicode(self.title)
    
    @models.permalink
    def get_absolute_url(self):
        return ('website:project_url', (), {})

    class Meta:
        verbose_name        = 'project'
        verbose_name_plural = 'projects'

class Member(models.Model):
    GROUP_CHOICES = (
        (u'graduate', u'Graduate'),
        (u'undergraduate', u'Undergraduate'),
        (u'faculty', u'Faculty')
    )

    CLASS_CHOICES = (
        (u'freshman', u'Freshman'),
        (u'sophomore', u'Sophomore'),
        (u'junior', u'Junior'),
        (u'senior', u'Senior')
    )

    user            = models.ForeignKey(User, related_name='profile', unique=True)
    group           = models.CharField(max_length=255, choices=GROUP_CHOICES)
    classification  = models.CharField(max_length=255, choices=CLASS_CHOICES, blank=True)
    city            = models.CharField(max_length=255)
    state           = models.CharField(max_length=2, choices=states.US_STATES)
    interests       = models.TextField(blank=True)
    homepage        = models.URLField(verify_exists=False, blank=True)
    blurb           = models.TextField(blank=True)
    image           = models.ImageField(upload_to='user_images', blank=True)

    def __unicode__(self):
        return unicode(self.user.get_full_name())
    
    @models.permalink
    def get_absolute_url(self):
        return ('website:profile_url', (self.pk,), {})

    class Meta:
        verbose_name        = 'member'
        verbose_name_plural = 'members'
        ordering            = ['user__last_name']

class ProjectMember(models.Model):
    project         = models.ForeignKey(Project, related_name='project_member')
    member          = models.ForeignKey(Member)

class ProjectCordinator(models.Model):
    project         = models.ManyToManyField(Project, related_name='project_coordinators')
    member          = models.ForeignKey(Member)

class ProjectVolunteer(models.Model):
    project         = models.ForeignKey(Project)

class News(models.Model):
    title           = models.CharField(max_length=255)
    description     = models.TextField(max_length=200)
    content         = models.TextField()
    date            = models.DateTimeField()
    slug            = models.SlugField(max_length=100)

    def __unicode__(self):
        return unicode(self.title)

    class Meta:
        verbose_name        = 'news'
        verbose_name_plural = 'news'

class Page(models.Model):
    title           = models.CharField(max_length=255)
    content         = models.TextField()
    slug            = models.SlugField(max_length=100)
    pub_front_page  = models.BooleanField(default=False)
    pub_menu        = models.BooleanField(default=False)

    def __unicode__(self):
        return unicode(self.title)
        
class Tag(models.Model):
    name            = models.CharField(max_length=255)

    def __unicode__(self):
        return unicode(self.name)

class BlogPost(models.Model):
    author          = models.ForeignKey(Member)
    title           = models.CharField(max_length=255)
    date            = models.DateTimeField()
    post            = models.TextField()
    tags            = models.ManyToManyField(Tag, blank=True, related_name='blogpost')

    @models.permalink
    def get_absolute_url(self):
        return ('website:blog_post_url', (), {'pk': self.author.pk, 'blog_pk': self.pk})
    
    def __unicode__(self):
        return unicode('%s by %s' % (self.title, self.author))

    class Meta:
        verbose_name        = 'blog post'
        verbose_name_plural = 'blog posts'
        ordering            = ['-date']
