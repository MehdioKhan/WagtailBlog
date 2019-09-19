from django.db import models
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel,InlinePanel
from wagtail.snippets.models import register_snippet
from wagtail.snippets.edit_handlers import SnippetChooserPanel
from modelcluster.models import ParentalManyToManyField,ParentalKey
from taggit.models import TaggedItemBase, Tag as TaggitTag
from modelcluster.contrib.taggit import ClusterTaggableManager
from wagtail.contrib.routable_page.models import RoutablePageMixin,route
from django.utils.dateformat import DateFormat
from django.utils.formats import date_format
from datetime import date,datetime
from django.http import Http404


class BlogPage(RoutablePageMixin,Page):
    description = models.CharField(max_length=255, blank=True,)

    content_panels = Page.content_panels + [
        FieldPanel('description', classname="full")
    ]

    def get_context(self, request, *args, **kwargs):
        context = super(BlogPage, self).get_context(request, *args, **kwargs)
        context['blog_page'] = self
        context['search_type'] = getattr(self, 'search_type', "")
        context['search_term'] = getattr(self, 'search_term', "")
        return context

    def get_posts(self):
        return PostPage.objects.descendant_of(self).live().order_by('-date')

    @route(r'^(\d{4})/$')
    @route(r'^(\d{4})/(\d{2})/$')
    @route(r'^(\d{4})/(\d{2})/(\d{2})/$')
    def posts_by_date(self,request,year,month=None,day=None,*args,**kwargs):
        self.posts = self.get_posts().filter(date__year=year)
        if month:
            self.posts = self.posts.filter(date__month=month)
            df = DateFormat(date(int(year),int(month),1))
            self.search_term = df.format('F Y')
        if day:
            self.posts = self.posts.filter(date__day=day)
            self.search_term = date_format(date(int(year),int(month),int(day)))
        return Page.serve(self,request,*args,**kwargs)

    @route(r'^(\d{4})/(\d{2})/(\d{2})/(.+)/$')
    def post_by_date_slug(self,request,year,month,day,slug,*args,**kwargs):
        post_page = self.get_posts().filter(slug=slug).first()
        if not post_page:
            raise Http404
        return Page.serve(post_page,request,*args,**kwargs)


class PostPage(Page):
    body = RichTextField(blank=True)
    date = models.DateTimeField(verbose_name="Post date",default=datetime.today)
    tags = ClusterTaggableManager(through='BlogPageTag', blank=True)
    content_panels = Page.content_panels + [
        FieldPanel('body', classname="full"),
        InlinePanel('categories', label='category'),
        FieldPanel('tags'),
    ]
    settings_panels = Page.settings_panels + [
        FieldPanel('date'),
    ]

    @property
    def blog_page(self):
        return self.get_parent().specific

    def get_context(self, request, *args, **kwargs):
        context = super(PostPage, self).get_context(request, *args, **kwargs)
        context['blog_page'] = self.blog_page
        return context


@register_snippet
class BlogCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=80)

    panels = [
        FieldPanel('name'),
        FieldPanel('slug'),
    ]

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"


class PageCategory(models.Model):
    page = ParentalKey('blog.PostPage', on_delete=models.CASCADE, related_name='categories')
    blog_category = models.ForeignKey(
        'blog.BlogCategory', on_delete=models.CASCADE, related_name='blog_pages')

    panels = [
        SnippetChooserPanel('blog_category'),
    ]

    class Meta:
        unique_together = ('page', 'blog_category')


class BlogPageTag(TaggedItemBase):
    content_object = ParentalKey('PostPage', related_name='post_tags')


@register_snippet
class Tag(TaggitTag):
    class Meta:
        proxy = True